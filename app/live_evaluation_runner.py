"""Isolierter, limitierter Runner für WP9B-Stufen 1 bis 4."""

from __future__ import annotations

import dataclasses
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

from .candidate_contract import CandidateRole
from .candidates import CandidateSelector
from .config import Settings
from .formulation import AnswerType, FormulatorError, build_formulator_evidence
from .i18n import TranslationCatalog, load_translation_catalog
from .interpreter import (
    INTERPRETER_CONTRACT_VERSION,
    AcuteRiskStatus,
    AgeGroup,
    ExplicitFacts,
    Gender,
    InputLanguage,
    Need,
    QueryInterpretation,
    RequestedDay,
    ScopeStatus,
    ThreeWayStatus,
    interpreter_alias_hints,
)
from .kb_loader import load_active_knowledge_base
from .live_evaluation import (
    LIVE_REPORT_SUBDIRECTORY,
    EvaluationComponent,
    EvaluationStage,
    LiveRunLimits,
    LiveScenario,
    load_live_scenario_catalog,
    redact_model_identifier,
)
from .live_evaluation_checks import _evaluate_e2e
from .live_evaluation_plan import build_run_manifest, collect_git_state
from .live_evaluation_runtime import (
    AtomicRunCounter,
    EvaluationLimitReached,
    EvaluationReportStore,
    EvaluationReportWriteError,
    LimitedEvaluationProvider,
    new_run_id,
)
from .llm_budget import LLMRequestBudget
from .llm_selection import SelectorError
from .models import Language, OfferRecord, QueryInteraction, QueryRequest, QueryResponse
from .providers.llm import BlabladorProvider, InterpreterError
from .providers.diagnostics import schema_issue_records
from .service import QueryService
from .translation_contract import TranslationRuntimePolicy


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


def _provider_identity(provider: Any) -> tuple[str, str, str, str, str | None]:
    """Identität der drei tatsächlich gesendeten Stufenmodelle, nicht des gemeinsamen Basiswerts.

    ``BlabladorProvider`` sendet pro Stufe ``interpreter_model``/``selector_model``/
    ``formulator_model`` (siehe ``app/providers/llm.py``); nur deren Abgleich mit den
    aus ``Settings`` erwarteten Stufenwerten (``_expected_identity``) erkennt eine
    Konfigurationsänderung zuverlässig. Der frühere Abgleich allein über den
    gemeinsamen ``model``-Basiswert übersah Abweichungen der Stufen-Overrides.
    """
    return (
        str(getattr(provider, "name", "")),
        str(getattr(provider, "interpreter_model", "")),
        str(getattr(provider, "selector_model", "")),
        str(getattr(provider, "formulator_model", "")),
        urlsplit(str(getattr(provider, "base_url", ""))).hostname,
    )


def _expected_identity(settings: Settings) -> tuple[str, str, str, str, str | None]:
    """Erwartete Identität aus denselben Stufen-Fallbacks wie ``BlabladorProvider``."""
    return (
        "blablador",
        settings.effective_interpreter_model or "",
        settings.effective_selector_model or "",
        settings.effective_formulator_model or "",
        urlsplit(settings.blablador_base_url or "").hostname,
    )


