"""Gegenproben zum antwortweiten, angebotsgebundenen Groundingvertrag.

Geprüft wird die Unterscheidung, um die es in diesem Vertrag geht: eine
bedeutungserhaltende Darstellungsabweichung ist keine falsche Angabe, ein
Widerspruch und eine unbelegte Zusage bleiben unzulässig. Die Grenze des
Verfahrens wird mitgeprüft: ``UNDECIDABLE`` führt zum kontrollierten Rückfall
und ist ausdrücklich keine Aussage über den Wahrheitswert.
"""

from __future__ import annotations

import pytest

from app.candidate_contract import CandidateRole
from app.formulation import (
    LEGACY_FORMULATOR_CONTRACT_VERSION as FORMULATOR_CONTRACT_VERSION,
    AnswerType,
    ClaimType,
    FactType,
    FormulatedSentence,
    FormulatorError,
    FormulatorResponse,
    GroundingDiagnosticCode,
    build_formulator_evidence,
)
from app.grounding import validate_formulation
from app.grounding_claims import (
    ClaimSupport,
    assess_service_claim,
    assess_target_claim,
    claims_admission,
    claims_current_availability,
    claims_suitability,
    condition_capability,
    detect_service_concepts,
    detect_target_concepts,
    service_condition_text,
)
from app.interpreter import Need
from app.main import create_app
from app.models import Language

from test_formulation import _settings


@pytest.fixture(scope="module")
def app():
    return create_app(_settings())


def _evidence(
    app,
    *,
    offer_ids: tuple[str, ...] = ("8",),
    language: Language = Language.DE,
    answer_type: AnswerType = AnswerType.GROUNDED_RESULT,
    roles: dict[str, CandidateRole] | None = None,
    need: Need = Need.SLEEP,
    query: str = "Ich brauche Hilfe.",
):
    offers = [app.state.kb.by_id()[offer_id] for offer_id in offer_ids]
    return build_formulator_evidence(
        query=query,
        language=language,
        answer_type=answer_type,
        need=need,
        offers=offers,
        roles=roles or {offer.id: CandidateRole.DIRECT_SERVICE for offer in offers},
        mandatory_ids=set(),
    )


def _fact(evidence, kind: FactType, *, offer_id: str | None = None, contains: str | None = None):
    for offer in evidence.selected_offers:
        if offer_id and offer.offer_id != offer_id:
            continue
        for fact in offer.facts:
            if fact.fact_type == kind and (contains is None or contains in fact.value):
                return fact
    raise AssertionError(f"missing {kind} {contains or ''}")


def _answer(evidence, *sentences: tuple[str, ClaimType, str, list[str]]) -> FormulatorResponse:
    return FormulatorResponse(
        contract_version=FORMULATOR_CONTRACT_VERSION,
        language=evidence.requested_language,
        sentences=[
            FormulatedSentence(text=text, claim_type=claim, offer_id=offer_id, fact_ids=fact_ids)
            for text, claim, offer_id, fact_ids in sentences
        ],
        card_ids=list(dict.fromkeys(offer_id for _, _, offer_id, _ in sentences)),
    )


def _diagnostic(response, evidence) -> GroundingDiagnosticCode | None:
    with pytest.raises(FormulatorError) as captured:
        validate_formulation(response, evidence)
    return captured.value.diagnostic_code


# ---------------------------------------------------------------------------
# 1. Antwortweite Belege, weiterhin strikt pro Angebot
# ---------------------------------------------------------------------------
def test_a_fact_cited_in_another_sentence_supports_the_same_offer(app) -> None:
    """Die Position der Fakt-ID entscheidet nicht; das Angebot entscheidet."""
    evidence = _evidence(app)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    description = _fact(evidence, FactType.DESCRIPTION)
    response = _answer(
        evidence,
        ("Nutze Übernachtungshaus für wohnungslose Frauen für erwachsene Frauen.", ClaimType.ACTION, "8", [name.fact_id]),
        ("Das Angebot ist so beschrieben.", ClaimType.FACT, "8", [description.fact_id]),
    )
    assert "Frauen" in description.value and "volljährige" in description.value
    assert validate_formulation(response, evidence).sentence_count == 2

    # Derselbe Satz ohne jeden belegenden Wert im Angebot bleibt unentscheidbar.
    alone = _answer(
        evidence,
        ("Nutze Übernachtungshaus für wohnungslose Frauen für erwachsene Frauen.", ClaimType.ACTION, "8", [name.fact_id]),
    )
    assert validate_formulation(alone, evidence).sentence_count == 1
    evidence.selected_offers[0].facts = [name]
    assert _diagnostic(alone, evidence) == GroundingDiagnosticCode.TARGET_FACT_MISSING


