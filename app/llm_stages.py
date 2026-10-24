"""Aufrufsteuerung der drei LLM-Stufen: Interpreter, Selector, Formulator.

Dieses Modul kapselt, *wie* ein Modell aufgerufen wird: gemeinsames
Zeitbudget, Retrypolitik, Fehlerklassifikation, Beobachtbarkeit und der
atomare Rückfall auf Templates. *Was* fachlich ausgewählt wird (Fachregeln,
Kandidaten, Dialoge) entscheidet die Orchestrierung in ``service.py``; *ob*
eine Formulierung belegt ist, entscheidet die Faktenprüfung (``grounding``),
die der Provider-Adapter vor jeder Rückgabe ausführt.

Alle Funktionen erhalten den Provider bei jedem Aufruf, statt ihn zu cachen:
Der Dienst kann ihn zur Laufzeit ersetzen (z. B. Tests oder Neuladen). Fehlt
er, liefern die Funktionen ``None`` bzw. ein Bypass-Ergebnis und die
Orchestrierung verwendet ihren deterministischen Pfad.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .candidate_contract import CandidateDecision
from .config import Settings
from .formulation import FormulatorError, FormulatorEvidence, GroundingDiagnosticCode
from .interpreter import QueryInterpretation
from .llm_budget import LLMBudgetExhausted, LLMRequestBudget
from .llm_selection import SelectionOutcome, SelectorError, bypass_outcome, fallback_outcome, selected_outcome
from .models import QueryInteraction
from .providers.llm import InterpreterError, ProviderAnswer


LOGGER = logging.getLogger("app.service")

# Ein ``FormulatorError`` (Vertragsverstoß, unbelegte Aussage, ...) ist meist
# eine einzelne Stichprobenschwäche des Modells, kein Strukturfehler. Ein
# Retry mit neuer Stichprobe behebt einen relevanten Anteil, ohne die
# Belegpflicht zu lockern. 2 = ursprünglicher Versuch plus ein Retry.
FORMULATOR_MAX_ATTEMPTS = 2

# Transportfehler, keine Stichprobenschwäche: ein Retry verbraucht nur das
# gemeinsame Budget, das eine andere Stufe noch benötigen kann.
_FORMULATOR_NON_RETRYABLE_ERRORS = frozenset({"formulator_timeout", "formulator_http_error"})


def _diagnostic(exc: FormulatorError) -> str | None:
    """Geschlossene Groundingdiagnose für das technische Log, nie Modelltext."""
    return exc.diagnostic_code.value if exc.diagnostic_code is not None else None


async def run_interpreter(
    provider: Any,
    settings: Settings,
    budget: LLMRequestBudget,
    interaction: QueryInteraction,
    **request: Any,
) -> QueryInterpretation | None:
    """Liefert die validierte Interpretation oder ``None`` (technischer Rückfall)."""
    if not provider:
        return None
    try:
        allocation = budget.begin(settings.llm_interpreter_timeout_seconds)
        try:
            interpretation = await provider.interpret_query(timeout_seconds=allocation.timeout_seconds, **request)
        finally:
            budget.finish(allocation)
    except LLMBudgetExhausted:
        interaction.fallback_used = True
        interaction.interpreter_error_code = "llm_budget_exhausted"
        interaction.llm_budget_status = "llm_budget_exhausted"
        LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "interpreter"})
        return None
    except InterpreterError as exc:
        interaction.fallback_used = True
        interaction.interpreter_error_code = exc.code
        if budget.exhausted:
            interaction.llm_budget_status = "llm_budget_exhausted"
        LOGGER.warning("query.interpreter.failed", extra={"error_code": exc.code})
        LOGGER.info("query.fallback.used", extra={"stage": "interpreter"})
        return None
    LOGGER.info("query.interpreter.completed", extra={"contract_version": interpretation.contract_version})
    return interpretation


async def run_selector(
    provider: Any,
    settings: Settings,
    budget: LLMRequestBudget,
    interaction: QueryInteraction,
    decision: CandidateDecision,
    **request: Any,
) -> tuple[SelectionOutcome, bool]:
    """Wählt aus der deterministisch begrenzten Kandidatenmenge.

    Returns:
        Das Auswahlergebnis und ob der Provider dabei ausgefallen ist; in dem
        Fall wird die nachfolgende Formulierung übersprungen.
    """
    selector_method = getattr(provider, "select_candidates", None) if provider else None
    selection = bypass_outcome(decision, selector_available=callable(selector_method), interpreter_succeeded=True)
    if selection is not None:
        return selection, False
    try:
        allocation = budget.begin(settings.llm_selector_timeout_seconds)
        try:
            result = await selector_method(decision=decision, timeout_seconds=allocation.timeout_seconds, **request)
        finally:
            budget.finish(allocation)
    except LLMBudgetExhausted:
        interaction.llm_budget_status = "llm_budget_exhausted"
        LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "selector"})
        return fallback_outcome(decision, SelectorError("llm_budget_exhausted")), True
    except SelectorError as exc:
        if budget.exhausted:
            interaction.llm_budget_status = "llm_budget_exhausted"
        LOGGER.warning("query.selector.failed", extra={"error_code": exc.code})
        return fallback_outcome(decision, exc), True
    selection = selected_outcome(decision, result)
    LOGGER.info("query.selector.completed", extra={"selected_count": len(selection.final_ids)})
    return selection, False


async def call_formulator_with_retry(
    formulator_method: Callable[..., Any],
    settings: Settings,
    budget: LLMRequestBudget,
    interaction: QueryInteraction,
    evidence: FormulatorEvidence,
) -> ProviderAnswer:
    """Wiederholt höchstens einmal nach einem Grounding-/Parsingfehler.

    Der Retry erhält nur die geschlossene Groundingdiagnose als Hinweis, nie
    den verworfenen Text. ``LLMBudgetExhausted`` erreicht den Aufrufer direkt.
    """
    retry_feedback: dict[str, GroundingDiagnosticCode] = {}
    for attempt in range(FORMULATOR_MAX_ATTEMPTS):
        allocation = budget.begin(settings.llm_formulator_timeout_seconds)
        interaction.formulator_used = True
        try:
            return await formulator_method(
                evidence=evidence, timeout_seconds=allocation.timeout_seconds, **retry_feedback,
            )
        except FormulatorError as exc:
            interaction.formulator_error_code = exc.code
            retryable = exc.code not in _FORMULATOR_NON_RETRYABLE_ERRORS
            if not (retryable and attempt + 1 < FORMULATOR_MAX_ATTEMPTS):
                raise
            if exc.diagnostic_code is not None:
                retry_feedback = {"retry_diagnostic": exc.diagnostic_code}
            LOGGER.warning(
                "query.formulation.retry",
                extra={"error_code": exc.code, "attempt": attempt + 1, "diagnostic_code": _diagnostic(exc)},
            )
        finally:
            budget.finish(allocation)
    raise AssertionError("unreachable: the loop above always returns or raises")


async def run_formulator(
    provider: Any,
    settings: Settings,
    budget: LLMRequestBudget,
    interaction: QueryInteraction,
    *,
    build_evidence: Callable[[], FormulatorEvidence],
    provider_failed: bool = False,
) -> ProviderAnswer | None:
    """Formuliert genau ein Evidence-Paket oder signalisiert den Template-Rückfall.

    Einheitlich für soziale Angebote, Toiletten und Trinkwasser: Ein nicht
    baubares Evidence-Paket, ein zu großer Kontext, ein Budget-, Transport-
    oder Groundingfehler führen atomar zu ``None``; der Aufrufer liefert dann
    sein kuratiertes Template. Es gibt keine Teilübernahme einer Modellantwort.
    """
    try:
        evidence = build_evidence()
    except (KeyError, ValueError):
        interaction.formulator_error_code = "formulator_contract_violation"
        interaction.formulator_fallback_used = True
        interaction.fallback_used = True
        LOGGER.warning("query.formulation.failed", extra={"error_code": "formulator_contract_violation"})
        return None
    formulator_method = getattr(provider, "formulate_answer", None) if provider else None
    if callable(formulator_method) and not provider_failed:
        try:
            if not provider.context_fits(evidence):
                raise FormulatorError("formulator_contract_violation")
            result = await call_formulator_with_retry(formulator_method, settings, budget, interaction, evidence)
            interaction.formulator_sentence_count = result.sentence_count
            return result
        except LLMBudgetExhausted:
            interaction.llm_budget_status = "llm_budget_exhausted"
            interaction.formulator_error_code = "formulator_skipped_budget"
            LOGGER.warning("query.llm_budget.exhausted", extra={"stage": "formulator"})
        except FormulatorError as exc:
            interaction.formulator_error_code = exc.code
            if budget.exhausted:
                interaction.llm_budget_status = "llm_budget_exhausted"
            LOGGER.warning(
                "query.formulation.failed", extra={"error_code": exc.code, "diagnostic_code": _diagnostic(exc)},
            )
    elif provider_failed:
        interaction.formulator_error_code = "formulator_skipped_provider"
    interaction.formulator_fallback_used = bool(provider or provider_failed)
    interaction.fallback_used = interaction.fallback_used or interaction.formulator_fallback_used
    return None
