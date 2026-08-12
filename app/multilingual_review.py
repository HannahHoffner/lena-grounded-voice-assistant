"""Exportiert synthetische Sprachreviews und kapselt den Opt-in-Live-Smoke."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .candidate_contract import CANDIDATE_CONTRACT_VERSION
from .config import Settings, load_settings
from .formulation import EVIDENCE_CONTRACT_VERSION, FORMULATOR_CONTRACT_VERSION, FORMULATOR_PROMPT_VERSION
from .i18n import write_json
from .interpreter import INTERPRETER_CONTRACT_VERSION, INTERPRETER_PROMPT_VERSION, Need
from .kb_loader import load_active_knowledge_base
from .live_evaluation import EvaluationStage, LiveRunLimits, require_live_authorization
from .live_evaluation_plan import build_live_dry_run, collect_git_state
from .live_evaluation_runner import (
    run_end_to_end_live_gate,
    run_interpreter_live_gate,
    run_selector_formulator_live_gate,
    run_stability_live_gate,
)
from .llm_selection import SELECTOR_CONTRACT_VERSION, SELECTOR_PROMPT_VERSION
from .models import Language
from .resources import packaged_bootstrap_data_root


SCENARIO_SCHEMA_VERSION = "1"
REVIEW_OUTPUT_VERSION = "1"


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewCriterion(ReviewModel):
    criterion_id: str
    label: str
    scale: list[str]
    comment_required_for: str | None = None


class DynamicScenario(ReviewModel):
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    synthetic_inputs: dict[Language, str]
    expected_need: Need
    expected_candidate_roles: list[str]
    expected_offer_ids: list[str]
    expected_answer_type: str
    forbidden_claims: list[str]
    required_facts: list[str]

    @model_validator(mode="after")
    def require_languages(self) -> "DynamicScenario":
        if set(self.synthetic_inputs) != set(Language):
            raise ValueError("scenario lacks a supported language")
        return self


class ScenarioCatalog(ReviewModel):
    schema_version: str
    description: str
    scenarios: list[DynamicScenario]
    review_raster: list[ReviewCriterion]

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "ScenarioCatalog":
        ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(ids) != len(set(ids)) or len(ids) < 16:
            raise ValueError("scenario inventory is incomplete or duplicated")
        return self


def load_scenario_catalog() -> ScenarioCatalog:
    path = packaged_bootstrap_data_root() / "i18n" / "dynamic_scenarios.json"
    try:
        return ScenarioCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RuntimeError("multilingual_scenario_catalog_invalid") from exc


def _select_scenarios(catalog: ScenarioCatalog, ids: list[str] | None) -> list[DynamicScenario]:
    if not ids:
        return catalog.scenarios
    selected = [item for item in catalog.scenarios if item.scenario_id in ids]
    if {item.scenario_id for item in selected} != set(ids):
        raise ValueError("unknown scenario id")
    return selected


def _review_item(
    scenario: DynamicScenario,
    language: Language,
    settings: Settings,
    fingerprint: str,
    raster: list[ReviewCriterion],
) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "input_language": language.value,
        "requested_output_language": language.value,
        "synthetic_input": scenario.synthetic_inputs[language],
        "expected_need": scenario.expected_need.value,
        "expected_candidate_roles": scenario.expected_candidate_roles,
        "expected_offer_ids": scenario.expected_offer_ids,
        "expected_answer_type": scenario.expected_answer_type,
        "forbidden_claims": scenario.forbidden_claims,
        "required_facts": scenario.required_facts,
        "model_identifier": settings.blablador_model or "not_configured",
        "prompt_versions": {
            "interpreter": INTERPRETER_PROMPT_VERSION,
            "selector": SELECTOR_PROMPT_VERSION,
            "formulator": FORMULATOR_PROMPT_VERSION,
        },
        "contract_versions": {
            "interpreter": INTERPRETER_CONTRACT_VERSION,
            "candidate": CANDIDATE_CONTRACT_VERSION,
            "selector": SELECTOR_CONTRACT_VERSION,
            "evidence": EVIDENCE_CONTRACT_VERSION,
            "formulator": FORMULATOR_CONTRACT_VERSION,
        },
        "knowledge_base_fingerprint": fingerprint,
        "output": None,
        "actual_offer_ids": [],
        "actual_answer_type": None,
        "stage_durations_ms": {},
        "validation_status": "not_run",
        "manual_review_status": "not_reviewed",
        "manual_review": {
            criterion.criterion_id: {"rating": "", "comment": ""} for criterion in raster
        },
    }


def build_review_template(
    settings: Settings,
    *,
    languages: list[Language],
    scenario_ids: list[str] | None,
    repetitions: int,
) -> dict[str, Any]:
    if not 1 <= repetitions <= 20:
        raise ValueError("repetitions must be between 1 and 20")
    catalog = load_scenario_catalog()
    kb = load_active_knowledge_base(settings)
    items = [
        {**_review_item(scenario, language, settings, kb.runtime_kb_fingerprint or "", catalog.review_raster), "repetition": repetition}
        for repetition in range(1, repetitions + 1)
        for scenario in _select_scenarios(catalog, scenario_ids)
        for language in languages
    ]
    return {
        "review_output_version": REVIEW_OUTPUT_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "synthetic_data_only": True,
        "interpretation_limit": "This finite scenario set is not representative and yields no general success rate.",
        "live_smoke_plan": {
            "query_count": len(items),
            "maximum_provider_calls": len(items) * 3,
            "maximum_provider_wait_seconds": len(items) * settings.llm_request_budget_seconds,
            "actual_duration_requires_explicit_live_run": True,
        },
        "items": items,
    }


def _languages(value: str) -> list[Language]:
    return list(dict.fromkeys(Language(item.strip()) for item in value.split(",") if item.strip()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or explicitly run synthetic multilingual LENA reviews.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--languages", default="de,en,pl,ro,ru")
    export.add_argument("--scenario-ids", default="")
    export.add_argument("--repetitions", type=int, default=1)

    dry_run = subparsers.add_parser("live-dry-run")
    dry_run.add_argument("--stage", choices=["all", *(stage.value for stage in EvaluationStage)], default="all")

    live = subparsers.add_parser("live-smoke")
    live.add_argument("--stage", choices=[stage.value for stage in EvaluationStage], required=True)
    live.add_argument("--expected-model", required=True)
    live.add_argument("--expected-provider-domain", required=True)
    live.add_argument("--confirm-live", action="store_true")
    live.add_argument("--max-requests", type=int, required=True)
    live.add_argument("--max-provider-calls", type=int, required=True)
    live.add_argument("--max-interpreter-calls", type=int, required=True)
    live.add_argument("--max-selector-calls", type=int, required=True)
    live.add_argument("--max-formulator-calls", type=int, required=True)
    live.add_argument("--max-total-runtime-seconds", type=float, required=True)
    live.add_argument("--max-failures", type=int, required=True)
    return parser


def _limits(args: argparse.Namespace) -> LiveRunLimits:
    try:
        return LiveRunLimits(
            max_requests=args.max_requests,
            max_provider_calls=args.max_provider_calls,
            max_interpreter_calls=args.max_interpreter_calls,
            max_selector_calls=args.max_selector_calls,
            max_formulator_calls=args.max_formulator_calls,
            max_total_runtime_seconds=args.max_total_runtime_seconds,
            max_failures=args.max_failures,
        )
    except ValidationError as exc:
        raise SystemExit("live_smoke_limits_invalid") from exc


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "live-dry-run":
        stage = None if args.stage == "all" else EvaluationStage(args.stage)
        print(json.dumps(build_live_dry_run(stage), ensure_ascii=False, indent=2))
        return
    if args.command == "live-smoke":
        stage = EvaluationStage(args.stage)
        limits = _limits(args)
        require_live_authorization(confirm_live=args.confirm_live, stage=stage, limits=limits)
        # Ein Lauf auf einem nicht committeten Stand ist nicht reproduzierbar
        # (siehe AP1/Thesis Abschnitt 5.9/6.7): Commit und Dirty-Status werden
        # hier geprüft, bevor Settings oder ein Provider initialisiert werden,
        # unabhängig davon, ob der Runner selbst (z. B. unter Pytest mit
        # Test-Doubles) auf einem dirty Arbeitsbaum lauffähig bleiben muss.
        if collect_git_state().dirty:
            raise SystemExit("live_smoke_dirty_worktree")
        print(json.dumps({
            "live_stage": stage.value,
            "expected_model": args.expected_model,
            "expected_provider_domain": args.expected_provider_domain,
            "limits": limits.model_dump(mode="json"),
            "automatically_starts_next_stage": False,
        }, ensure_ascii=False, indent=2))
        settings = load_settings()
        # Prüft die drei tatsächlich gesendeten Stufenmodelle (siehe
        # Settings.effective_interpreter_model/_selector_model/_formulator_model), nicht nur
        # den gemeinsamen Basiswert: BlabladorProvider kann pro Stufe eigene Overrides senden,
        # die vom Basiswert abweichen. Weichen die Stufen voneinander ab, kann ein einzelnes
        # --expected-model sie nicht eindeutig beschreiben; das Kommando bricht dann bewusst ab,
        # statt eine Stufe stillschweigend ungeprüft zu lassen.
        effective_models = {
            settings.effective_interpreter_model,
            settings.effective_selector_model,
            settings.effective_formulator_model,
        }
        if effective_models != {args.expected_model}:
            raise SystemExit("live_smoke_model_identifier_mismatch")
        if urlsplit(settings.blablador_base_url or "").hostname != args.expected_provider_domain:
            raise SystemExit("live_smoke_provider_domain_mismatch")
        runner = {
            EvaluationStage.INTERPRETER: run_interpreter_live_gate,
            EvaluationStage.SELECTOR_FORMULATOR: run_selector_formulator_live_gate,
            EvaluationStage.END_TO_END: run_end_to_end_live_gate,
            EvaluationStage.STABILITY: run_stability_live_gate,
        }[stage]
        result = asyncio.run(runner(settings, limits))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    settings = load_settings()
    report = build_review_template(
        settings,
        languages=_languages(args.languages),
        scenario_ids=[item for item in args.scenario_ids.split(",") if item] or None,
        repetitions=args.repetitions,
    )
    write_json(args.output, report)
    print(json.dumps({"items": len(report["items"]), "live": False}, indent=2))


if __name__ == "__main__":
    main()
