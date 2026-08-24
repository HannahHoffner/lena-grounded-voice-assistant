"""Atomare Laufgrenzen und lokaler Reportstore für WP9B."""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from time import monotonic
from typing import Any

from .live_evaluation import (
    LIVE_REPORT_SUBDIRECTORY,
    RUN_ID_RE,
    EvaluationComponent,
    LiveRunLimits,
)
from .providers.diagnostics import HTTP_STATUS_FAILURE_KINDS, SAFE_PROVIDER_FAILURE_KINDS

_HTTP_STATUS_FAILURE_VALUES = frozenset(item.value for item in HTTP_STATUS_FAILURE_KINDS)


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


def new_run_id() -> str:
    return "run_" + uuid.uuid4().hex


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
        temporary.write_bytes(content)
        os.replace(temporary, path)

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
    ) -> None:
        record: dict[str, Any] = {"scenario_id": scenario_id, "error_code": code[:80]}
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
        self._errors.append(record)
        self._write_jsonl("redacted-errors.jsonl", self._errors)

    def finalize(self, summary: dict[str, Any]) -> None:
        self._write_json("summary.json", summary)
