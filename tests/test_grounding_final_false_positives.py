"""Price/age and Polish prose regressions without weakening actual constraints."""

import pytest

from app.formulation import ClaimType, FactType, FormulatorError
from app.grounding import validate_formulation
from app.grounding_claims import claims_admission, claims_personal_receipt
from app.grounding_constraints import contradicts_age_bound, schedule_matches
from app.models import Language
from test_grounding_claims import app
from test_grounding_corrections import packet, response


@pytest.mark.parametrize("amount", ["5 €", "5,00 €", "5.00 €"])
def test_price_from_is_not_a_minimum_age(app, amount):
    evidence = packet(app, Language.DE, [
        (FactType.MINIMUM_AGE, "18"),
        (FactType.SERVICE, "Übernachtungen ab 5,00 € pro Nacht"),
    ])
    text = f"Probe bietet Übernachtungen ab {amount} pro Nacht an."
    assert validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence).answer


@pytest.mark.parametrize("text", [
    "Probe bietet Übernachtungen ab 5,00 € für Menschen ab 16 Jahren.",
    "Probe bietet Übernachtungen ab 5,00 € für Menschen unter 18 Jahren.",
    "Probe bietet Übernachtungen ab 50,00 € pro Nacht.",
])
def test_price_context_does_not_hide_age_or_changed_price(app, text):
    evidence = packet(app, Language.DE, [
        (FactType.MINIMUM_AGE, "18"),
        (FactType.SERVICE, "Übernachtungen ab 5,00 € pro Nacht"),
    ])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence)


def test_price_masking_preserves_real_age_bounds():
    facts = [("minimum_age", "18"), ("maximum_age", "65")]
    assert not contradicts_age_bound("Ab 18 Jahren, Preis ab 5,00 €.", facts, Language.DE)
    assert contradicts_age_bound("Ab 17 Jahren, Preis ab 5,00 €.", facts, Language.DE)
    assert contradicts_age_bound("Alter 18-70, Preis ab 5,00 €.", facts, Language.DE)


@pytest.mark.parametrize("restriction", ["w godzinach ich działań", "w godzinach działania", "w godzinach pracy"])
def test_polish_operating_condition_variants_are_recognized(app, restriction):
    evidence = packet(app, Language.PL, [
        (FactType.PHONE, "0152 33661087 (nur zu Einsatzzeiten des Busses)"),
        (FactType.OPENING_TIME, "codziennie 18:00-23:00"),
    ])
    text = f"Probe: 0152 33661087 {restriction} (codziennie 18:00–23:00)."
    assert validate_formulation(response(evidence, text, ClaimType.ACTION), evidence).answer


@pytest.mark.parametrize("restriction", ["", "poza godzinami pracy", "nie w godzinach pracy", "nie w godzinach ich działań"])
def test_polish_missing_or_negated_operating_condition_stays_rejected(app, restriction):
    evidence = packet(app, Language.PL, [(FactType.PHONE, "0152 33661087 (nur zu Einsatzzeiten des Busses)")])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, f"Probe: 0152 33661087 {restriction}.", ClaimType.ACTION), evidence)


def test_polish_general_distribution_is_not_a_personal_receipt_or_admission():
    assert not claims_personal_receipt("Rozdają ciepłe jedzenie i napoje.", Language.PL)
    assert not claims_admission("Rozdają ciepłe koce; miejsca noclegowe są osobno.", Language.PL)


@pytest.mark.parametrize("text", ["Dają ci jedzenie.", "Da ci posiłek.", "Dostaniesz jedzenie.", "Otrzymasz jedzenie."])
def test_polish_real_personal_receipt_remains_detected(text):
    assert claims_personal_receipt(text, Language.PL)
    assert claims_admission(text.replace("jedzenie", "miejsce").replace("posiłek", "miejsce"), Language.PL)


def test_polish_inflected_sunday_binds_to_its_actual_window():
    condition = "wydawanie jedzenia: niedziela 20:00-21:00"
    assert schedule_matches("W niedzielę od 20:00 do 21:00.", condition, Language.PL, complete=True)
    assert not schedule_matches("W sobotę od 20:00 do 21:00.", condition, Language.PL, complete=True)
    assert not schedule_matches("W niedzielę od 18:00 do 23:00.", condition, Language.PL, complete=True)


def bus_answer(app, weekday="niedzielę", start="20:00", end="21:00"):
    evidence = packet(app, Language.PL, [
        (FactType.PHONE, "0152 33661087 (nur zu Einsatzzeiten des Busses)"),
        (FactType.OPENING_TIME, "codziennie 18:00-23:00"),
        (FactType.SERVICE, "wydawanie jedzenia"),
        (FactType.SERVICE_CONDITION, "wydawanie jedzenia: niedziela 20:00-21:00"),
    ])
    answer = response(evidence, "Probe: 0152 33661087 w godzinach ich działań (codziennie 18:00–23:00).", ClaimType.ACTION)
    service = response(evidence, f"W {weekday} od {start} do {end} rozdają ciepłe jedzenie.", ClaimType.SERVICE)
    answer.sentences.extend(service.sentences)
    return answer, evidence


def test_polish_contact_and_food_keep_their_separate_windows(app):
    answer, evidence = bus_answer(app)
    assert validate_formulation(answer, evidence).answer


@pytest.mark.parametrize("weekday", ["poniedziałek", "wtorek", "środę", "czwartek", "piątek", "sobotę"])
def test_polish_wrong_food_weekday_stays_rejected_in_productive_validator(app, weekday):
    answer, evidence = bus_answer(app, weekday=weekday)
    with pytest.raises(FormulatorError):
        validate_formulation(answer, evidence)


def test_polish_food_cannot_borrow_phone_operating_hours(app):
    answer, evidence = bus_answer(app, start="18:00", end="23:00")
    with pytest.raises(FormulatorError):
        validate_formulation(answer, evidence)
