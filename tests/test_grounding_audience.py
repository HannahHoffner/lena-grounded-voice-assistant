"""Evidence-bound audience coordination through helpers and real validation."""

import asyncio

import pytest

from app.candidate_contract import CandidateRole
from app.formulation import AnswerType, ClaimType, EvidenceFact, FactType, GroundingDiagnosticCode, build_formulator_evidence
from app.grounding import validate_formulation
from app.grounding_claims import transliterated
from app.grounding_constraints import has_negation, service_text_without_cited_audience
from app.interpreter import Need
from app.models import Language
from app.providers.llm import BlabladorProvider
from test_formulation import _settings
from test_grounding_claims import _answer, _diagnostic, _evidence, _fact, app


_LANGUAGE_CASES = [
    (Language.DE, "Beratung für Menschen ohne Krankenversicherung", "und",
     "Ausstellung anonymer Behandlungsscheine", "Keine "),
    (Language.EN, "Counselling for people without health insurance", "and",
     "Issuing anonymous treatment vouchers", "No "),
    (Language.PL, "Poradnictwo dla osób bez ubezpieczenia", "i",
     "Wydawanie anonimowych skierowań na leczenie", "Nie "),
    (Language.RO, "Consiliere socială pentru persoane fără acces regulat la sistemul de sănătate", "și",
     "Emitere de fișe de tratament anonime", "Nu "),
    (Language.RU, "Консультация для людей без страховки", "и",
     "Выдача анонимных направлений на лечение", "Не "),
]


@pytest.mark.parametrize("language,service,joiner,extra,negative", _LANGUAGE_CASES)
def test_only_cited_audience_is_removed_before_cited_service(language, service, joiner, extra, negative):
    facts = [("service", service), ("service", "> " + extra)]
    text = f"{service} {joiner} {extra}."
    masked = service_text_without_cited_audience(text, facts, language)
    assert masked != transliterated(text)
    assert transliterated(extra) in masked
    assert not has_negation(masked, language)


@pytest.mark.parametrize("language,service,joiner,extra,negative", _LANGUAGE_CASES)
def test_uncited_or_negative_continuation_does_not_create_a_boundary(language, service, joiner, extra, negative):
    text = f"{service} {joiner} {extra}."
    for facts in (
        [("service", service)],
        [("service", service), ("service", negative + extra)],
        [("service", service), ("display_name", extra)],
    ):
        assert service_text_without_cited_audience(text, facts, language) == transliterated(text)


@pytest.mark.parametrize("language,service,joiner,extra,negative", _LANGUAGE_CASES)
def test_negation_outside_the_audience_remains_visible(language, service, joiner, extra, negative):
    facts = [("service", service), ("service", extra)]
    text = f"{negative}{service} {joiner} {extra}."
    masked = service_text_without_cited_audience(text, facts, language)
    assert has_negation(masked, language)
    assert masked.startswith(transliterated(negative))


@pytest.mark.parametrize("language,service,joiner,extra,negative", _LANGUAGE_CASES)
def test_coordinated_services_and_their_negation_through_validator(app, language, service, joiner, extra, negative):
    evidence = _evidence(app, offer_ids=("24",), language=language)
    name = _fact(evidence, FactType.DISPLAY_NAME)
    first = EvidenceFact(fact_id="f_5555555555555555", fact_type=FactType.SERVICE, value=service)
    second = EvidenceFact(fact_id="f_6666666666666666", fact_type=FactType.SERVICE, value=extra)
    evidence.selected_offers[0].facts = [name, first, second]
    response = _answer(evidence,
        (f"CABL: {service} {joiner} {extra}.", ClaimType.SERVICE, "24",
         [name.fact_id, first.fact_id, second.fact_id]),
    )
    assert validate_formulation(response, evidence).sentence_count == 1
    response.sentences[0].text = f"CABL: {negative}{service} {joiner} {extra}."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING


