"""Counterexamples from review plus controls, through the real validator."""

import asyncio
import pytest

from app.candidate_contract import CandidateRole
from app.formulation import ClaimType, FactType, GroundingDiagnosticCode, EvidenceFact, AnswerType, build_formulator_evidence
from app.grounding import validate_formulation
from app.grounding_claims import ClaimSupport, assess_service_claim, assess_target_claim, claims_current_availability, transliterated
from app.grounding_constraints import contradicts_age_bound, schedule_matches, service_text_without_cited_audience
from app.models import Language
from app.interpreter import Need
from app.providers.llm import BlabladorProvider
from test_formulation import _settings
from test_grounding_claims import _answer, _diagnostic, _evidence, _fact, app


@pytest.mark.parametrize("language,wrong,right", [
    (Language.DE, "für Frauen unter 18", "für Frauen ab 18"),
    (Language.EN, "for women under 18", "for women aged 18 and over"),
    (Language.PL, "dla kobiet poniżej 18 lat", "dla kobiet od 18 lat"),
    (Language.RO, "pentru femei sub 18 ani", "pentru femei de la 18 ani"),
    (Language.RU, "для женщин младше 18 лет", "для женщин от 18 лет"),
])
def test_age_relation_not_just_number_occurrence(app, language, wrong, right):
    evidence = _evidence(app, language=language)
    ids = [_fact(evidence, kind).fact_id for kind in (
        FactType.DISPLAY_NAME, FactType.MINIMUM_AGE, FactType.ELIGIBLE_GENDER,
    )]
    response = _answer(evidence, (f"Scharni {wrong}.", ClaimType.ACTION, "8", ids))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED
    response.sentences[0].text = f"Scharni {right}."
    assert validate_formulation(response, evidence).sentence_count == 1
    # An omitted restrictive citation must not conceal the contradiction.
    response.sentences[0].fact_ids.remove(_fact(evidence, FactType.MINIMUM_AGE).fact_id)
    response.sentences[0].text = f"Scharni {wrong}."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED


def test_upper_age_bound_and_unrelated_numbers():
    facts = [("maximum_age", "18")]
    assert contradicts_age_bound("for people over 18", facts, Language.EN)
    assert not contradicts_age_bound("for people up to 18", facts, Language.EN)
    assert not contradicts_age_bound("Call 12345 after 18:00", facts, Language.EN)
    assert not contradicts_age_bound("Geöffnet ab 17:00", [("minimum_age", "18")], Language.DE)


def test_multiple_explicitly_eligible_groups_do_not_exclude_each_other():
    facts = [("eligible_gender", "female"), ("eligible_gender", "male")]
    assert assess_target_claim("For women and men", facts, Language.EN)[0] is ClaimSupport.SUPPORTED


@pytest.mark.parametrize("language,day,daily,food", [
    (Language.DE, "Sonntag", "täglich", "Essen"),
    (Language.EN, "Sunday", "daily", "food"),
    (Language.PL, "niedziela", "codziennie", "jedzenie"),
    (Language.RO, "duminică", "zilnic", "mâncare"),
    (Language.RU, "воскресенье", "ежедневно", "еда"),
])
def test_schedule_day_and_time_order(app, language, day, daily, food):
    evidence = _evidence(app, offer_ids=("21",), language=language)
    condition = next(f for f in evidence.selected_offers[0].facts
                     if f.fact_type == FactType.SERVICE_CONDITION and "20:00" in f.value)
    ids = [_fact(evidence, FactType.DISPLAY_NAME).fact_id,
           _fact(evidence, FactType.SERVICE, contains="warmes Essen").fact_id, condition.fact_id]
    response = _answer(evidence, (f"Hilfebus: {food} {day} 20:00-21:00.", ClaimType.SERVICE, "21", ids))
    assert validate_formulation(response, evidence).sentence_count == 1
    for wrong in (f"{daily} 20:00-21:00", f"{day} 21:00-20:00"):
        response.sentences[0].text = f"Hilfebus: {food} {wrong}."
        assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_CONDITION_MISMATCH


def test_multiple_windows_must_not_be_merged():
    condition = "food: Monday 18:00-19:00; Sunday 20:00-21:00"
    assert not schedule_matches("Monday 20:00-21:00", condition, Language.EN, complete=True)
    assert schedule_matches("Sunday 20:00-21:00", condition, Language.EN, complete=True)


def test_visible_condition_may_be_in_another_sentence_of_same_offer(app):
    evidence = _evidence(app, offer_ids=("21",), language=Language.EN)
    ids = [_fact(evidence, FactType.DISPLAY_NAME).fact_id,
           _fact(evidence, FactType.SERVICE, contains="warmes Essen").fact_id]
    condition = _fact(evidence, FactType.SERVICE_CONDITION, contains="food distribution")
    response = _answer(evidence,
                       ("Hilfebus gives you food.", ClaimType.SERVICE, "21", ids),
                       ("The documented distribution time is Sunday 20:00-21:00.",
                        ClaimType.FACT, "21", [condition.fact_id]))
    assert validate_formulation(response, evidence).sentence_count == 2


