"""A real service failure path, without a real provider failure or network call."""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.live_evaluation import EvaluationStage, load_live_scenario_catalog
from app.live_evaluation_checks import _evaluate_e2e, _expected_interpreter_failure
from app.live_evaluation_runner import _build_isolated_service, _run_e2e_scenario
from app.live_evaluation_runtime import AtomicRunCounter, LimitedEvaluationProvider
from app.models import Language, QueryRequest
from app.providers.llm import InterpreterError
from test_live_evaluation import FakeFullPipelineProvider, _minimal_response, _settings


def _fixture():
    return next(s for s in load_live_scenario_catalog().scenarios if s.scenario_id == "e_interpreter_error")


def _counter():
    return AtomicRunCounter(load_live_scenario_catalog().plan(EvaluationStage.END_TO_END).live_limits)


def test_fixture_runs_actual_service_fallback_and_does_not_leak_to_next_turn(tmp_path: Path):
    async def run():
        settings = _settings(tmp_path)
        counter = _counter()
        service, wrapper = await _build_isolated_service(
            settings, tmp_path / "isolated", FakeFullPipelineProvider, counter,
        )
        result = await _run_e2e_scenario(_fixture(), service, counter, lambda: 0.0)
        assert result["technically_valid"] is True
        assert result["content_mismatches"] == []
        assert result["unverified_metrics"] == []
        assert result["response_type"] == "technical_fallback"
        assert "Hilfebus" in result["answers"][0]["text"]
        assert result["fault_injections"] == [{
            "turn": 1, "error_code": "interpreter_http_error", "injected_errors": 1,
            "provider_calls": {"interpreter": 0, "selector": 0, "formulator": 0},
        }]
        assert result["stage_errors"] == [{
            "turn": 1, "stage": "interpreter", "error_code": "interpreter_http_error",
            "response_type": "technical_fallback", "fallback_used": True,
            "recovered": False, "answer_provider": "template", "expected_injected_error": True,
        }]
        assert counter.snapshot()["provider_calls"] == 0
        assert wrapper.provider.interpreter_calls == 0
        await service.query(QueryRequest(query="Synthetische Folgefrage", language=Language.DE))
        assert wrapper.provider.interpreter_calls == 1
        assert counter.snapshot()["interpreter_calls"] == 1
        assert not (settings.runtime_dir / "sessions.json").exists()

    asyncio.run(run())


def test_fixture_restores_wrapper_even_if_query_processing_raises(tmp_path: Path):
    async def run():
        wrapper = LimitedEvaluationProvider(FakeFullPipelineProvider(_settings(tmp_path)), _counter())
        with pytest.raises(RuntimeError, match="synthetic"):
            with wrapper.interpreter_failure_fixture() as observation:
                with pytest.raises(InterpreterError, match="interpreter_http_error"):
                    await wrapper.interpret_query(query="synthetic")
                raise RuntimeError("synthetic")
        assert observation["injected_errors"] == 1
        assert observation["provider_calls"] == {"interpreter": 0, "selector": 0, "formulator": 0}
        await wrapper.interpret_query(query="normal")
        assert wrapper.provider.interpreter_calls == 1

    asyncio.run(run())


def _fallback():
    response = _minimal_response(answer_type="technical_fallback")
    response.interaction.route = "interpreter_error"
    response.interaction.interpreter_error_code = "interpreter_http_error"
    return response


def _observation():
    return {
        "error_code": "interpreter_http_error", "injected_errors": 1,
        "provider_calls": {"interpreter": 0, "selector": 0, "formulator": 0},
    }


@pytest.mark.parametrize("change", ["missing", "not_triggered", "wrong_code", "real_call", "selector_call", "formulator_call"])
def test_expected_failure_requires_actual_injection_and_no_real_calls(change):
    observation = _observation()
    if change == "missing":
        observation = None
    elif change == "not_triggered":
        observation["injected_errors"] = 0
    elif change == "wrong_code":
        observation["error_code"] = "interpreter_timeout"
    else:
        stage = {"real_call": "interpreter", "selector_call": "selector", "formulator_call": "formulator"}[change]
        observation["provider_calls"][stage] = 1
    assert _expected_interpreter_failure(_fallback(), observation) is False
    checks, mismatches, _, _ = _evaluate_e2e(_fixture(), _fallback(), fault_observation=observation)
    assert checks["interpreter_failure_fixture_valid"] is False
    assert "interpreter_failure_fixture_valid" in mismatches


@pytest.mark.parametrize("change", ["wrong_type", "wrong_route", "wrong_error", "selector_error", "formulator_error", "foreign_card", "marker", "foreign_spoken", "foreign_source", "model_answer"])
def test_expected_failure_does_not_hide_incorrect_fallback_or_additional_errors(change):
    response = _fallback()
    if change == "wrong_type":
        response.answer_type = "clarification"
    elif change == "wrong_route":
        response.interaction.route = "other"
    elif change == "wrong_error":
        response.interaction.interpreter_error_code = "interpreter_timeout"
    elif change.endswith("_error"):
        setattr(response.interaction, change + "_code", change.replace("_error", "_timeout"))
    elif change == "foreign_card":
        response.card_ids = ["22"]
    elif change == "marker":
        response.map_marker_ids = ["21"]
    elif change == "foreign_spoken":
        response.spoken_result_ids = ["22"]
    elif change == "foreign_source":
        response.interaction.source_ids = ["22"]
    else:
        response.provider = "blablador"
    assert _expected_interpreter_failure(response, _observation()) is False


def test_absent_wrapper_cannot_silently_skip_fault_fixture():
    class Service:
        async def query(self, request):
            raise AssertionError("must not query without injectable evaluation boundary")

    with pytest.raises(RuntimeError, match="fault_fixture_provider_required"):
        asyncio.run(_run_e2e_scenario(_fixture(), Service(), _counter(), lambda: 0.0))


@pytest.mark.parametrize("change", ["string_flag", "multiple_turns", "wrong_component"])
def test_fault_fixture_rejects_ambiguous_or_unsupported_configuration(change):
    data = _fixture().model_dump()
    if change == "string_flag":
        data["fixture"]["inject_interpreter_error"] = "true"
    elif change == "multiple_turns":
        data["synthetic_inputs"].append("zweiter Turn")
    else:
        data["component"] = "interpreter"
    with pytest.raises(ValidationError):
        type(_fixture()).model_validate(data)
