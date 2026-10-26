"""Blablador-Client fuer Interpretation und geerdete Antwortformulierung."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from ..candidate_contract import CandidateDecision
from ..config import Settings
from ..formulation import (
    MAX_FORMULATOR_RESPONSE_CHARS,
    AnswerType,
    FormulatorError,
    FormulatorEvidence,
    GroundingDiagnosticCode,
    formulator_retry_instruction,
)
from ..grounding import validate_formulation
from ..formulator_prose import GroundedFormulatorResponse, formulator_response_prompt, prose_evidence_payload
from ..interpreter import (
    INTERPRETER_CONTRACT_VERSION,
    INTERPRETER_PROMPT_VERSION,
    INTERPRETER_SYSTEM_PROMPT,
    INTERNAL_ID_RE,
    MAX_INTERPRETER_INPUT_CHARS,
    MAX_INTERPRETER_RESPONSE_CHARS,
    InterpreterAliasHint,
    InterpreterDialogContext,
    InterpreterUserPayload,
    QueryInterpretation,
    interpreter_session_context,
    need_hint_from_category,
    validate_no_internal_ids,
)
from ..llm_selection import (
    MAX_SELECTOR_RESPONSE_CHARS,
    SELECTOR_SYSTEM_PROMPT,
    CandidateSelectionResponse,
    SelectorError,
    selector_payload,
)
from ..models import (
    Category,
    ChatTurn,
    Language,
    OfferRecord,
)
from .diagnostics import (
    HTTP_STATUS_FAILURE_KINDS,
    ProviderFailureKind,
    SchemaValidationIssue,
    classify_provider_failure,
    interpreter_schema_issues,
    schema_issue_records,
)

LOGGER = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    """Kennzeichnet einen sicher auf Templates zurückfallenden Providerfehler."""
    pass


class ProviderTimeoutError(ProviderError):
    """Kennzeichnet eine abgelaufene Gesamtgrenze eines LLM-Schritts."""


class InterpreterError(ProviderError):
    """Redigierbarer, maschinenlesbarer Fehler der Interpretationsstufe."""

    def __init__(
        self,
        code: str,
        *,
        provider_failure_kind: ProviderFailureKind | None = None,
        upstream_status: int | None = None,
        schema_issues: tuple[SchemaValidationIssue, ...] = (),
    ) -> None:
        schema_issue_records(schema_issues)
        if schema_issues and code != "interpreter_schema_error":
            raise ValueError("schema diagnostics require an interpreter schema error")
        if upstream_status is not None and (
            type(upstream_status) is not int or not 100 <= upstream_status <= 599
        ):
            raise ValueError("upstream_status must be a valid HTTP status")
        if upstream_status is not None and provider_failure_kind not in HTTP_STATUS_FAILURE_KINDS:
            raise ValueError("upstream_status requires an HTTP failure kind")
        if provider_failure_kind in HTTP_STATUS_FAILURE_KINDS and upstream_status is None:
            raise ValueError("HTTP failure kind requires upstream_status")
        super().__init__(code)
        self.code = code
        self.provider_failure_kind = provider_failure_kind
        self.upstream_status = upstream_status
        self.schema_issues = schema_issues


def _interpreter_http_error(exc: BaseException) -> InterpreterError:
    failure_kind, upstream_status = classify_provider_failure(exc)
    return InterpreterError(
        "interpreter_http_error",
        provider_failure_kind=failure_kind,
        upstream_status=upstream_status,
    )


@dataclass(frozen=True)
class ProviderAnswer:
    answer: str
    card_ids: list[str]
    sentence_count: int = 1
    answer_type: AnswerType = AnswerType.GROUNDED_RESULT
    reference_assessment: dict[str, object] | None = None


def _strict_interpreter_content(response: dict[str, Any]) -> str:
    """Liest die Modellantwort ohne tolerante Markdown-Nachbearbeitung."""
    raw_content = response["choices"][0]["message"]["content"]
    if not isinstance(raw_content, str):
        raise TypeError("interpreter response contains no JSON text")
    content = raw_content.strip()
    if not content or len(content) > MAX_INTERPRETER_RESPONSE_CHARS:
        raise ValueError("interpreter response size is invalid")
    return content


def _strict_selector_content(response: dict[str, Any]) -> str:
    """Liest ausschließlich kurzen reinen JSON-Text der Auswahlstufe."""
    raw_content = response["choices"][0]["message"]["content"]
    if not isinstance(raw_content, str):
        raise TypeError("selector response contains no JSON text")
    content = raw_content.strip()
    if len(content) > MAX_SELECTOR_RESPONSE_CHARS:
        raise SelectorError("selector_contract_violation")
    if not content:
        raise ValueError("selector response is empty")
    return content


def _strict_formulator_content(response: dict[str, Any]) -> str:
    """Akzeptiert ausschließlich begrenzten reinen JSON-Text."""
    raw_content = response["choices"][0]["message"]["content"]
    if not isinstance(raw_content, str):
        raise TypeError("formulator response contains no JSON text")
    content = raw_content.strip()
    if not content:
        raise ValueError("formulator response is empty")
    if len(content) > MAX_FORMULATOR_RESPONSE_CHARS:
        raise FormulatorError("formulator_contract_violation")
    return content


class BlabladorProvider:
    """Implementiert drei getrennte Verträge auf einem gemeinsamen Transport."""
    name = "blablador"

    def __init__(self, settings: Settings) -> None:
        if not settings.blablador_configured:
            raise ProviderError("Blablador is not configured")
        self.base_url = settings.blablador_base_url or ""
        self.api_key = settings.blablador_api_key or ""
        self.model = settings.blablador_model or ""
        self.interpreter_model = settings.effective_interpreter_model or ""
        self.selector_model = settings.effective_selector_model or ""
        self.formulator_model = settings.effective_formulator_model or ""
        # Vom Provider je Stufe zuletzt zurückgemeldete Modellkennung (Antwortfeld
        # "model"), nicht die gesendete Alias-Anfrage. None, solange die Stufe in
        # dieser Providerinstanz noch keine erfolgreiche Antwort hatte.
        self.last_confirmed_models: dict[str, str | None] = {
            "interpreter": None,
            "selector": None,
            "formulator": None,
        }
        self.timeout = settings.blablador_timeout_seconds
        self.interpreter_timeout = settings.llm_interpreter_timeout_seconds
        self.selector_timeout = settings.llm_selector_timeout_seconds
        self.formulator_timeout = settings.llm_formulator_timeout_seconds
        self.max_context_chars = settings.blablador_max_context_chars
        self.max_tokens = settings.blablador_max_tokens

    def context_fits(self, evidence: FormulatorEvidence) -> bool:
        payload = json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        return len(payload) <= self.max_context_chars

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _request_with_timeout(
        self,
        payload: dict[str, Any],
        *,
        timeout_seconds: float,
        stage: str,
    ) -> dict[str, Any]:
        """Begrenzt einen asynchronen Provideraufruf auf eine Gesamtdauer."""
        try:
            async with asyncio.timeout(timeout_seconds):
                response = await self._post(payload)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError(f"Blablador {stage} timed out") from exc
        if not isinstance(response, dict):
            raise ValueError("LLM response must be a JSON object")
        confirmed_model = response.get("model")
        if isinstance(confirmed_model, str) and confirmed_model.strip():
            self.last_confirmed_models[stage] = confirmed_model.strip()
        return response

    async def interpret_query(
        self,
        *,
        query: str,
        language: Language,
        category: Category | None,
        aliases: list[InterpreterAliasHint],
        conversation_history: list[ChatTurn] | None = None,
        dialog_context: InterpreterDialogContext | None = None,
        timeout_seconds: float | None = None,
    ) -> QueryInterpretation:
        """Interpretiert Bedarf und explizite Fakten, ohne Angebote zu sehen."""
        if len(query) > MAX_INTERPRETER_INPUT_CHARS:
            raise InterpreterError("interpreter_contract_violation")
        user_contract = InterpreterUserPayload(
            contract_version=INTERPRETER_CONTRACT_VERSION,
            prompt_version=INTERPRETER_PROMPT_VERSION,
            requested_interface_language=language,
            selected_need_hint=need_hint_from_category(category),
            current_query=query,
            recent_user_messages=interpreter_session_context(conversation_history),
            known_aliases=aliases,
            open_dialog=dialog_context,
        )
        payload = {
            "model": self.interpreter_model,
            "temperature": 0,
            "max_tokens": min(self.max_tokens, 4096),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": INTERPRETER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(user_contract.model_dump(mode="json"), ensure_ascii=False),
                },
            ],
        }
        try:
            response = await self._request_with_timeout(
                payload,
                timeout_seconds=min(self.interpreter_timeout, timeout_seconds or self.interpreter_timeout),
                stage="interpreter",
            )
        except ProviderTimeoutError as exc:
            raise InterpreterError("interpreter_timeout") from exc
        except InterpreterError:
            raise
        except (httpx.HTTPError, ProviderError) as exc:
            raise _interpreter_http_error(exc) from exc
        except (TypeError, ValueError) as exc:
            raise InterpreterError("interpreter_invalid_json") from exc

        try:
            content = _strict_interpreter_content(response)
            raw = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InterpreterError("interpreter_invalid_json") from exc
        if not isinstance(raw, dict):
            raise InterpreterError("interpreter_schema_error")
        if INTERNAL_ID_RE.search(json.dumps(raw, ensure_ascii=False)):
            raise InterpreterError("interpreter_contract_violation")
        try:
            parsed = QueryInterpretation.model_validate(raw)
        except ValidationError as exc:
            issues = interpreter_schema_issues(exc)
            LOGGER.warning(
                "query.interpreter.schema_invalid",
                extra={"error_code": "interpreter_schema_error", "schema_issues": schema_issue_records(issues)},
            )
            raise InterpreterError("interpreter_schema_error", schema_issues=issues) from exc
        try:
            validate_no_internal_ids(parsed)
        except ValueError as exc:
            raise InterpreterError("interpreter_contract_violation") from exc
        return parsed

    async def select_candidates(
        self,
        *,
        query: str,
        language: Language,
        interpretation: QueryInterpretation,
        decision: CandidateDecision,
        offers: list[OfferRecord],
        timeout_seconds: float | None = None,
    ) -> CandidateSelectionResponse:
        """Wählt ausschließlich IDs aus dem kompakten auswählbaren Index."""
        try:
            user_contract = selector_payload(query, language, interpretation, decision, offers)
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise SelectorError("selector_contract_violation") from exc
        allowed = {candidate.id for candidate in user_contract.candidates}
        payload = {
            "model": self.selector_model,
            "temperature": 0,
            "max_tokens": min(self.max_tokens, 4096),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SELECTOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(user_contract.model_dump(mode="json"), ensure_ascii=False),
                },
            ],
        }
        try:
            response = await self._request_with_timeout(
                payload,
                timeout_seconds=min(self.selector_timeout, timeout_seconds or self.selector_timeout),
                stage="selector",
            )
        except ProviderTimeoutError as exc:
            raise SelectorError("selector_timeout") from exc
        except httpx.HTTPError as exc:
            raise SelectorError("selector_http_error") from exc
        except (TypeError, ValueError, ProviderError) as exc:
            raise SelectorError("selector_http_error") from exc
        try:
            content = _strict_selector_content(response)
            raw = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SelectorError("selector_invalid_json") from exc
        if not isinstance(raw, dict):
            raise SelectorError("selector_schema_error")
        try:
            result = CandidateSelectionResponse.model_validate(raw)
        except ValidationError as exc:
            raise SelectorError("selector_schema_error") from exc
        if len(result.selected_ids) > user_contract.maximum_selected_ids:
            raise SelectorError("selector_contract_violation")
        if any(offer_id not in allowed for offer_id in result.selected_ids):
            raise SelectorError("selector_invalid_id")
        return result

    async def formulate_answer(
        self,
        *,
        evidence: FormulatorEvidence,
        timeout_seconds: float | None = None,
        retry_diagnostic: GroundingDiagnosticCode | None = None,
    ) -> ProviderAnswer:
        """Formuliert und validiert eine vollständige Evidence-Antwort atomar.

        Raises:
            FormulatorError: Mit redigiertem stufenspezifischem Fehlercode.
        """
        context = json.dumps(prose_evidence_payload(evidence), ensure_ascii=False, separators=(",", ":"))
        if len(context) > self.max_context_chars:
            raise FormulatorError("formulator_contract_violation")
        # Only trusted closed feedback is added, never the rejected model response.
        system_prompt = formulator_response_prompt()
        if retry_diagnostic is not None:
            system_prompt += "\n" + formulator_retry_instruction(retry_diagnostic)
        payload = {
            "model": self.formulator_model,
            "temperature": 0,
            "max_tokens": min(self.max_tokens, 4096),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
        }
        try:
            response = await self._request_with_timeout(
                payload,
                timeout_seconds=min(self.formulator_timeout, timeout_seconds or self.formulator_timeout),
                stage="formulator",
            )
        except ProviderTimeoutError as exc:
            raise FormulatorError("formulator_timeout") from exc
        except httpx.HTTPError as exc:
            raise FormulatorError("formulator_http_error") from exc
        except (ProviderError, TypeError, ValueError) as exc:
            raise FormulatorError("formulator_http_error") from exc
        try:
            content = _strict_formulator_content(response)
            raw = json.loads(content)
        except FormulatorError:
            raise
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise FormulatorError("formulator_invalid_json") from exc
        if not isinstance(raw, dict):
            raise FormulatorError("formulator_schema_error")
        try:
            parsed = GroundedFormulatorResponse.model_validate(raw)
        except ValidationError as exc:
            raise FormulatorError("formulator_schema_error") from exc
        try:
            validated = validate_formulation(parsed, evidence)
        except FormulatorError as exc:
            # Keep the strict parsed response in memory for the synthetic live
            # evaluation. Normal application logging and API errors continue to
            # expose only the redacted error and optional closed diagnostic code.
            exc.rejected_response = parsed
            raise
        return ProviderAnswer(
            answer=validated.answer,
            card_ids=validated.card_ids,
            sentence_count=validated.sentence_count,
            answer_type=validated.answer_type,
            reference_assessment=validated.reference_assessment,
        )
