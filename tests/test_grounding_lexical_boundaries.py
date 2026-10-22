"""Bounded regressions for the four observed lexical grounding false alarms."""

import pytest

from app.formulation import EvidenceFact, FactType, FormulatorError
from app.grounding import _contains_sentence_break, validate_formulation
from app.grounding_claims import ClaimSupport, assess_service_claim
from app.grounding_constraints import contains_fee_literal
from app.models import Language
from app.interpreter import Need
from app.formulation import ClaimType
from test_grounding_claims import _answer, _evidence, _fact, app


@pytest.mark.parametrize("food", ["Imbiss", "Mittagessen", "Imbiss‑Mittagessen", "Imbiss-Mittagessen"])
def test_evidenced_german_food_compounds_pass_real_validator(app, food):
    evidence = _evidence(app, offer_ids=("9",), need=Need.FOOD)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    response = _answer(evidence,
        (f"Nutze „{name.value}“.", ClaimType.ACTION, "9", [name.fact_id]),
        (f"Es gibt {food}.", ClaimType.SERVICE, "9", [name.fact_id]),
    )
    assert validate_formulation(response, evidence).sentence_count == 2


@pytest.mark.parametrize("food", ["Imbiss", "Mittagessen", "Imbiss‑Mittagessen"])
def test_food_compound_needs_its_own_offer_service_evidence(app, food):
    evidence = _evidence(app, offer_ids=("9",), need=Need.FOOD)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    evidence.selected_offers[0].facts = [name]
    response = _answer(evidence, (f"{name.value}: {food}.", ClaimType.ACTION, "9", [name.fact_id]))
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def _packet(app, language, offer_id, name, need, values):
    evidence = _evidence(app, offer_ids=("22",), language=language, need=need)
    offer = evidence.selected_offers[0]
    offer.offer_id = offer_id
    offer.display_name = name
    offer.facts = [EvidenceFact(
        fact_id=f"f_{index:016x}", fact_type=kind, value=value,
    ) for index, (kind, value) in enumerate([(FactType.DISPLAY_NAME, name), *values], 1)]
    return evidence


def _water_packet(app):
    return _packet(app, Language.RU, "drinking_fountain:katharinenstrasse", "Katharinenstraße",
        Need.DRINKING_WATER, [
            (FactType.SERVICE, "Kostenloser Trinkwasserbrunnen"),
            (FactType.POTABLE_WATER_STATUS, "verified"),
            (FactType.AIR_DISTANCE, "605 m Entfernung vom Leipzig Hauptbahnhof"),
        ])


@pytest.mark.parametrize("fountain", ["фонтан", "фонтана", "фонтаны"])
def test_russian_fountain_is_supported_by_verified_water_packet(app, fountain):
    evidence = _water_packet(app)
    offer = evidence.selected_offers[0]
    response = _answer(evidence, (
        f"Ближайший бесплатный {fountain} — «Katharinenstraße», 605 m Entfernung vom Leipzig Hauptbahnhof.",
        ClaimType.SERVICE, offer.offer_id, [offer.facts[0].fact_id],
    ))
    assert validate_formulation(response, evidence).sentence_count == 1


@pytest.mark.parametrize("values", [
    [("service", "Декоративный фонтан")],
    [("display_name", "Trinkwasserbrunnen"), ("potable_water_status", "verified")],
    [("service", "Kostenloser Trinkwasserbrunnen"), ("potable_water_status", "unknown")],
    [("service", "Kostenloser Trinkwasserbrunnen")],
])
def test_russian_fountain_requires_typed_verification_and_service_support(values):
    assert assess_service_claim("Ближайший фонтан.", values, Language.RU)[0] is ClaimSupport.UNDECIDABLE


def _toilet_packet(app, *, facility=True):
    values = [(FactType.SERVICE, "Öffentliche Toilette")]
    if facility:
        values.append((FactType.FACILITY, "bez barier"))
    return _packet(app, Language.PL, "toilet:0005", "Goethestraße (Schwanenteich)", Need.TOILET, values)


def test_evidenced_barrier_free_facility_does_not_negate_toilet_service(app):
    evidence = _toilet_packet(app)
    offer = evidence.selected_offers[0]
    response = _answer(evidence,
        ("Skorzystaj z „Goethestraße (Schwanenteich)”.", ClaimType.ACTION, offer.offer_id, [offer.facts[0].fact_id]),
        ("Toaleta publiczna, bez barier.", ClaimType.SERVICE, offer.offer_id, [offer.facts[0].fact_id]),
    )
    assert validate_formulation(response, evidence).sentence_count == 2


