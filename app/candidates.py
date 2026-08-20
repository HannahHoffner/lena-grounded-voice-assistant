"""Deterministische, erklaerbare Begrenzung kuratierter Runtime-Angebote."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .candidate_contract import (
    CANDIDATE_CONTRACT_VERSION,
    EXCLUDED_SOURCE_IDS,
    CandidateDecision,
    CandidateItem,
    CandidateRole,
    CandidateSelectionContext,
    ExcludedItem,
    FactsUsed,
    MissingFact,
    ReasonCode,
    RuleCode,
    SelectionConflict,
    SelectionStatus,
)
from .candidate_context import (
    build_selection_context,
    normalize_candidate_text,
    schedule_matches,
)
from .interpreter import (
    AcuteRiskStatus,
    AgeGroup,
    Gender,
    Need,
    QueryInterpretation,
    RequestedDay,
    RequestedService,
    ThreeWayStatus,
)
from .models import OfferRecord
from .result_time import food_schedule_matches


def _facts(interpretation: QueryInterpretation) -> FactsUsed:
    return FactsUsed.model_validate(interpretation.explicit_facts.model_dump(mode="python"))


def _requested_capabilities(interpretation: QueryInterpretation, need: Need) -> set[str]:
    explicit = {
        item.value
        for item in interpretation.explicit_service_requests
        if item != RequestedService.YOUTH_SUPPORT
    }
    if explicit:
        return explicit
    return {
        Need.FOOD: {RequestedService.FOOD.value},
        Need.DRINKING_WATER: {RequestedService.DRINKING_WATER.value},
        Need.SLEEP: {RequestedService.OVERNIGHT_STAY.value},
        Need.MEDICAL: {RequestedService.MEDICAL_CARE.value, "medical_access", RequestedService.WOUND_CARE.value},
        Need.ADVICE: {RequestedService.COUNSELLING.value},
    }.get(need, set())


class CandidateSelector:
    """Wendet ausschliesslich versionierte Runtime-Merkmale auf eine Interpretation an."""

    def select(
        self,
        interpretation: QueryInterpretation,
        offers: list[OfferRecord],
        *,
        context: CandidateSelectionContext | None = None,
        now: datetime | None = None,
    ) -> CandidateDecision:
        if interpretation.acute_risk_status == AcuteRiskStatus.DETECTED:
            raise ValueError("acute risk must be handled before candidate selection")
        if EXCLUDED_SOURCE_IDS.intersection(offer.id for offer in offers):
            raise ValueError("candidate selector requires curated runtime offers")
        context = context or CandidateSelectionContext()
        current = now or datetime.now(ZoneInfo("Europe/Berlin"))
        need = interpretation.need
        rules = [RuleCode.RUNTIME_APPROVED_ONLY, RuleCode.CURRENT_INTERPRETATION_FIRST]
        conflicts: list[SelectionConflict] = []
        if need == Need.UNKNOWN and context.ui_need_hint:
            need = context.ui_need_hint
            rules.append(RuleCode.UI_HINT_FALLBACK)
        elif context.ui_need_hint and context.ui_need_hint != need:
            rules.append(RuleCode.UI_HINT_OVERRIDDEN)
            conflicts.append(SelectionConflict(field="need", preferred_value=need.value, ignored_value=context.ui_need_hint.value))
        facts = _facts(interpretation)
        explicit_services = set(interpretation.explicit_service_requests)
        explicit_youth = RequestedService.YOUTH_SUPPORT in explicit_services
        explicit_protection = RequestedService.PROTECTION in explicit_services
        if explicit_youth:
            rules.append(RuleCode.EXPLICIT_YOUTH_ROUTING)
        if need == Need.TOILET:
            return self._terminal(need, facts, SelectionStatus.UNSUPPORTED_NEED, [*rules, RuleCode.TOILET_UNSUPPORTED])
        if need == Need.DRINKING_WATER:
            rules.append(RuleCode.WATER_EVIDENCE_ONLY)
        if need == Need.GENERAL_HELP:
            rules.append(RuleCode.GENERAL_HELP_REFERRAL)
        rules.append(RuleCode.NEED_AND_SERVICE_EVIDENCE)
        if context.alias:
            rules.append(RuleCode.ALIAS_LIMIT)
        if facts.district and not (context.alias and context.alias.district_narrowed):
            rules.append(RuleCode.DISTRICT_RECORDED_NOT_VALIDATED)

        requested = _requested_capabilities(interpretation, need)
        selected: list[CandidateItem] = []
        conditional: list[CandidateItem] = []
        excluded: list[ExcludedItem] = []
        global_missing: set[MissingFact] = set()
        alias_ids = set(context.alias.offer_ids) if context.alias else None
        minor = facts.age_group == AgeGroup.UNDER_18 or (
            facts.age is not None and facts.age <= 17
        )
        unsupported = [
            hint.value[:80] for hint in interpretation.uncertain_hints
            if hint.field.value == "other" and any(
                term in normalize_candidate_text(hint.value)
                for term in ("tier", "hund", "animal", "paar", "couple")
            )
        ]
        if unsupported:
            global_missing.add(MissingFact.UNSUPPORTED_CONDITION)

        for offer in offers:
            if alias_ids is not None and offer.id not in alias_ids:
                excluded.append(ExcludedItem(offer_id=offer.id, reason_codes=[ReasonCode.ALIAS_SCOPE_MISMATCH]))
                continue
            youth_alias_match = bool(alias_ids is not None and offer.id in alias_ids)
            if (
                "youth_explicit_only" in offer.priority_rules
                and not explicit_youth
                and not youth_alias_match
            ):
                excluded.append(
                    ExcludedItem(offer_id=offer.id, reason_codes=[ReasonCode.YOUTH_INTENT_REQUIRED])
                )
                continue
            direct_match = bool(requested.intersection(offer.capabilities)) and (
                need.value in offer.needs
                or (need == Need.GENERAL_HELP and bool(interpretation.explicit_service_requests))
            )
            if (
                need == Need.GENERAL_HELP
                and interpretation.explicit_service_requests
                and offer.place_type in {"overnight_accommodation", "emergency_accommodation"}
            ):
                direct_match = False
            referral_match = need.value in offer.referral_needs
            if need == Need.GENERAL_HELP and interpretation.explicit_service_requests:
                referral_match = False
            if (
                need == Need.SLEEP
                and "general_help_referral_first" in offer.priority_rules
                and (facts.gender in {Gender.FEMALE, Gender.MALE} or facts.drug_use == ThreeWayStatus.YES)
                and not minor
            ):
                referral_match = False
            if need == Need.GENERAL_HELP and not interpretation.explicit_service_requests:
                direct_match = False
            if not direct_match and not referral_match:
                excluded.append(ExcludedItem(offer_id=offer.id, reason_codes=[ReasonCode.NEED_NOT_SUPPORTED]))
                continue

            reasons = [ReasonCode.REFERRAL_NEED_MATCH if referral_match and not direct_match else ReasonCode.NEED_CAPABILITY_MATCH]
            missing: set[MissingFact] = set()
            blocked: ReasonCode | None = None
            schedule_matched = False
            if context.alias:
                reasons.append(ReasonCode.ALIAS_MATCH)
                if context.alias.district_narrowed:
                    reasons.append(ReasonCode.DISTRICT_ALIAS_MATCH)
            # FOOD_AGE_UNRESTRICTED gilt bewusst nur fuer minimum_age (Erwachsenen-
            # Angebote wie Diakonie/Schwanenteich): Essensausgabe ist fuer alle da,
            # auch wenn die institutionelle Zustaendigkeit (Beratung, Fallzuordnung)
            # formal bei Erwachsenen liegt (siehe
            # docs/exec-plans/fix-food-age-restriction.md). maximum_age
            # Jugendangebote bis 26 bleiben dagegen altersgebunden. Zusaetzlich
            # passieren sie das vorangestellte Intent-Gate nur bei ausdruecklichem
            # Jugendbedarf oder einem exakten Alias; Alter allein aktiviert sie nicht.
            if offer.minimum_age is not None:
                if need == Need.FOOD:
                    rules.append(RuleCode.FOOD_AGE_UNRESTRICTED)
                elif facts.age is None:
                    if (
                        facts.age_group in {AgeGroup.ADULT, AgeGroup.NOT_UNDER_27}
                        and offer.minimum_age <= 27
                    ) or (
                        facts.age_group == AgeGroup.UNDER_27
                        and offer.minimum_age <= 18
                    ):
                        reasons.append(ReasonCode.EXPLICIT_TARGET_MATCH)
                    else:
                        missing.add(MissingFact.AGE)
                        reasons.append(ReasonCode.AGE_NOT_ESTABLISHED)
                elif facts.age < offer.minimum_age:
                    blocked = ReasonCode.AGE_OUTSIDE_RANGE
            if offer.maximum_age is not None:
                if facts.age is None:
                    if facts.age_group == AgeGroup.UNDER_18 and offer.maximum_age >= 17:
                        reasons.append(ReasonCode.EXPLICIT_TARGET_MATCH)
                    elif facts.age_group == AgeGroup.UNDER_27 and offer.maximum_age == 26:
                        reasons.append(ReasonCode.EXPLICIT_TARGET_MATCH)
                    elif facts.age_group == AgeGroup.NOT_UNDER_27 and offer.maximum_age <= 26:
                        blocked = ReasonCode.AGE_OUTSIDE_RANGE
                    else:
                        missing.add(MissingFact.AGE)
                        reasons.append(ReasonCode.AGE_NOT_ESTABLISHED)
                elif facts.age > offer.maximum_age:
                    blocked = ReasonCode.AGE_OUTSIDE_RANGE
            if offer.eligible_genders:
                if facts.gender == Gender.UNKNOWN:
                    missing.add(MissingFact.GENDER)
                    reasons.append(ReasonCode.GENDER_NOT_ESTABLISHED)
                elif facts.gender.value not in offer.eligible_genders:
                    blocked = ReasonCode.TARGET_GROUP_MISMATCH
                else:
                    reasons.append(ReasonCode.EXPLICIT_TARGET_MATCH)
            if offer.requires_explicit_drug_use:
                rules.append(RuleCode.DRUG_SPECIFIC_REQUIRES_EXPLICIT)
                if facts.drug_use == ThreeWayStatus.UNKNOWN:
                    missing.add(MissingFact.DRUG_USE)
                    reasons.append(ReasonCode.DRUG_USE_NOT_EXPLICIT)
                elif facts.drug_use == ThreeWayStatus.NO:
                    blocked = ReasonCode.DRUG_USE_MISMATCH
                else:
                    reasons.append(ReasonCode.EXPLICIT_TARGET_MATCH)
            if "helene_after_21_or_no_social_benefit_entitlement" in offer.access_rules:
                rules.append(RuleCode.HELENE_RESTRICTED_ACCESS)
                explicit_after_21 = bool(
                    facts.requested_time and int(facts.requested_time[:2]) >= 21
                )
                current_after_21 = bool(
                    facts.requested_time is None
                    and facts.requested_day in {None, RequestedDay.TODAY, RequestedDay.TONIGHT}
                    and current.hour >= 21
                )
                after_21 = explicit_after_21 or current_after_21
                no_benefit = facts.no_social_benefit_entitlement == ThreeWayStatus.YES
                if not after_21 and not no_benefit:
                    if facts.requested_time or facts.no_social_benefit_entitlement == ThreeWayStatus.NO:
                        blocked = ReasonCode.TIME_CONDITION_NOT_MET
                    else:
                        missing.update({MissingFact.REQUESTED_TIME, MissingFact.SOCIAL_BENEFIT_ENTITLEMENT})
                        reasons.append(ReasonCode.HELENE_ACCESS_NOT_ESTABLISHED)
            matching_capability = next((item for item in requested if item in offer.service_schedules), None)
            if need == Need.FOOD:
                schedule_rule = offer.service_schedules.get(matching_capability) if matching_capability else None
                rules.append(RuleCode.DOCUMENTED_TIME_ONLY)
                if not food_schedule_matches(schedule_rule, offer.opening_hours_raw, facts, current):
                    blocked = ReasonCode.TIME_CONDITION_NOT_MET
                else:
                    reasons.append(ReasonCode.DOCUMENTED_SCHEDULE)
                    schedule_matched = True
            elif matching_capability:
                rules.append(RuleCode.DOCUMENTED_TIME_ONLY)
                strict_current_schedule = need == Need.DRINKING_WATER
                schedule = schedule_matches(
                    offer.service_schedules[matching_capability],
                    facts,
                    current,
                    use_current_when_unspecified=strict_current_schedule,
                )
                if schedule is False or (strict_current_schedule and schedule is not True):
                    blocked = ReasonCode.TIME_CONDITION_NOT_MET
                else:
                    reasons.append(ReasonCode.DOCUMENTED_SCHEDULE)
                    schedule_matched = schedule is True
            if blocked:
                excluded.append(ExcludedItem(offer_id=offer.id, reason_codes=[blocked]))
                continue

            role = CandidateRole.REFERRAL_CONTACT if referral_match and not direct_match else CandidateRole.DIRECT_SERVICE
            priority = 50
            if schedule_matched:
                priority = 10
            if minor and need == Need.SLEEP and "minor_sleep_first" in offer.priority_rules:
                rules.append(RuleCode.MINOR_SLEEP_ROUTING)
                reasons.append(ReasonCode.MINOR_SLEEP_PRIORITY)
                priority = 0
            elif minor and need == Need.SLEEP and "minor_crisis_first" in offer.priority_rules:
                rules.append(RuleCode.MINOR_SLEEP_ROUTING)
                reasons.append(
                    ReasonCode.MINOR_CRISIS_PRIORITY
                    if explicit_protection
                    else ReasonCode.CURATED_PRIORITY
                )
                priority = 0 if explicit_protection else 5
                role = CandidateRole.REFERRAL_CONTACT
            elif need == Need.SLEEP and "general_sleep_contact_first" in offer.priority_rules and facts.drug_use != ThreeWayStatus.YES and not minor:
                rules.append(RuleCode.GENERAL_SLEEP_RUECKE_FIRST)
                reasons.append(ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY)
                priority = 0
                role = CandidateRole.REFERRAL_CONTACT
                missing.discard(MissingFact.GENDER)
                missing.discard(MissingFact.AGE)
            elif need == Need.GENERAL_HELP and "general_help_referral_first" in offer.priority_rules:
                reasons.append(ReasonCode.CURATED_PRIORITY)
                priority = 0
                role = CandidateRole.REFERRAL_CONTACT
            if context.alias and context.alias.alias_kind == "organization" and len(context.alias.offer_ids) > 1:
                matching_ids = [item for item in offers if item.id in context.alias.offer_ids and (need.value in item.needs or need.value in item.referral_needs)]
                if len(matching_ids) > 1 and not context.alias.district_narrowed:
                    missing.add(MissingFact.DISTRICT if all(item.maximum_age == 26 for item in matching_ids) else MissingFact.NEED)
                    reasons.append(ReasonCode.AMBIGUOUS_ORGANIZATION_ALIAS)
            if missing or role == CandidateRole.CONDITIONAL_CANDIDATE or unsupported:
                item = CandidateItem(offer_id=offer.id, role=CandidateRole.CONDITIONAL_CANDIDATE, reason_codes=list(dict.fromkeys(reasons)), missing_facts=sorted(missing, key=lambda value: value.value), priority_tier=priority)
                conditional.append(item)
                global_missing.update(missing)
            else:
                selected.append(CandidateItem(offer_id=offer.id, role=role, reason_codes=list(dict.fromkeys(reasons)), priority_tier=priority))

        rules.append(RuleCode.STABLE_ID_SORT)
        selected.sort(key=lambda item: (item.priority_tier, item.offer_id))
        conditional.sort(key=lambda item: (item.priority_tier, item.offer_id))
        by_id = {offer.id: offer for offer in offers}
        mandatory: list[CandidateItem] = []
        selectable: list[CandidateItem] = []
        for item in selected:
            offer = by_id[item.offer_id]
            binding_priority = (
                ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY in item.reason_codes
                or ReasonCode.CURATED_PRIORITY in item.reason_codes
                or ReasonCode.MINOR_SLEEP_PRIORITY in item.reason_codes
                or ReasonCode.MINOR_CRISIS_PRIORITY in item.reason_codes
            )
            unique_alias_match = bool(context.alias and len(selected) == 1)
            (mandatory if binding_priority or unique_alias_match else selectable).append(item)
        general_sleep_contact = any(
            ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY in item.reason_codes for item in mandatory
        )
        if selected and not general_sleep_contact and need != Need.GENERAL_HELP and not unsupported:
            global_missing.clear()
        clarification = bool(
            (not selected and conditional)
            or need in {Need.UNKNOWN, Need.GENERAL_HELP}
            or general_sleep_contact
        )
        if unsupported:
            clarification = True
        if clarification:
            status = SelectionStatus.CLARIFICATION_RECOMMENDED
        elif selected:
            status = SelectionStatus.CANDIDATES_AVAILABLE
        elif need == Need.UNKNOWN:
            status = SelectionStatus.CLARIFICATION_RECOMMENDED
            global_missing.add(MissingFact.NEED)
        else:
            status = SelectionStatus.NO_ELIGIBLE_CANDIDATE
        return CandidateDecision(
            contract_version=CANDIDATE_CONTRACT_VERSION,
            need=need,
            facts_used=facts,
            mandatory_candidates=mandatory,
            selectable_candidates=selectable,
            conditional_candidates=conditional,
            excluded_candidates=excluded,
            missing_information=sorted(global_missing, key=lambda value: value.value),
            clarification_recommended=status == SelectionStatus.CLARIFICATION_RECOMMENDED,
            selection_status=status,
            applied_rules=list(dict.fromkeys(rules)),
            conflicts=conflicts,
            unsupported_conditions=unsupported,
        )

    @staticmethod
    def _terminal(need: Need, facts: FactsUsed, status: SelectionStatus, rules: list[RuleCode]) -> CandidateDecision:
        return CandidateDecision(
            contract_version=CANDIDATE_CONTRACT_VERSION,
            need=need,
            facts_used=facts,
            selection_status=status,
            clarification_recommended=status == SelectionStatus.CLARIFICATION_RECOMMENDED,
            applied_rules=rules,
        )

    def interpreter_unavailable(
        self,
        offers: list[OfferRecord],
        fallback: CandidateDecision | None = None,
    ) -> CandidateDecision:
        if EXCLUDED_SOURCE_IDS.intersection(offer.id for offer in offers):
            raise ValueError("candidate selector requires curated runtime offers")
        facts = FactsUsed(
            age=None,
            age_group=AgeGroup.UNKNOWN,
            gender=Gender.UNKNOWN,
            drug_use=ThreeWayStatus.UNKNOWN,
            no_social_benefit_entitlement=ThreeWayStatus.UNKNOWN,
            district=None,
            requested_day=None,
            requested_time=None,
        )
        if fallback is None:
            return self._terminal(Need.UNKNOWN, facts, SelectionStatus.INTERPRETER_UNAVAILABLE, [RuleCode.RUNTIME_APPROVED_ONLY])
        return CandidateDecision(
            contract_version=CANDIDATE_CONTRACT_VERSION,
            need=fallback.need,
            facts_used=facts,
            mandatory_candidates=fallback.mandatory_candidates,
            selectable_candidates=fallback.selectable_candidates,
            conditional_candidates=fallback.conditional_candidates,
            excluded_candidates=fallback.excluded_candidates,
            missing_information=fallback.missing_information,
            clarification_recommended=False,
            selection_status=SelectionStatus.INTERPRETER_UNAVAILABLE,
            applied_rules=fallback.applied_rules,
        )
