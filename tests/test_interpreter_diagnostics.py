"""Sichere Schemadiagnosen ohne Modellinhalte oder aufgeweichte Verträge."""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.interpreter import INTERPRETER_SYSTEM_PROMPT, QueryInterpretation
from app.live_evaluation import EvaluationStage, load_live_scenario_catalog
from app.live_evaluation_runner import _run_e2e_scenario, run_end_to_end_live_gate, run_interpreter_live_gate
from app.live_evaluation_runtime import (
    AtomicRunCounter, EvaluationReportStore, LimitedEvaluationProvider, new_run_id,
)
from app.models import Language
from app.providers.diagnostics import (
    SchemaValidationIssue,
    interpreter_schema_issues,
    schema_issue_records,
)
from app.providers.llm import BlabladorProvider, InterpreterError
from test_interpreter import _result
from test_live_evaluation import _acute_test_scenario, _minimal_response, _settings


SECRET = "private-person-secret-value"


def _issues(payload):
    with pytest.raises(ValidationError) as raised:
        QueryInterpretation.model_validate(payload)
    return interpreter_schema_issues(raised.value)


@pytest.mark.parametrize(("mutation", "path", "error_type"), [
    (lambda p: p.pop("acute_risk_status"), "acute_risk_status", "missing"),
    (lambda p: p.update(need=SECRET), "need", "enum"),
    (lambda p: p["explicit_facts"].update(age=SECRET), "explicit_facts.age", "int_type"),
    (lambda p: p.update({SECRET: SECRET}), "<extra>", "extra_forbidden"),
    (lambda p: p["explicit_facts"].update({SECRET: SECRET}), "explicit_facts.<extra>", "extra_forbidden"),
    (lambda p: p.update(uncertain_hints=[{"field": "other", "value": ""}]),
     "uncertain_hints.*.value", "string_too_short"),
    (lambda p: p.update(scope_status="out_of_scope", need="general_help"),
     "$", "out_of_scope_need_mismatch"),
    (lambda p: p.update(potentially_missing_information=["age"]),
     "$", "clarification_mismatch"),
    (lambda p: p.update(explicit_service_requests=["food", "food"]),
     "$", "duplicate_services"),
    (lambda p: p.update(potentially_missing_information=["age", "age"], clarification_may_be_needed=True),
     "$", "duplicate_missing_information"),
    (lambda p: p["explicit_facts"].update(age=16, age_group="adult"),
     "explicit_facts", "age_group_mismatch"),
    (lambda p: p["explicit_facts"].update(district=" "),
     "explicit_facts.district", "blank_district"),
])
def test_schema_diagnostics_are_closed_and_values_are_not_copied(mutation, path, error_type):
    payload = _result()
    mutation(payload)
    records = schema_issue_records(_issues(payload))
    assert records == [{"field_path": path, "error_type": error_type}]
    assert SECRET not in json.dumps(records)


def test_diagnostics_are_bounded_and_unknown_types_do_not_leak():
    records = schema_issue_records(_issues({SECRET: SECRET}))
    assert len(records) == 8
    assert SECRET not in json.dumps(records)
    fabricated = ValidationError.from_exception_data("synthetic", [
        {"type": "value_error", "loc": (SECRET,), "input": SECRET,
         "ctx": {"error": ValueError(SECRET)}},
    ])
    assert schema_issue_records(interpreter_schema_issues(fabricated)) == [
        {"field_path": "<extra>", "error_type": "value_error"},
    ]


@pytest.mark.parametrize(("path", "error_type"), [
    (SECRET, "missing"), ("need", SECRET), ("need." + SECRET, "enum"),
])
def test_diagnostic_objects_reject_unallowlisted_fields(path, error_type):
    with pytest.raises(ValueError):
        SchemaValidationIssue(path, error_type)


def test_prompt_covers_semantic_validator_rules():
    for phrase in (
        "If scope_status is out_of_scope, need must be unknown",
        "0-4 unique values", "0-8 unique values",
        "true only when potentially_missing_information is non-empty, false otherwise",
        "A numeric age determines the matching age_group",
        "district must not be empty or whitespace-only",
    ):
        assert phrase in INTERPRETER_SYSTEM_PROMPT


class InvalidSchemaProvider(BlabladorProvider):
    async def _post(self, payload):
        result = _result()
        result["need"] = SECRET
        return {"choices": [{"message": {"content": json.dumps(result)}}]}


def test_real_provider_logs_only_safe_schema_metadata(tmp_path, caplog):
    provider = InvalidSchemaProvider(_settings(tmp_path))
    with pytest.raises(InterpreterError) as raised:
        asyncio.run(provider.interpret_query(query=SECRET, language=Language.DE, category=None, aliases=[]))
    assert raised.value.code == "interpreter_schema_error"
    assert schema_issue_records(raised.value.schema_issues) == [{"field_path": "need", "error_type": "enum"}]
    record = next(r for r in caplog.records if r.message == "query.interpreter.schema_invalid")
    assert record.schema_issues == [{"field_path": "need", "error_type": "enum"}]
    assert record.exc_info is None
    assert SECRET not in str(record.__dict__)


