"""Presentation freedom must not authorize unsupported factual assertions."""
import pytest

from app.candidate_contract import CandidateRole
from app.formulation import (
    AnswerType, BindingPolicy, ClaimType, EvidenceFact, FactType,
    FormulatedSentence, FormulatorError, GroundingDiagnosticCode,
)
from app.grounding import validate_formulation
from app.grounding_claims import detect_service_concepts
from app.grounding_constraints import contradicts_age_bound, schedule_matches
from app.interpreter import Need
from app.models import Language
from test_formulation import app, _evidence, _fact, _response


def test_multiple_grounded_sentences_in_one_block_and_false_counterexample(app):
    evidence = _evidence(app)
    address = _fact(evidence, FactType.ADDRESS)
    response = _response(evidence, text=f"Nutze Übernachtungshaus für wohnungslose Frauen. Adresse: {address.value}.")
    result = validate_formulation(response, evidence)
    assert result.answer == response.sentences[0].text
    assert "multiple_sentences_in_block" in result.reference_assessment["presentation_observations"]
    response.sentences[0].text = "Nutze Übernachtungshaus für wohnungslose Frauen. Adresse: Fantasiestraße 99999."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_characterizes_unchecked_extra_service_in_a_longer_grounded_block(app):
    evidence = _evidence(app)
    address = _fact(evidence, FactType.ADDRESS).value
    phone = _fact(evidence, FactType.PHONE).value
    hours = _fact(evidence, FactType.OPENING_TIME).value
    text = ("Nutze Übernachtungshaus für wohnungslose Frauen. Übernachtungshaus für wohnungslose Frauen bietet einen Schlafplatz und Grundversorgung mit Essen, Kleidung und Hygiene. "
            f"Adresse: {address}. Telefon: {phone}. Öffnungszeiten: {hours}.")
    assert 220 < len(text) < 550
    response = _response(evidence, text=text)
    assert validate_formulation(response, evidence).answer == text
    response.sentences[0].text += " Übernachtungshaus für wohnungslose Frauen bietet Wundversorgung an."
    assert validate_formulation(response, evidence).answer == response.sentences[0].text  # Deliberately unchecked lexical support.


def test_multiple_blocks_share_the_600_character_total_budget(app):
    evidence = _evidence(app)
    response = _response(evidence, text="Nutze Übernachtungshaus für wohnungslose Frauen. " * 10)
    response.sentences.append(response.sentences[0].model_copy())
    with pytest.raises(FormulatorError, match="formulator_contract_violation"):
        validate_formulation(response, evidence)


def test_grounded_fact_can_answer_first_without_forced_action(app):
    evidence = _evidence(app)
    address = _fact(evidence, FactType.ADDRESS)
    response = _response(evidence, text=f"Übernachtungshaus für wohnungslose Frauen: {address.value}", claim_type=ClaimType.FACT)
    assert validate_formulation(response, evidence).answer == response.sentences[0].text


