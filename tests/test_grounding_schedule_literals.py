"""Evidence-bound schedule literals, not global abbreviation exceptions."""

import asyncio

import pytest

from app.candidate_contract import CandidateRole
from app.formulation import (
    AnswerType, ClaimType, EvidenceFact, FactType, FormulatorError,
    build_formulator_evidence,
)
from app.grounding import _contains_sentence_break, _strip_evidence_literals, validate_formulation
from app.interpreter import Need
from app.models import Language
from app.providers.llm import BlabladorProvider
from test_formulation import _settings
from test_grounding_claims import _answer, _evidence, _fact, app


@pytest.mark.parametrize("kind", [FactType.OPENING_TIME, FactType.STAND_TIME])
@pytest.mark.parametrize(("language", "literal"), [
    (Language.DE, "Mittwoch: 18:30 Uhr Hauptbahnhof"),
    (Language.EN, "Wednesday: 6:30 p.m. Hauptbahnhof"),
    (Language.PL, "Środa: godz. 18:30 Hauptbahnhof"),
    (Language.RO, "Miercuri: ora 18:30 Hauptbahnhof"),
    (Language.RU, "Среда: 18:30 ч. Hauptbahnhof"),
])
def test_full_schedule_literal_without_quote_marker_is_masked(app, kind, language, literal):
    evidence = _evidence(app, offer_ids=("25",), language=language)
    evidence.selected_offers[0].facts = [
        EvidenceFact(fact_id="f_5555555555555555", fact_type=kind, value="> " + literal),
    ]
    original = literal + "."
    assert _strip_evidence_literals(original, evidence).strip() == "."
    assert not _contains_sentence_break(_strip_evidence_literals(original, evidence))
    assert evidence.selected_offers[0].facts[0].value == "> " + literal


@pytest.mark.parametrize("kind", [FactType.SERVICE, FactType.DESCRIPTION, FactType.ADDRESS])
def test_quote_marker_normalization_is_not_applied_to_other_fact_types(app, kind):
    evidence = _evidence(app)
    literal = "Среда: 18:30 ч. Hauptbahnhof"
    evidence.selected_offers[0].facts = [
        EvidenceFact(fact_id="f_5555555555555555", fact_type=kind, value="> " + literal),
    ]
    assert _strip_evidence_literals(literal + ".", evidence) == literal + "."


def _recorded_uvo_response(app):
    evidence = build_formulator_evidence(
        query="Мне нужна медицинская помощь.", language=Language.RU,
        answer_type=AnswerType.GROUNDED_RESULT, need=Need.MEDICAL,
        offers=[app.state.kb.by_id()["25"]], roles={"25": CandidateRole.DIRECT_SERVICE},
        translation_catalog=app.state.service.translation_catalog,
        translation_policy=app.state.service.translation_policy,
    )
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE, contains="Выездная медицинская помощь")
    phone = _fact(evidence, FactType.PHONE)
    schedule = _fact(evidence, FactType.OPENING_TIME, contains="Среда: 18:30")
    assert schedule.value == "> Среда: 18:30 ч. Hauptbahnhof"
    assert [name.fact_id, service.fact_id, phone.fact_id, schedule.fact_id] == [
        "f_ea576ccbd1ef35d7", "f_13f84ab56bb2f063", "f_37fc64201ad9f94c", "f_4c19e137fb8f2499",
    ]
    response = _answer(evidence,
        ("Воспользуйся “UVO” для выездной медицинской помощи.", ClaimType.ACTION,
         "25", [name.fact_id, service.fact_id]),
        ("Позвони по телефону 015777682195.", ClaimType.FACT, "25", [phone.fact_id]),
        ("Среда: 18:30 ч. Hauptbahnhof.", ClaimType.FACT, "25", [schedule.fact_id]),
    )
    return evidence, response


def test_saved_russian_answer_passes_real_validator_unchanged(app):
    """Replay f_ru_grounded from run_16e1cc0...; no external call."""
    evidence, response = _recorded_uvo_response(app)
    result = validate_formulation(response, evidence)
    assert result.sentence_count == 3
    assert result.card_ids == ["25"]
    assert result.answer == " ".join(sentence.text for sentence in response.sentences)
    assert "18:30 ч. Hauptbahnhof." in result.answer


def test_saved_russian_answer_passes_provider_with_mock_transport(app, monkeypatch):
    evidence, response = _recorded_uvo_response(app)
    # Historical recorded free-text response uses its explicit research adapter.
    from app.prompt_comparison import ComparisonProvider
    from app.formulation import LEGACY_FORMULATOR_SYSTEM_PROMPT
    provider = ComparisonProvider(_settings("blablador"), LEGACY_FORMULATOR_SYSTEM_PROMPT)
    calls = []

    async def post(payload):
        calls.append(payload)
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}

    monkeypatch.setattr(provider, "_post", post)
    result = asyncio.run(provider.formulate_answer(evidence=evidence))
    assert len(calls) == 1
    assert result.answer == " ".join(sentence.text for sentence in response.sentences)


@pytest.mark.parametrize("text", [
    "Среда: 19:30 ч. Hauptbahnhof.",
    "Среда: 18:30 ч. UnbelegterOrt.",
    "Среда: 18:30 ч. Hauptbahnhof. Здесь есть свободные места.",
])
def test_real_sentences_and_changed_schedule_details_remain_rejected(app, text):
    evidence, response = _recorded_uvo_response(app)
    response.sentences[-1].text = text
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


def test_non_cited_schedule_is_accepted_only_while_present_in_offer_evidence(app):
    evidence, response = _recorded_uvo_response(app)
    response.sentences[-1].fact_ids = [_fact(evidence, FactType.PHONE).fact_id]
    assert validate_formulation(response, evidence).sentence_count == 3
    evidence.selected_offers[0].facts = [f for f in evidence.selected_offers[0].facts
                                        if f.fact_type != FactType.OPENING_TIME]
    with pytest.raises(FormulatorError):
        validate_formulation(response, evidence)


@pytest.mark.parametrize("marker", [">> ", "- ", "* ", "# "])
def test_schedule_presentation_marker_does_not_change_verified_details(app, marker):
    evidence, response = _recorded_uvo_response(app)
    fact = _fact(evidence, FactType.OPENING_TIME, contains="Среда: 18:30")
    fact.value = marker + fact.value.removeprefix("> ")
    assert validate_formulation(response, evidence).answer == " ".join(s.text for s in response.sentences)


@pytest.mark.parametrize("text", [
    "Среда: 18:30 ч. Hauptbahnhof. Позвони ещё раз.",
    "Среда: 18:30 ч. Позвони по телефону.",
])
def test_grounded_schedule_can_include_a_contact_request(app, text):
    evidence, response = _recorded_uvo_response(app)
    response.sentences[-1].text = text
    assert validate_formulation(response, evidence).answer.endswith(text)


def test_time_abbreviation_alone_does_not_disable_sentence_detection():
    assert _contains_sentence_break("18:30 ч. Позвони по телефону.")
    assert _contains_sentence_break("Первое предложение. Второе предложение.")
    assert _contains_sentence_break("First sentence. Second sentence.")
