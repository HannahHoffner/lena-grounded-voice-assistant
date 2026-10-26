"""Produktiver Vertrag 6: Behauptungen stammen aus Fakten, nicht aus Modelltext."""

import asyncio
import json

import pytest
from pydantic import ValidationError

from app.answer_plan import AnswerAct, FormulatorPlan, formulator_plan_prompt
from app.formulation import (
    AnswerType, BindingPolicy, EvidenceFact, FactType, PLAN_FORMULATOR_CONTRACT_VERSION as FORMULATOR_CONTRACT_VERSION,
    FormulatorError, FormulatorEvidence,
)
from app.grounding import validate_formulation
from app.models import Language
from app.prompt_comparison_cases import comparison_cases
from app.providers.llm import BlabladorProvider
from test_formulation import _settings


def packet(family="meal", language=Language.DE):
    return FormulatorEvidence.model_validate(next(c["evidence"] for c in comparison_cases()
        if c["family"] == family and c["evidence"]["requested_language"] == language.value))


def plan(evidence, act="facts", *, kinds=(FactType.SERVICE,), reason=None, index=0):
    offer = evidence.selected_offers[index]
    return FormulatorPlan(contract_version=FORMULATOR_CONTRACT_VERSION,
        language=evidence.requested_language,
        sentences=[AnswerAct(act=act, offer_id=offer.offer_id,
            fact_ids=[f.fact_id for f in offer.facts if f.fact_type in kinds] if act == "facts" else [],
            reason=reason)], card_ids=[offer.offer_id])


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("family", ["meal", "weekend", "negation", "service_time", "eligibility"])
def test_readable_facts_and_restrictions_survive_without_word_tests(language, family):
    evidence = packet(family, language)
    response = plan(evidence)
    result = validate_formulation(response, evidence)
    assert evidence.selected_offers[0].display_name in result.answer
    assert result.reference_assessment["mode"] == "controlled_answer_plan"
    for fact in evidence.selected_offers[0].facts:
        if fact.fact_type in {FactType.SERVICE, FactType.NOTE, FactType.SERVICE_CONDITION, FactType.MINIMUM_AGE}:
            assert fact.value in result.answer
            assert fact.fact_id in result.reference_assessment["emitted_fact_ids"][response.sentences[0].offer_id]


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("family,reason", [("unknown_fee", "fee"), ("unsupported_service", "detail"),
    ("availability", "availability"), ("seasonal_water", "availability"), ("injection", "detail")])
def test_bounded_unknown_answers_need_no_invented_fact_reference(language, family, reason):
    evidence = packet(family, language)
    result = validate_formulation(plan(evidence, "unknown", reason=reason), evidence)
    assert evidence.selected_offers[0].display_name in result.answer
    assert result.answer
    assert result.card_ids == [evidence.selected_offers[0].offer_id]
    assert "500" not in result.answer


@pytest.mark.parametrize("text", ["Scharni repariert Fahrräder.", "Bei Scharni ist Fahrradreparatur möglich.",
    "Scharni hilft bei der Steuererklärung.", "Scharni nimmt dich heute garantiert auf."])
def test_arbitrary_paraphrases_cannot_enter_any_answer_act(text):
    evidence = packet()
    for act in ("facts", "contact", "unknown", "boundary"):
        raw = plan(evidence).model_dump(mode="json")
        raw["sentences"][0].update(act=act, text=text)
        with pytest.raises(ValidationError):
            FormulatorPlan.model_validate(raw)


def test_reason_and_fact_reference_are_closed_not_prose():
    with pytest.raises(ValidationError):
        AnswerAct(act="unknown", offer_id="40", reason="repairs bicycles")
    with pytest.raises(ValidationError):
        AnswerAct(act="facts", offer_id="40", fact_ids=["repairs bicycles"])


def test_references_cannot_cross_offer_boundary_or_be_invented():
    evidence = packet("two_offers")
    response = plan(evidence)
    response.sentences[0].fact_ids = [evidence.selected_offers[1].facts[1].fact_id]
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(response, evidence)
    response.sentences[0].fact_ids = ["f_ffffffffffffffff"]
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("reason,family", [("fee", "meal"), ("hours", "weekend"), ("access", "eligibility")])
def test_known_information_cannot_be_declared_missing(reason, family):
    evidence = packet(family)
    with pytest.raises(FormulatorError):
        validate_formulation(plan(evidence, "unknown", reason=reason), evidence)


def test_oversized_condition_never_leaves_an_unconditional_service_claim():
    evidence = packet("eligibility")
    evidence.selected_offers[0].facts.append(EvidenceFact(
        fact_id="f_ffffffffffffffff", fact_type=FactType.NOTE, value="x" * 600))
    result = validate_formulation(plan(evidence), evidence)
    assert len(result.answer) <= 600
    assert result.answer == "Frage bei Lichtpunkt nach."
    assert result.reference_assessment["emitted_fact_ids"] == {evidence.selected_offers[0].offer_id: []}
    assert result.reference_assessment["presentation_observations"] == ["length_limited"]
    assert result.card_ids == [evidence.selected_offers[0].offer_id]


def test_language_cards_and_primary_result_are_enforced():
    evidence = packet("two_offers")
    response = plan(evidence)
    response.language = Language.RU
    with pytest.raises(FormulatorError, match="invalid_language"):
        validate_formulation(response, evidence)
    response.language = evidence.requested_language
    response.card_ids = ["999"]
    with pytest.raises(FormulatorError, match="invalid_card"):
        validate_formulation(response, evidence)