@pytest.mark.parametrize("hyphen", ["\u2010", "\u2011", "\ufe63", "\uff0d"])
def test_name_typography_does_not_change_identity(app, hyphen):
    offer = app.state.kb.by_id()["8"].model_copy(update={"display_name": "Kontakt-Test"})
    evidence = _evidence(app, offers=[offer])
    response = _response(evidence, text=f"Nutze Kontakt{hyphen}Test.")
    assert validate_formulation(response, evidence).answer == response.sentences[0].text
    response.sentences[0].text = f"Nutze Kontakt{hyphen}Tests."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("language,text,wrong", [
    (Language.RO, "LENA nu poate răspunde la această întrebare.", "LENA poate răspunde la această întrebare."),
    (Language.DE, "Dabei kann ich dir nicht helfen.", "Dabei kann ich dir helfen."),
    (Language.EN, "I cannot answer that question.", "I can answer that question."),
])
def test_short_boundary_needs_no_domain_list_but_must_express_boundary(app, language, text, wrong):
    evidence = _evidence(app, offers=[], answer_type=AnswerType.OUT_OF_SCOPE,
                         language=language, need=Need.UNKNOWN)
    response = _response(evidence, text=text, claim_type=ClaimType.DOMAIN_BOUNDARY,
                         policy_ids=[BindingPolicy.OUT_OF_SCOPE_BOUNDARY])
    assert validate_formulation(response, evidence).answer == text
    response.sentences[0].text = wrong
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def _fee_packet(app, language=Language.DE, status="paid"):
    evidence = _evidence(app, need=Need.TOILET, language=language)
    offer = evidence.selected_offers[0]
    offer.display_name = "Testtoilette"
    offer.facts = [
        EvidenceFact(fact_id="f_1000000000000001", fact_type=FactType.DISPLAY_NAME, value="Testtoilette"),
        EvidenceFact(fact_id="f_1000000000000002", fact_type=FactType.SERVICE, value="Öffentliche Toilette"),
        EvidenceFact(fact_id="f_1000000000000003", fact_type=FactType.FEE_STATUS, value=status),
        EvidenceFact(fact_id="f_1000000000000004", fact_type=FactType.FEE, value="50 cent (cash or card)"),
    ]
    return evidence


def test_fee_may_be_omitted_but_wrong_amount_stays_rejected(app):
    evidence = _fee_packet(app)
    response = _response(evidence, text="Nutze Testtoilette.")
    assert validate_formulation(response, evidence).card_ids == ["8"]
    response.sentences[0].text = "Testtoilette kostet 5 cent."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("language,text", [
    (Language.DE, "Testtoilette ist kostenlos."),
    (Language.EN, "Testtoilette is free."),
    (Language.PL, "Testtoilette jest bezpłatna."),
    (Language.RO, "Testtoilette este gratuită."),
    (Language.RU, "Testtoilette бесплатна."),
])
@pytest.mark.parametrize("status", ["paid", "unknown", "free"])
def test_explicit_free_claim_requires_verified_free_status(app, language, text, status):
    evidence = _fee_packet(app, language, status)
    response = _response(evidence, text=text)
    if status == "free":
        assert validate_formulation(response, evidence).answer == text
    else:
        with pytest.raises(FormulatorError) as error:
            validate_formulation(response, evidence)
        assert error.value.diagnostic_code == GroundingDiagnosticCode.FEE_CLAIM_UNSUPPORTED


def test_operational_service_label_requires_content_support_not_just_a_time(app):
    evidence = _evidence(app, offer_ids=("21",), need=Need.GENERAL_HELP,
                         answer_type=AnswerType.AMBIGUOUS_HELP_FALLBACK,
                         roles={"21": CandidateRole.REFERRAL_CONTACT})
    response = _response(evidence, text="Melde dich bei Hilfebus.", claim_type=ClaimType.REFERRAL)
    time = _fact(evidence, FactType.OPENING_TIME, contains="18:00")
    response.sentences.append(FormulatedSentence(
        text="Der Bus fährt täglich von 18:00 bis 23:00 Uhr (Einsatzzeiten).",
        claim_type=ClaimType.SERVICE, offer_id="21", fact_ids=[time.fact_id],
    ))
    assert validate_formulation(response, evidence).sentence_count == 2
    for wrong in (
        "Der Bus fährt täglich von 23:00 bis 18:00 Uhr.",
        "Der Bus bietet Zimmer täglich von 18:00 bis 23:00 Uhr.",
        "Der Bus bietet Essen täglich von 18:00 bis 23:00 Uhr.",
    ):
        response.sentences[-1].text = wrong
        with pytest.raises(FormulatorError):
            validate_formulation(response, evidence)


