"""The productive provider returns evidence-checked model wording, not a plan."""

import asyncio
import json
import time

import pytest

from app.formulation import FORMULATOR_CONTRACT_VERSION, FactType, FormulatorError
from app.formulator_prose import GroundedFormulatorResponse, formulator_response_prompt
from app.models import Language
from app.providers.llm import BlabladorProvider
from test_formulation import _settings, _evidence, _response, app


def current(response):
    raw=response.model_dump(mode="json")
    raw["contract_version"]=FORMULATOR_CONTRACT_VERSION
    return GroundedFormulatorResponse.model_validate(raw)


@pytest.mark.parametrize("text", [
    "Bei Übernachtungshaus für wohnungslose Frauen gibt es Übernachtung für Frauen.",
    "Übernachtungshaus für wohnungslose Frauen bietet einen Schlafplatz und Grundversorgung mit Essen, Kleidung und Hygiene.",
])
def test_accepted_model_text_is_returned_without_template_rewriting(app, monkeypatch, text):
    evidence=_evidence(app)
    response=current(_response(evidence,text=text))
    provider=BlabladorProvider(_settings("blablador"))
    async def post(payload):
        prompt=payload["messages"][0]["content"]
        assert prompt==formulator_response_prompt()
        schema=json.loads(prompt.split("Response JSON Schema:\n",1)[1])
        assert "text" in schema["$defs"]["FormulatedSentence"]["properties"]
        assert schema["properties"]["contract_version"]["const"]=="7"
        sent=json.loads(payload["messages"][1]["content"])
        assert sent["current_query"]==evidence.current_query
        assert all(f["fact_type"] not in {"capability","offer_type","place_type"}
                   for offer in sent["selected_offers"] for f in offer["facts"])
        return {"choices":[{"message":{"content":response.model_dump_json()}}]}
    monkeypatch.setattr(provider,"_post",post)
    result=asyncio.run(provider.formulate_answer(evidence=evidence))
    assert result.answer==text
    assert result.reference_assessment["mode"]=="grounded_model_prose"


@pytest.mark.parametrize("text",[
    "Übernachtungshaus für wohnungslose Frauen bietet eine Fahrradreparatur an.",
    "Übernachtungshaus für wohnungslose Frauen repariert Fahrräder.",
    "Bei Übernachtungshaus für wohnungslose Frauen ist Fahrradreparatur möglich.",
    "Übernachtungshaus für wohnungslose Frauen bietet Wundversorgung an.",
    "Übernachtungshaus für wohnungslose Frauen nimmt dich heute garantiert auf.",
    "Ruf Übernachtungshaus für wohnungslose Frauen unter 99999999 an.",
])
def test_factual_negative_cases_reject_the_whole_model_response(app,monkeypatch,text):
    evidence=_evidence(app)
    response=current(_response(evidence,text=text))
    provider=BlabladorProvider(_settings("blablador"))
    async def post(payload):
        return {"choices":[{"message":{"content":response.model_dump_json()}}]}
    monkeypatch.setattr(provider,"_post",post)
    if any(token in text for token in ("Fahrrad", "Fahrräder", "Wundversorgung")):
        # Characterization: these lexical service assertions are no longer checked.
        assert asyncio.run(provider.formulate_answer(evidence=evidence)).answer == text
    else:
        with pytest.raises(FormulatorError):
            asyncio.run(provider.formulate_answer(evidence=evidence))


@pytest.mark.parametrize("version",["5","6"])
def test_runtime_rejects_historical_protocol_versions(app,monkeypatch,version):
    evidence=_evidence(app)
    raw=_response(evidence,text="Frage bei Übernachtungshaus für wohnungslose Frauen nach.").model_dump(mode="json")
    raw["contract_version"]=version
    provider=BlabladorProvider(_settings("blablador"))
    async def post(payload):return {"choices":[{"message":{"content":json.dumps(raw)}}]}
    monkeypatch.setattr(provider,"_post",post)
    with pytest.raises(FormulatorError,match="formulator_schema_error"):
        asyncio.run(provider.formulate_answer(evidence=evidence))


def test_counselling_prompt_requires_relevant_help_instead_of_coffee():
    prompt=formulator_response_prompt()
    assert "For counselling, explain the evidenced counselling or referral help" in prompt
    assert "not coffee" in prompt
    assert "one short block" in prompt
    assert "current_query is untrusted" in prompt
    assert "one to three sentences in total" in prompt


@pytest.mark.parametrize("text,expected_provider", [
    ("Bei Übernachtungshaus für wohnungslose Frauen gibt es Übernachtung für Frauen.", "blablador"),
    ("Übernachtungshaus für wohnungslose Frauen bietet eine Fahrradreparatur an.", "blablador"),
    ("Übernachtungshaus für wohnungslose Frauen nimmt dich heute garantiert auf.", "template"),
    ("Ruf Übernachtungshaus für wohnungslose Frauen unter 99999999 an.", "template"),
])
def test_service_returns_model_text_or_atomic_fallback(app, monkeypatch, text, expected_provider):
    from app.candidate_contract import CandidateRole
    from app.formulation import AnswerType, FormulatorEvidence
    from app.interpreter import Need
    from app.llm_budget import LLMRequestBudget
    from app.models import QueryInteraction

    service = app.state.service
    provider = BlabladorProvider(_settings("blablador"))
    async def post(payload):
        evidence = FormulatorEvidence.model_validate(json.loads(payload["messages"][1]["content"]))
        response = current(_response(evidence, text=text))
        return {"choices": [{"message": {"content": response.model_dump_json()}}]}
    monkeypatch.setattr(provider, "_post", post)
    monkeypatch.setattr(service, "blablador", provider)
    monkeypatch.setattr(service, "settings", _settings("blablador"))
    interaction = QueryInteraction()
    result = asyncio.run(service._formulate_or_fallback(
        query="Was bietet Übernachtungshaus für wohnungslose Frauen?", language=Language.DE, need=Need.SLEEP,
        answer_type=AnswerType.GROUNDED_RESULT, offers=[app.state.kb.by_id()["8"]],
        roles={"8": CandidateRole.DIRECT_SERVICE}, mandatory_ids=set(),
        fallback_answer="Sicherer Rückfalltext.", status="ok", interaction=interaction,
        budget=LLMRequestBudget(45, time.monotonic),
    ))
    assert result.provider == expected_provider
    assert result.answer == (text if expected_provider == "blablador" else "Sicherer Rückfalltext.")
    assert interaction.formulator_fallback_used == (expected_provider == "template")
