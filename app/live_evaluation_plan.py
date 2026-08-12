"""Providerfreie Konfigurationssicht, Dry-Run und Run-Manifest für WP9B."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from .application_texts import APPLICATION_COPY_VERSION
from .candidate_contract import CANDIDATE_CONTRACT_VERSION
from .config import Settings
from .formulation import (
    EVIDENCE_CONTRACT_VERSION,
    FORMULATOR_CONTRACT_VERSION,
    FORMULATOR_PROMPT_VERSION,
    FormulatorEvidence,
)
from .interpreter import (
    INTERPRETER_CONTRACT_VERSION,
    INTERPRETER_PROMPT_VERSION,
    InterpreterAliasHint,
    InterpreterDialogContext,
    InterpreterUserPayload,
)
from .kb_loader import KnowledgeBase, load_active_knowledge_base
from .live_evaluation import (
    LIVE_REPORT_SUBDIRECTORY,
    LIVE_SCENARIO_CATALOG_VERSION,
    EvaluationStage,
    LiveRunLimits,
    StrictModel,
    live_scenario_hash,
    load_live_scenario_catalog,
    redact_model_identifier,
)
from .llm_selection import (
    SELECTOR_CONTRACT_VERSION,
    SELECTOR_PROMPT_VERSION,
    SelectorCandidateView,
    SelectorNeedView,
    SelectorUserPayload,
)
from .policy_facts import EMERGENCY_POLICY
from .resources import checkout_root, packaged_bootstrap_data_root
from .safety import SAFETY_POLICY_VERSION


class RedactedLiveConfiguration(StrictModel):
    provider_name: Literal["blablador", "template"]
    provider_base_domain: str | None
    redacted_model_identifier: str
    redacted_interpreter_model_identifier: str
    redacted_selector_model_identifier: str
    redacted_formulator_model_identifier: str
    model_assignment: Literal["shared_across_llm_stages", "per_stage_overrides"]
    configured_timeouts: dict[str, float]
    global_budget_seconds: float
    temperature: Literal[0] = 0
    response_format: Literal["json_object"] = "json_object"
    maximum_tokens: dict[str, int]


_SAFE_CONFIG_NAMES = (
    "REWRITE_PROVIDER", "LENA_REWRITE_PROVIDER", "BLABLADOR_MODEL", "LENA_LLM_MODEL",
    "BLABLADOR_INTERPRETER_MODEL", "BLABLADOR_SELECTOR_MODEL", "BLABLADOR_FORMULATOR_MODEL",
    "BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL",
    "LLM_INTERPRETER_TIMEOUT_SECONDS", "LLM_SELECTOR_TIMEOUT_SECONDS",
    "LLM_FORMULATOR_TIMEOUT_SECONDS", "LLM_REQUEST_BUDGET_SECONDS",
    "BLABLADOR_MAX_TOKENS", "LENA_LLM_MAX_TOKENS",
)


def _safe_values(root: Path, environ: Mapping[str, str]) -> dict[str, str]:
    values = {name: environ[name] for name in _SAFE_CONFIG_NAMES if environ.get(name)}
    for filename, override in ((".env", False), (".env.local", True)):
        path = root / filename
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            if name in _SAFE_CONFIG_NAMES and (override or name not in values):
                values[name] = value.strip().strip('"').strip("'")
    return values


def _safe_float(values: Mapping[str, str], name: str, default: float) -> float:
    try:
        value = float(values.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value >= 0.1 else default


def load_redacted_live_configuration(
    root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> RedactedLiveConfiguration:
    """Liest ausschließlich nicht geheime Planwerte, ohne Settings oder Provider."""

    values = _safe_values(root or checkout_root() or Path.cwd(), environ or os.environ)
    provider = (values.get("REWRITE_PROVIDER") or values.get("LENA_REWRITE_PROVIDER") or "template").casefold()
    provider = provider if provider in {"template", "blablador"} else "template"
    raw_model = values.get("BLABLADOR_MODEL") or values.get("LENA_LLM_MODEL") or "not_configured"
    model = redact_model_identifier(raw_model)
    # Stufen-Overrides folgen genau dem Fallback, den BlabladorProvider real anwendet
    # (Settings.effective_interpreter_model/_selector_model/_formulator_model): eigener
    # Wert, sonst der gemeinsame Basiswert. Ohne diesen Abgleich zeigte die Vorschau
    # weiterhin "shared_across_llm_stages", obwohl die Anwendung längst Stufen-Overrides
    # verwendet.
    raw_interpreter_override = values.get("BLABLADOR_INTERPRETER_MODEL")
    raw_selector_override = values.get("BLABLADOR_SELECTOR_MODEL")
    raw_formulator_override = values.get("BLABLADOR_FORMULATOR_MODEL")
    interpreter_model = redact_model_identifier(raw_interpreter_override or raw_model)
    selector_model = redact_model_identifier(raw_selector_override or raw_model)
    formulator_model = redact_model_identifier(raw_formulator_override or raw_model)
    # Maßgeblich ist, ob überhaupt ein Stufen-Override konfiguriert ist, nicht ob die
    # resultierenden Werte zufällig übereinstimmen (aktuell sind alle drei "alias-fast").
    model_assignment = (
        "per_stage_overrides"
        if any((raw_interpreter_override, raw_selector_override, raw_formulator_override))
        else "shared_across_llm_stages"
    )
    raw_base_url = values.get("BLABLADOR_BASE_URL") or values.get("LENA_LLM_BASE_URL") or ""
    base_domain = urlsplit(raw_base_url).hostname
    try:
        configured_max = max(200, int(values.get("BLABLADOR_MAX_TOKENS") or values.get("LENA_LLM_MAX_TOKENS") or 1200))
    except ValueError:
        configured_max = 1200
    return RedactedLiveConfiguration(
        provider_name=provider,
        provider_base_domain=base_domain,
        redacted_model_identifier=model,
        redacted_interpreter_model_identifier=interpreter_model,
        redacted_selector_model_identifier=selector_model,
        redacted_formulator_model_identifier=formulator_model,
        model_assignment=model_assignment,
        configured_timeouts={
            "interpreter": _safe_float(values, "LLM_INTERPRETER_TIMEOUT_SECONDS", 15.0),
            "selector": _safe_float(values, "LLM_SELECTOR_TIMEOUT_SECONDS", 10.0),
            "formulator": _safe_float(values, "LLM_FORMULATOR_TIMEOUT_SECONDS", 30.0),
        },
        global_budget_seconds=_safe_float(values, "LLM_REQUEST_BUDGET_SECONDS", 45.0),
        maximum_tokens={
            "interpreter": min(configured_max, 700),
            "selector": min(configured_max, 300),
            "formulator": min(configured_max, 900),
        },
    )


def provider_free_evaluation_settings(root: Path | None = None) -> Settings:
    """Erzeugt read-only Templateeinstellungen ohne `.env`- oder Providerzugriff."""

    app_root = (root or checkout_root() or Path.cwd()).resolve()
    bootstrap = packaged_bootstrap_data_root()
    return Settings(
        app_root=app_root,
        kb_path=bootstrap / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=30,
        blablador_max_context_chars=50_000,
        bootstrap_data_dir=bootstrap,
        data_dir=app_root / "data",
        runtime_dir=app_root / "runtime",
        curation_path=bootstrap / "curation" / "social_offers.json",
        wfs_auto_sync=False,
        toilet_auto_sync=False,
        drinking_fountain_auto_sync=False,
        interaction_logging_enabled=False,
    )


def provider_payload_field_inventory() -> dict[str, Any]:
    """Leitet das übertragbare Inventar direkt aus den positiven Verträgen ab."""

    return {
        "interpreter": {
            "payload": sorted(InterpreterUserPayload.model_fields),
            "alias": sorted(InterpreterAliasHint.model_fields),
            "dialog": sorted(InterpreterDialogContext.model_fields),
        },
        "selector": {
            "payload": sorted(SelectorUserPayload.model_fields),
            "need": sorted(SelectorNeedView.model_fields),
            "candidate": sorted(SelectorCandidateView.model_fields),
        },
        "formulator": {
            "payload": sorted(FormulatorEvidence.model_fields),
            "offer": ["offer_id", "display_name", "candidate_role", "mandatory", "facts"],
            "fact": ["fact_id", "fact_type", "value"],
            "policy": ["policy_id", "instruction"],
        },
        "forbidden_field_classes": [
            "api_key", "authorization", "raw_fields", "raw_properties", "wfs_record",
            "session_file", "interaction_log", "review_note", "curation_reason",
            "excluded_candidate", "conditional_candidate", "coordinates",
        ],
    }


def _release_inventory(kb: KnowledgeBase) -> dict[str, Any]:
    curation = kb.metadata.get("curation", {})
    toilets = kb.metadata.get("public_toilets", {})
    fountains = kb.metadata.get("drinking_fountains", {})
    return {
        "runtime_kb_fingerprint": kb.runtime_kb_fingerprint,
        "social_release_id": (
            curation.get("approved_source_release_id") if isinstance(curation, dict) else None
        ) or kb.release_id,
        "toilet_release_id": toilets.get("release_id") if isinstance(toilets, dict) else None,
        "drinking_fountain_release_id": fountains.get("release_id") if isinstance(fountains, dict) else None,
        "runtime_counts": {
            "social_offers": len(kb.offers),
            "public_toilets": len(kb.public_toilets),
            "drinking_fountains": len(kb.drinking_fountains),
        },
    }


def build_live_dry_run(stage: EvaluationStage | None = None) -> dict[str, Any]:
    """Plant den vollständigen Lauf ohne Provider, HTTP-Client oder Schreibzugriff."""

    catalog = load_live_scenario_catalog()
    kb = load_active_knowledge_base(provider_free_evaluation_settings())
    configuration = load_redacted_live_configuration()
    plans = catalog.stages if stage is None else [catalog.plan(stage)]
    releases = _release_inventory(kb)
    return {
        "status": "prepared_not_executed",
        "live_provider_calls_authorized": False,
        "synthetic_data_only": True,
        "catalog_version": catalog.catalog_version,
        "scenario_hash": live_scenario_hash(),
        "provider": configuration.model_dump(mode="json"),
        "versions": {
            "interpreter_contract": INTERPRETER_CONTRACT_VERSION,
            "interpreter_prompt": INTERPRETER_PROMPT_VERSION,
            "candidate_contract": CANDIDATE_CONTRACT_VERSION,
            "selector_contract": SELECTOR_CONTRACT_VERSION,
            "selector_prompt": SELECTOR_PROMPT_VERSION,
            "evidence_contract": EVIDENCE_CONTRACT_VERSION,
            "formulator_contract": FORMULATOR_CONTRACT_VERSION,
            "formulator_prompt": FORMULATOR_PROMPT_VERSION,
            "safety_policy": SAFETY_POLICY_VERSION,
            "emergency_policy": EMERGENCY_POLICY.policy_version,
            "application_text": APPLICATION_COPY_VERSION,
        },
        **releases,
        "output_root": "runtime_dir/" + str(LIVE_REPORT_SUBDIRECTORY).replace("\\", "/") + "/<opaque-run-id>",
        "payload_field_inventory": provider_payload_field_inventory(),
        "stages": [
            {
                **plan.model_dump(mode="json"),
                "scenario_count": len(plan.scenario_ids),
                "languages": sorted({item.language for item in catalog.scenarios_for(plan.stage)}),
                "cost_estimate": "not_determinable_without_reliable_provider_pricing",
                "automatically_starts_next_stage": False,
            }
            for plan in plans
        ],
    }


def build_run_manifest(
    *,
    run_id: str,
    stage: EvaluationStage,
    settings: Settings,
    kb: KnowledgeBase,
    limits: LiveRunLimits,
) -> dict[str, Any]:
    releases = _release_inventory(kb)
    return {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "stage": stage.value,
        "synthetic_data_only": True,
        "synthetic_scenario_catalog_version": LIVE_SCENARIO_CATALOG_VERSION,
        "scenario_hash": live_scenario_hash(),
        "provider_name": "blablador",
        # "redacted_model_identifier" bleibt der gemeinsame Basiswert (Rückwärtskompatibilität
        # bestehender Reports). Für den tatsächlichen Identitätsabgleich sind ausschließlich die
        # drei Stufenwerte maßgeblich, da BlabladorProvider pro Stufe eigene Overrides sendet.
        "redacted_model_identifier": redact_model_identifier(settings.blablador_model),
        "redacted_interpreter_model_identifier": redact_model_identifier(settings.effective_interpreter_model),
        "redacted_selector_model_identifier": redact_model_identifier(settings.effective_selector_model),
        "redacted_formulator_model_identifier": redact_model_identifier(settings.effective_formulator_model),
        "interpreter_contract_version": INTERPRETER_CONTRACT_VERSION,
        "interpreter_prompt_version": INTERPRETER_PROMPT_VERSION,
        "selector_contract_version": SELECTOR_CONTRACT_VERSION,
        "selector_prompt_version": SELECTOR_PROMPT_VERSION,
        "formulator_contract_version": FORMULATOR_CONTRACT_VERSION,
        "formulator_prompt_version": FORMULATOR_PROMPT_VERSION,
        "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
        "safety_policy_version": SAFETY_POLICY_VERSION,
        "runtime_kb_fingerprint": releases["runtime_kb_fingerprint"],
        "social_release_id": releases["social_release_id"],
        "toilet_release_id": releases["toilet_release_id"],
        "drinking_fountain_release_id": releases["drinking_fountain_release_id"],
        "application_text_version": APPLICATION_COPY_VERSION,
        "configured_timeouts": {
            "interpreter": settings.llm_interpreter_timeout_seconds,
            "selector": settings.llm_selector_timeout_seconds,
            "formulator": settings.llm_formulator_timeout_seconds,
        },
        "global_budget": settings.llm_request_budget_seconds,
        "request_limit": limits.max_requests,
        "provider_call_limit": limits.max_provider_calls,
        "component_call_limits": {
            "interpreter": limits.max_interpreter_calls,
            "selector": limits.max_selector_calls,
            "formulator": limits.max_formulator_calls,
        },
        "runtime_limit_seconds": limits.max_total_runtime_seconds,
        "failure_limit": limits.max_failures,
    }
