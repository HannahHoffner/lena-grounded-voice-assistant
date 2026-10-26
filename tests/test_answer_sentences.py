"""Visible regression: source formatting must not become an answer table."""

from pathlib import Path

import pytest

from app.answer_plan import AnswerAct, FormulatorPlan
from app.answer_sentences import display_value, fact_sentences
from app.formulation import EvidenceFact, FactType, PLAN_FORMULATOR_CONTRACT_VERSION as FORMULATOR_CONTRACT_VERSION, FormulatorError
from app.grounding import validate_formulation
from app.models import Language
from test_answer_plan import packet, plan


def replace_facts(evidence, pairs):
    offer = evidence.selected_offers[0]
    offer.facts = [EvidenceFact(fact_id=f"f_{i:016x}", fact_type=kind, value=value)
                   for i, (kind, value) in enumerate(pairs)]
    return offer


def test_screenshot_source_values_become_simple_sentences_without_mutating_evidence():
    evidence = packet()
    offer = replace_facts(evidence, [
        (FactType.SERVICE, "> Kaffee, Tee, Wasser"),
        (FactType.SERVICE, "> belegte Brötchen"),
        (FactType.OPENING_TIME, "> Montag - Freitag: 09:00 - 18:00 Uhr"),
        (FactType.TARGET_GROUP, "people_experiencing_homelessness"),
    ])
    offer.display_name = "Bahnhofsmission Leipzig"
    before = evidence.model_dump_json()
    response = plan(evidence, kinds=(FactType.SERVICE, FactType.OPENING_TIME))
    result = validate_formulation(response, evidence)
    assert result.answer == (
        "Bei Bahnhofsmission Leipzig gibt es Kaffee, Tee, Wasser und belegte Brötchen. "
        "Die angegebenen Öffnungszeiten sind Montag - Freitag: 09:00 - 18:00 Uhr. "
        "Das Angebot richtet sich an wohnungslose Menschen."
    )
    assert evidence.model_dump_json() == before
    assert result.reference_assessment["renderer_version"] == "1"
    assert result.reference_assessment["emitted_fact_ids"][offer.offer_id] == [f.fact_id for f in offer.facts]
    assert ">" not in result.answer and ";" not in result.answer and "Angebot:" not in result.answer


@pytest.mark.parametrize("language", list(Language))
def test_full_sentences_keep_conditions_negation_contacts_and_binding_in_all_languages(language):
    evidence = packet("eligibility", language)
    offer = replace_facts(evidence, [
        (FactType.SERVICE, "> Suppe"),
        (FactType.SERVICE, "> Brot"),
        (FactType.MINIMUM_AGE, "18"),
        (FactType.SERVICE_CONDITION, "Nur Freitag 18:00–19:00"),
        (FactType.NOTE, "Keine Übernachtung"),
        (FactType.ADDRESS, "Testplatz 123"),
        (FactType.PHONE, "+49 341 123456"),
    ])
    result = validate_formulation(plan(evidence, kinds=(FactType.SERVICE, FactType.PHONE)), evidence)
    assert offer.display_name in result.answer
    assert result.answer.endswith(".")
    for value in ["Suppe", "Brot", "18", "Nur Freitag 18:00–19:00", "Keine Übernachtung", "+49 341 123456"]:
        assert value in result.answer
    assert not any(label in result.answer for label in ["Angebot:", "Öffnungszeiten:", "Zielgruppe:", "> "])
    assert len(result.answer) <= 600
    assert all(f.fact_id in result.reference_assessment["emitted_fact_ids"][offer.offer_id]
               for f in offer.facts if f.fact_type != FactType.ADDRESS)


@pytest.mark.parametrize("language", list(Language))
def test_each_renderable_fact_type_has_a_complete_sentence(language):
    internal = {FactType.DISPLAY_NAME, FactType.ALIAS, FactType.CAPABILITY, FactType.PLACE_TYPE, FactType.OFFER_TYPE}
    for kind in set(FactType) - internal:
        text = fact_sentences("Testort", [(kind.value, "Quellwert 123")], language)
        assert "Testort" in text and "Quellwert 123" in text
        assert text.endswith(".")
        assert "Testort:" not in text and ";" not in text