@pytest.mark.parametrize("text,facility", [
    ("Toaleta publiczna, bez barier.", False),
    ("To nie jest toaleta publiczna, bez barier.", True),
    ("Bez barier i toalet.", True),
    ("Bez barier oraz toalety.", True),
    ("Bez barier / toalet.", True),
])
def test_facility_exception_does_not_hide_other_negation_or_missing_evidence(app, text, facility):
    evidence = _toilet_packet(app, facility=facility)
    offer = evidence.selected_offers[0]
    response = _answer(evidence,
        ("Skorzystaj z „Goethestraße (Schwanenteich)”.", ClaimType.ACTION, offer.offer_id, [offer.facts[0].fact_id]),
        (text, ClaimType.SERVICE, offer.offer_id, [offer.facts[0].fact_id]),
    )
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("text", ["Kontakt: tel. 0800 44 6666 02.", "Kontakt: tel. +49 341 123456."])
def test_telephone_abbreviation_before_number_is_not_a_sentence_break(text):
    assert _contains_sentence_break(text) is False


def _toilet_phone_response(app):
    evidence = _toilet_packet(app)
    offer = evidence.selected_offers[0]
    offer.facts.extend([
        EvidenceFact(fact_id="f_0000000000000010", fact_type=FactType.PHONE, value="0800 44 6666 02"),
        EvidenceFact(fact_id="f_0000000000000011", fact_type=FactType.FEE, value="50 centów (gotówka lub karta)"),
        EvidenceFact(fact_id="f_0000000000000012", fact_type=FactType.FEE_STATUS, value="paid"),
    ])
    text = "Skorzystaj z „Goethestraße (Schwanenteich)”, płatna toaleta (50 centów, gotówka lub karta), bez barier, all‑gender, z przewijakiem, tel. 0800 44 6666 02."
    response = _answer(evidence, (text, ClaimType.ACTION, offer.offer_id, [offer.facts[0].fact_id]))
    return evidence, response


def test_recorded_toilet_sentence_with_known_telephone_passes_full_validator(app):
    evidence, response = _toilet_phone_response(app)
    assert validate_formulation(response, evidence).sentence_count == 1


@pytest.mark.parametrize("change", ["unknown_phone", "wrong_fee"])
def test_telephone_fix_keeps_value_and_sentence_validation(app, change):
    evidence, response = _toilet_phone_response(app)
    if change == "unknown_phone":
        response.sentences[0].text = response.sentences[0].text.replace("0800 44 6666 02", "0800 44 9999 02")
    else:
        response.sentences[0].text = response.sentences[0].text.replace("50 centów", "5 centów")
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("change", ["second_sentence", "missing_payment"])
def test_optional_detail_and_multiple_sentences_do_not_make_correct_values_false(app, change):
    evidence, response = _toilet_phone_response(app)
    if change == "second_sentence":
        response.sentences[0].text += " Druga wiadomość."
    else:
        response.sentences[0].text = response.sentences[0].text.replace("lub karta", "")
    assert validate_formulation(response, evidence).answer == response.sentences[0].text


@pytest.mark.parametrize("text", [
    "Kontakt: tel. Nie ma toalet.",
    "Kontakt: tel. 0800 44 6666 02. Nie ma toalet.",
    "Pierwsze zdanie. Drugie zdanie.",
])
def test_telephone_exception_does_not_allow_a_second_sentence(text):
    assert _contains_sentence_break(text) is True


@pytest.mark.parametrize("text,valid", [
    ("Opłata: 50 centów (gotówka lub karta).", True),
    ("Opłata: 50 centów, gotówka lub karta.", True),
    ("Opłata: 150 centów (gotówka lub karta).", False),
    ("Opłata: 0,50 centów (gotówka lub karta).", False),
    ("Opłata: 0.50 centów (gotówka lub karta).", False),
    ("Opłata: 50 centów (gotówka).", False),
    ("Opłata: 50 centów (karta).", False),
])
def test_fee_formatting_preserves_amount_and_complete_payment_conditions(text, valid):
    assert contains_fee_literal(text, "50 centów (gotówka lub karta)") is valid
