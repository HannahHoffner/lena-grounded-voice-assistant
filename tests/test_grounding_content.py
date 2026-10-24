"""Claimtypunabhängige Faktenprüfung (Audit F-01, 23.10.2026).

Die Audit-Gegenprobe ``Scharni bietet eine Fahrradreparatur an.`` wurde als
``action``/``fact`` akzeptiert. Diese Tests sichern, dass unbelegte, fehlende
und widersprüchliche Aussagen unabhängig vom deklarierten Claimtyp verworfen
werden, und dass belegte Paraphrasen weiterhin zulässig bleiben.
"""

from __future__ import annotations

import pytest

from app.formulation import ClaimType, FormulatorError, GroundingDiagnosticCode, formulator_retry_instruction
from app.grounding import validate_formulation
from app.grounding_content import asserts_provision, unsupported_content_words
from app.models import Language
from tests.test_formulation import _evidence, _response, _settings
from app.main import create_app


ALL_CLAIM_TYPES = (ClaimType.ACTION, ClaimType.FACT, ClaimType.SERVICE)


@pytest.fixture(scope="module")
def app():
    return create_app(_settings())


def _validate(app, text: str, claim_type: ClaimType, language: Language = Language.DE):
    evidence = _evidence(app, language=language)
    return validate_formulation(_response(evidence, text=text, claim_type=claim_type), evidence)


def _rejection(app, text: str, claim_type: ClaimType, language: Language = Language.DE) -> FormulatorError:
    with pytest.raises(FormulatorError) as caught:
        _validate(app, text, claim_type, language)
    assert caught.value.code == "formulator_ungrounded_claim"
    return caught.value


def test_scharni_evidence_contains_no_bicycle_fact(app) -> None:
    evidence = _evidence(app)
    values = " ".join(fact.value.casefold() for offer in evidence.selected_offers for fact in offer.facts)
    assert "fahrrad" not in values and "bicycle" not in values


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
@pytest.mark.parametrize(("language", "text"), [
    (Language.DE, "Scharni bietet eine Fahrradreparatur an."),
    (Language.DE, "Bei Scharni bekommst du eine Fahrradreparatur."),
    (Language.DE, "Scharni hat eine Autowerkstatt."),
    (Language.DE, "Scharni ist eine Fahrradwerkstatt."),
    (Language.DE, "Bei Scharni findest du eine Fahrradreparatur."),
    (Language.EN, "Scharni offers bicycle repair."),
    (Language.EN, "Scharni is a bicycle workshop."),
    (Language.PL, "Scharni oferuje naprawę rowerów."),
    (Language.RO, "Scharni oferă reparații de biciclete."),
    (Language.RU, "Scharni предлагает ремонт велосипедов."),
])
def test_unsupported_service_is_rejected_for_every_declared_claim_type(app, language, text, claim_type) -> None:
    _rejection(app, text, claim_type, language)


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
@pytest.mark.parametrize("text", [
    "Scharni bietet einen Schlafplatz und eine Fahrradreparatur an.",
    "Scharni bietet Grundversorgung mit Essen, Kleidung, Hygiene und Fahrradreparatur.",
])
def test_unsupported_item_inside_a_supported_list_is_not_carried_by_the_list(app, text, claim_type) -> None:
    error = _rejection(app, text, claim_type)
    assert error.diagnostic_code == GroundingDiagnosticCode.CONTENT_NOT_COVERED


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
def test_known_but_missing_service_is_rejected_for_every_claim_type(app, claim_type) -> None:
    # Wundversorgung ist ein bekanntes Konzept, aber kein Fakt dieses Angebots.
    error = _rejection(app, "Scharni bietet Wundversorgung an.", claim_type)
    assert error.diagnostic_code == GroundingDiagnosticCode.SERVICE_FACT_MISSING


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
@pytest.mark.parametrize(("text", "expected"), [
    ("Scharni bietet Schlafplätze für Männer an.", GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED),
    ("Scharni bietet Schlafplätze für Jugendliche unter 18 Jahren an.", GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED),
])
def test_statement_contradicting_curated_restrictions_is_rejected(app, text, expected, claim_type) -> None:
    error = _rejection(app, text, claim_type)
    assert error.diagnostic_code == expected


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
@pytest.mark.parametrize("text", [
    "Scharni bietet keine Schlafplätze an.",
    "Scharni nimmt dich heute garantiert auf.",
    "Scharni hat jetzt freie Plätze.",
])
def test_negated_admission_and_realtime_claims_are_rejected(app, text, claim_type) -> None:
    _rejection(app, text, claim_type)


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
@pytest.mark.parametrize(("language", "text"), [
    (Language.DE, "Scharni bietet einen Schlafplatz an."),
    (Language.DE, "Bei Scharni bekommst du Grundversorgung mit Essen, Kleidung und Hygiene."),
    (Language.DE, "Bei Scharni werden Schlafplätze angeboten."),
    (Language.DE, "Scharni ist eine Notunterkunft für alleinstehende volljährige Frauen."),
    (Language.EN, "Scharni offers overnight accommodation."),
    (Language.PL, "Scharni oferuje nocleg."),
    (Language.RO, "Scharni oferă cazare."),
    (Language.RU, "Scharni предлагает ночлег."),
])
def test_evidenced_paraphrases_remain_valid_for_every_claim_type(app, language, text, claim_type) -> None:
    assert _validate(app, text, claim_type, language).answer == text


