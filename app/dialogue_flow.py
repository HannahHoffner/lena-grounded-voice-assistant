"""Begrenzte fachliche Aufloesung der explizit freigegebenen Dialogtypen."""

from __future__ import annotations

from .candidate_contract import CandidateDecision, CandidateSelectionContext, MissingFact, ReasonCode, SelectionStatus
from .dialogue import DialogState, DialogType, KnownExplicitFacts, new_dialog
from .interpreter import (
    AcuteRiskStatus,
    AgeGroup,
    ExplicitFacts,
    Gender,
    InputLanguage,
    InterpreterDialogContext,
    Need,
    QueryInterpretation,
    RequestedService,
    ScopeStatus,
)
from .models import Language


def known_facts(interpretation: QueryInterpretation) -> KnownExplicitFacts:
    facts = interpretation.explicit_facts
    return KnownExplicitFacts(
        age=facts.age,
        age_group=facts.age_group,
        gender=facts.gender,
        drug_use=facts.drug_use,
        no_social_benefit_entitlement=facts.no_social_benefit_entitlement,
        district=facts.district,
    )


def interpreter_dialog_context(dialog: DialogState) -> InterpreterDialogContext:
    return InterpreterDialogContext(
        dialog_version=dialog.dialog_version,
        dialog_type=dialog.dialog_type.value,
        originating_need=dialog.originating_need,
        originating_services=dialog.originating_services,
        requested_fields=dialog.requested_fields,
        allowed_choice_values=[choice.value for choice in dialog.choices],
        known_explicit_facts=dialog.known_explicit_facts.model_dump(mode="json"),
        alias=dialog.alias,
    )


def merge_dialog_facts(
    interpretation: QueryInterpretation,
    dialog: DialogState,
) -> QueryInterpretation:
    """Uebernimmt nur bekannte oder in der aktuellen Antwort explizite Fakten."""
    current = interpretation.explicit_facts
    prior = dialog.known_explicit_facts
    merged = current.model_copy(deep=True)
    if merged.age is None:
        merged.age = prior.age
    if merged.age_group == AgeGroup.UNKNOWN:
        merged.age_group = prior.age_group
    for field in ("gender", "drug_use", "no_social_benefit_entitlement"):
        if getattr(merged, field).value == "unknown":
            setattr(merged, field, getattr(prior, field))
    if merged.district is None:
        merged.district = prior.district
    result = interpretation.model_copy(deep=True)
    result.explicit_facts = ExplicitFacts.model_validate(merged.model_dump(mode="python"))
    if result.need in {Need.UNKNOWN, Need.GENERAL_HELP} and dialog.originating_need != Need.UNKNOWN:
        result.need = dialog.originating_need
    if not result.explicit_service_requests and dialog.originating_services:
        result.explicit_service_requests = list(dialog.originating_services)
    return result


def interpretation_from_choices(
    dialog: DialogState,
    values: list[str],
    language: Language,
) -> QueryInterpretation:
    facts = dialog.known_explicit_facts.model_copy(deep=True)
    need = dialog.originating_need
    services: list[RequestedService] = []
    if dialog.dialog_type == DialogType.SLEEP_TARGET_GROUP:
        if "under_18" in values:
            facts.age_group = AgeGroup.UNDER_18
        elif "female" in values:
            facts.gender = Gender.FEMALE
    elif dialog.dialog_type == DialogType.ORGANIZATION_NEED:
        if values == ["sleep"]:
            need = Need.SLEEP
            services = [RequestedService.OVERNIGHT_STAY]
        elif values == ["day_support"]:
            need = Need.GENERAL_HELP
            services = [
                RequestedService.FOOD,
                RequestedService.HYGIENE,
                RequestedService.COUNSELLING,
                RequestedService.DAY_STAY,
            ]
    elif dialog.dialog_type == DialogType.GENERAL_NEED:
        value = values[0]
        need = Need(value)
        service_map = {
            "food": RequestedService.FOOD,
            "drinking_water": RequestedService.DRINKING_WATER,
            "sleep": RequestedService.OVERNIGHT_STAY,
            "medical": RequestedService.MEDICAL_CARE,
            "advice": RequestedService.COUNSELLING,
        }
        if value in service_map:
            services = [service_map[value]]
    elif dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION:
        need = dialog.originating_need
        services = list(dialog.originating_services)
        risk_status = {
            "immediate_danger_yes": AcuteRiskStatus.DETECTED,
            "immediate_danger_no": AcuteRiskStatus.NOT_DETECTED,
            "immediate_danger_unsure": AcuteRiskStatus.UNCERTAIN,
        }[values[0]]
    else:
        risk_status = AcuteRiskStatus.NOT_DETECTED
    return QueryInterpretation(
        contract_version="4",
        need=need,
        explicit_service_requests=services,
        scope_status=ScopeStatus.IN_SCOPE,
        input_language=InputLanguage(language.value),
        explicit_facts=ExplicitFacts(
            **facts.model_dump(mode="python"),
            requested_day=None,
            requested_time=None,
        ),
        uncertain_hints=[],
        potentially_missing_information=[],
        clarification_may_be_needed=False,
        acute_risk_status=(
            risk_status
            if dialog.dialog_type == DialogType.ACUTE_RISK_CONFIRMATION
            else AcuteRiskStatus.NOT_DETECTED
        ),
    )