def _confirmed_model(provider: Any, component: str) -> str:
    """Liest die vom Provider zuletzt für diese Stufe zurückgemeldete, redigierte Kennung.

    Unterscheidet sich von ``_provider_identity``: Dort wird die *gesendete* Anfrage
    geprüft (Konfigurationsabgleich), hier die vom Provider in der Antwort tatsächlich
    *bestätigte* Modellkennung (Providerseitige Alias-Auflösung, siehe
    ``BlabladorProvider.last_confirmed_models``).
    """
    confirmed = getattr(provider, "last_confirmed_models", None)
    value = confirmed.get(component) if isinstance(confirmed, dict) else None
    return redact_model_identifier(value) if value else "not_yet_confirmed"


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
    git_state = collect_git_state()
    kb = load_active_knowledge_base(settings)
    run_id = new_run_id()
    store = EvaluationReportStore(settings.runtime_dir, run_id)
    manifest = build_run_manifest(
        run_id=run_id,
        stage=EvaluationStage.INTERPRETER,
        settings=settings,
        kb=kb,
        limits=limits,
        git_state=git_state,
    )
    store.initialize(manifest)
    counter = AtomicRunCounter(limits, clock=clock)
    expected_identity = _expected_identity(settings)
    status = "completed"
    abort_reason: str | None = None
    content_mismatches = 0
    critical_content_errors = 0
    aliases = interpreter_alias_hints(kb.offers, kb.organization_aliases)
    current_scenario_id = "run"

    try:
        provider = LimitedEvaluationProvider(provider_factory(settings), counter)
        if _provider_identity(provider) != expected_identity:
            raise EvaluationLimitReached("live_evaluation_provider_identity_mismatch")
        for scenario in catalog.scenarios_for(EvaluationStage.INTERPRETER):
            current_scenario_id = scenario.scenario_id
            if _provider_identity(provider) != expected_identity:
                raise EvaluationLimitReached("live_evaluation_provider_identity_changed")
            counter.reserve_request()
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
                    "confirmed_model_identifier": _confirmed_model(provider, "interpreter"),
                }
                store.append_result(result)
                if critical:
                    counter.record_failure()
            except InterpreterError as exc:
                provider_failure_kind = (
                    exc.provider_failure_kind.value if exc.provider_failure_kind is not None else None
                )
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
                    "confirmed_model_identifier": _confirmed_model(provider, "interpreter"),
                    "provider_failure_kind": provider_failure_kind,
                    "upstream_status": exc.upstream_status,
                    "schema_issues": schema_issue_records(exc.schema_issues),
                })
                store.append_error(
                    scenario_id=scenario.scenario_id,
                    code=exc.code,
                    provider_failure_kind=provider_failure_kind,
                    upstream_status=exc.upstream_status,
                    schema_issues=exc.schema_issues,
                )
                counter.record_failure()
    except EvaluationLimitReached as exc:
        status = "aborted"
        abort_reason = exc.code
        store.append_error(scenario_id=current_scenario_id, code=exc.code)
    except EvaluationReportWriteError as exc:
        status = "aborted"
        abort_reason = exc.code
        store.append_error(scenario_id=current_scenario_id, code=exc.code, report_write_error=exc)
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


def _synthetic_interpretation(fixture: dict[str, Any], language: str) -> QueryInterpretation:
    """Baut eine minimale, interpreterfreie Bedarfsbeschreibung aus einem Stufe-2-Fixture.

    Der Selectorlauf besitzt laut Katalog null Interpreterrufe; die Kandidaten
    entstehen deshalb direkt aus dem deterministischen ``CandidateSelector`` mit
    einer synthetisch gesetzten, ausdrücklich einfachen Interpretation.
    """
    requested_time = fixture.get("requested_time")
    return QueryInterpretation(
        contract_version=INTERPRETER_CONTRACT_VERSION,
        need=Need(fixture["need"]),
        explicit_service_requests=[],
        scope_status=ScopeStatus.IN_SCOPE,
        input_language=InputLanguage(language),
        explicit_facts=ExplicitFacts(
            age=None,
            age_group=AgeGroup.UNKNOWN,
            gender=Gender.UNKNOWN,
            drug_use=ThreeWayStatus.UNKNOWN,
            no_social_benefit_entitlement=ThreeWayStatus.UNKNOWN,
            district=None,
            requested_day=RequestedDay.TODAY if requested_time else None,
            requested_time=requested_time,
        ),
        uncertain_hints=[],
        potentially_missing_information=[],
        clarification_may_be_needed=False,
        acute_risk_status=AcuteRiskStatus.NOT_DETECTED,
    )


_FORMULATOR_NEED_KEYWORDS: tuple[tuple[Need, tuple[str, ...]], ...] = (
    (Need.SLEEP, ("schlafplatz", "übernachtung", "notschlafstelle", "unterkunft", "schlaf")),
    (Need.FOOD, ("essen", "suppe", "verpflegung", "lebensmittel")),
    (Need.MEDICAL, ("medizin", "gesundheit", "wundversorgung", "ärztlich", "behandlung", "versorgung")),
    (Need.ADVICE, ("beratung", "sozialdienst", "sozialberatung", "clearing")),
    (Need.DRINKING_WATER, ("trinkwasser",)),
    (Need.TOILET, ("toilette",)),
)


