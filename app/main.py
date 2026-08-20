"""FastAPI-Einstiegspunkt und HTTP-Adapter der LENA-Anwendung."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .candidate_contract import CANDIDATE_CONTRACT_VERSION
from .application_texts import (
    APPLICATION_COPY_VERSION,
    application_text,
    application_text_summary,
    load_application_texts,
    public_application_copy,
)
from .config import Settings, load_settings
from .i18n import translation_summary
from .interpreter import INTERPRETER_CONTRACT_VERSION, INTERPRETER_PROMPT_VERSION
from .llm_selection import SELECTOR_CONTRACT_VERSION, SELECTOR_PROMPT_VERSION
from .formulation import (
    EVIDENCE_CONTRACT_VERSION,
    FORMULATOR_CONTRACT_VERSION,
    FORMULATOR_PROMPT_VERSION,
)
from .dialogue import (
    DIALOG_CONTRACT_VERSION,
    DialogRequestError,
    public_dialogue_copy,
)
from .interactions import InteractionRecord, InteractionWriter
from .safety import (
    SAFETY_POLICY_VERSION,
    SAFETY_PREFLIGHT_VERSION,
    SUPPORTED_SAFETY_LANGUAGES,
    SafetyTextKind,
    safety_text,
)
from .kb_loader import KnowledgeBase, KnowledgeBaseError, load_active_knowledge_base
from .models import Language, QueryRequest, QueryResponse, SpeechSynthesisRequest
from .translation_contract import TranslationRuntimePolicy
from .service import QueryService
from .speech import (
    SpeechSynthesizer,
    SpeechSynthesisError,
    SpeechSynthesisTimeoutError,
    SpeechTranscriber,
    SpeechTranscriptionAudioError,
    SpeechTranscriptionAudioTooLongError,
    SpeechTranscriptionError,
    SpeechTranscriptionTimeoutError,
)
from .wfs_sync import load_wfs_state, sync_wfs
from .toilet_sync import fetch_toilets, load_toilet_state
from .drinking_fountain_sync import fetch_drinking_fountains, load_drinking_fountain_state
from .resources import static_root as package_static_root
from .version import software_version


SUPPORTED_AUDIO_MEDIA_TYPES = {
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-wav",
}
LOGGER = logging.getLogger(__name__)


async def _read_limited_body(request: Request, maximum_bytes: int) -> bytes:
    """Liest einen Request-Body, ohne die konfigurierte Speichergrenze zu umgehen.

    Die Prüfung des Headers ermöglicht eine frühe Ablehnung. Das zusätzliche
    Zählen der tatsächlich empfangenen Chunks schützt auch Requests ohne
    vertrauenswürdigen ``Content-Length``-Header.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        if declared_length < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
        if declared_length > maximum_bytes:
            raise HTTPException(status_code=413, detail="Request body too large")

    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > maximum_bytes:
            raise HTTPException(status_code=413, detail="Request body too large")
        chunks.append(chunk)
    return b"".join(chunks)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Erzeugt die Anwendung und verdrahtet Daten, Provider und Routen.

    Args:
        settings: Optionale explizite Konfiguration, insbesondere für Tests.

    Returns:
        Eine vollständig konfigurierte FastAPI-Instanz.

    Side Effects:
        Lädt die kanonische Wissensbasis und startet bei aktivierter automatischer
        Synchronisation während des Lifecycles einen WFS-Hintergrundtask.
    """
    settings = settings or load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.technical_log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    kb: KnowledgeBase | None = None
    kb_error = False
    kb_error_code: str | None = None
    kb_error_source_status: str | None = None
    try:
        kb = load_active_knowledge_base(settings)
    except KnowledgeBaseError as exc:
        kb_error = True
        kb_error_code = exc.code
        kb_error_source_status = exc.source_status

    service = QueryService(settings, kb) if kb else None
    speech_transcriber = SpeechTranscriber(settings)
    speech_synthesizer = SpeechSynthesizer(settings)
    interaction_writer = InteractionWriter(
        settings.interaction_log_path
        or (settings.runtime_dir or settings.app_root / "runtime") / "logs" / "interactions.jsonl",
        enabled=settings.interaction_logging_enabled,
    )

    async def wfs_loop(app: FastAPI) -> None:
        while True:
            try:
                result = await sync_wfs(settings, promote=settings.wfs_auto_promote)
                LOGGER.info(
                    "wfs.sync.completed",
                    extra={"changed": result.changed, "promoted": result.promoted},
                )
                app.state.last_wfs_check = {
                    "status": "ok",
                    "checked_at": result.checked_at,
                    "changed": result.changed,
                    "promoted": result.promoted,
                }
                if result.promoted:
                    refreshed = load_active_knowledge_base(settings)
                    app.state.kb = refreshed
                    app.state.service = QueryService(settings, refreshed)
                    app.state.kb_error = False
                    app.state.kb_error_code = None
                    app.state.kb_error_source_status = None
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                LOGGER.warning("wfs.sync.failed", extra={"error_type": type(exc).__name__})
                app.state.last_wfs_check = {"status": "error"}
            await asyncio.sleep(settings.wfs_check_interval_hours * 3600)

    async def toilet_loop(app: FastAPI) -> None:
        while True:
            try:
                result = await fetch_toilets(settings, stage=True)
                app.state.last_toilet_check = {
                    "status": result.status,
                    "changed": result.changed,
                    "record_count": result.record_count,
                }
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                LOGGER.warning("toilet.sync.failed", extra={"error_type": type(exc).__name__})
                app.state.last_toilet_check = {"status": "error"}
            await asyncio.sleep(settings.toilet_check_interval_seconds)

    async def drinking_fountain_loop(app: FastAPI) -> None:
        while True:
            try:
                result = await fetch_drinking_fountains(settings, stage=True)
                app.state.last_drinking_fountain_check = {
                    "status": result.status,
                    "changed": result.changed,
                    "record_count": result.record_count,
                }
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                LOGGER.warning("drinking_fountain.sync.failed", extra={"error_type": type(exc).__name__})
                app.state.last_drinking_fountain_check = {"status": "error"}
            await asyncio.sleep(settings.drinking_fountain_check_interval_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = []
        if settings.wfs_auto_sync:
            tasks.append(asyncio.create_task(wfs_loop(app)))
        if settings.toilet_auto_sync:
            tasks.append(asyncio.create_task(toilet_loop(app)))
        if settings.drinking_fountain_auto_sync:
            tasks.append(asyncio.create_task(drinking_fountain_loop(app)))
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="LENA", version=software_version(), lifespan=lifespan)
    app.state.settings = settings
    app.state.kb = kb
    app.state.kb_error = kb_error
    app.state.kb_error_code = kb_error_code
    app.state.kb_error_source_status = kb_error_source_status
    app.state.service = service
    app.state.speech_transcriber = speech_transcriber
    app.state.speech_synthesizer = speech_synthesizer
    app.state.interaction_writer = interaction_writer
    app.state.last_wfs_check = None
    app.state.last_toilet_check = None
    app.state.last_drinking_fountain_check = None

    @app.middleware("http")
    async def prevent_dev_cache(request, call_next):
        started_at = perf_counter()
        LOGGER.info("request.started", extra={"method": request.method, "path": request.url.path})
        try:
            response = await call_next(request)
        except Exception as exc:
            LOGGER.error(
                "request.failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    "error_type": type(exc).__name__,
                },
            )
            raise
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        LOGGER.info(
            "request.completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return response

    static_root = package_static_root()
    app.mount("/static", StaticFiles(directory=static_root), name="static")

    @app.get("/")
    async def frontend() -> FileResponse:
        return FileResponse(static_root / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        active_kb = app.state.kb
        active_service = app.state.service
        effective = active_service.effective_provider if active_service else "template"
        wfs_state = load_wfs_state(settings)
        toilet_state = load_toilet_state(settings)
        fountain_state = load_drinking_fountain_state(settings)
        toilet_metadata = active_kb.metadata.get("public_toilets", {}) if active_kb else {}
        fountain_metadata = active_kb.metadata.get("drinking_fountains", {}) if active_kb else {}
        official_offer_metadata = active_kb.metadata.get("official_offer_source", {}) if active_kb else {}
        return {
            "status": "ok" if active_kb else "error",
            "kb_loaded": active_kb is not None,
            "offer_count": len(active_kb.offers) if active_kb else 0,
            "source_kind": active_kb.source_kind if active_kb else None,
            "source_hash": active_kb.source_hash if active_kb else None,
            "data_release_id": active_kb.release_id if active_kb else None,
            "runtime_kb_fingerprint": (
                active_kb.runtime_kb_fingerprint if active_kb else None
            ),
            "runtime_kb_status": (
                active_kb.metadata.get("runtime_kb_status", "ok") if active_kb else "error"
            ),
            "source_status": (
                active_kb.metadata.get("source_status")
                if active_kb
                else app.state.kb_error_source_status
            ),
            "runtime_source": (
                active_kb.metadata.get("runtime_source") if active_kb else None
            ),
            "error_code": app.state.kb_error_code,
            "configured_provider": settings.rewrite_provider,
            "active_provider": effective,
            "llm_interpreter_available": active_service.interpreter_available if active_service else False,
            "llm_formulator_available": (
                active_service.formulator_context_available if active_service else False
            ),
            "llm_selector_available": active_service.selector_available if active_service else False,
            "interpreter_contract_version": INTERPRETER_CONTRACT_VERSION,
            "interpreter_prompt_version": INTERPRETER_PROMPT_VERSION,
            "selector_contract_version": SELECTOR_CONTRACT_VERSION,
            "selector_prompt_version": SELECTOR_PROMPT_VERSION,
            "formulator_contract_version": FORMULATOR_CONTRACT_VERSION,
            "formulator_prompt_version": FORMULATOR_PROMPT_VERSION,
            "evidence_contract_version": EVIDENCE_CONTRACT_VERSION,
            "llm_request_budget_seconds": settings.llm_request_budget_seconds,
            "candidate_contract_version": CANDIDATE_CONTRACT_VERSION,
            "dialog_contract_version": DIALOG_CONTRACT_VERSION,
            "safety_policy_version": SAFETY_POLICY_VERSION,
            "safety_preflight_version": SAFETY_PREFLIGHT_VERSION,
            "acute_risk_policy_status": "deterministic_after_validated_interpretation",
            "acute_risk_uncertain_policy": "structured_confirmation_dialog",
            "technical_fallback_includes_emergency_guidance": True,
            "safety_dialogue_contract_version": DIALOG_CONTRACT_VERSION,
            "safety_text_resource_version": APPLICATION_COPY_VERSION,
            "supported_safety_languages": list(SUPPORTED_SAFETY_LANGUAGES),
            "safety_translation_status_by_language": {
                language.value: load_application_texts().languages[language].linguistic_review_status.value
                for language in Language
            },
            "application_texts": application_text_summary(),
            "wfs": {
                "auto_sync": settings.wfs_auto_sync,
                "auto_promote": settings.wfs_auto_promote,
                "interval_hours": settings.wfs_check_interval_hours,
                "last_checked_at": wfs_state.get("last_checked_at"),
                "last_status": wfs_state.get("last_status"),
                "pending_changes": wfs_state.get("pending_changes", False),
                "source_response_timestamp": wfs_state.get("source_response_timestamp"),
                "background_check": app.state.last_wfs_check,
            },
            "public_toilets": {
                "runtime_status": toilet_metadata.get("runtime_status", "error"),
                "source_status": (
                    "change_pending"
                    if toilet_state.get("pending_changes")
                    else toilet_metadata.get("source_status", "release_error")
                ),
                "runtime_source": toilet_metadata.get("runtime_source"),
                "active_release_id": toilet_metadata.get("release_id"),
                "source_hash": toilet_metadata.get("source_hash"),
                "normalization_version": toilet_metadata.get("normalization_version"),
                "record_count": toilet_metadata.get("record_count", 0),
                "eligible_record_count": toilet_metadata.get("eligible_record_count", 0),
                "valid_geometry_count": toilet_metadata.get("valid_geometry_count", 0),
                "missing_geometry_count": toilet_metadata.get("missing_geometry_count", 0),
                "fee_free_count": toilet_metadata.get("fee_free_count", 0),
                "fee_paid_count": toilet_metadata.get("fee_paid_count", 0),
                "fee_unknown_count": toilet_metadata.get("fee_unknown_count", 0),
                "error_code": toilet_metadata.get("error_code"),
                "auto_sync": settings.toilet_auto_sync,
                "auto_promote": False,
                "interval_seconds": settings.toilet_check_interval_seconds,
                "last_checked_at": toilet_state.get("last_checked_at"),
                "last_status": toilet_state.get("last_status"),
                "pending_changes": toilet_state.get("pending_changes", False),
                "source_change_pending": toilet_state.get("pending_changes", False),
                "background_check": app.state.last_toilet_check,
            },
            "drinking_fountain_source_status": (
                "change_pending"
                if fountain_state.get("pending_changes")
                else fountain_metadata.get("source_status", "release_error")
            ),
            "drinking_fountain_runtime_status": fountain_metadata.get("runtime_status", "error"),
            "drinking_fountain_runtime_source": fountain_metadata.get("runtime_source"),
            "drinking_fountain_release_id": fountain_metadata.get("release_id"),
            "drinking_fountain_source_retrieved_at": fountain_metadata.get("source_retrieved_at"),
            "drinking_fountain_record_count": fountain_metadata.get("record_count", 0),
            "drinking_fountain_runtime_eligible_count": fountain_metadata.get("runtime_eligible_count", 0),
            "drinking_fountain_valid_geometry_count": fountain_metadata.get("valid_geometry_count", 0),
            "drinking_fountain_excluded_count": fountain_metadata.get("excluded_count", 0),
            "drinking_fountain_outside_leipzig_count": fountain_metadata.get("outside_leipzig_count", 0),
            "drinking_fountain_mobile_excluded_count": fountain_metadata.get("mobile_excluded_count", 0),
            "drinking_fountain_source_change_pending": fountain_state.get("pending_changes", False),
            "drinking_fountain_last_verified_release": fountain_metadata.get("last_verified_release"),
            "drinking_fountains": {
                **fountain_metadata,
                "auto_sync": settings.drinking_fountain_auto_sync,
                "auto_promote": False,
                "interval_seconds": settings.drinking_fountain_check_interval_seconds,
                "last_checked_at": fountain_state.get("last_checked_at"),
                "last_status": fountain_state.get("last_status"),
                "pending_changes": fountain_state.get("pending_changes", False),
                "background_check": app.state.last_drinking_fountain_check,
            },
            "curation": (active_kb.metadata.get("curation") if active_kb else None),
            "official_offer_source": {
                "source_version": official_offer_metadata.get("source_version"),
                "source_hash": official_offer_metadata.get("source_hash"),
                "record_count": official_offer_metadata.get("record_count", 0),
                "status": "verified" if official_offer_metadata else "unavailable",
            },
            "source_change_pending": (
                active_kb.metadata.get("source_change_pending", False) if active_kb else False
            ),
            "translations": (
                translation_summary(
                    active_service.translation_catalog,
                    active_kb,
                    TranslationRuntimePolicy(settings.translation_runtime_policy),
                )
                if active_kb and active_service
                else None
            ),
            "speech": {
                "server_transcription_available": speech_transcriber.configured,
                "transcription_model": settings.speech_transcription_model if speech_transcriber.configured else None,
                "server_synthesis_available": speech_synthesizer.configured,
                "synthesis_model": settings.speech_synthesis_model if speech_synthesizer.configured else None,
            },
            "license": (active_kb.metadata.get("license") if active_kb else None),
        }

    @app.get("/api/speech/config")
    async def speech_config() -> dict[str, object]:
        return {
            "server_transcription_available": app.state.speech_transcriber.configured,
            "server_synthesis_available": app.state.speech_synthesizer.configured,
            "synthesis_format": settings.speech_synthesis_response_format,
            "supported_languages": [language.value for language in Language],
        }

    @app.get("/api/dialogue/copy")
    async def dialogue_copy(language: Language = Query(default=Language.DE)) -> dict[str, object]:
        return public_dialogue_copy(language)

    @app.get("/api/i18n/copy")
    async def application_copy(language: Language = Query(default=Language.DE)) -> dict[str, object]:
        return public_application_copy(language)

    @app.post("/api/speech/transcribe")
    async def transcribe_speech(
        request: Request,
        language: Language = Query(default=Language.DE),
    ) -> dict[str, str]:
        content_type = request.headers.get("content-type", "audio/webm").split(";", 1)[0]
        content_type = content_type.strip().casefold() or "audio/webm"
        if content_type not in SUPPORTED_AUDIO_MEDIA_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported audio media type")
        audio = await _read_limited_body(request, settings.speech_transcription_max_bytes)
        if not audio:
            raise HTTPException(status_code=422, detail="Audio body must not be empty")
        started_at = perf_counter()
        try:
            text = await app.state.speech_transcriber.transcribe(
                audio,
                content_type=content_type,
                language=language,
            )
        except SpeechTranscriptionAudioError as exc:
            LOGGER.warning(
                "stt.audio_rejected",
                extra={
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    "error_code": exc.code,
                },
            )
            status_code = 413 if isinstance(exc, SpeechTranscriptionAudioTooLongError) else 422
            detail = "Audio duration too long" if status_code == 413 else "Audio could not be decoded"
            raise HTTPException(status_code=status_code, detail=detail) from exc
        except SpeechTranscriptionError as exc:
            event = "stt.timeout" if isinstance(exc, SpeechTranscriptionTimeoutError) else "stt.failed"
            log_context: dict[str, object] = {
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                "error_code": exc.code,
            }
            upstream_status = getattr(exc, "upstream_status", None)
            if upstream_status is not None:
                log_context["upstream_status"] = upstream_status
            LOGGER.warning(
                event,
                extra=log_context,
            )
            raise HTTPException(status_code=503, detail="Speech transcription failed") from exc
        LOGGER.info(
            "stt.completed",
            extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
        )
        return {"text": text}

    @app.post("/api/speech/synthesize")
    async def synthesize_speech(payload: SpeechSynthesisRequest) -> Response:
        if len(payload.text) > settings.speech_synthesis_max_chars:
            raise HTTPException(status_code=422, detail="Speech synthesis text too long")
        active_service = app.state.service
        session = active_service.sessions.get(payload.session_id) if active_service else None
        # Only ever speaks text the server itself already produced for this
        # session: either the last turn's main answer (replay), or one of the
        # per-card spoken_text values from that same turn (see
        # QueryService.query() / app/spoken_text.py). Never arbitrary
        # client-supplied text.
        known_texts = set(session.speakable_texts) if session else set()
        if session and session.turns:
            known_texts.add(session.turns[-1].answer)
        if session is None or session.language != payload.language or payload.text not in known_texts:
            raise HTTPException(status_code=409, detail="tts_text_invalid")
        started_at = perf_counter()
        try:
            audio = await app.state.speech_synthesizer.synthesize(
                payload.text,
                language=payload.language,
            )
        except SpeechSynthesisError as exc:
            event = "tts.timeout" if isinstance(exc, SpeechSynthesisTimeoutError) else "tts.failed"
            LOGGER.warning(
                event,
                extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
            )
            raise HTTPException(status_code=503, detail="Speech synthesis failed") from exc
        LOGGER.info(
            "tts.completed",
            extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
        )
        return Response(content=audio, media_type=app.state.speech_synthesizer.media_type)

    @app.post("/api/query", response_model=QueryResponse)
    async def answer_query(payload: QueryRequest) -> QueryResponse:
        if len(payload.query) > settings.query_max_chars:
            raise HTTPException(status_code=422, detail="Query text too long")
        active_service = app.state.service
        if not active_service:
            response = QueryResponse(
                answer=safety_text(payload.language, SafetyTextKind.TECHNICAL),
                language=payload.language,
                provider="template",
                status="error",
                answer_type="technical_fallback",
            )
            response.interaction.route = "runtime_unavailable"
            response.interaction.answer_type = "technical_fallback"
            response.interaction.safety_path = "interpreter_failure"
            response.interaction.safety_fallback_used = True
            response.interaction.safety_response_language = payload.language
        else:
            try:
                response = await active_service.query(payload)
            except DialogRequestError as exc:
                raise HTTPException(status_code=409, detail="dialog_response_invalid") from exc
        trace = response.interaction
        app.state.interaction_writer.write(
            InteractionRecord(
                session_id=response.session_id,
                language=payload.language,
                input_mode=payload.input_mode,
                user_query=(
                    "[redacted_safety_input]"
                    if trace.safety_path != "none"
                    else payload.query
                ),
                assistant_answer=response.answer,
                route=trace.route,
                source_ids=trace.source_ids,
                candidate_result_count=trace.candidate_result_count,
                acute_risk_detected=trace.acute_risk_detected,
                acute_risk_status=trace.acute_risk_status,
                safety_path=trace.safety_path,
                safety_dialogue_used=trace.safety_dialogue_used,
                safety_dialogue_result=trace.safety_dialogue_result,
                safety_fallback_used=trace.safety_fallback_used,
                safety_response_language=trace.safety_response_language,
                fallback_used=trace.fallback_used,
                interpreter_error_code=trace.interpreter_error_code,
                data_release_id=trace.data_release_id,
                candidate_selection_status=trace.candidate_selection_status,
                dialog_type=trace.dialog_type,
                dialog_attempt_count=trace.dialog_attempt_count,
                dialog_result_status=trace.dialog_result_status,
                selector_used=trace.selector_used,
                selection_source=trace.selection_source,
                selector_bypass_reason=trace.selector_bypass_reason,
                selector_eligible_count=trace.selector_eligible_count,
                selector_final_count=trace.selector_final_count,
                selector_fallback_used=trace.selector_fallback_used,
                selector_error_code=trace.selector_error_code,
                answer_type=trace.answer_type,
                formulator_used=trace.formulator_used,
                formulator_fallback_used=trace.formulator_fallback_used,
                formulator_error_code=trace.formulator_error_code,
                formulator_sentence_count=trace.formulator_sentence_count,
                formulator_offer_count=trace.formulator_offer_count,
                formulator_language=trace.formulator_language,
                llm_budget_status=trace.llm_budget_status,
                infrastructure_source=trace.infrastructure_source,
                infrastructure_result_count=trace.infrastructure_result_count,
                infrastructure_spoken_count=trace.infrastructure_spoken_count,
                infrastructure_card_count=trace.infrastructure_card_count,
                infrastructure_marker_count=trace.infrastructure_marker_count,
                infrastructure_distance_ranking_used=trace.infrastructure_distance_ranking_used,
                infrastructure_district_ranking_used=trace.infrastructure_district_ranking_used,
                infrastructure_error_code=trace.infrastructure_error_code,
                infrastructure_distance_class=trace.infrastructure_distance_class,
            )
        )
        return response

    return app
