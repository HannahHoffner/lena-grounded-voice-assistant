"""Do not fix false rejections by allowing changed values or hidden promises."""

import pytest

from app.formulation import ClaimType, FactType, FormulatorError, EvidenceFact
from app.grounding import validate_formulation
from app.grounding_surface import evidenced_venue
from app.models import Language
from test_grounding_claims import app
from test_grounding_corrections import packet, response


@pytest.mark.parametrize("text", [
    "Probe: öffentliches Trinkwasser (Betrieb von April bis Oktober, aktueller Status unbekannt).",
    "Probe: Trinkwasserbrunnen (aktueller Betriebsstatus unbekannt).",
])
def test_unknown_parenthetical_is_not_a_current_promise(app, text):
    evidence = packet(app, Language.DE, [(FactType.SERVICE, "Kostenloser Trinkwasserbrunnen")])
    assert validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence).answer


@pytest.mark.parametrize("text", [
    "Probe gibt dir jetzt Trinkwasser (aktueller Status unbekannt).",
    "Probe: Trinkwasser ist jetzt verfügbar (aktueller Status unbekannt).",
    "Probe: aktueller Status unbekannt, aber der Trinkwasserbrunnen funktioniert gerade.",
    "Probe: Trinkwasserbrunnen (aktueller Status unbekannt und jetzt geöffnet).",
])
def test_unknown_does_not_hide_a_current_promise(app, text):
    evidence = packet(app, Language.DE, [(FactType.SERVICE, "Kostenloser Trinkwasserbrunnen")])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence)


@pytest.mark.parametrize("language,service,qualifier,negation", [
    (Language.RU, "общественный туалет", "без барьеров", "не"),
    (Language.RO, "toaletă publică", "fără bariere", "nu"),
    (Language.PL, "toaleta publiczna", "bez barier", "nie"),
])
def test_accessibility_qualifier_requires_own_fact_and_preserves_other_negation(app, language, service, qualifier, negation):
    evidence = packet(app, language, [(FactType.SERVICE, service), (FactType.FACILITY, qualifier)])
    assert validate_formulation(response(evidence, f"Probe: {service}, {qualifier}.", ClaimType.SERVICE), evidence).answer
    for text in (f"Probe: {negation} {service}, {qualifier}.",
                 f"Probe: {qualifier} / {service}."):
        with pytest.raises(FormulatorError):
            validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence)
    evidence.selected_offers[0].facts.pop()
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, f"Probe: {service}, {qualifier}.", ClaimType.SERVICE), evidence)


def test_homeless_women_qualifier_needs_typed_audience_and_keeps_real_negation(app):
    evidence = packet(app, Language.RO, [(FactType.SERVICE, "Loc de dormit"),
                                        (FactType.TARGET_GROUP, "adults"),
                                        (FactType.TARGET_GROUP, "women"),
                                        (FactType.TARGET_GROUP, "people_experiencing_homelessness")])
    text = "Probe oferă loc de dormit pentru femei adulte fără adăpost."
    assert validate_formulation(response(evidence, text, ClaimType.SERVICE), evidence).answer
    for wrong in (text.replace("oferă", "nu oferă"), text.replace("adăpost.", "adăpost și cazare.")):
        with pytest.raises(FormulatorError):
            validate_formulation(response(evidence, wrong, ClaimType.SERVICE), evidence)


@pytest.mark.parametrize("amount", ["50 €", "0,50 €", "-5 €", "5,01 €"])
def test_distinct_amounts_are_not_equal_under_normalization(app, amount):
    evidence = packet(app, Language.EN, [(FactType.SERVICE, "Overnight accommodation (5,00 €)")])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, f"Probe: overnight accommodation ({amount}).", ClaimType.SERVICE), evidence)


def test_venue_exception_is_source_and_location_bound():
    facts = [("note", "Monday at Tagestreff Oase, Nürnberger Straße 31")]
    assert evidenced_venue("UVO holds consultations at Tagestreff Oase.", "Tagestreff Oase", facts)
    assert not evidenced_venue("Tagestreff Oase provides UVO's services.", "Tagestreff Oase", facts)
    assert not evidenced_venue("UVO holds consultations at Tagestreff Oase.", "Tagestreff Oase", [])
    assert not evidenced_venue("UVO holds consultations at Other Place.", "Other Place", facts)


def test_a_venue_does_not_allow_other_offers_facts(app):
    evidence = packet(app, Language.EN, [(FactType.NOTE, "Monday at Tagestreff Oase"),
                                        (FactType.SERVICE, "medical care")])
    other = evidence.selected_offers[0].model_copy(deep=True)
    other.offer_id = "10"
    other.display_name = "Tagestreff Oase"
    other.facts = [EvidenceFact(fact_id="f_0000000000000010", fact_type=FactType.DISPLAY_NAME, value=other.display_name),
                   EvidenceFact(fact_id="f_0000000000000011", fact_type=FactType.PHONE, value="0341 9999999")]
    evidence.selected_offers.append(other)
    answer = response(evidence, "Probe offers medical care at Tagestreff Oase.", ClaimType.SERVICE)
    assert validate_formulation(answer, evidence).answer
    answer.sentences[0].text += " Call 0341 9999999."
    with pytest.raises(FormulatorError):
        validate_formulation(answer, evidence)
    answer.sentences[0].text = "Probe offers medical care at Tagestreff Oase."
    answer.sentences[0].fact_ids.append(other.facts[1].fact_id)
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(answer, evidence)


@pytest.mark.parametrize("text", [
    "Probe: call 0152 33661087 outside operating hours.",
    "Probe: call 0152 33661087 not during operating hours.",
])
def test_negated_operating_condition_does_not_pass(app, text):
    evidence = packet(app, Language.EN, [(FactType.PHONE, "0152 33661087 (nur zu Einsatzzeiten des Busses)")])
    with pytest.raises(FormulatorError):
        validate_formulation(response(evidence, text, ClaimType.ACTION), evidence)
