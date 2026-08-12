"""Versionierte Planung und harte Grenzen der synthetischen Live-Evaluation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .resources import packaged_bootstrap_data_root


LIVE_EVALUATION_CONTRACT_VERSION = "1"
LIVE_SCENARIO_CATALOG_VERSION = "1"
LIVE_SMOKE_ENVIRONMENT_FLAG = "LENA_ALLOW_LIVE_SMOKE"
LIVE_REPORT_SUBDIRECTORY = Path("live-evaluations")
RUN_ID_RE = re.compile(r"^run_[0-9a-f]{32}$")
EXECUTABLE_LIVE_STAGES = frozenset(
    {"interpreter", "selector-formulator", "end-to-end", "stability"}
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationStage(str, Enum):
    INTERPRETER = "interpreter"
    SELECTOR_FORMULATOR = "selector-formulator"
    END_TO_END = "end-to-end"
    STABILITY = "stability"


class EvaluationComponent(str, Enum):
    INTERPRETER = "interpreter"
    SELECTOR = "selector"
    FORMULATOR = "formulator"
    END_TO_END = "end_to_end"


class AssessmentKind(str, Enum):
    AUTOMATIC = "automatic"
    RULE_BASED = "rule_based"
    HUMAN = "human"


class StageCalls(StrictModel):
    interpreter: int = Field(ge=0)
    selector: int = Field(ge=0)
    formulator: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.interpreter + self.selector + self.formulator


class LiveRunLimits(StrictModel):
    max_requests: int = Field(gt=0)
    max_provider_calls: int = Field(gt=0)
    max_interpreter_calls: int = Field(ge=0)
    max_selector_calls: int = Field(ge=0)
    max_formulator_calls: int = Field(ge=0)
    max_total_runtime_seconds: float = Field(gt=0)
    max_failures: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_call_total(self) -> "LiveRunLimits":
        component_total = (
            self.max_interpreter_calls + self.max_selector_calls + self.max_formulator_calls
        )
        if component_total != self.max_provider_calls:
            raise ValueError("component call limits must equal provider call limit")
        if not math.isfinite(self.max_total_runtime_seconds):
            raise ValueError("runtime limit must be finite")
        return self


class ScenarioExpectation(StrictModel):
    required: dict[str, Any] = Field(default_factory=dict)
    allowed: dict[str, list[Any]] = Field(default_factory=dict)
    forbidden: list[str] = Field(default_factory=list)
    human_review_required: list[str] = Field(default_factory=list)


class LiveScenario(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    component: EvaluationComponent
    language: Literal["de", "en", "pl", "ro", "ru"]
    synthetic_inputs: list[str] = Field(min_length=1, max_length=3)
    fixture: dict[str, Any] = Field(default_factory=dict)
    expectation: ScenarioExpectation

    @model_validator(mode="after")
    def validate_synthetic_inputs(self) -> "LiveScenario":
        if any(not item.strip() or len(item) > 2_000 for item in self.synthetic_inputs):
            raise ValueError("synthetic input is empty or too long")
        return self


class MetricDefinition(StrictModel):
    metric_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    assessment: AssessmentKind


class EvaluationStagePlan(StrictModel):
    stage: EvaluationStage
    scenario_ids: list[str] = Field(min_length=1)
    repetitions: int = Field(default=1, ge=1, le=10)
    request_count: int = Field(gt=0)
    minimum_calls: StageCalls
    maximum_calls: StageCalls
    maximum_provider_wait_seconds: float = Field(gt=0)
    live_limits: LiveRunLimits

    @model_validator(mode="after")
    def validate_limits(self) -> "EvaluationStagePlan":
        if self.live_limits.max_requests != self.request_count:
            raise ValueError("request limit must equal planned request count")
        if self.live_limits.max_provider_calls != self.maximum_calls.total:
            raise ValueError("provider limit must equal planned maximum calls")
        for component in ("interpreter", "selector", "formulator"):
            if getattr(self.minimum_calls, component) > getattr(self.maximum_calls, component):
                raise ValueError("minimum calls exceed maximum calls")
            if getattr(self.live_limits, f"max_{component}_calls") != getattr(
                self.maximum_calls, component
            ):
                raise ValueError("component limit differs from stage plan")
        return self


class LiveScenarioCatalog(StrictModel):
    contract_version: Literal[LIVE_EVALUATION_CONTRACT_VERSION]
    catalog_version: Literal[LIVE_SCENARIO_CATALOG_VERSION]
    synthetic_data_only: Literal[True]
    synthetic_safety_notice: Literal[
        "All described danger situations are fictional test cases and do not represent real events."
    ]
    scenarios: list[LiveScenario] = Field(min_length=1, max_length=100)
    stages: list[EvaluationStagePlan] = Field(min_length=4, max_length=4)
    metrics: dict[EvaluationComponent, list[MetricDefinition]]

    @model_validator(mode="after")
    def validate_catalog(self) -> "LiveScenarioCatalog":
        by_id = {item.scenario_id: item for item in self.scenarios}
        if len(by_id) != len(self.scenarios):
            raise ValueError("duplicate scenario ID")
        by_stage = {item.stage: item for item in self.stages}
        if set(by_stage) != set(EvaluationStage):
            raise ValueError("every stage must occur exactly once")
        for plan in self.stages:
            if any(item not in by_id for item in plan.scenario_ids):
                raise ValueError("stage references an unknown scenario")
        interpreter = by_stage[EvaluationStage.INTERPRETER]
        interpreter_items = [by_id[item] for item in interpreter.scenario_ids]
        if len(interpreter_items) != 15 or interpreter.minimum_calls != StageCalls(
            interpreter=15, selector=0, formulator=0
        ):
            raise ValueError("interpreter gate must contain exactly 15 isolated calls")
        languages = [item.language for item in interpreter_items]
        if any(languages.count(language) != 3 for language in ("de", "en", "pl", "ro", "ru")):
            raise ValueError("interpreter gate requires three scenarios per language")
        stage_two = [by_id[item] for item in by_stage[EvaluationStage.SELECTOR_FORMULATOR].scenario_ids]
        if sum(item.component == EvaluationComponent.SELECTOR for item in stage_two) != 6:
            raise ValueError("selector-formulator gate requires six selector scenarios")
        if sum(item.component == EvaluationComponent.FORMULATOR for item in stage_two) != 10:
            raise ValueError("selector-formulator gate requires ten formulator scenarios")
        if len(by_stage[EvaluationStage.END_TO_END].scenario_ids) != 27:
            raise ValueError("end-to-end gate requires twenty-seven scenario flows")
        end_to_end = [by_id[item] for item in by_stage[EvaluationStage.END_TO_END].scenario_ids]
        safety_cases = {
            str(item.fixture["safety_case"])
            for item in end_to_end
            if "safety_case" in item.fixture
        }
        if safety_cases != {
            "acute", "uncertain", "non_acute", "historical", "denied",
            "metaphorical", "quoted", "other_person", "prompt_injection",
        }:
            raise ValueError("end-to-end gate lacks the fixed safety evaluation matrix")
        if len(by_stage[EvaluationStage.STABILITY].scenario_ids) != 6:
            raise ValueError("stability gate requires six scenario flows")
        return self

    def plan(self, stage: EvaluationStage) -> EvaluationStagePlan:
        return next(item for item in self.stages if item.stage == stage)

    def scenarios_for(self, stage: EvaluationStage) -> list[LiveScenario]:
        by_id = {item.scenario_id: item for item in self.scenarios}
        return [by_id[item] for item in self.plan(stage).scenario_ids]


def redact_model_identifier(value: str | None) -> str:
    """Reduziert eine Modellkennung auf ein sicheres, kurzes Zeichenrepertoire.

    Gemeinsam genutzt von der providerfreien Planvorschau, dem Run-Manifest
    und der laufzeitseitigen Erfassung der vom Provider zurückgemeldeten
    Modellkennung, damit alle drei Stellen identisch redigieren.
    """
    return re.sub(r"[^A-Za-z0-9._:/-]", "_", value or "not_configured")[:100] or "not_configured"


def _catalog_path() -> Path:
    return packaged_bootstrap_data_root() / "evaluation" / "live_scenarios.json"


def load_live_scenario_catalog() -> LiveScenarioCatalog:
    try:
        return LiveScenarioCatalog.model_validate_json(_catalog_path().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("live_evaluation_catalog_invalid") from exc


def live_scenario_hash() -> str:
    catalog = load_live_scenario_catalog()
    payload = json.dumps(catalog.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def require_live_authorization(
    *,
    confirm_live: bool,
    stage: EvaluationStage,
    limits: LiveRunLimits,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Prüft sämtliche Freigaben und Grenzen vor Settings/Providerinitialisierung."""

    if not confirm_live:
        raise SystemExit("live_smoke_requires_explicit_confirmation")
    if (environ or os.environ).get(LIVE_SMOKE_ENVIRONMENT_FLAG, "").strip().casefold() != "true":
        raise SystemExit("live_smoke_requires_environment_confirmation")
    expected = load_live_scenario_catalog().plan(stage).live_limits
    if limits != expected:
        raise SystemExit("live_smoke_limits_do_not_match_versioned_stage_plan")
    if stage.value not in EXECUTABLE_LIVE_STAGES:
        raise SystemExit("live_smoke_stage_prepared_but_not_released")