def test_another_offers_fact_never_substitutes(app) -> None:
    """Die Zusammenfassung bleibt angebotsgebunden, auch antwortweit."""
    evidence = _evidence(app, offer_ids=("8", "10"))
    own_name = _fact(evidence, FactType.DISPLAY_NAME, offer_id="8")
    other_description = _fact(evidence, FactType.DESCRIPTION, offer_id="10")
    evidence.selected_offers[0].facts = [own_name]
    response = _answer(
        evidence,
        ("Nutze Übernachtungshaus für wohnungslose Frauen für Frauen.", ClaimType.ACTION, "8", [own_name.fact_id]),
        ("Dazu gibt es diese Beschreibung.", ClaimType.FACT, "10", [other_description.fact_id]),
    )
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.TARGET_FACT_MISSING

    # Eine angebotsfremde Referenz im selben Satz bleibt ein Referenzfehler.
    cross = _answer(
        evidence,
        ("Nutze Übernachtungshaus für wohnungslose Frauen für Frauen.", ClaimType.ACTION, "8", [own_name.fact_id, other_description.fact_id]),
    )
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(cross, evidence)


def test_presence_of_an_eligible_fact_type_is_still_not_enough(app) -> None:
    """Ein Fakt zulässigen Typs belegt nichts, wenn sein Wert die Aussage nicht trägt."""
    evidence = _evidence(app)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    minimum_age = _fact(evidence, FactType.MINIMUM_AGE)
    response = _answer(
        evidence,
        ("Nutze Übernachtungshaus für wohnungslose Frauen für Minderjährige.", ClaimType.ACTION, "8", [name.fact_id, minimum_age.fact_id]),
    )
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED


@pytest.mark.parametrize(
    ("language", "text"),
    [
        (Language.DE, "Nutze Übernachtungshaus für wohnungslose Frauen für Männer."),
        (Language.EN, "Use Übernachtungshaus für wohnungslose Frauen for men."),
        (Language.PL, "Skorzystaj z Übernachtungshaus für wohnungslose Frauen dla mężczyzn."),
        (Language.RO, "Folosește Übernachtungshaus für wohnungslose Frauen pentru bărbați."),
        (Language.RU, "Используй Übernachtungshaus für wohnungslose Frauen для мужчин."),
    ],
)
def test_changed_gender_is_contradicted_in_every_language(app, language, text) -> None:
    """Frauen zu Männern verändert: ablehnen, und zwar als Widerspruch."""
    evidence = _evidence(app, language=language)
    response = _answer(
        evidence,
        (
            text,
            ClaimType.ACTION,
            "8",
            [
                _fact(evidence, FactType.DISPLAY_NAME).fact_id,
                _fact(evidence, FactType.ELIGIBLE_GENDER, contains="female").fact_id,
            ],
        ),
    )
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED


# ---------------------------------------------------------------------------
# 2. referral_contact beschreibt die Empfehlung, nicht den Leistungsumfang
# ---------------------------------------------------------------------------
def test_referral_offer_may_describe_its_own_evidenced_service(app) -> None:
    """claim_type=service ist bei einem Referral nicht allein wegen des Enumwerts falsch."""
    evidence = _evidence(
        app,
        offer_ids=("21",),
        answer_type=AnswerType.GROUNDED_REFERRAL,
        roles={"21": CandidateRole.REFERRAL_CONTACT},
        need=Need.FOOD,
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="warmes Essen")
    response = _answer(
        evidence,
        ("Melde dich beim Hilfebus.", ClaimType.REFERRAL, "21", [name.fact_id]),
        ("Der Hilfebus gibt warmes Essen aus.", ClaimType.SERVICE, "21", [service.fact_id]),
    )
    assert validate_formulation(response, evidence).sentence_count == 2