def test_directive_and_operational_sentences_are_not_provision_assertions(app) -> None:
    assert not asserts_provision("Nutze Scharni.", Language.DE)
    assert not asserts_provision("Ruf Scharni an.", Language.DE)
    assert asserts_provision("Scharni bietet Essen an.", Language.DE)
    assert asserts_provision("Scharni is a shelter.", Language.EN)
    assert _validate(app, "Nutze Scharni.", ClaimType.ACTION).answer == "Nutze Scharni."


def test_residual_words_are_reported_without_free_text_side_channels() -> None:
    facts = [("service", "Schlafplatz"), ("service", "Wäsche waschen")]
    assert unsupported_content_words("Dort gibt es Schlafplätze und Wäschewaschen.", facts, Language.DE) == ()
    assert unsupported_content_words(
        "Dort gibt es Schlafplätze und Fahrradreparatur.", facts, Language.DE,
    ) == ("fahrradreparatur",)
    # Ohne Leistungsprädikat wird kein Inhaltswort beansprucht.
    assert unsupported_content_words("Fahrradreparatur.", facts, Language.DE) == ()


def test_fee_words_need_a_curated_fee_status_to_be_exempt() -> None:
    without_status = [("service", "Mahlzeiten")]
    with_status = [("service", "Mahlzeiten"), ("fee_status", "free")]
    text = "Dort gibt es kostenlose Mahlzeiten."
    assert unsupported_content_words(text, without_status, Language.DE) == ("kostenlose",)
    assert unsupported_content_words(text, with_status, Language.DE) == ()


def test_content_diagnostic_has_closed_retry_guidance() -> None:
    instruction = formulator_retry_instruction(GroundingDiagnosticCode.CONTENT_NOT_COVERED)
    assert "content_not_covered" in instruction
    assert "Fahrrad" not in instruction


# Live beobachtet am 23.10.2026 (Blablador alias-fast, Anfrage „Wo kann ich
# essen?“): Der erste Satz ist vollständig belegt und wurde nur wegen der
# Abkürzungen „Mo‑Fr“/„So“ und des „E“ aus „E‑Mail“ verworfen; der zweite
# erfindet eine Abendverpflegung und muss verworfen bleiben.
LIVE_SUPPORTED = (
    "Die Bahnhofsmission Leipzig (Willy‑Brandt‑Platz 2a, 04109 Leipzig) bietet Kaffee, Tee, "
    "Wasser und belegte Brötchen an. Öffnungszeiten: Mo‑Fr 09:00‑18:00, So 13:30‑18:00."
)
LIVE_INVENTED = (
    "Die Bahnhofsmission Leipzig bietet Kaffee, Tee, Wasser und belegte Brötchen an; bei Bedarf "
    "kann man nach einer Abendverpflegung fragen."
)


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
def test_live_observed_formatting_words_do_not_reject_a_supported_answer(app, claim_type) -> None:
    from app.interpreter import Need

    evidence = _evidence(app, offer_ids=("22",), need=Need.FOOD)
    validated = validate_formulation(_response(evidence, text=LIVE_SUPPORTED, claim_type=claim_type), evidence)
    assert validated.answer == LIVE_SUPPORTED


@pytest.mark.parametrize("claim_type", ALL_CLAIM_TYPES)
def test_live_observed_invented_addition_is_still_rejected(app, claim_type) -> None:
    from app.interpreter import Need

    evidence = _evidence(app, offer_ids=("22",), need=Need.FOOD)
    with pytest.raises(FormulatorError) as caught:
        validate_formulation(_response(evidence, text=LIVE_INVENTED, claim_type=claim_type), evidence)
    assert caught.value.diagnostic_code == GroundingDiagnosticCode.CONTENT_NOT_COVERED


def test_weekday_abbreviations_and_single_letters_are_not_content() -> None:
    facts = [("service", "Mittagessen"), ("opening_time", "Montag bis Freitag 12:00 - 13:00")]
    assert unsupported_content_words("Dort gibt es Mittagessen, Mo-Fr, per E-Mail.", facts, Language.DE) == ()
    assert unsupported_content_words("It offers lunch Mon-Fri.", [("service", "lunch")], Language.EN) == ()


def test_generic_person_heads_and_schedule_labels_are_not_content() -> None:
    facts = [("display_name", "UVO"), ("service", "Medizinische Versorgung"), ("target_group", "wohnungslose Menschen")]
    assert unsupported_content_words(
        "UVO bietet medizinische Versorgung für wohnungslose Menschen. Termine: Mittwoch.", facts, Language.DE,
    ) == ()
    # Das Kopfnomen macht eine unbelegte Leistung nicht zulässig.
    assert unsupported_content_words(
        "UVO bietet Rechtsberatung für Menschen.", facts, Language.DE,
    ) == ("rechtsberatung",)
