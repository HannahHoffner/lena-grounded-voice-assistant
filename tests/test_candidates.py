"""Fachliche Vertrags- und Regeltests der deterministischen Kandidatenstufe."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.candidate_contract import CandidateDecision, CandidateRole, ReasonCode, RuleCode, SelectionStatus
from app.candidates import CandidateSelector, build_selection_context
from app.curation import load_curation_catalog, project_runtime_offers
from app.interpreter import AcuteRiskStatus, Need, QueryInterpretation, RequestedService
from app.kb_loader import load_knowledge_base
from app.models import Category, OfferRecord


ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_curation_catalog(ROOT / "app" / "resources" / "bootstrap" / "curation" / "social_offers.json")
SOURCE = load_knowledge_base(ROOT / "data" / "wfs" / "releases" / "legacy-3b72f95a88f9" / "offers.json")
OFFERS, ORGANIZATION_ALIASES = project_runtime_offers(SOURCE.offers, CATALOG)
SELECTOR = CandidateSelector()
NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)  # Monday; rules receive an explicit clock.


def interpretation(
    need: Need,
    *,
    services: list[RequestedService] | None = None,
    age: int | None = None,
    gender: str = "unknown",
    drug_use: str = "unknown",
    no_benefit: str = "unknown",
    district: str | None = None,
    day: str | None = None,
    time: str | None = None,
    language: str = "de",
    risk: AcuteRiskStatus = AcuteRiskStatus.NOT_DETECTED,
    hints: list[dict[str, str]] | None = None,
) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
                "contract_version": "3",
            "need": need.value,
            "explicit_service_requests": [item.value for item in services or []],
            "scope_status": "unclear" if need == Need.UNKNOWN else "in_scope",
            "input_language": language,
            "explicit_facts": {
                "age": age,
                "gender": gender,
                "drug_use": drug_use,
                "no_social_benefit_entitlement": no_benefit,
                "district": district,
                "requested_day": day,
                "requested_time": time,
            },
            "uncertain_hints": hints or [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": risk.value,
        }
    )


def decide(value: QueryInterpretation, *, query: str = "", category: Category | None = None) -> CandidateDecision:
    context = build_selection_context(
        query=query,
        interpretation=value,
        offers=OFFERS,
        organization_aliases=ORGANIZATION_ALIASES,
        ui_category=category,
    )
    return SELECTOR.select(value, OFFERS, context=context, now=NOW)


def ids(decision: CandidateDecision) -> list[str]:
    return [item.offer_id for item in decision.candidates]


def conditional_ids(decision: CandidateDecision) -> list[str]:
    return [item.offer_id for item in decision.conditional_candidates]


def test_runtime_taxonomy_is_complete_strict_and_excludes_social_office_records() -> None:
    assert len(OFFERS) == 26
    assert not {"1", "2", "3", "4"}.intersection(offer.id for offer in OFFERS)
    assert all(offer.place_type and offer.capabilities for offer in OFFERS)
    with pytest.raises(ValidationError):
        CandidateDecision.model_validate(
            {
                "contract_version": "2",
                "need": "food",
                "facts_used": interpretation(Need.FOOD).explicit_facts.model_dump(mode="json"),
                "selectable_candidates": [{"offer_id": "1", "role": "direct_service", "reason_codes": ["need_capability_match"], "priority_tier": 0}],
                "clarification_recommended": False,
                "selection_status": "candidates_available",
                "applied_rules": ["runtime_approved_only"],
            }
        )


def test_current_interpretation_overrides_conflicting_ui_hint() -> None:
    decision = decide(interpretation(Need.SLEEP, age=30, gender="male"), category=Category.FOOD)
    assert decision.need == Need.SLEEP
    assert RuleCode.UI_HINT_OVERRIDDEN in decision.applied_rules
    assert decision.conflicts[0].ignored_value == "food"
    assert "7" in ids(decision)
    assert not any("food" in OFFERS[[offer.id for offer in OFFERS].index(item)].needs for item in ids(decision))


def test_ui_hint_is_only_used_when_interpreter_need_is_unknown() -> None:
    decision = decide(interpretation(Need.UNKNOWN), category=Category.SLEEP)

    assert decision.need == Need.SLEEP
    assert RuleCode.UI_HINT_FALLBACK in decision.applied_rules
    assert ids(decision)[0] == "7"


def test_general_sleep_uses_ruecke_as_referral_and_keeps_specific_offers_conditional() -> None:
    decision = decide(interpretation(Need.SLEEP))
    assert decision.selection_status == SelectionStatus.CLARIFICATION_RECOMMENDED
    assert ids(decision)[0] == "7"
    ruecke = decision.candidates[0]
    assert decision.mandatory_candidates == [ruecke]
    assert ruecke.role == CandidateRole.REFERRAL_CONTACT
    assert ReasonCode.GENERAL_SLEEP_CONTACT_PRIORITY in ruecke.reason_codes
    assert {"5", "6", "8", "23"} <= set(conditional_ids(decision))
    assert "age" in {item.value for item in decision.missing_information}
    assert "gender" in {item.value for item in decision.missing_information}


@pytest.mark.parametrize("age", [16, 17, 18, 24, 26])
def test_u27_sleep_routes_to_youth_referrals_with_rossplatz_first(age: int) -> None:
    decision = decide(interpretation(Need.SLEEP, age=age, gender="female"))
    assert ids(decision)[0] == "17.1"
    assert decision.mandatory_candidates[0].offer_id == "17.1"
    assert all(item.role == CandidateRole.REFERRAL_CONTACT for item in decision.candidates)
    assert "8" not in ids(decision)
    if age < 18:
        assert "8" not in conditional_ids(decision)
    else:
        assert "8" in conditional_ids(decision)


def test_age_27_ends_u27_priority_and_unknown_or_young_does_not_create_numeric_age() -> None:
    adult = decide(interpretation(Need.SLEEP, age=27, gender="male"))
    assert ids(adult)[0] == "7"
    assert not any(item.offer_id.startswith("17.") for item in adult.candidates)
    young = decide(
        interpretation(Need.SLEEP, hints=[{"field": "age", "value": "young"}])
    )
    assert young.facts_used.age is None
    assert ids(young)[0] == "7"


def test_woman_sleep_uses_scharni_only_when_adult_and_keeps_curated_geometry_state() -> None:
    adult = decide(interpretation(Need.SLEEP, age=30, gender="female"))
    assert ids(adult) == ["8"]
    scharni = next(offer for offer in OFFERS if offer.id == "8")
    assert scharni.address == "Georg-Schumann-Str. 268, 04159 Leipzig"
    assert scharni.geometry is None
    assert scharni.coordinates_status == "not_verified_after_address_change"
    minor = decide(interpretation(Need.SLEEP, age=17, gender="female"))
    assert "8" not in ids(minor) + conditional_ids(minor)


def test_male_sleep_ruecke_precedes_helene_and_helene_requires_explicit_trigger() -> None:
    ordinary = decide(interpretation(Need.SLEEP, age=30, gender="male"))
    assert ids(ordinary)[0] == "7"
    assert "23" in conditional_ids(ordinary)
    after_21 = decide(interpretation(Need.SLEEP, age=30, gender="male", time="21:30"))
    assert ids(after_21)[:2] == ["7", "23"]
    no_benefit = decide(interpretation(Need.SLEEP, age=30, gender="male", no_benefit="yes"))
    assert "23" in ids(no_benefit)
    tonight = decide(interpretation(Need.SLEEP, age=30, gender="male", day="tonight"))
    assert "23" not in ids(tonight)

    late_now = SELECTOR.select(
        interpretation(Need.SLEEP, age=30, gender="male"),
        OFFERS,
        now=NOW.replace(hour=22),
    )
    assert "23" in ids(late_now)


def test_drug_specific_offers_require_explicit_drug_use_and_alias_does_not_infer_it() -> None:
    unknown = decide(interpretation(Need.SLEEP, age=30), query="Schoppi schlafen")
    assert ids(unknown) == []
    assert conditional_ids(unknown) == ["6"]
    explicit = decide(interpretation(Need.SLEEP, age=30, drug_use="yes"), query="Schoppi schlafen")
    assert ids(explicit) == ["6"]
    day_offer = decide(
        interpretation(Need.ADVICE, age=30, drug_use="yes", services=[RequestedService.COUNSELLING]),
        query="Schoppi Beratung",
    )
    assert ids(day_offer) == ["11"]


def test_mobile_alias_never_guesses_team_but_gruenau_narrows_for_u27() -> None:
    ambiguous = decide(interpretation(Need.ADVICE, age=24), query="Kübel Beratung")
    assert ids(ambiguous) == []
    assert set(conditional_ids(ambiguous)) == {"19.1", "19.2", "19.3"}
    narrowed = decide(interpretation(Need.ADVICE, age=24, district="Grünau"), query="Kübel in Grünau")
    assert ids(narrowed) == ["19.2"]
    assert ReasonCode.DISTRICT_ALIAS_MATCH in narrowed.candidates[0].reason_codes


def test_suedpol_alias_needs_a_district_and_connewitz_selects_its_curated_team() -> None:
    ambiguous = decide(interpretation(Need.ADVICE, age=24), query="Südpol Beratung")
    assert ids(ambiguous) == []
    assert set(conditional_ids(ambiguous)) == {"20.1", "20.2"}

    narrowed = decide(
        interpretation(Need.ADVICE, age=24, district="Connewitz"),
        query="Südpol in Connewitz",
    )
    assert ids(narrowed) == ["20.1"]
    assert ReasonCode.DISTRICT_ALIAS_MATCH in narrowed.candidates[0].reason_codes


def test_u27_primary_contact_priority_is_catalog_data_not_a_hardcoded_offer_id() -> None:
    renamed = [
        offer.model_copy(update={"id": "99.1"}) if offer.id == "17.1" else offer
        for offer in OFFERS
    ]
    decision = SELECTOR.select(
        interpretation(Need.SLEEP, age=24, gender="female"),
        renamed,
        now=NOW,
    )

    assert ids(decision)[0] == "99.1"
    assert "u27_primary_contact" in next(
        offer.priority_rules for offer in renamed if offer.id == "99.1"
    )


@pytest.mark.parametrize(
    ("service", "expected"),
    [
        (RequestedService.FOOD, {"9", "10", "14", "16", "18", "21", "22"}),
        (RequestedService.HYGIENE, {"9", "10", "16"}),
        (RequestedService.SHOWER, {"9", "10", "17.1", "17.2", "17.3", "18", "19.1", "19.2", "19.3"}),
        (RequestedService.LAUNDRY, {"9", "10", "17.1", "17.2", "17.3", "18", "19.1", "19.2", "19.3"}),
        (RequestedService.CLOTHING, {"9", "14", "16", "19.1", "19.2", "19.3", "21", "22"}),
        (RequestedService.POSTAL, {"9", "10", "17.1", "17.2", "17.3", "18"}),
    ],
)
def test_basic_needs_use_only_positive_capability_evidence(service: RequestedService, expected: set[str]) -> None:
    decision = decide(interpretation(Need.GENERAL_HELP, services=[service], age=24))
    assert set(ids(decision)) == expected


def test_water_is_not_food_and_uses_only_documented_drinks_or_water() -> None:
    decision = decide(interpretation(Need.DRINKING_WATER, services=[RequestedService.DRINKING_WATER]))
    assert set(ids(decision)) == {"16", "21", "22"}
    assert {"7", "11"} <= set(conditional_ids(decision))
    assert all(offer_id not in {"1", "2", "3", "4"} for offer_id in ids(decision))
    assert all(next(offer for offer in OFFERS if offer.id == offer_id).place_type != "drinking_fountain" for offer_id in ids(decision))


def test_food_need_ignores_age_restriction_even_when_offer_requires_adults() -> None:
    """Fachliche Klarstellung des Nutzers: Essensausgaben sind für alle, auch

    wenn dieselbe Streetwork-Organisation für Beratung eine Altersgrenze hat.
    Angebot 14 (Schwanenteich, Dienstag 17-18 Uhr) hat minimum_age=18, darf
    aber bei einer reinen Essensfrage nicht daran scheitern.
    """
    tuesday_before_1800 = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    value = interpretation(Need.FOOD)
    context = build_selection_context(
        query="", interpretation=value, offers=OFFERS, organization_aliases=ORGANIZATION_ALIASES, ui_category=None
    )
    decision = SELECTOR.select(value, OFFERS, context=context, now=tuesday_before_1800)
    assert "14" in ids(decision)
    item = next(item for item in decision.candidates if item.offer_id == "14")
    assert ReasonCode.AGE_NOT_ESTABLISHED not in item.reason_codes
    assert RuleCode.FOOD_AGE_UNRESTRICTED in decision.applied_rules

    advice = interpretation(Need.ADVICE)
    advice_context = build_selection_context(
        query="", interpretation=advice, offers=OFFERS, organization_aliases=ORGANIZATION_ALIASES, ui_category=None
    )
    advice_decision = SELECTOR.select(advice, OFFERS, context=advice_context, now=tuesday_before_1800)
    assert "14" in conditional_ids(advice_decision)
    advice_item = next(item for item in advice_decision.conditional_candidates if item.offer_id == "14")
    assert ReasonCode.AGE_NOT_ESTABLISHED in advice_item.reason_codes


def test_medical_distinguishes_care_access_and_mobile_schedule() -> None:
    generic = decide(interpretation(Need.MEDICAL))
    assert set(ids(generic)) == {"10", "24", "25"}
    assert "15" in conditional_ids(generic)
    saturday = decide(interpretation(Need.MEDICAL, day="saturday"))
    assert "25" not in ids(saturday)
    wound = decide(interpretation(Need.MEDICAL, services=[RequestedService.WOUND_CARE], age=30, drug_use="yes"))
    assert ids(wound) == ["11"]


def test_alternative_three_requires_explicit_drug_use_and_proven_sleep_capability() -> None:
    unknown = decide(interpretation(Need.SLEEP, age=30))
    explicit = decide(interpretation(Need.SLEEP, age=30, drug_use="yes"))

    assert "5" not in ids(unknown)
    assert "5" in conditional_ids(unknown)
    assert "5" in ids(explicit)


def test_general_help_is_referral_plus_clarification_and_toilet_is_unsupported() -> None:
    general = decide(interpretation(Need.GENERAL_HELP))
    assert general.selection_status == SelectionStatus.CLARIFICATION_RECOMMENDED
    assert ids(general)[0] == "21"
    assert general.candidates[0].role == CandidateRole.REFERRAL_CONTACT
    toilet = decide(interpretation(Need.TOILET))
    assert toilet.selection_status == SelectionStatus.UNSUPPORTED_NEED
    assert ids(toilet) == []


def test_acute_risk_cannot_reach_selector_and_interpreter_failure_is_explicit() -> None:
    with pytest.raises(ValueError, match="acute risk"):
        decide(interpretation(Need.MEDICAL, risk=AcuteRiskStatus.DETECTED))
    unavailable = SELECTOR.interpreter_unavailable(OFFERS)
    assert unavailable.selection_status == SelectionStatus.INTERPRETER_UNAVAILABLE
    assert not unavailable.candidates


def test_unvalidated_district_and_unsupported_conditions_do_not_claim_suitability() -> None:
    district = decide(interpretation(Need.ADVICE, age=30, district="Connewitz"))
    assert RuleCode.DISTRICT_RECORDED_NOT_VALIDATED in district.applied_rules
    animal = decide(
        interpretation(Need.SLEEP, hints=[{"field": "other", "value": "mit Hund"}])
    )
    assert animal.selection_status == SelectionStatus.CLARIFICATION_RECOMMENDED
    assert animal.unsupported_conditions == ["mit Hund"]

    pair = decide(
        interpretation(Need.SLEEP, hints=[{"field": "other", "value": "als Paar"}])
    )
    assert pair.selection_status == SelectionStatus.CLARIFICATION_RECOMMENDED
    assert pair.unsupported_conditions == ["als Paar"]


def test_queer_and_no_money_do_not_infer_gender_or_benefit_entitlement() -> None:
    queer = decide(
        interpretation(Need.SLEEP, hints=[{"field": "gender", "value": "queer"}])
    )
    no_money = decide(
        interpretation(
            Need.SLEEP,
            age=30,
            gender="male",
            hints=[{"field": "other", "value": "kein Geld"}],
        )
    )

    assert queer.facts_used.gender.value == "unknown"
    assert ids(queer)[0] == "7"
    assert no_money.facts_used.no_social_benefit_entitlement.value == "unknown"
    assert "23" not in ids(no_money)


def test_reason_and_rule_code_contracts_are_stable_and_machine_readable() -> None:
    assert {item.value for item in ReasonCode} == {
        "need_capability_match",
        "referral_need_match",
        "alias_match",
        "district_alias_match",
        "explicit_target_match",
        "general_sleep_contact_priority",
        "u27_referral_priority",
        "u27_supplemental_only",
        "curated_priority",
        "documented_schedule",
        "need_not_supported",
        "target_group_mismatch",
        "age_not_established",
        "age_outside_range",
        "gender_not_established",
        "drug_use_not_explicit",
        "drug_use_mismatch",
        "helene_access_not_established",
        "time_condition_not_met",
        "alias_scope_mismatch",
        "ambiguous_organization_alias",
    }
    assert all(value.value == value.value.casefold() and " " not in value.value for value in RuleCode)


@pytest.mark.parametrize("language", ["de", "en", "pl", "ro", "ru"])
def test_language_does_not_change_same_structured_selection(language: str) -> None:
    decision = decide(interpretation(Need.SLEEP, age=30, gender="female", language=language))
    assert ids(decision) == ["8"]


def test_names_raw_text_and_source_index_are_not_candidate_rule_inputs() -> None:
    changed: list[OfferRecord] = [
        offer.model_copy(update={"name": f"renamed-{offer.id}", "raw_text": "irrelevant", "source_index": 999})
        for offer in OFFERS
    ]
    value = interpretation(Need.SLEEP, age=30, gender="female")
    original = SELECTOR.select(value, OFFERS, now=NOW)
    mutated = SELECTOR.select(value, changed, now=NOW)
    assert ids(original) == ids(mutated) == ["8"]
