"""Isolierter, limitierter Runner für WP9B-Stufe 1."""

from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic
from typing import Any, Callable
from urllib.parse import urlsplit

from .config import Settings
from .interpreter import QueryInterpretation, interpreter_alias_hints
from .kb_loader import load_active_knowledge_base
from .live_evaluation import (
    LIVE_REPORT_SUBDIRECTORY,
    EvaluationComponent,
    EvaluationStage,
    LiveRunLimits,
    LiveScenario,
    load_live_scenario_catalog,
)
from .live_evaluation_plan import build_run_manifest
from .live_evaluation_runtime import (
    AtomicRunCounter,
    EvaluationLimitReached,
    EvaluationReportStore,
    new_run_id,
)
from .models import Language
from .providers.llm import BlabladorProvider, InterpreterError


def _actual_value(output: QueryInterpretation, name: str) -> Any:
    value = getattr(output, name)
    return value.value if hasattr(value, "value") else value


def _evaluate_interpretation(
    scenario: LiveScenario,
    output: QueryInterpretation,
) -> tuple[dict[str, bool], list[str], bool]:
    required = scenario.expectation.required
    mismatches = [
        name
        for name, expected in required.items()
        if name in QueryInterpretation.model_fields and _actual_value(output, name) != expected
    ]
    mismatches.extend(
        name
        for name, allowed in scenario.expectation.allowed.items()
        if name in QueryInterpretation.model_fields
        and _actual_value(output, name) not in allowed
        and name not in mismatches
    )
    metrics = {
        "json_parse_valid": True,
        "schema_valid": True,
        "contract_valid": True,
        "need_correct": "need" not in mismatches,
        "scope_correct": "scope_status" not in mismatches,
        "language_correct": "input_language" not in mismatches,
        "explicit_facts_correct": "explicit_facts" not in mismatches,
        "missing_information_correct": "potentially_missing_information" not in mismatches,
        "acute_risk_status_correct": "acute_risk_status" not in mismatches,
        "forbidden_id_absent": True,
        "forbidden_answer_absent": True,
    }
    expected_risk = required.get("acute_risk_status")
    critical = (
        expected_risk == "detected" and output.acute_risk_status.value != "detected"
    ) or (
        expected_risk == "uncertain" and output.acute_risk_status.value == "not_detected"
    )
    return metrics, mismatches, critical


def _error_metrics(code: str) -> dict[str, bool]:
    parsed = code not in {"interpreter_invalid_json", "interpreter_timeout", "interpreter_http_error"}
    schema = parsed and code != "interpreter_schema_error"
    return {
        "json_parse_valid": parsed,
        "schema_valid": schema,
        "contract_valid": False,
        "need_correct": False,
        "scope_correct": False,
        "language_correct": False,
        "explicit_facts_correct": False,
        "missing_information_correct": False,
        "acute_risk_status_correct": False,
        "forbidden_id_absent": code != "interpreter_contract_violation",
        "forbidden_answer_absent": code != "interpreter_contract_violation",
    }


def _provider_identity(provider: Any) -> tuple[str, str, str | None]:
    return (
        str(getattr(provider, "name", "")),
        str(getattr(provider, "model", "")),
        urlsplit(str(getattr(provider, "base_url", ""))).hostname,
    )