def test_romanian_changing_table_is_not_food_but_an_actual_meal_is(app):
    assert "food" not in detect_service_concepts("Masă de înfășat", Language.RO)
    assert "food" in detect_service_concepts("Masă de înfășat și masă caldă", Language.RO)
    evidence = _fee_packet(app, Language.RO)
    evidence.selected_offers[0].facts.append(EvidenceFact(
        fact_id="f_1000000000000005", fact_type=FactType.FACILITY, value="Fără bariere",
    ))
    response = _response(evidence, text="Testtoilette este o toaletă publică, fără bariere.", claim_type=ClaimType.SERVICE)
    assert validate_formulation(response, evidence).answer == response.sentences[0].text
    response.sentences[0].text = "Testtoilette nu este o toaletă publică, fără bariere."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_polish_age_range_keeps_both_bounds_and_the_exclusive_upper_bound():
    facts = [("minimum_age", "14"), ("maximum_age", "17")]
    assert not contradicts_age_bound("od 14 do poniżej 18 lat", facts, Language.PL)
    assert contradicts_age_bound("od 13 do poniżej 18 lat", facts, Language.PL)
    assert contradicts_age_bound("od 14 do 18 lat", facts, Language.PL)


def test_weekday_abbreviations_preserve_ranges_and_time_direction():
    condition = "Montag bis Freitag 16:00 - 08:00 Uhr"
    assert schedule_matches("Mo-Fr 16:00-08:00", condition, Language.DE, complete=True)
    assert schedule_matches("Dienstag 16:00-08:00", condition, Language.DE, complete=True)
    assert not schedule_matches("Sa-So 16:00-08:00", condition, Language.DE, complete=True)
    assert not schedule_matches("Mo-Fr 08:00-16:00", condition, Language.DE, complete=True)


@pytest.mark.parametrize("language,wrong,right,condition", [
    (Language.DE, "montags", "sonntags", "Sonntag 20:00-21:00"),
    (Language.EN, "Mondays", "Sundays", "Sunday 20:00-21:00"),
])
def test_weekday_inflection_never_erases_a_wrong_day(language, wrong, right, condition):
    assert not schedule_matches(f"{wrong} 20:00-21:00", condition, language, complete=False)
    assert schedule_matches(f"{right} 20:00-21:00", condition, language, complete=False)


def test_inflected_weekday_range_cannot_be_supported_by_only_two_endpoints():
    assert not schedule_matches("montags bis freitags 20:00-21:00",
                                "Montag, Freitag 20:00-21:00", Language.DE, complete=False)


def test_full_validator_rejects_monday_food_for_the_sunday_hilfebus_service(app):
    evidence = _evidence(app, offer_ids=("21",), need=Need.FOOD)
    response = _response(evidence, text="Hilfebus: Essensausgabe sonntags 20:00-21:00.", claim_type=ClaimType.SERVICE)
    assert validate_formulation(response, evidence).answer == response.sentences[0].text
    response.sentences[0].text = "Hilfebus: Essensausgabe montags 20:00-21:00."
    with pytest.raises(FormulatorError) as error:
        validate_formulation(response, evidence)
    assert error.value.diagnostic_code == GroundingDiagnosticCode.SERVICE_CONDITION_MISMATCH


def test_payment_method_can_be_omitted_but_not_invented_or_excluded(app):
    evidence = _fee_packet(app, Language.EN)
    response = _response(evidence, text="Use Testtoilette; payment by cash.")
    assert validate_formulation(response, evidence).answer == response.sentences[0].text
    response.sentences[0].text = "Use Testtoilette; cash only."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)
    evidence.selected_offers[0].facts[-1].value = "50 cent (cash)"
    response.sentences[0].text = "Use Testtoilette; payment by card."
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_accessibility_and_ui_card_reference_are_not_fee_claims(app):
    evidence = _fee_packet(app, Language.EN)
    evidence.selected_offers[0].facts[-1].value = "50 cent (cash)"
    evidence.selected_offers[0].facts.append(EvidenceFact(
        fact_id="f_1000000000000005", fact_type=FactType.FACILITY, value="Barrier-free",
    ))
    response = _response(evidence, text="Use Testtoilette; barrier-free. More information is in the card.")
    assert validate_formulation(response, evidence).answer == response.sentences[0].text