def is_clear_topic_change(interpretation: QueryInterpretation, dialog: DialogState) -> bool:
    need = interpretation.need
    if need in {Need.UNKNOWN, Need.GENERAL_HELP}:
        return False
    if dialog.dialog_type == DialogType.GENERAL_NEED:
        return False
    if dialog.dialog_type == DialogType.ORGANIZATION_NEED:
        return need not in {Need.SLEEP, Need.FOOD, Need.ADVICE}
    return need != dialog.originating_need


def choose_dialog(
    interpretation: QueryInterpretation,
    decision: CandidateDecision,
    context: CandidateSelectionContext,
    *,
    fingerprint: str,
    timeout_seconds: int,
) -> DialogState | None:
    alias = context.alias
    if (
        alias
        and alias.alias_kind == "organization"
        and len(alias.offer_ids) > 1
        and decision.selection_status in {
            SelectionStatus.CLARIFICATION_RECOMMENDED,
            SelectionStatus.INTERPRETER_UNAVAILABLE,
        }
    ):
        mobile_like = MissingFact.DISTRICT in decision.missing_information
        if not mobile_like and not (
            interpretation.need in {Need.UNKNOWN, Need.GENERAL_HELP}
            and not interpretation.explicit_service_requests
        ):
            return None
        dialog_type = DialogType.ORGANIZATION_DISTRICT if mobile_like else DialogType.ORGANIZATION_NEED
        return new_dialog(
            dialog_type,
            need=interpretation.need,
            fingerprint=fingerprint,
            session_timeout_seconds=timeout_seconds,
            facts=known_facts(interpretation),
            alias=alias.alias,
        )
    if interpretation.need == Need.SLEEP:
        facts = interpretation.explicit_facts
        if (
            facts.gender == Gender.FEMALE
            and facts.age is None
            and facts.age_group == AgeGroup.UNKNOWN
        ):
            return new_dialog(
                DialogType.SLEEP_AGE,
                need=Need.SLEEP,
                fingerprint=fingerprint,
                session_timeout_seconds=timeout_seconds,
                facts=known_facts(interpretation),
            )
        has_general_contact = any(
            ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY in item.reason_codes
            for item in decision.candidates
        )
        if not has_general_contact:
            return None
        if (
            facts.gender != Gender.UNKNOWN
            or facts.age is not None
            or facts.age_group != AgeGroup.UNKNOWN
        ):
            return None
        return new_dialog(
            DialogType.SLEEP_TARGET_GROUP,
            need=Need.SLEEP,
            fingerprint=fingerprint,
            session_timeout_seconds=timeout_seconds,
            facts=known_facts(interpretation),
        )
    if interpretation.need in {Need.GENERAL_HELP, Need.UNKNOWN}:
        return new_dialog(
            DialogType.GENERAL_NEED,
            need=Need.GENERAL_HELP,
            fingerprint=fingerprint,
            session_timeout_seconds=timeout_seconds,
            facts=known_facts(interpretation),
        )
    return None
