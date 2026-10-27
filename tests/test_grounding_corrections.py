"""Correct variants and counterexamples through the productive prose validator."""

import pytest

from app.formulation import AnswerType, BindingPolicy, ClaimType, EvidenceFact, FactType, FormulatorError
from app.formulator_prose import GroundedFormulatorResponse
from app.grounding import validate_formulation
from app.grounding_constraints import contradicts_age_bound
from app.grounding_schedules import fact_schedule_matches
from app.grounding_values import mask_known_phones
from app.interpreter import Need
from app.models import Language
from test_grounding_claims import _answer, _evidence, app


def packet(app, language, values, *, need=Need.MEDICAL):
    evidence = _evidence(app, language=language, need=need)
    offer = evidence.selected_offers[0]
    offer.display_name = "Probe"
    offer.facts = [EvidenceFact(fact_id=f"f_{index:016x}", fact_type=kind, value=value)
                   for index, (kind, value) in enumerate([(FactType.DISPLAY_NAME, "Probe"), *values], 1)]
    return evidence


def response(evidence, text, claim=ClaimType.FACT):
    offer = evidence.selected_offers[0]
    raw = _answer(evidence, (text, claim, offer.offer_id, [f.fact_id for f in offer.facts])).model_dump(mode="json")
    raw['contract_version'] = '7'
    return GroundedFormulatorResponse.model_validate(raw)


@pytest.mark.parametrize("phone", ["0341 420920-0", "0341 420920‑0", "0341-420920-0", "03414209200"])
def test_equivalent_complete_phone_formats_pass(app, phone):
    evidence = packet(app, Language.EN, [(FactType.PHONE, "0341 420920-0 (Frau Beispiel)")])
    answer = response(evidence, f"Call Probe at {phone}.", ClaimType.ACTION)
    assert validate_formulation(answer, evidence).answer == answer.sentences[0].text


@pytest.mark.parametrize("phone", ["0341 420920-1", "420920-0", "0341 999999-0", "+49 341 4209200"])
def test_changed_or_shortened_phone_does_not_pass(app, phone):
    evidence = packet(app, Language.EN, [(FactType.PHONE, "0341 420920-0 (Frau Beispiel)")])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, f"Call Probe at {phone}.", ClaimType.ACTION), evidence)


def test_house_number_and_postcode_are_not_joined_into_a_phone():
    text = "Plautstr. 18 (04179 Leipzig)"
    assert mask_known_phones(text, ["0341 1234502"])[1] is False


@pytest.mark.parametrize("language,restriction", [
    (Language.DE, "während der Einsatzzeiten"),
    (Language.EN, "during deployment times"),
    (Language.PL, "w godzinach pracy"),
    (Language.RO, "în timpul orelor de intervenție"),
    (Language.RU, "в часы их работы"),
])
def test_operating_condition_can_be_localized_but_not_omitted(app, language, restriction):
    evidence = packet(app, language, [(FactType.PHONE, "0152 33661087 (nur zu Einsatzzeiten des Busses)")])
    # Use a language-neutral contact heading; the restriction itself is localized.
    answer = response(evidence, f"Probe: 0152 33661087 ({restriction}).", ClaimType.ACTION)
    assert validate_formulation(answer, evidence).answer
    answer.sentences[0].text = "Probe: 0152 33661087."
    with pytest.raises(FormulatorError):
        validate_formulation(answer, evidence)


@pytest.mark.parametrize("amount", ["5 €", "5.0 €", "5.00 €", "5,00 €"])
def test_euro_format_is_numeric_but_service_stays_bound(app, amount):
    evidence = packet(app, Language.EN, [(FactType.SERVICE, "Overnight accommodation (5,00 €)"),
                                        (FactType.SERVICE, "Laundry (2,50 €)")])
    assert validate_formulation(response(evidence, f"Probe: overnight accommodation ({amount}).", ClaimType.SERVICE), evidence).answer
    for text in (f"Probe: laundry ({amount}).", "Probe: overnight accommodation (50 €)."):
        with pytest.raises(FormulatorError):
            validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence)


