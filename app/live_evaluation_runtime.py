"""Atomare Laufgrenzen und lokaler Reportstore für WP9B."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from .formulation import FormulatorError, GroundingDiagnosticCode
from .live_evaluation import (
    LIVE_REPORT_SUBDIRECTORY,
    RUN_ID_RE,
    EvaluationComponent,
    LiveRunLimits,
)
from .providers.diagnostics import (
    HTTP_STATUS_FAILURE_KINDS, SAFE_PROVIDER_FAILURE_KINDS,
    SchemaValidationIssue, schema_issue_records,
)
from .providers.llm import InterpreterError

_HTTP_STATUS_FAILURE_VALUES = frozenset(item.value for item in HTTP_STATUS_FAILURE_KINDS)
_SAFE_GROUNDING_DIAGNOSTICS = frozenset(item.value for item in GroundingDiagnosticCode)
_REPORT_WRITE_OPERATIONS = frozenset({"temporary_write", "replace"})
_REPORT_WRITE_FAILURE_KINDS = frozenset({
    "access_denied", "sharing_violation", "lock_violation", "permission_error", "os_error",
})


class EvaluationLimitReached(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AtomicRunCounter:
    """Reserviert jeden Request und Providercall vor Ausführung threadsicher."""

    def __init__(self, limits: LiveRunLimits, *, clock: Any = monotonic) -> None:
        self.limits = limits
        self.clock = clock
        self.started_at = clock()
        self._lock = threading.Lock()
        self.requests = 0
        self.interpreter_calls = 0
        self.selector_calls = 0
        self.formulator_calls = 0
        self.failures = 0

    def _check_runtime(self) -> None:
        if self.clock() - self.started_at >= self.limits.max_total_runtime_seconds:
            raise EvaluationLimitReached("live_evaluation_runtime_limit")

    def reserve_request(self) -> None:
        with self._lock:
            self._check_runtime()
            if self.requests >= self.limits.max_requests:
                raise EvaluationLimitReached("live_evaluation_request_limit")
            self.requests += 1

    def reserve_provider_call(self, component: EvaluationComponent) -> None:
        field = f"{component.value}_calls"
        if component == EvaluationComponent.END_TO_END:
            raise ValueError("end-to-end is not a provider component")
        with self._lock:
            self._check_runtime()
            total = self.interpreter_calls + self.selector_calls + self.formulator_calls
            if total >= self.limits.max_provider_calls:
                raise EvaluationLimitReached("live_evaluation_provider_limit")
            if getattr(self, field) >= getattr(self.limits, f"max_{field}"):
                raise EvaluationLimitReached(f"live_evaluation_{component.value}_limit")
            setattr(self, field, getattr(self, field) + 1)

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.limits.max_failures:
                raise EvaluationLimitReached("live_evaluation_failure_limit")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "requests": self.requests,
                "provider_calls": self.interpreter_calls + self.selector_calls + self.formulator_calls,
                "interpreter_calls": self.interpreter_calls,
                "selector_calls": self.selector_calls,
                "formulator_calls": self.formulator_calls,
                "failures": self.failures,
            }


class LimitedEvaluationProvider:
    """Evaluation-only boundary counting real calls, including formulation retries.

    Query metadata cannot prove how many calls happened (preflight bypasses and
    retries differ). Reserve at the provider boundary without altering runtime
    service behavior, and never let an in-flight call outlive the run budget.
    """

    def __init__(self, provider: Any, counter: AtomicRunCounter) -> None:
        self.provider = provider
        self.counter = counter
        # Verworfene Formulierungen der End-to-End-Stufe. Dort behandelt
        # ``QueryService`` den Fehler intern und liefert die Vorlage, sodass der
        # Runner ihn nie sieht. Diese Grenze liegt davor und erfasst auch den
        # Wiederholungsversuch, weil er ein zweiter Aufruf durch dieselbe
        # Grenze ist. Der Inhalt entspricht dem, was Stufe 2 ohnehin sichert.
        self.formulator_rejections: list[dict[str, Any]] = []
        self.interpreter_schema_issues: tuple[SchemaValidationIssue, ...] = ()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.provider, name)

    async def _call(self, component: EvaluationComponent, method: str, **kwargs: Any) -> Any:
        self.counter.reserve_provider_call(component)
        remaining = self.counter.limits.max_total_runtime_seconds - (
            self.counter.clock() - self.counter.started_at
        )
        try:
            async with asyncio.timeout(max(0, remaining)):
                return await getattr(self.provider, method)(**kwargs)
        except TimeoutError as exc:
            raise EvaluationLimitReached("live_evaluation_runtime_limit") from exc

    async def interpret_query(self, **kwargs: Any) -> Any:
        self.interpreter_schema_issues = ()
        try:
            return await self._call(EvaluationComponent.INTERPRETER, "interpret_query", **kwargs)
        except InterpreterError as exc:
            self.interpreter_schema_issues = exc.schema_issues
            raise

    async def select_candidates(self, **kwargs: Any) -> Any:
        return await self._call(EvaluationComponent.SELECTOR, "select_candidates", **kwargs)

    async def formulate_answer(self, **kwargs: Any) -> Any:
        try:
            return await self._call(EvaluationComponent.FORMULATOR, "formulate_answer", **kwargs)
        except FormulatorError as exc:
            self.formulator_rejections.append({
                "error_code": exc.code,
                "grounding_diagnostic_code": (
                    exc.diagnostic_code.value if exc.diagnostic_code is not None else None
                ),
                "rejected_structured_output": (
                    exc.rejected_response.model_dump(mode="json")
                    if exc.rejected_response is not None
                    else None
                ),
            })
            raise


def new_run_id() -> str:
    return "run_" + uuid.uuid4().hex


class EvaluationReportWriteError(RuntimeError):
    """Content-free report failure; never serialize the underlying OS message."""

    code = "live_evaluation_report_write_error"

    def __init__(self, operation: str, error: OSError) -> None:
        if operation not in _REPORT_WRITE_OPERATIONS:
            raise ValueError("invalid report write operation")
        super().__init__(self.code)
        self.operation = operation
        self.failure_kind = {
            5: "access_denied", 32: "sharing_violation", 33: "lock_violation",
        }.get(getattr(error, "winerror", None),
              "permission_error" if isinstance(error, PermissionError) else "os_error")


class EvaluationReportStore:
    """Schreibt ausschließlich vier erlaubte Laufdateien atomar."""

    def __init__(self, runtime_dir: Path, run_id: str) -> None:
        if not RUN_ID_RE.fullmatch(run_id):
            raise ValueError("invalid live evaluation run ID")
        self.path = runtime_dir / LIVE_REPORT_SUBDIRECTORY / run_id
        self._results: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
        except OSError as exc:
            raise EvaluationReportWriteError("temporary_write", exc) from None
        # Windows readers/sync clients can temporarily deny replacement. Retry
        # only that operation, never a provider call or a direct non-atomic write.
        # On permanent failure retain the unpublished snapshot for diagnosis.
        for attempt in range(3):
            try:
                os.replace(temporary, path)
                return
            except OSError as exc:
                if getattr(exc, "winerror", None) in {5, 32, 33} and attempt < 2:
                    sleep(0.05 * (attempt + 1))
                    continue
                raise EvaluationReportWriteError("replace", exc) from None

    def initialize(self, manifest: dict[str, Any]) -> None:
        self.path.mkdir(parents=True, exist_ok=False)
        self._write_json("manifest.json", manifest)

    def _write_json(self, name: str, payload: dict[str, Any]) -> None:
        content = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self._atomic_write(self.path / name, content)

    def _write_jsonl(self, name: str, values: list[dict[str, Any]]) -> None:
        content = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in values)
        self._atomic_write(self.path / name, content.encode("utf-8"))

    def append_result(self, result: dict[str, Any]) -> None:
        self._results.append(result)
        self._write_jsonl("stage-results.jsonl", self._results)

    def append_error(
        self,
        *,
        scenario_id: str,
        code: str,
        provider_failure_kind: str | None = None,
        upstream_status: int | None = None,
        grounding_diagnostic_code: str | None = None,
        report_write_error: EvaluationReportWriteError | None = None,
        schema_issues: tuple[SchemaValidationIssue, ...] = (),
    ) -> None:
        record: dict[str, Any] = {"scenario_id": scenario_id, "error_code": code[:80]}
        issue_records = schema_issue_records(schema_issues)
        if issue_records:
            if code != "interpreter_schema_error":
                raise ValueError("schema diagnostics require an interpreter schema error")
            record["schema_issues"] = issue_records
        if report_write_error is not None:
            if code != EvaluationReportWriteError.code:
                raise ValueError("report diagnostic requires a report write error")
            if (not isinstance(report_write_error, EvaluationReportWriteError)
                    or report_write_error.operation not in _REPORT_WRITE_OPERATIONS
                    or report_write_error.failure_kind not in _REPORT_WRITE_FAILURE_KINDS):
                raise ValueError("report diagnostic is not allowlisted")
            record["report_operation"] = report_write_error.operation
            record["report_failure_kind"] = report_write_error.failure_kind
        if provider_failure_kind is not None:
            if provider_failure_kind not in SAFE_PROVIDER_FAILURE_KINDS:
                raise ValueError("provider failure kind is not allowlisted")
            record["provider_failure_kind"] = provider_failure_kind
        if upstream_status is not None:
            if type(upstream_status) is not int or not 100 <= upstream_status <= 599:
                raise ValueError("upstream status is invalid")
            if provider_failure_kind not in _HTTP_STATUS_FAILURE_VALUES:
                raise ValueError("upstream status requires an HTTP failure kind")
            record["upstream_status"] = upstream_status
        elif provider_failure_kind in _HTTP_STATUS_FAILURE_VALUES:
            raise ValueError("HTTP failure kind requires upstream status")
        if grounding_diagnostic_code is not None:
            if code != "formulator_ungrounded_claim":
                raise ValueError("grounding diagnostic requires an ungrounded formulator error")
            if grounding_diagnostic_code not in _SAFE_GROUNDING_DIAGNOSTICS:
                raise ValueError("grounding diagnostic is not allowlisted")
            record["grounding_diagnostic_code"] = grounding_diagnostic_code
        self._errors.append(record)
        self._write_jsonl("redacted-errors.jsonl", self._errors)

    def finalize(self, summary: dict[str, Any]) -> None:
        self._write_json("summary.json", summary)