def test_historical_plan_schema_is_preserved_but_runtime_rejects_it(monkeypatch):
    evidence = packet("unknown_fee")
    provider = BlabladorProvider(_settings("blablador"))
    response = plan(evidence, "unknown", reason="fee")
    from app.answer_plan import planner_evidence_payload
    def check_historical_schema():
        prompt = formulator_plan_prompt()
        schema = json.loads(prompt.split("Response JSON Schema:\n", 1)[1])
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["AnswerAct"]["properties"]["act"]["enum"] == ["facts", "contact", "unknown", "boundary"]
        assert schema["$defs"]["AnswerAct"]["properties"]["policy_ids"]["maxItems"] == 2
        assert "All offer-bound acts MUST have policy_ids=[]" in prompt
        payload_evidence = planner_evidence_payload(evidence)
        offered = payload_evidence["selected_offers"][0]
        assert offered["display_name"] == evidence.selected_offers[0].display_name
        assert all(f["fact_type"] not in {"display_name", "alias", "capability", "offer_type", "place_type"}
                   for f in offered["facts"])
        source = {f.fact_id: f.model_dump(mode="json") for f in evidence.selected_offers[0].facts}
        assert all(source[f["fact_id"]] == f for f in offered["facts"])
    check_historical_schema()
    async def post(payload):
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}
    monkeypatch.setattr(provider, "_post", post)
    with pytest.raises(FormulatorError, match="formulator_schema_error"):
        asyncio.run(provider.formulate_answer(evidence=evidence))
    result = validate_formulation(response, evidence)
    assert "Kosten" in result.answer
    assert "Stadtpunkt" in result.answer


@pytest.mark.parametrize("wire_version", ["5", "6"])
def test_runtime_rejects_legacy_prose_even_with_valid_offer_and_fact(monkeypatch, wire_version):
    provider = BlabladorProvider(_settings("blablador"))
    evidence = packet()
    async def post(payload):
        return {"choices": [{"message": {"content": json.dumps({
            "contract_version": wire_version, "language": "de", "sentences": [{
                "text": "Nordpunkt repariert Fahrräder.", "claim_type": "fact", "offer_id": "40",
                "fact_ids": [evidence.selected_offers[0].facts[0].fact_id], "policy_ids": []}], "card_ids": ["40"]})}}]}
    monkeypatch.setattr(provider, "_post", post)
    with pytest.raises(FormulatorError, match="formulator_schema_error"):
        asyncio.run(provider.formulate_answer(evidence=evidence))


@pytest.mark.parametrize("language", list(Language))
@pytest.mark.parametrize("reason", ["fee", "hours", "access", "availability", "detail"])
def test_three_long_named_unknown_acts_fit_without_claiming_missing_information(language, reason):
    evidence = packet("unknown_fee", language)
    original = evidence.selected_offers[0]
    evidence.selected_offers = [original.model_copy(update={
        "offer_id": str(40 + i), "display_name": "A" * 119 + str(i),
        "facts": [EvidenceFact(fact_id=f"f_{i:016x}", fact_type=FactType.ADDRESS, value="Testplatz 1")],
    }) for i in range(3)]
    evidence = FormulatorEvidence.model_validate(evidence.model_dump())
    response = FormulatorPlan(contract_version=FORMULATOR_CONTRACT_VERSION, language=language,
        sentences=[AnswerAct(act="unknown", offer_id=o.offer_id, reason=reason) for o in evidence.selected_offers])
    result = validate_formulation(response, evidence)
    assert len(result.answer) <= 600
    for offer in evidence.selected_offers:
        assert offer.display_name in result.answer
    assert result.card_ids == [o.offer_id for o in evidence.selected_offers]
    assert all(not ids for ids in result.reference_assessment["emitted_fact_ids"].values())


@pytest.mark.parametrize("language", list(Language))
def test_layout_keeps_whole_contact_fact_when_service_conditions_do_not_fit(language):
    evidence = packet("eligibility", language)
    offer = evidence.selected_offers[0]
    offer.facts.extend([
        EvidenceFact(fact_id="f_aaaaaaaaaaaaaaaa", fact_type=FactType.NOTE, value="x" * 600),
        EvidenceFact(fact_id="f_bbbbbbbbbbbbbbbb", fact_type=FactType.ADDRESS, value="Testplatz 123, Leipzig"),
    ])
    response = plan(evidence, kinds=(FactType.SERVICE, FactType.ADDRESS))
    result = validate_formulation(response, evidence)
    assert len(result.answer) <= 600
    assert "Testplatz 123, Leipzig" in result.answer
    for fact in offer.facts:
        if fact.fact_type == FactType.SERVICE:
            assert fact.value not in result.answer
    assert "f_bbbbbbbbbbbbbbbb" in result.reference_assessment["emitted_fact_ids"][offer.offer_id]
    assert "f_aaaaaaaaaaaaaaaa" not in result.reference_assessment["emitted_fact_ids"][offer.offer_id]


def test_layout_does_not_hide_invalid_late_reference_after_a_long_fact():
    evidence = packet("eligibility")
    evidence.selected_offers[0].facts.append(EvidenceFact(
        fact_id="f_aaaaaaaaaaaaaaaa", fact_type=FactType.NOTE, value="x" * 600))
    response = plan(evidence)
    response.sentences.append(AnswerAct(act="facts", offer_id=evidence.selected_offers[0].offer_id,
                                      fact_ids=["f_ffffffffffffffff"]))
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("act,policies", [("fact", []), ("offer", []), ("contact", ["referral_wording"])])
def test_recorded_schema_mistakes_remain_rejected_instead_of_silently_repaired(act, policies):
    raw = plan(packet()).model_dump(mode="json")
    raw["sentences"][0].update(act=act, policy_ids=policies)
    with pytest.raises(ValidationError):
        FormulatorPlan.model_validate(raw)