@pytest.mark.parametrize("language,text", [
    (Language.DE, "Andere Details sind unbekannt, aber der Hilfebus gibt dir jetzt Essen."),
    (Language.EN, "Other details are unknown, but Hilfebus gives you food now."),
    (Language.PL, "Szczegóły są nieznane, ale teraz dostaniesz jedzenie."),
    (Language.RO, "Detaliul este necunoscut, dar acum primești mâncare."),
    (Language.RU, "Это неизвестно, но сейчас тебе дадут еду."),
])
def test_unrelated_unknown_does_not_exempt_current_service(language, text):
    assert claims_current_availability(text, language)


def test_unknown_status_itself_is_not_a_current_service_promise():
    text = "Currently the water fountain operation is unknown."
    assert not claims_current_availability(text, Language.EN, known_unknown_values=[text])
    assert claims_current_availability(text, Language.EN)
    assert claims_current_availability("Details are unknown, but food is available now.", Language.EN)
    assert claims_current_availability("With unknown details there is food now.", Language.EN)


@pytest.mark.parametrize("language,text,positive", [
    (Language.DE, "Scharni bietet keine Schlafplätze.", "Scharni bietet Schlafplätze."),
    (Language.EN, "Scharni does not offer sleeping accommodation.", "Scharni offers sleeping accommodation."),
    (Language.PL, "Scharni nie oferuje noclegu.", "Scharni oferuje nocleg."),
    (Language.RO, "Scharni nu oferă cazare.", "Scharni oferă cazare."),
    (Language.RU, "Scharni не предлагает ночлег.", "Scharni предлагает ночлег."),
])
def test_negative_service_claim_does_not_match_positive_evidence(app, language, text, positive):
    evidence = _evidence(app, language=language)
    # Curated, nonlocalized capability supports each language equally.
    ids = [_fact(evidence, FactType.DISPLAY_NAME).fact_id,
           _fact(evidence, FactType.CAPABILITY, contains="overnight").fact_id]
    response = _answer(evidence, (text, ClaimType.SERVICE, "8", ids))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
    response.sentences[0].text = positive
    assert validate_formulation(response, evidence).sentence_count == 1


def test_unknown_service_is_not_supported(app):
    assert assess_service_claim("sells bicycles", [("service", "sleep")], Language.EN)[0] is ClaimSupport.NOT_CHECKED
    evidence = _evidence(app, language=Language.EN)
    ids = [_fact(evidence, kind).fact_id for kind in (FactType.DISPLAY_NAME, FactType.DESCRIPTION)]
    response = _answer(evidence, ("Scharni sells bicycles.", ClaimType.SERVICE, "8", ids))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING


def test_bed_promise_needs_no_assurance_word(app):
    evidence = _evidence(app, language=Language.EN)
    ids = [_fact(evidence, FactType.DISPLAY_NAME).fact_id,
           _fact(evidence, FactType.CAPABILITY, contains="overnight").fact_id]
    response = _answer(evidence, ("At Scharni you will get a bed.", ClaimType.SERVICE, "8", ids))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.ADMISSION_CLAIM_UNSUPPORTED


def test_negative_source_does_not_support_positive_claim_but_can_be_quoted(app):
    evidence = _evidence(app, language=Language.EN)
    offer = evidence.selected_offers[0]
    name = _fact(evidence, FactType.DISPLAY_NAME)
    negative = EvidenceFact(fact_id="f_1111111111111111", fact_type=FactType.SERVICE,
                            value="No sleeping accommodation is offered")
    offer.facts = [name, negative]
    response = _answer(evidence,
                       ("Use Scharni.", ClaimType.ACTION, "8", [name.fact_id]),
                       ("Sleeping accommodation is offered.", ClaimType.SERVICE, "8", [negative.fact_id]))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
    response.sentences[1].text = negative.value + "."
    assert validate_formulation(response, evidence).sentence_count == 2


def test_current_claim_bypass_is_rejected_through_validator(app):
    evidence = _evidence(app, offer_ids=("21",), language=Language.EN)
    ids = [_fact(evidence, FactType.DISPLAY_NAME).fact_id,
           _fact(evidence, FactType.SERVICE, contains="warmes Essen").fact_id]
    response = _answer(evidence,
                       ("Other details are unknown, but Hilfebus gives you food now.",
                        ClaimType.SERVICE, "21", ids))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.CURRENT_AVAILABILITY_UNSUPPORTED