def test_stage_one_persists_safe_diagnostics_without_changing_gate(tmp_path):
    settings = _settings(tmp_path)
    limits = load_live_scenario_catalog().plan(EvaluationStage.INTERPRETER).live_limits
    result = asyncio.run(run_interpreter_live_gate(settings, limits, provider_factory=InvalidSchemaProvider))
    assert result["counts"]["failures"] == 3
    assert result["contract_gate_passed"] is False
    assert result["content_gate_passed"] is False
    root = settings.runtime_dir / result["report_directory"]
    for filename in ("stage-results.jsonl", "redacted-errors.jsonl"):
        text = (root / filename).read_text(encoding="utf-8")
        assert SECRET not in text
        rows = [json.loads(line) for line in text.splitlines()]
        rows = [r for r in rows if r.get("schema_issues")]
        assert len(rows) == 3
        assert all(r["schema_issues"] == [{"field_path": "need", "error_type": "enum"}] for r in rows)


def test_e2e_retains_schema_diagnosis_before_service_handles_exception(tmp_path):
    settings = _settings(tmp_path)
    limits = load_live_scenario_catalog().plan(EvaluationStage.END_TO_END).live_limits
    result = asyncio.run(run_end_to_end_live_gate(settings, limits, provider_factory=InvalidSchemaProvider))
    assert result["contract_gate_passed"] is False
    root = settings.runtime_dir / result["report_directory"]
    text = (root / "stage-results.jsonl").read_text(encoding="utf-8")
    assert SECRET not in text
    errors = [error for line in text.splitlines() for error in json.loads(line)["stage_errors"]
              if error["error_code"] == "interpreter_schema_error"]
    assert errors
    assert all(e["schema_issues"] == [{"field_path": "need", "error_type": "enum"}] for e in errors)


def test_report_store_validates_schema_diagnostics(tmp_path: Path):
    store = EvaluationReportStore(tmp_path, new_run_id())
    store.initialize({})
    issues = (SchemaValidationIssue("need", "enum"),)
    with pytest.raises(ValueError):
        store.append_error(scenario_id="synthetic", code="interpreter_timeout", schema_issues=issues)
    with pytest.raises(ValueError):
        store.append_error(scenario_id="synthetic", code="interpreter_schema_error", schema_issues=issues * 9)
    with pytest.raises(ValueError):
        store.append_error(scenario_id="synthetic", code="interpreter_schema_error", schema_issues=({"input": SECRET},))
    store.append_error(scenario_id="synthetic", code="interpreter_schema_error", schema_issues=issues)
    record = json.loads((store.path / "redacted-errors.jsonl").read_text(encoding="utf-8"))
    assert record["schema_issues"] == [{"field_path": "need", "error_type": "enum"}]


def test_evaluation_wrapper_clears_diagnostics_on_next_success_or_other_failure(tmp_path):
    class SwitchingProvider(BlabladorProvider):
        responses = iter([
            {**_result(), "need": SECRET}, _result(), None,
        ])

        async def _post(self, payload):
            result = next(self.responses)
            return {"choices": [{"message": {"content": json.dumps(result)}}]}

    limits = load_live_scenario_catalog().plan(EvaluationStage.INTERPRETER).live_limits
    provider = LimitedEvaluationProvider(SwitchingProvider(_settings(tmp_path)), AtomicRunCounter(limits))

    async def run():
        kwargs = dict(query="Synthetischer Test", language=Language.DE, category=None, aliases=[])
        with pytest.raises(InterpreterError):
            await provider.interpret_query(**kwargs)
        assert provider.interpreter_schema_issues
        await provider.interpret_query(**kwargs)
        assert provider.interpreter_schema_issues == ()
        with pytest.raises(InterpreterError):
            await provider.interpret_query(**kwargs)
        assert provider.interpreter_schema_issues == ()

    asyncio.run(run())


def test_e2e_clears_schema_diagnostics_between_turns_without_interpreter_calls():
    limits = load_live_scenario_catalog().plan(EvaluationStage.END_TO_END).live_limits
    counter = AtomicRunCounter(limits)
    wrapper = LimitedEvaluationProvider(object(), counter)
    wrapper.interpreter_schema_issues = (SchemaValidationIssue("need", "enum"),)
    scenario = _acute_test_scenario("t_schema_turn_boundary", "uncertain")
    scenario.synthetic_inputs = ["Synthetischer erster Turn", "Synthetischer Folgeturn"]

    class FakeService:
        blablador = wrapper
        calls = 0

        async def query(self, request):
            self.calls += 1
            if self.calls == 1:
                wrapper.interpreter_schema_issues = (SchemaValidationIssue("need", "enum"),)
            response = _minimal_response(answer_type="technical_fallback")
            response.interaction.interpreter_error_code = "interpreter_schema_error"
            return response

    result = asyncio.run(_run_e2e_scenario(scenario, FakeService(), counter, lambda: 0.0))
    assert result["stage_errors"][0]["schema_issues"] == [{"field_path": "need", "error_type": "enum"}]
    assert result["stage_errors"][1]["schema_issues"] == []