async def run_interpreter_live_gate(
    settings: Settings,
    limits: LiveRunLimits,
    *,
    provider_factory: Callable[[Settings], Any] = BlabladorProvider,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Führt nur nach vorgelagerter CLI-Freigabe exakt Stufe 1 aus."""

    if not settings.blablador_configured:
        raise RuntimeError("live_evaluation_provider_not_configured")
    catalog = load_live_scenario_catalog()
    plan = catalog.plan(EvaluationStage.INTERPRETER)
    if limits != plan.live_limits:
        raise RuntimeError("live_evaluation_limits_not_bound_to_catalog")
    kb = load_active_knowledge_base(settings)
    run_id = new_run_id()
    store = EvaluationReportStore(settings.runtime_dir, run_id)
    manifest = build_run_manifest(
        run_id=run_id,
        stage=EvaluationStage.INTERPRETER,
        settings=settings,
        kb=kb,
        limits=limits,
    )
    store.initialize(manifest)
    counter = AtomicRunCounter(limits, clock=clock)
    expected_identity = ("blablador", settings.blablador_model or "", urlsplit(settings.blablador_base_url or "").hostname)
    status = "completed"
    abort_reason: str | None = None
    content_mismatches = 0
    critical_content_errors = 0
    aliases = interpreter_alias_hints(kb.offers, kb.organization_aliases)
    current_scenario_id = "run"

    try:
        provider = provider_factory(settings)
        if _provider_identity(provider) != expected_identity:
            raise EvaluationLimitReached("live_evaluation_provider_identity_mismatch")
        for scenario in catalog.scenarios_for(EvaluationStage.INTERPRETER):
            current_scenario_id = scenario.scenario_id
            if _provider_identity(provider) != expected_identity:
                raise EvaluationLimitReached("live_evaluation_provider_identity_changed")
            counter.reserve_request()
            counter.reserve_provider_call(EvaluationComponent.INTERPRETER)
            started = clock()
            try:
                output = await provider.interpret_query(
                    query=scenario.synthetic_inputs[0],
                    language=Language(scenario.language),
                    category=None,
                    aliases=aliases,
                    conversation_history=[],
                    dialog_context=None,
                    timeout_seconds=settings.llm_interpreter_timeout_seconds,
                )
                metrics, mismatches, critical = _evaluate_interpretation(scenario, output)
                content_mismatches += bool(mismatches)
                critical_content_errors += critical
                result = {
                    "scenario_id": scenario.scenario_id,
                    "language": scenario.language,
                    "synthetic_input": scenario.synthetic_inputs[0],
                    "structured_output": output.model_dump(mode="json"),
                    "metrics": metrics,
                    "content_mismatches": mismatches,
                    "critical_content_error": critical,
                    "technically_valid": True,
                    "linguistic_review_pending": True,
                    "duration_ms": round((clock() - started) * 1_000, 2),
                }
                store.append_result(result)
                if critical:
                    counter.record_failure()
            except InterpreterError as exc:
                store.append_result({
                    "scenario_id": scenario.scenario_id,
                    "language": scenario.language,
                    "synthetic_input": scenario.synthetic_inputs[0],
                    "structured_output": None,
                    "metrics": _error_metrics(exc.code),
                    "content_mismatches": [],
                    "critical_content_error": False,
                    "technically_valid": False,
                    "linguistic_review_pending": True,
                    "duration_ms": round((clock() - started) * 1_000, 2),
                })
                store.append_error(scenario_id=scenario.scenario_id, code=exc.code)
                counter.record_failure()
    except EvaluationLimitReached as exc:
        status = "aborted"
        abort_reason = exc.code
        store.append_error(scenario_id=current_scenario_id, code=exc.code)
    except Exception:
        status = "aborted"
        abort_reason = "live_evaluation_unexpected_runtime_error"
        store.append_error(scenario_id=current_scenario_id, code=abort_reason)

    counts = counter.snapshot()
    contract_gate_passed = (
        status == "completed"
        and counts["requests"] == plan.request_count
        and counts["interpreter_calls"] == plan.maximum_calls.interpreter
        and counts["failures"] == 0
    )
    summary = {
        "run_id": run_id,
        "stage": EvaluationStage.INTERPRETER.value,
        "status": status,
        "completed_at": datetime.now(UTC).isoformat(),
        "abort_reason": abort_reason,
        "contract_gate_passed": contract_gate_passed,
        "content_gate_passed": contract_gate_passed and content_mismatches == 0,
        "content_mismatch_count": content_mismatches,
        "critical_content_error_count": critical_content_errors,
        "counts": counts,
        "next_stage_started": False,
        "product_release_asserted": False,
        "clinical_validation_asserted": False,
        "linguistic_review_status": "pending",
    }
    store.finalize(summary)
    return {
        **summary,
        "report_directory": str(LIVE_REPORT_SUBDIRECTORY / run_id).replace("\\", "/"),
    }