def test_a_cited_unknown_status_note_is_still_renderable(app):
    evidence = _evidence(app, language=Language.EN)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    note = EvidenceFact(fact_id="f_2222222222222222", fact_type=FactType.NOTE,
                        value="Currently sleeping accommodation availability is unknown")
    evidence.selected_offers[0].facts.append(note)
    ids = [note.fact_id, _fact(evidence, FactType.CAPABILITY, contains="overnight").fact_id]
    response = _answer(evidence,
                       ("Use Scharni.", ClaimType.ACTION, "8", [name.fact_id]),
                       (note.value + ".", ClaimType.FACT, "8", ids))
    assert validate_formulation(response, evidence).sentence_count == 2
    response.sentences[1].text = "Sleeping accommodation is available now, but other details are unknown."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.CURRENT_AVAILABILITY_UNSUPPORTED


def test_recorded_romanian_counselling_response_passes_real_provider_validation(app, monkeypatch):
    """Replay the exact schema-valid output from run_1a3636... without a live call."""
    evidence = build_formulator_evidence(
        query="Am nevoie de ajutor medical.", language=Language.RO,
        answer_type=AnswerType.GROUNDED_REFERRAL, need=Need.MEDICAL,
        offers=[app.state.kb.by_id()["24"]], roles={"24": CandidateRole.REFERRAL_CONTACT},
        translation_catalog=app.state.service.translation_catalog,
        translation_policy=app.state.service.translation_policy,
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="Consiliere socială")
    assert name.fact_id == "f_abe67692e2acf7bf"
    assert service.fact_id == "f_4b7b1e78895ebd88"
    recorded = _answer(evidence,
        ("Contactează „CABL”.", ClaimType.REFERRAL, "24", [name.fact_id]),
        ("Oferă consiliere socială pentru persoane fără acces regulat la sistemul de sănătate.",
         ClaimType.SERVICE, "24", [service.fact_id]),
    )
    provider = BlabladorProvider(_settings("blablador"))

    async def post(_payload):
        return {"choices": [{"message": {"content": recorded.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", post)
    result = asyncio.run(provider.formulate_answer(evidence=evidence))
    assert result.answer == " ".join(sentence.text for sentence in recorded.sentences)
    assert result.card_ids == ["24"]


@pytest.mark.parametrize("language,positive,negative,changed", [
    (Language.DE, "Beratung für Menschen ohne Krankenversicherung",
     "Keine Beratung für Menschen ohne Krankenversicherung", "Beratung für Menschen ohne Arbeit"),
    (Language.EN, "Counselling for people without health insurance",
     "No counselling for people without health insurance", "Counselling for people without work"),
    (Language.PL, "Poradnictwo dla osób bez ubezpieczenia",
     "Nie oferuje poradnictwa dla osób bez ubezpieczenia", "Poradnictwo dla osób bez pracy"),
    (Language.RO, "Consiliere pentru persoane fără asigurare",
     "Nu oferă consiliere pentru persoane fără asigurare", "Consiliere pentru persoane fără muncă"),
    (Language.RU, "Консультация для людей без страховки",
     "Не предлагает консультацию для людей без страховки", "Консультация для людей без работы"),
])
def test_cited_audience_qualifier_does_not_negate_service(app, language, positive, negative, changed):
    evidence = _evidence(app, offer_ids=("24",), language=language)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = EvidenceFact(fact_id="f_3333333333333333", fact_type=FactType.SERVICE, value=positive)
    evidence.selected_offers[0].facts = [name, service]
    response = _answer(evidence, (f"CABL: {positive}.", ClaimType.SERVICE, "24", [name.fact_id, service.fact_id]))
    assert validate_formulation(response, evidence).sentence_count == 1
    response.sentences[0].text = f"CABL: {negative}."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
    # Do not mask an unsupported qualifier. Its eventual assessment still
    # depends on the existing language-specific lexical coverage.
    assert service_text_without_cited_audience(changed, [("service", positive)], language) == transliterated(changed)
    # A negative source cannot support the positive service just because the
    # audience qualifier is identical and can be separated from both texts.
    service.value = negative
    response.sentences[0].text = f"CABL: {positive}."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING


def test_audience_without_service_is_not_evidence_of_that_service(app):
    evidence = _evidence(app, offer_ids=("24",), language=Language.EN)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = EvidenceFact(fact_id="f_4444444444444444", fact_type=FactType.SERVICE,
                           value="Counselling for people without food")
    evidence.selected_offers[0].facts = [name, service]
    response = _answer(evidence, ("CABL offers food.", ClaimType.SERVICE, "24", [name.fact_id, service.fact_id]))
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
    response.sentences[0].text = "CABL offers counselling for people without food but does not offer counselling."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
    service.value = "Counselling for people without food and sleeping accommodation"
    response.sentences[0].text = "CABL offers sleeping accommodation."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