def test_complete_audience_with_coordinated_deprivation_has_priority():
    short = "Counselling for people without food"
    long = short + " and sleeping accommodation"
    facts = [("service", short), ("service", long), ("service", "sleeping accommodation")]
    masked = service_text_without_cited_audience(long + ".", facts, Language.EN)
    assert "food" not in masked
    assert "sleeping" not in masked
    # No independent service fact: a conjunction alone must not end the audience.
    assert service_text_without_cited_audience(long + ".", [("service", short)], Language.EN) == transliterated(long + ".")


def test_partial_or_extended_service_suffix_does_not_match():
    base = "Counselling for people without health insurance"
    extra = "issuing anonymous treatment vouchers"
    facts = [("service", base), ("service", extra)]
    for suffix in (extra + " and food", extra + " immediately", "not " + extra):
        text = base + " and " + suffix + "."
        assert service_text_without_cited_audience(text, facts, Language.EN) == transliterated(text)


def _recorded_cabl_response(app):
    evidence = build_formulator_evidence(
        query="Am nevoie de ajutor medical.", language=Language.RO,
        answer_type=AnswerType.GROUNDED_REFERRAL, need=Need.MEDICAL,
        offers=[app.state.kb.by_id()["24"]], roles={"24": CandidateRole.REFERRAL_CONTACT},
        translation_catalog=app.state.service.translation_catalog,
        translation_policy=app.state.service.translation_policy,
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    counselling = _fact(evidence, FactType.SERVICE, contains="Consiliere socială")
    voucher = _fact(evidence, FactType.SERVICE, contains="Emitere de fișe")
    address = _fact(evidence, FactType.ADDRESS)
    phone = _fact(evidence, FactType.PHONE)
    assert [name.fact_id, counselling.fact_id, voucher.fact_id, address.fact_id, phone.fact_id] == [
        "f_abe67692e2acf7bf", "f_4b7b1e78895ebd88", "f_f1cdef575c862948",
        "f_029ebb4769e4af84", "f_ca3a05181035f441",
    ]
    response = _answer(evidence,
        ("Contactează „CABL”.", ClaimType.REFERRAL, "24", [name.fact_id]),
        ("Oferă consiliere socială pentru persoane fără acces regulat la sistemul de sănătate și emitere de fișe de tratament anonime.",
         ClaimType.SERVICE, "24", [counselling.fact_id, voucher.fact_id]),
        ("Adresă: Taubestr. 2, 04347 Leipzig, telefon 017645982130.",
         ClaimType.FACT, "24", [address.fact_id, phone.fact_id]),
    )
    return evidence, response


def test_recorded_coordinated_romanian_response_passes_validator(app):
    """Replay f_ro_grounded from run_e9efd98... without a live call."""
    evidence, response = _recorded_cabl_response(app)
    result = validate_formulation(response, evidence)
    assert result.sentence_count == 3
    assert result.card_ids == ["24"]
    assert result.answer == " ".join(sentence.text for sentence in response.sentences)


def test_recorded_response_passes_real_provider_validation(app, monkeypatch):
    evidence, response = _recorded_cabl_response(app)
    provider = BlabladorProvider(_settings("blablador"))
    calls = []

    async def post(payload):
        calls.append(payload)
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", post)
    result = asyncio.run(provider.formulate_answer(evidence=evidence))
    assert len(calls) == 1
    assert result.answer == " ".join(sentence.text for sentence in response.sentences)


@pytest.mark.parametrize("mutation", ["missing_citation", "negated_service", "additional_negation", "invented_service"])
def test_coordinated_romanian_counterexamples_are_rejected(app, mutation):
    evidence, response = _recorded_cabl_response(app)
    sentence = response.sentences[1]
    if mutation == "missing_citation":
        sentence.fact_ids.remove("f_f1cdef575c862948")
    elif mutation == "negated_service":
        sentence.text = "Nu " + sentence.text
    elif mutation == "additional_negation":
        sentence.text = sentence.text[:-1] + " și nu oferă consiliere."
    else:
        sentence.text = sentence.text[:-1] + " și cazare."
    assert _diagnostic(response, evidence) == GroundingDiagnosticCode.SERVICE_FACT_MISSING
