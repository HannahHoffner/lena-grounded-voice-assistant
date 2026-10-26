"""Geschlossener Antwortplan: Fakten auswählen, nie Modellprosa ausliefern.

Die Prüfung kennt nur das Evidence-Paket. Wortwahl, Syntax und selbst erklärte
Claimtypen dienen nicht als Wahrheitsnachweis. Historische Freitextverträge
werden hier nicht akzeptiert.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_validator

from .answer_act_texts import act_text, enum_text, source_text
from .answer_sentences import ANSWER_RENDERER_VERSION, display_value, fact_sentences
from .application_texts import application_text
from .formulation import (
    AnswerType, BindingPolicy, FactId, FactType, PLAN_FORMULATOR_CONTRACT_VERSION as FORMULATOR_CONTRACT_VERSION,
    PLAN_FORMULATOR_SYSTEM_PROMPT as FORMULATOR_SYSTEM_PROMPT, FormulatorError, FormulatorEvidence, GroundingDiagnosticCode, OfferId, StrictModel,
)
from .models import Language


class AnswerAct(StrictModel):
    act: Literal["facts", "contact", "unknown", "boundary"]
    offer_id: OfferId | None = None
    fact_ids: list[FactId] = Field(default_factory=list, max_length=6)
    reason: Literal["fee", "hours", "access", "availability", "detail"] | None = None
    policy_ids: list[BindingPolicy] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def coherent_act(self) -> "AnswerAct":
        if len(self.fact_ids) != len(set(self.fact_ids)) or len(self.policy_ids) != len(set(self.policy_ids)):
            raise ValueError("duplicate reference")
        if self.act == "boundary":
            if self.offer_id is not None or self.fact_ids or self.reason or not self.policy_ids:
                raise ValueError("boundary requires only policies")
        elif self.offer_id is None or self.policy_ids:
            raise ValueError("offer act requires offer binding and no policies")
        elif self.act == "facts":
            if not self.fact_ids or self.reason:
                raise ValueError("facts act requires only fact references")
        elif self.act == "unknown":
            if self.fact_ids or not self.reason:
                raise ValueError("unknown act requires a reason and no fact claims")
        elif self.fact_ids or self.reason:
            raise ValueError("contact act takes no extra claims")
        return self


class FormulatorPlan(StrictModel):
    contract_version: Literal[FORMULATOR_CONTRACT_VERSION]
    language: Language
    sentences: list[AnswerAct] = Field(min_length=1, max_length=3)
    card_ids: list[OfferId] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def unique_cards(self) -> "FormulatorPlan":
        if len(self.card_ids) != len(set(self.card_ids)):
            raise ValueError("duplicate card")
        return self


def formulator_plan_prompt() -> str:
    """Expose the actual wire schema; keep prose and parser field names aligned."""
    return FORMULATOR_SYSTEM_PROMPT + "\nResponse JSON Schema:\n" + json.dumps(
        FormulatorPlan.model_json_schema(), ensure_ascii=False, separators=(",", ":"),
    )


_INTERNAL_TYPES = {FactType.DISPLAY_NAME, FactType.ALIAS, FactType.CAPABILITY,
                   FactType.OFFER_TYPE, FactType.PLACE_TYPE}
_RESTRICTIONS = {FactType.TARGET_GROUP, FactType.MINIMUM_AGE, FactType.MAXIMUM_AGE,
                 FactType.ELIGIBLE_GENDER, FactType.ACCESS, FactType.SERVICE_CONDITION, FactType.NOTE}
_CONDITION_SENSITIVE = {FactType.SERVICE, FactType.DESCRIPTION, FactType.FACILITY,
                        FactType.FEE, FactType.FEE_STATUS, FactType.NOTE}
_ENUM_TYPES = {FactType.TARGET_GROUP, FactType.ELIGIBLE_GENDER, FactType.ACCESS,
               FactType.FEE_STATUS}


def planner_evidence_payload(evidence: FormulatorEvidence) -> dict:
    """Offer only renderable references; selection metadata is not answer text.

    The original packet remains the validator's authority. Display names and
    candidate roles are already explicit fields; no source fact is rewritten.
    """
    payload = evidence.model_dump(mode="json")
    for offer in payload["selected_offers"]:
        offer["facts"] = [fact for fact in offer["facts"] if fact["fact_type"] not in _INTERNAL_TYPES]
    return payload


def _invalid(diagnostic=GroundingDiagnosticCode.CONTENT_NOT_COVERED):
    return FormulatorError("formulator_ungrounded_claim", diagnostic_code=diagnostic)


def _unknown(offer, reason: str, language: Language) -> str:
    kinds = {fact.fact_type for fact in offer.facts}
    known_fee = any(f.fact_type == FactType.FEE or
                    (f.fact_type == FactType.FEE_STATUS and f.value in {"free", "paid"})
                    for f in offer.facts)
    if reason == "fee" and known_fee:
        raise _invalid(GroundingDiagnosticCode.FEE_CLAIM_UNSUPPORTED)
    if reason == "hours" and kinds & {FactType.OPENING_TIME, FactType.STAND_TIME, FactType.SERVICE_CONDITION}:
        raise _invalid(GroundingDiagnosticCode.TIME_NOT_CITED)
    if reason == "access" and kinds & (_RESTRICTIONS - {FactType.NOTE, FactType.SERVICE_CONDITION}):
        raise _invalid(GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED)
    return act_text("unknown_" + reason, language, name=offer.display_name)


def _fact_value(fact, language: Language) -> str:
    if fact.fact_type in _INTERNAL_TYPES:
        raise FormulatorError("formulator_invalid_fact")
    value = source_text(fact.fact_type.value, fact.value, language)
    if fact.fact_type in _ENUM_TYPES:
        try:
            value = enum_text(value, language)
        except KeyError as exc:
            # Unknown curation enum must not leak as an unexplained code.
            raise FormulatorError("formulator_invalid_fact") from exc
    elif fact.fact_type == FactType.OPERATION_STATUS and value == "unknown":
        value = enum_text(value, language)
    elif fact.fact_type == FactType.AIR_DISTANCE and fact.value.endswith(" m Entfernung vom Leipzig Hauptbahnhof"):
        number = fact.value.split(" ", 1)[0]
        if not number.isdigit():
            raise FormulatorError("formulator_invalid_fact")
        value = number + " m"
    if not display_value(value):
        raise FormulatorError("formulator_invalid_fact")
    return value


def _render_facts(offer, act: AnswerAct, language: Language) -> tuple[str, list[str]]:
    by_id = {fact.fact_id: fact for fact in offer.facts}
    if any(key not in by_id for key in act.fact_ids):
        raise FormulatorError("formulator_invalid_fact")
    facts = [by_id[key] for key in act.fact_ids if by_id[key].fact_type not in {FactType.DISPLAY_NAME, FactType.ALIAS}]
    if not facts:
        raise FormulatorError("formulator_invalid_fact")
    if any(f.fact_type in _CONDITION_SENSITIVE for f in facts):
        # Conditions are data, not optional stylistic material for the model.
        facts.extend(f for f in offer.facts if f.fact_type in _RESTRICTIONS and f.fact_id not in act.fact_ids)
    elif any(f.fact_type in {FactType.OPENING_TIME, FactType.STAND_TIME} for f in facts):
        # An exact opening/stop time does not assert personal eligibility.
        # Keep service-specific windows alongside it, without unrelated prose.
        facts.extend(f for f in offer.facts if f.fact_type == FactType.SERVICE_CONDITION and f.fact_id not in act.fact_ids)
    text = fact_sentences(offer.display_name,
                          [(fact.fact_type.value, _fact_value(fact, language)) for fact in facts], language)
    if offer.candidate_role == "referral_contact":
        text = act_text("referral", language, name=offer.display_name) + " " + text
    return text, [fact.fact_id for fact in facts]


def _fit_facts(offer, act: AnswerAct, language: Language, budget: int, compact: str) -> tuple[str, list[str]]:
    """Keep whole facts with all their conditions, in the planner's priority order.

    Called only after the complete act has passed validation. Even omitted
    content must never conceal an invalid reference or an internal fact type.
    """
    chosen = []
    text, emitted = compact, []
    by_id = {fact.fact_id: fact for fact in offer.facts}
    for key in act.fact_ids:
        if by_id[key].fact_type in {FactType.DISPLAY_NAME, FactType.ALIAS}:
            continue
        candidate, references = _render_facts(offer, act.model_copy(update={"fact_ids": chosen + [key]}), language)
        if len(candidate) <= budget:
            chosen.append(key)
            text, emitted = candidate, references
    return text, emitted


def _fit_answer(records, language: Language) -> tuple[str, dict, list[str]]:
    """Reserve a bounded act for every mentioned offer before spending on facts."""
    texts, emitted, observations = [], {}, []
    remaining = 600 - max(0, len(records) - 1)
    for index, (act, offer, full, references, compact) in enumerate(records):
        reserve = sum(len(record[4]) for record in records[index + 1:])
        budget = remaining - reserve
        if len(full) > budget:
            observations.append("length_limited")
            full, references = (_fit_facts(offer, act, language, budget, compact)
                                if act.act == "facts" else (compact, []))
        texts.append(full)
        remaining -= len(full)
        if offer is not None:
            emitted.setdefault(offer.offer_id, []).extend(references)
    answer = " ".join(texts)
    if len(answer) > 600:
        # This guards the fixed localized acts, not model-controlled prose.
        raise FormulatorError("formulator_contract_violation")
    return answer, emitted, list(dict.fromkeys(observations))


def render_answer_plan(plan: FormulatorPlan, evidence: FormulatorEvidence) -> tuple[str, list[str], dict]:
    """Prüft Bindungen und rendert atomar; bei Fehlern keine Teilübernahme."""
    if plan.language != evidence.requested_language:
        raise FormulatorError("formulator_invalid_language")
    offers = {offer.offer_id: offer for offer in evidence.selected_offers}
    policies = {policy.policy_id for policy in evidence.binding_policies}
    if any(key not in offers for key in plan.card_ids):
        raise FormulatorError("formulator_invalid_card")
    records = []
    declared = {}
    used = set(plan.card_ids)
    for act in plan.sentences:
        if act.act == "boundary":
            required = (BindingPolicy.OUT_OF_SCOPE_BOUNDARY if evidence.answer_type == AnswerType.OUT_OF_SCOPE
                        else BindingPolicy.NO_VERIFIED_RESULT if evidence.answer_type == AnswerType.NO_VERIFIED_RESULT else None)
            if required is None or required not in act.policy_ids or not set(act.policy_ids) <= policies:
                raise FormulatorError("formulator_invalid_fact")
            text = application_text(plan.language, "fallback.out_of_scope" if required == BindingPolicy.OUT_OF_SCOPE_BOUNDARY else "fallback.no_results")
            if not any(record[2] == text for record in records):
                records.append((act, None, text, [], text))
            continue
        if act.offer_id not in offers:
            raise FormulatorError("formulator_invalid_fact")
        offer = offers[act.offer_id]
        used.add(act.offer_id)
        declared.setdefault(act.offer_id, []).extend(act.fact_ids)
        if act.act == "facts":
            text, fact_ids = _render_facts(offer, act, plan.language)
        elif act.act == "unknown":
            text = _unknown(offer, act.reason, plan.language)
            fact_ids = []
        else:
            text = act_text("contact", plan.language, name=offer.display_name)
            fact_ids = []
        compact = act_text("compact_unknown_" + act.reason if act.act == "unknown" else "contact",
                           plan.language, name=offer.display_name)
        records.append((act, offer, text, fact_ids, compact))
    if evidence.need.value in {"toilet", "drinking_water"} and evidence.selected_offers:
        if plan.sentences[0].offer_id != evidence.selected_offers[0].offer_id:
            raise FormulatorError("formulator_contract_violation")
    answer, emitted, observations = _fit_answer(records, plan.language)
    cards = [o.offer_id for o in evidence.selected_offers if o.mandatory or o.offer_id in used]
    assessment = {
        "scope": "selected_offer_evidence", "mode": "controlled_answer_plan",
        "renderer_version": ANSWER_RENDERER_VERSION,
        "declared_fact_ids": {k: list(dict.fromkeys(v)) for k, v in declared.items()},
        "emitted_fact_ids": {k: list(dict.fromkeys(v)) for k, v in emitted.items()},
        "available_fact_ids": {k: [f.fact_id for f in o.facts] for k, o in offers.items()},
        "presentation_observations": observations,
    }
    return answer, cards, assessment