@pytest.mark.parametrize("value,expected", [
    ("> Kaffee", "Kaffee"), ("> > - Suppe", "Suppe"),
    ("* Keine Aufnahme ohne Anmeldung", "Keine Aufnahme ohne Anmeldung"),
    ("18. Lebensjahr", "18. Lebensjahr"), ("1. April bis 31. Oktober", "1. April bis 31. Oktober"),
    ("- 5 Grad", "- 5 Grad"), ("+49 341 123", "+49 341 123"),
    ("Beitrag > 5 Euro", "Beitrag > 5 Euro"),
    ("> 5 Euro", "> 5 Euro"), (">=18 Jahre", ">=18 Jahre"),
    ("> Nur Freitag\n> Keine Ausgabe am Samstag", "Nur Freitag / Keine Ausgabe am Samstag"),
])
def test_source_formatting_never_removes_age_dates_negation_or_numbers(value, expected):
    assert display_value(value) == expected


@pytest.mark.parametrize("language", list(Language))
def test_multi_offer_sentences_remain_separate_and_do_not_merge_services(language):
    evidence = packet("two_offers", language)
    acts = [plan(evidence, index=i).sentences[0] for i in range(2)]
    response = FormulatorPlan(contract_version=FORMULATOR_CONTRACT_VERSION, language=language, sentences=acts)
    result = validate_formulation(response, evidence)
    for offer in evidence.selected_offers:
        assert offer.display_name in result.answer
        assert offer.offer_id in result.reference_assessment["emitted_fact_ids"]
    assert len(result.answer) <= 600


def test_formatting_only_value_is_a_controlled_rejection():
    evidence = packet()
    replace_facts(evidence, [(FactType.SERVICE, "> >")])
    with pytest.raises(FormulatorError, match="formulator_invalid_fact"):
        validate_formulation(plan(evidence), evidence)


def test_recorded_bootstrap_contains_the_screenshot_source_format():
    source = Path(__file__).resolve().parents[1] / "app/resources/bootstrap/canonical/offers.json"
    assert '"> Kaffee, Tee, Wasser"' in source.read_text(encoding="utf-8")
    assert '"> belegte Brötchen"' in source.read_text(encoding="utf-8")


def test_http_food_path_uses_real_bootstrap_facts_and_sentence_renderer(tmp_path):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from app.llm_selection import CandidateSelectionResponse
    from app.interpreter import Need, RequestedService
    from app.main import create_app
    from test_api import _interpretation, settings

    class Provider:
        async def interpret_query(self, **kwargs):
            return _interpretation(Need.FOOD, facts={"requested_day": "tuesday", "age": 30},
                                   services=[RequestedService.FOOD])

        async def select_candidates(self, **kwargs):
            return CandidateSelectionResponse(contract_version="1", selection_status="selected", selected_ids=["22"])

        def context_fits(self, evidence):
            return True

        async def formulate_answer(self, **kwargs):
            evidence = kwargs["evidence"]
            offer = next(offer for offer in evidence.selected_offers if offer.offer_id == "22")
            services = [f.fact_id for f in offer.facts if f.fact_type == FactType.SERVICE
                        and f.value in {"> Kaffee, Tee, Wasser", "> belegte Brötchen"}]
            hours = [f.fact_id for f in offer.facts if f.fact_type == FactType.OPENING_TIME][:1]
            response = FormulatorPlan(contract_version=FORMULATOR_CONTRACT_VERSION, language=Language.DE,
                sentences=[AnswerAct(act="facts", offer_id="22", fact_ids=services + hours)], card_ids=["22"])
            return validate_formulation(response, evidence)

    app = create_app(replace(settings(), runtime_dir=tmp_path / "runtime"))
    app.state.service.blablador = Provider()
    with TestClient(app) as client:
        result = client.post("/api/query", json={"query": "Ich habe Hunger.", "language": "de"})
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "ok"
    assert "Bahnhofsmission Leipzig" in body["answer"]
    assert "belegte Brötchen" in body["answer"]
    assert "Bei Bahnhofsmission Leipzig gibt es" in body["answer"]
    assert not any(label in body["answer"] for label in ["> ", "Angebot:", "; Öffnungszeiten:"])