def _infer_need(offer: OfferRecord) -> Need:
    """Ordnet ein Angebot heuristisch einem Bedarf zu; beeinflusst nur den Prompttext.

    ``FormulatorEvidence.need`` fließt nicht in die Faktenauswahl von
    ``build_formulator_evidence`` ein (diese richtet sich nach ``answer_type``);
    eine ungefähre Zuordnung ist deshalb ausreichend und unkritisch.
    """
    haystack = " ".join([offer.display_name or offer.name, *offer.services]).casefold()
    for need, keywords in _FORMULATOR_NEED_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return need
    return Need.GENERAL_HELP


async def run_selector_formulator_live_gate(
    settings: Settings,
    limits: LiveRunLimits,
    *,
    provider_factory: Callable[[Settings], Any] = BlabladorProvider,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Führt Stufe 2 aus: sechs isolierte Auswahl- und zehn Formulierungsfälle."""

    if not settings.blablador_configured:
        raise RuntimeError("live_evaluation_provider_not_configured")
    catalog = load_live_scenario_catalog()
    plan = catalog.plan(EvaluationStage.SELECTOR_FORMULATOR)
    if limits != plan.live_limits:
        raise RuntimeError("live_evaluation_limits_not_bound_to_catalog")
    git_state = collect_git_state()
    kb = load_active_knowledge_base(settings)
    by_id = kb.by_id()
    translation_catalog = load_translation_catalog(settings, kb)
    translation_policy = TranslationRuntimePolicy(settings.translation_runtime_policy)
    run_id = new_run_id()
    store = EvaluationReportStore(settings.runtime_dir, run_id)
    manifest = build_run_manifest(
        run_id=run_id,
        stage=EvaluationStage.SELECTOR_FORMULATOR,
        settings=settings,
        kb=kb,
        limits=limits,
        git_state=git_state,
    )
    store.initialize(manifest)
    counter = AtomicRunCounter(limits, clock=clock)
    expected_identity = _expected_identity(settings)
    status = "completed"
    abort_reason: str | None = None
    content_mismatches = 0
    critical_content_errors = 0
    current_scenario_id = "run"
    scratch = tempfile.TemporaryDirectory(prefix="lena-live-eval-stage2-")

    try:
        service, provider = await _build_isolated_service(
            settings, Path(scratch.name), provider_factory, counter
        )
        if _provider_identity(provider) != expected_identity:
            raise EvaluationLimitReached("live_evaluation_provider_identity_mismatch")

        for scenario in catalog.scenarios_for(EvaluationStage.SELECTOR_FORMULATOR):
            current_scenario_id = scenario.scenario_id
            if _provider_identity(provider) != expected_identity:
                raise EvaluationLimitReached("live_evaluation_provider_identity_changed")
            counter.reserve_request()
            started = clock()
            if scenario.component == EvaluationComponent.SELECTOR:
                result = await _run_selector_scenario(scenario, provider, kb, counter)
            else:
                result = await _run_formulator_scenario(
                    scenario,
                    service,
                    by_id,
                    counter,
                    translation_catalog=translation_catalog,
                    translation_policy=translation_policy,
                    clock=clock,
                )
            result["duration_ms"] = round((clock() - started) * 1_000, 2)
            content_mismatches += bool(result["content_mismatches"])
            critical_content_errors += int(result["critical_content_error"])
            store.append_result(result)
            if not result["technically_valid"]:
                store.append_error(
                    scenario_id=scenario.scenario_id,
                    code=result.get("error_code", "unknown"),
                    grounding_diagnostic_code=result.get("grounding_diagnostic_code"),
                )
                counter.record_failure()
    except EvaluationLimitReached as exc:
        status = "aborted"
        abort_reason = exc.code
        store.append_error(scenario_id=current_scenario_id, code=exc.code)
    except EvaluationReportWriteError as exc:
        status = "aborted"
        abort_reason = exc.code
        store.append_error(scenario_id=current_scenario_id, code=exc.code, report_write_error=exc)
    except Exception:
        status = "aborted"
        abort_reason = "live_evaluation_unexpected_runtime_error"
        store.append_error(scenario_id=current_scenario_id, code=abort_reason)
    finally:
        scratch.cleanup()

    counts = counter.snapshot()
    contract_gate_passed = (
        status == "completed"
        and counts["requests"] == plan.request_count
        and counts["failures"] == 0
    )
    summary = {
        "run_id": run_id,
        "stage": EvaluationStage.SELECTOR_FORMULATOR.value,
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


async def _run_selector_scenario(
    scenario: LiveScenario,
    provider: Any,
    kb: Any,
    counter: AtomicRunCounter,
) -> dict[str, Any]:
    interpretation = _synthetic_interpretation(scenario.fixture, scenario.language)
    decision = CandidateSelector().select(interpretation, kb.offers)
    base = {
        "scenario_id": scenario.scenario_id,
        "component": "selector",
        "language": scenario.language,
        "synthetic_input": scenario.synthetic_inputs[0],
        "linguistic_review_pending": True,
    }
    if len(decision.selectable_candidates) < 2:
        return {
            **base,
            "structured_output": None,
            "metrics": {"selected_ids_from_candidates": True, "prompt_injection_resisted": True},
            "content_mismatches": [],
            "critical_content_error": False,
            "technically_valid": True,
            "bypass_reason": "insufficient_selectable_candidates",
        }
    try:
        result = await provider.select_candidates(
            query=scenario.synthetic_inputs[0],
            language=Language(scenario.language),
            interpretation=interpretation,
            decision=decision,
            offers=kb.offers,
        )
    except SelectorError as exc:
        return {
            **base,
            "structured_output": None,
            "metrics": {"selected_ids_from_candidates": False, "prompt_injection_resisted": exc.code != "selector_invalid_id"},
            "content_mismatches": [],
            "critical_content_error": False,
            "technically_valid": False,
            "error_code": exc.code,
            "confirmed_model_identifier": _confirmed_model(provider, "selector"),
        }
    selectable_ids = {item.offer_id for item in decision.selectable_candidates}
    ok = set(result.selected_ids) <= selectable_ids
    return {
        **base,
        "structured_output": result.model_dump(mode="json"),
        "metrics": {"selected_ids_from_candidates": ok, "prompt_injection_resisted": ok},
        "content_mismatches": [] if ok else ["selected_ids_from_candidates"],
        "critical_content_error": False,
        "technically_valid": True,
        "confirmed_model_identifier": _confirmed_model(provider, "selector"),
    }


async def _run_formulator_scenario(
    scenario: LiveScenario,
    service: QueryService,
    by_id: dict[str, OfferRecord],
    counter: AtomicRunCounter,
    *,
    translation_catalog: TranslationCatalog,
    translation_policy: TranslationRuntimePolicy,
    clock: Callable[[], float],
) -> dict[str, Any]:
    """Misst den Formulatorpfad der Anwendung, einschliesslich ihres Retrys.

    Der frühere direkte Aufruf von ``provider.formulate_answer`` mass einen
    unwiederholten Erstaufruf, den die Anwendung so nie ausführt: Jede Anfrage
    läuft über ``QueryService._call_formulator`` mit
    ``FORMULATOR_MAX_ATTEMPTS`` und übergibt einem zweiten Versuch die
    geschlossene Groundingdiagnose als Korrekturhinweis.

    Die Retry-Schleife wird bewusst nicht nachgebaut, sondern genau die der
    Anwendung aufgerufen; eine Kopie würde mit der Zeit abweichen und dann
    nicht mehr die Anwendung messen. Jedes Szenario erhält ein eigenes
    Anfragebudget, weil es einer einzelnen Nutzeranfrage entspricht.
    """
    offers = [by_id[offer_id] for offer_id in scenario.fixture["offer_ids"]]
    answer_type = AnswerType(scenario.fixture["answer_type"])
    roles = {
        offer.id: (
            CandidateRole.REFERRAL_CONTACT
            if answer_type == AnswerType.GROUNDED_REFERRAL
            else CandidateRole.DIRECT_SERVICE
        )
        for offer in offers
    }
    evidence = build_formulator_evidence(
        query=scenario.synthetic_inputs[0],
        language=Language(scenario.language),
        answer_type=answer_type,
        need=_infer_need(offers[0]),
        offers=offers,
        roles=roles,
        translation_catalog=translation_catalog,
        translation_policy=translation_policy,
    )
    base = {
        "scenario_id": scenario.scenario_id,
        "component": "formulator",
        "language": scenario.language,
        "synthetic_input": scenario.synthetic_inputs[0],
        "linguistic_review_pending": True,
    }
    provider = service.blablador
    try:
        answer = await service._call_formulator(
            provider.formulate_answer,
            evidence=evidence,
            budget=LLMRequestBudget(service.settings.llm_request_budget_seconds, clock),
            interaction=QueryInteraction(),
        )
    except FormulatorError as exc:
        failed = {
            **base,
            "structured_output": None,
            "metrics": {"grounding_valid": False, "requested_language_correct": False},
            "content_mismatches": [],
            "critical_content_error": False,
            "technically_valid": False,
            "error_code": exc.code,
            "confirmed_model_identifier": _confirmed_model(provider, "formulator"),
        }
        if exc.diagnostic_code is not None:
            failed["grounding_diagnostic_code"] = exc.diagnostic_code.value
        if exc.rejected_response is not None:
            failed["rejected_structured_output"] = exc.rejected_response.model_dump(mode="json")
        return failed
    return {
        **base,
        "structured_output": {
            "answer": answer.answer,
            "card_ids": answer.card_ids,
            "sentence_count": answer.sentence_count,
            "answer_type": answer.answer_type.value,
        },
        "metrics": {"grounding_valid": True, "requested_language_correct": True},
        "reference_assessment": answer.reference_assessment,
        "content_mismatches": [],
        "critical_content_error": False,
        "technically_valid": True,
        "confirmed_model_identifier": _confirmed_model(provider, "formulator"),
    }


async def _run_e2e_scenario(
    scenario: LiveScenario,
    service: QueryService,
    counter: AtomicRunCounter,
    clock: Callable[[], float],
) -> dict[str, Any]:
    session_id: str | None = None
    response: QueryResponse | None = None
    dialogue_opened = False
    technically_valid = True
    stage_errors: list[dict[str, Any]] = []
    # Verworfene Formulierungen werden auf der Evaluationsgrenze erfasst, weil
    # QueryService sie intern behandelt. Der Puffer wird je Szenario geleert,
    # damit jede Verwerfung ihrem Szenario und Turn zugeordnet bleibt.
    rejection_buffer: list[dict[str, Any]] = getattr(
        getattr(service, "blablador", None), "formulator_rejections", []
    )
    rejection_buffer.clear()
    formulator_rejections: list[dict[str, Any]] = []
    reference_buffer = getattr(getattr(service, "blablador", None), "formulator_reference_assessments", [])
    reference_buffer.clear()
    reference_assessments: list[dict[str, Any]] = []
    # Sichtbare Antworten je Turn. Stufe 2 sichert den Antworttext ohnehin; ohne
    # ihn traegt ein End-to-End-Lauf keine qualitative Bewertung.
    answers: list[dict[str, Any]] = []
    started = clock()
    for turn_index, text in enumerate(scenario.synthetic_inputs):
        evaluation_provider = getattr(service, "blablador", None)
        if isinstance(evaluation_provider, LimitedEvaluationProvider):
            evaluation_provider.interpreter_schema_issues = ()
        counter.reserve_request()
        language = Language(scenario.fixture.get("second_language", scenario.language)) if turn_index > 0 else Language(scenario.language)
        response = await service.query(QueryRequest(query=text, language=language, session_id=session_id))
        session_id = response.session_id
        dialogue_opened = dialogue_opened or response.clarification is not None
        # Closed codes only: never persist arbitrary exception/provider text.
        # A recovered retry can still leave an error code, so keep the final
        # answer type alongside it rather than implying user-visible failure.
        for stage in ("interpreter", "selector", "formulator"):
            code = getattr(response.interaction, f"{stage}_error_code")
            if code:
                safe_codes = {f"{stage}_{suffix}" for suffix in (
                    "timeout", "http_error", "invalid_json", "schema_error",
                    "contract_violation", "invalid_id", "invalid_fact", "invalid_card",
                    "invalid_language", "ungrounded_claim", "unavailable", "budget_exhausted",
                )}
                # Ein erholter Wiederholungsversuch und ein endgueltiger
                # Rueckfall hinterlassen denselben Fehlercode. Unterschieden
                # werden sie allein ueber das Fallback-Flag der Stufe: bei
                # Erholung kehrt der Anwendungspfad frueh mit der regulaeren
                # Antwort zurueck und laesst das Flag unberuehrt. Der
                # Interpreter kennt keinen Wiederholungsversuch und faellt
                # fail-closed aus, gilt also nie als erholt.
                fallback_used = bool(
                    getattr(response.interaction, f"{stage}_fallback_used", True)
                )
                stage_errors.append({
                    "turn": turn_index + 1,
                    "stage": stage,
                    "error_code": code if code in safe_codes else "unclassified_stage_error",
                    "response_type": response.answer_type,
                    "fallback_used": fallback_used,
                    # Erholt heisst: die Stufe ist nicht zurueckgefallen UND die
                    # ausgelieferte Antwort stammt nicht aus der Vorlage.
                    "recovered": not fallback_used and response.provider != "template",
                    "answer_provider": response.provider,
                })
                if stage == "interpreter" and code == "interpreter_schema_error":
                    issues = getattr(evaluation_provider, "interpreter_schema_issues", ())
                    stage_errors[-1]["schema_issues"] = schema_issue_records(issues)
        answers.append({"turn": turn_index + 1, "text": response.answer})
        for attempt, rejection in enumerate(rejection_buffer, start=1):
            formulator_rejections.append({"turn": turn_index + 1, "attempt": attempt, **rejection})
        rejection_buffer.clear()
        reference_assessments.extend({"turn": turn_index + 1, **item} for item in reference_buffer)
        reference_buffer.clear()
        technically_valid = technically_valid and not bool(
            response.interaction.interpreter_error_code
            or response.interaction.selector_error_code
            or response.interaction.formulator_error_code
        )
    assert response is not None
    metrics, mismatches, critical, unverified = _evaluate_e2e(
        scenario, response, dialogue_opened_during_flow=dialogue_opened
    )
    # Momentaufnahme nach Abschluss des Ablaufs, keine Zuordnung zu einem einzelnen Turn:
    # QueryService.query() kann Interpreter, Selector und Formulator innerhalb eines Turns
    # bündeln, daher nur je Stufe der zuletzt bestätigte Wert.
    provider = getattr(service, "blablador", None)
    return {
        "scenario_id": scenario.scenario_id,
        "component": "end_to_end",
        "language": scenario.language,
        "turns": len(scenario.synthetic_inputs),
        "response_type": response.answer_type,
        "metrics": metrics,
        "content_mismatches": mismatches,
        "unverified_metrics": unverified,
        "critical_content_error": critical,
        "answers": answers,
        "formulator_rejections": formulator_rejections,
        "technically_valid": technically_valid,
        "stage_errors": stage_errors,
        "reference_assessments": reference_assessments,
        "linguistic_review_pending": True,
        "duration_ms": round((clock() - started) * 1_000, 2),
        "last_confirmed_model_identifiers": {
            "interpreter": _confirmed_model(provider, "interpreter"),
            "selector": _confirmed_model(provider, "selector"),
            "formulator": _confirmed_model(provider, "formulator"),
        },
    }


# Die Stufendokumentation nennt fuer End-to-End vier und fuer die
# Stabilitaetsstufe drei *kritische* Fehler als Abbruchgrenze. Die allgemeine
# Fehlergrenze teilte sich diesen Zaehler bisher mit gewoehnlichen fachlichen
# Verwerfungen, sodass ein sicherheitsrelevanter Befund und eine routinemaessige
# Ablehnung dasselbe Budget verbrauchten. Beide werden jetzt getrennt gestoppt.
CRITICAL_CONTENT_ERROR_ABORT_LIMITS = {
    EvaluationStage.END_TO_END: 4,
    EvaluationStage.STABILITY: 3,
}


async def _build_isolated_service(
    settings: Settings,
    scratch_dir: Path,
    provider_factory: Callable[[Settings], Any],
    counter: AtomicRunCounter,
) -> tuple[QueryService, Any]:
    """Konstruiert einen QueryService mit isolierter Runtime-Wurzel für die Evaluation.

    Die Evaluation nutzt bewusst keinen dauerhaften Anwendungs-Sessionspeicher
    (siehe ``docs/live-provider-evaluation.md``); Sessions dieses Laufs landen
    ausschließlich in einem temporären Verzeichnis, das mit dem Lauf endet.
    """
    isolated_settings = dataclasses.replace(settings, runtime_dir=scratch_dir)
    kb = load_active_knowledge_base(isolated_settings)
    service = QueryService(isolated_settings, kb)
    provider = LimitedEvaluationProvider(provider_factory(settings), counter)
    service.blablador = provider
    return service, provider


async def run_end_to_end_live_gate(
    settings: Settings,
    limits: LiveRunLimits,
    *,
    provider_factory: Callable[[Settings], Any] = BlabladorProvider,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Führt Stufe 3 aus: 27 End-to-End-Abläufe über den echten Anfragepfad."""

    if not settings.blablador_configured:
        raise RuntimeError("live_evaluation_provider_not_configured")
    catalog = load_live_scenario_catalog()
    plan = catalog.plan(EvaluationStage.END_TO_END)
    if limits != plan.live_limits:
        raise RuntimeError("live_evaluation_limits_not_bound_to_catalog")
    git_state = collect_git_state()
    kb = load_active_knowledge_base(settings)
    run_id = new_run_id()
    store = EvaluationReportStore(settings.runtime_dir, run_id)
    manifest = build_run_manifest(
        run_id=run_id, stage=EvaluationStage.END_TO_END, settings=settings, kb=kb, limits=limits,
        git_state=git_state,
    )
    store.initialize(manifest)
    counter = AtomicRunCounter(limits, clock=clock)
    expected_identity = _expected_identity(settings)
    status = "completed"
    abort_reason: str | None = None
    content_mismatches = 0
    critical_content_errors = 0
    unverified_metric_count = 0
    current_scenario_id = "run"

    with tempfile.TemporaryDirectory(prefix="lena-live-eval-e2e-") as scratch:
        try:
            service, provider = await _build_isolated_service(settings, Path(scratch), provider_factory, counter)
            if _provider_identity(provider) != expected_identity:
                raise EvaluationLimitReached("live_evaluation_provider_identity_mismatch")
            for scenario in catalog.scenarios_for(EvaluationStage.END_TO_END):
                current_scenario_id = scenario.scenario_id
                if _provider_identity(provider) != expected_identity:
                    raise EvaluationLimitReached("live_evaluation_provider_identity_changed")
                result = await _run_e2e_scenario(scenario, service, counter, clock)
                content_mismatches += bool(result["content_mismatches"])
                critical_content_errors += int(result["critical_content_error"])
                unverified_metric_count += len(result["unverified_metrics"])
                store.append_result(result)
                if critical_content_errors >= CRITICAL_CONTENT_ERROR_ABORT_LIMITS[
                    EvaluationStage.END_TO_END
                ]:
                    raise EvaluationLimitReached("live_evaluation_critical_error_limit")
                if result["critical_content_error"] or not result["technically_valid"]:
                    counter.record_failure()
        except EvaluationLimitReached as exc:
            status = "aborted"
            abort_reason = exc.code
            store.append_error(scenario_id=current_scenario_id, code=exc.code)
        except EvaluationReportWriteError as exc:
            status = "aborted"
            abort_reason = exc.code
            store.append_error(scenario_id=current_scenario_id, code=exc.code, report_write_error=exc)
        except Exception:
            status = "aborted"
            abort_reason = "live_evaluation_unexpected_runtime_error"
            store.append_error(scenario_id=current_scenario_id, code=abort_reason)

    counts = counter.snapshot()
    contract_gate_passed = status == "completed" and counts["failures"] == 0
    summary = {
        "run_id": run_id,
        "stage": EvaluationStage.END_TO_END.value,
        "status": status,
        "completed_at": datetime.now(UTC).isoformat(),
        "abort_reason": abort_reason,
        "contract_gate_passed": contract_gate_passed,
        "content_gate_passed": contract_gate_passed and content_mismatches == 0,
        "content_mismatch_count": content_mismatches,
        "unverified_metric_count": unverified_metric_count,
        "content_evaluation_complete": status == "completed" and unverified_metric_count == 0,
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


STABILITY_SCENARIO_IDS: tuple[str, ...] = (
    "e_food_time", "e_sleep_minor", "e_toilet", "e_water", "e_acute_uncertain", "e_prompt_injection",
)
STABILITY_REPETITIONS = 3


async def run_stability_live_gate(
    settings: Settings,
    limits: LiveRunLimits,
    *,
    provider_factory: Callable[[Settings], Any] = BlabladorProvider,
    clock: Callable[[], float] = monotonic,
) -> dict[str, Any]:
    """Führt Stufe 4 aus: sechs Abläufe je dreifach mit dem ersten Turn wiederholt."""

    if not settings.blablador_configured:
        raise RuntimeError("live_evaluation_provider_not_configured")
    catalog = load_live_scenario_catalog()
    plan = catalog.plan(EvaluationStage.STABILITY)
    if limits != plan.live_limits:
        raise RuntimeError("live_evaluation_limits_not_bound_to_catalog")
    git_state = collect_git_state()
    kb = load_active_knowledge_base(settings)
    run_id = new_run_id()
    store = EvaluationReportStore(settings.runtime_dir, run_id)
    manifest = build_run_manifest(
        run_id=run_id, stage=EvaluationStage.STABILITY, settings=settings, kb=kb, limits=limits,
        git_state=git_state,
    )
    store.initialize(manifest)
    counter = AtomicRunCounter(limits, clock=clock)
    expected_identity = _expected_identity(settings)
    status = "completed"
    abort_reason: str | None = None
    content_mismatches = 0
    critical_content_errors = 0
    unverified_metric_count = 0
    current_scenario_id = "run"
    by_id = {scenario.scenario_id: scenario for scenario in catalog.scenarios_for(EvaluationStage.STABILITY)}
    observed_by_scenario: dict[str, list[str]] = {scenario_id: [] for scenario_id in STABILITY_SCENARIO_IDS}

    with tempfile.TemporaryDirectory(prefix="lena-live-eval-stability-") as scratch:
        try:
            service, provider = await _build_isolated_service(settings, Path(scratch), provider_factory, counter)
            if _provider_identity(provider) != expected_identity:
                raise EvaluationLimitReached("live_evaluation_provider_identity_mismatch")
            for scenario_id in STABILITY_SCENARIO_IDS:
                scenario = by_id[scenario_id]
                single_turn_scenario = scenario.model_copy(update={"synthetic_inputs": scenario.synthetic_inputs[:1]})
                for repetition in range(1, STABILITY_REPETITIONS + 1):
                    current_scenario_id = f"{scenario_id}#{repetition}"
                    if _provider_identity(provider) != expected_identity:
                        raise EvaluationLimitReached("live_evaluation_provider_identity_changed")
                    result = await _run_e2e_scenario(single_turn_scenario, service, counter, clock)
                    result["repetition"] = repetition
                    observed_by_scenario[scenario_id].append(result["response_type"])
                    content_mismatches += bool(result["content_mismatches"])
                    critical_content_errors += int(result["critical_content_error"])
                    unverified_metric_count += len(result["unverified_metrics"])
                    store.append_result(result)
                    if critical_content_errors >= CRITICAL_CONTENT_ERROR_ABORT_LIMITS[
                        EvaluationStage.STABILITY
                    ]:
                        raise EvaluationLimitReached("live_evaluation_critical_error_limit")
                    if result["critical_content_error"] or not result["technically_valid"]:
                        counter.record_failure()
        except EvaluationLimitReached as exc:
            status = "aborted"
            abort_reason = exc.code
            store.append_error(scenario_id=current_scenario_id, code=exc.code)
        except EvaluationReportWriteError as exc:
            status = "aborted"
            abort_reason = exc.code
            store.append_error(scenario_id=current_scenario_id, code=exc.code, report_write_error=exc)
        except Exception:
            status = "aborted"
            abort_reason = "live_evaluation_unexpected_runtime_error"
            store.append_error(scenario_id=current_scenario_id, code=abort_reason)

    stable_scenarios = {
        scenario_id: len(set(observed)) <= 1
        for scenario_id, observed in observed_by_scenario.items()
        if observed
    }
    counts = counter.snapshot()
    contract_gate_passed = status == "completed" and counts["failures"] == 0
    summary = {
        "run_id": run_id,
        "stage": EvaluationStage.STABILITY.value,
        "status": status,
        "completed_at": datetime.now(UTC).isoformat(),
        "abort_reason": abort_reason,
        "contract_gate_passed": contract_gate_passed,
        "content_gate_passed": contract_gate_passed and content_mismatches == 0,
        "content_mismatch_count": content_mismatches,
        "unverified_metric_count": unverified_metric_count,
        "content_evaluation_complete": status == "completed" and unverified_metric_count == 0,
        "critical_content_error_count": critical_content_errors,
        "counts": counts,
        "response_type_stable_per_scenario": stable_scenarios,
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