def test_referral_offer_may_not_promise_admission_or_suitability(app) -> None:
    """Die belegte Leistungsbeschreibung bleibt von der Zusage getrennt."""
    evidence = _evidence(
        app,
        offer_ids=("7",),
        answer_type=AnswerType.GROUNDED_REFERRAL,
        roles={"7": CandidateRole.REFERRAL_CONTACT},
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    for text, expected in (
        ("Dort wirst du aufgenommen.", GroundingDiagnosticCode.ADMISSION_CLAIM_UNSUPPORTED),
        ("Dieses Angebot ist für dich geeignet.", GroundingDiagnosticCode.SUITABILITY_CLAIM_UNSUPPORTED),
    ):
        response = _answer(
            evidence,
            (f"Melde dich bei {name.value}.", ClaimType.REFERRAL, "7", [name.fact_id]),
            (text, ClaimType.FACT, "7", [name.fact_id]),
        )
        assert _diagnostic(response, evidence) == expected


# ---------------------------------------------------------------------------
# 3. Leistungsgebundene Zeitfenster aus den kuratierten Daten
# ---------------------------------------------------------------------------
def test_curated_schedules_become_service_bound_conditions(app) -> None:
    """Die Zuordnung stammt aus der Kuratierung, nicht aus einer zweiten Quelle."""
    evidence = _evidence(app, offer_ids=("21",), need=Need.FOOD)
    conditions = {
        condition_capability(fact.value): fact.value
        for fact in evidence.selected_offers[0].facts
        if fact.fact_type == FactType.SERVICE_CONDITION
    }
    assert conditions["food"] == "Essensausgabe: Sonntag 20:00-21:00"
    assert conditions["counselling"] == "Beratung: täglich 18:00-23:00"
    # Regeln ohne festes Fenster werden ausgelassen statt geraten.
    assert service_condition_text("medical_care", "mobile_alternative_stands", Language.DE) is None


def test_contact_hours_must_not_appear_as_food_distribution_hours(app) -> None:
    """Kontaktzeiten dürfen nicht als Essensausgabezeiten erscheinen."""
    evidence = _evidence(app, offer_ids=("21",), need=Need.FOOD)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="warmes Essen")
    opening = _fact(evidence, FactType.OPENING_TIME, contains="18:00")
    wrong = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        (
            "Essen gibt es dort von 18:00 bis 23:00 Uhr.",
            ClaimType.SERVICE,
            "21",
            [service.fact_id, opening.fact_id],
        ),
    )
    assert _diagnostic(wrong, evidence) == GroundingDiagnosticCode.SERVICE_CONDITION_MISMATCH

    condition = _fact(evidence, FactType.SERVICE_CONDITION, contains="Essensausgabe")
    right = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        (
            "Essen gibt es dort Sonntag 20:00-21:00.",
            ClaimType.SERVICE,
            "21",
            [service.fact_id, condition.fact_id],
        ),
    )
    assert validate_formulation(right, evidence).sentence_count == 2


def test_general_description_is_allowed_but_a_personal_promise_needs_the_condition(app) -> None:
    """„Der Hilfebus bietet Essen an" ist belegbar, „dort bekommst du Essen" braucht mehr."""
    evidence = _evidence(app, offer_ids=("21",), need=Need.FOOD)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="warmes Essen")
    condition = _fact(evidence, FactType.SERVICE_CONDITION, contains="Essensausgabe")

    general = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        ("Der Hilfebus gibt warmes Essen aus.", ClaimType.SERVICE, "21", [service.fact_id]),
    )
    assert validate_formulation(general, evidence).sentence_count == 2

    promised = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        ("Dort bekommst du warmes Essen.", ClaimType.SERVICE, "21", [service.fact_id]),
    )
    assert _diagnostic(promised, evidence) == GroundingDiagnosticCode.SERVICE_CONDITION_MISSING

    with_condition = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        (
            "Dort bekommst du warmes Essen.",
            ClaimType.SERVICE,
            "21",
            [service.fact_id, condition.fact_id],
        ),
    )
    assert _diagnostic(with_condition, evidence) == GroundingDiagnosticCode.SERVICE_CONDITION_MISSING
    with_condition.sentences[1].text = "Dort bekommst du Sonntag 20:00-21:00 warmes Essen."
    assert validate_formulation(with_condition, evidence).sentence_count == 2