@pytest.mark.parametrize("language,correct,wrong", [
    (Language.DE, "Alter 14-17", "Alter 12-17"),
    (Language.EN, "aged 14-17", "aged 14-18"),
    (Language.PL, "od 14 do 17 lat", "od 12 do 17 lat"),
    (Language.RO, "între 14 și 17 ani", "între 14 și 18 ani"),
    (Language.RU, "от 14 до 17 лет", "от 12 до 17 лет"),
])
def test_complete_age_range_is_checked_in_each_language(language, correct, wrong):
    facts = [("minimum_age", "14"), ("maximum_age", "17")]
    assert not contradicts_age_bound(correct, facts, language)
    assert contradicts_age_bound(wrong, facts, language)


def test_contact_under_is_not_a_german_age_limit():
    facts = [("minimum_age", "18"), ("phone", "0341 1234502")]
    assert not contradicts_age_bound("Kontaktiere uns unter 0341 1234502.", facts, Language.DE)
    assert contradicts_age_bound("Für Frauen unter 18, Telefon 0341 1234502.", facts, Language.DE)


def test_time_window_works_without_service_word_coverage(app):
    evidence = packet(app, Language.RU, [(FactType.SERVICE, "Почтовый адрес"),
                                        (FactType.NOTE, "Среда: 12:30 - 14:00 ч")])
    answer = response(evidence, "Probe: почтовый адрес, среда 12:30–14:00.")
    assert validate_formulation(answer, evidence).answer
    for text in ("Probe: почтовый адрес, среда 14:00–12:30.",
                 "Probe: почтовый адрес, четверг 12:30–14:00.",
                 "Probe: почтовый адрес, среда 12:30–15:00."):
        with pytest.raises(FormulatorError):
            validate_formulation(response(evidence, text), evidence)


def test_day_cannot_be_borrowed_from_a_different_window():
    facts = [("opening_time", "Monday 09:00-18:00"), ("opening_time", "Sunday 13:30-18:00")]
    assert fact_schedule_matches("Monday 09:00-18:00; Sunday 13:30-18:00.", facts, Language.EN)
    assert not fact_schedule_matches("Sunday 09:00-18:00.", facts, Language.EN)
    assert not fact_schedule_matches("Sun 09:00-18:00.", facts, Language.EN)


def test_english_window_can_use_german_infrastructure_facts():
    facts = [("opening_time", "Montag - Freitag: 09:00 - 18:00 Uhr"),
             ("opening_time", "Sonntag: 13:30 - 18:00 Uhr")]
    assert fact_schedule_matches("Open Mon-Fri 09:00-18:00 and Sun 13:30-18:00.", facts, Language.EN)
    assert not fact_schedule_matches("Open Sun 09:00-18:00.", facts, Language.EN)


@pytest.mark.parametrize("language,text", [
    (Language.EN, "Probe: medical help at Nürnberger Straße 31."),
    (Language.PL, "Probe: pomoc przy Nürnberger Straße 31."),
])
def test_sourced_street_inside_a_note_is_not_foreign_prose(app, language, text):
    evidence = packet(app, language, [(FactType.NOTE, "Termin in Nürnberger Straße 31"),
                                        (FactType.SERVICE, "medical care")])
    assert validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence).answer


def test_real_german_clause_in_english_text_is_rejected(app):
    evidence = packet(app, Language.EN, [(FactType.PHONE, "0341 1234502")])
    with pytest.raises(FormulatorError, match="formulator_invalid_language"):
        validate_formulation(response(evidence, "Probe: Du kannst sie unter 0341 1234502 erreichen.", ClaimType.ACTION), evidence)


@pytest.mark.parametrize("language,text", [
    (Language.EN, "Sorry, I can’t help with that request."),
    (Language.EN, "Sorry, I can't help with that request."),
    (Language.DE, "Ich kann dir dabei leider nicht helfen."),
])
def test_clear_boundary_variants_are_accepted_but_missing_boundary_is_not(app, language, text):
    evidence = _evidence(app, language=language, offer_ids=(), answer_type=AnswerType.OUT_OF_SCOPE)
    from app.formulation import FormulatedSentence
    raw = {'contract_version': '7', 'language': language.value, 'sentences': [
        FormulatedSentence(text=text, claim_type=ClaimType.DOMAIN_BOUNDARY,
                           policy_ids=[BindingPolicy.OUT_OF_SCOPE_BOUNDARY]).model_dump(mode='json')], 'card_ids': []}
    answer = GroundedFormulatorResponse.model_validate(raw)
    assert validate_formulation(answer, evidence).answer == text
    answer.sentences[0].text = "Probe."
    with pytest.raises(FormulatorError):
        validate_formulation(answer, evidence)