def test_a_general_service_fact_does_not_establish_current_availability(app) -> None:
    """„Dort bekommst du jetzt Essen" folgt aus keinem allgemeinen Leistungsfakt."""
    evidence = _evidence(app, offer_ids=("21",), need=Need.FOOD)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="warmes Essen")
    condition = _fact(evidence, FactType.SERVICE_CONDITION, contains="Essensausgabe")
    response = _answer(
        evidence,
        ("Nutze den Hilfebus.", ClaimType.ACTION, "21", [name.fact_id]),
        (
            "Dort bekommst du jetzt warmes Essen.",
            ClaimType.SERVICE,
            "21",
            [service.fact_id, condition.fact_id],
        ),
    )
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.CURRENT_AVAILABILITY_UNSUPPORTED


# ---------------------------------------------------------------------------
# 4. Die Bewertungsstufe selbst
# ---------------------------------------------------------------------------
def test_three_outcomes_are_distinguished() -> None:
    """Belegt, widersprüchlich und unentscheidbar bleiben getrennte Ergebnisse."""
    women = [("eligible_gender", "female"), ("description", "Unterkunft für Frauen")]
    assert assess_target_claim("Für Frauen.", women, Language.DE)[0] is ClaimSupport.SUPPORTED
    assert assess_target_claim("Für Männer.", women, Language.DE)[0] is ClaimSupport.CONTRADICTED
    # Ohne kuratierte Beschränkung gibt es keinen Widerspruch, nur fehlenden Beleg.
    assert assess_target_claim("Für Männer.", [("description", "Beratung")], Language.DE)[0] is (
        ClaimSupport.UNDECIDABLE
    )
    # Für Leistungen existiert keine kuratierte Negativliste, deshalb kein Widerspruch.
    assert assess_service_claim("Es gibt Essen.", [("service", "Beratung")], Language.DE)[0] is (
        ClaimSupport.UNDECIDABLE
    )
    assert assess_service_claim("Es gibt Essen.", [("capability", "food")], Language.DE)[0] is (
        ClaimSupport.SUPPORTED
    )


def test_cited_proper_names_do_not_create_target_or_service_claims() -> None:
    """Regressionsschutz: „Menschen" ist keine Geschlechtsbehauptung."""
    assert detect_target_concepts(
        "Umfeldnahe Versorgung von Menschen ohne festen Wohnsitz", Language.DE
    ) == set()
    assert detect_target_concepts("Bei UVO kann man sich melden.", Language.DE) == set()
    # This helper sees raw text; the validator masks the exact proper name first.
    assert detect_target_concepts("Übernachtungshaus für wohnungslose Frauen ist für Männer.", Language.DE) == {"female", "male"}
    assert detect_service_concepts("Der Hilfebus gibt warmes Essen aus.", Language.DE) == {"food"}


@pytest.mark.parametrize(
    ("language", "admission", "suitability", "current"),
    [
        (Language.DE, "Dort wirst du aufgenommen.", "Das ist für dich geeignet.", "Dort gibt es jetzt Essen."),
        (Language.EN, "You will be admitted there.", "This is suitable for you.", "There is food there now."),
        (Language.PL, "Zostaniesz przyjęty.", "To jest odpowiednie dla ciebie.", "Teraz jest tam jedzenie."),
        (Language.RO, "Vei fi primit acolo.", "Este potrivit pentru tine.", "Acum este mâncare acolo."),
        (Language.RU, "Тебя примут там.", "Это подходит тебе.", "Сейчас там есть еда."),
    ],
)
def test_unsupported_promises_are_detected_in_every_language(
    language, admission, suitability, current
) -> None:
    assert claims_admission(admission, language)
    assert claims_suitability(suitability, language)
    assert claims_current_availability(current, language)
    # Eine belegbare allgemeine Leistungsbeschreibung löst keine dieser Klassen aus.
    neutral = {
        Language.DE: "Der Hilfebus gibt warmes Essen aus.",
        Language.EN: "The bus hands out warm food.",
        Language.PL: "Autobus wydaje ciepłe jedzenie.",
        Language.RO: "Autobuzul oferă mâncare caldă.",
        Language.RU: "Автобус раздаёт горячую еду.",
    }[language]
    assert not claims_admission(neutral, language)
    assert not claims_suitability(neutral, language)
    assert not claims_current_availability(neutral, language)
