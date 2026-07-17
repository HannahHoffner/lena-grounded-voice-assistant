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

from .config import Settings, load_settings
from .i18n import load_translation_store, translation_summary
from .interactions import InteractionRecord, InteractionWriter
from .kb_loader import KnowledgeBase, KnowledgeBaseError, load_active_knowledge_base
from .models import Language, QueryRequest, QueryResponse, SpeechSynthesisRequest
from .service import NO_RESULTS, QueryService
from .speech import (
    SpeechSynthesizer,
    SpeechSynthesisError,
    SpeechSynthesisTimeoutError,
    SpeechTranscriber,
    SpeechTranscriptionError,
    SpeechTranscriptionTimeoutError,
)
from .wfs_sync import load_wfs_state, sync_wfs


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
    try:
        kb = load_active_knowledge_base(settings)
    except KnowledgeBaseError:
        kb_error = True

    service = QueryService(settings, kb) if kb else None
    speech_transcriber = SpeechTranscriber(settings)
    speech_synthesizer = SpeechSynthesizer(settings)
    interaction_writer = InteractionWriter(
        settings.interaction_log_path or settings.app_root / "runtime" / "logs" / "interactions.jsonl",
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
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                LOGGER.warning("wfs.sync.failed", extra={"error_type": type(exc).__name__})
                app.state.last_wfs_check = {"status": "error"}
            await asyncio.sleep(settings.wfs_check_interval_hours * 3600)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(wfs_loop(app)) if settings.wfs_auto_sync else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="LENA", version="0.2.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.kb = kb
    app.state.kb_error = kb_error
    app.state.service = service
    app.state.speech_transcriber = speech_transcriber
    app.state.speech_synthesizer = speech_synthesizer
    app.state.interaction_writer = interaction_writer
    app.state.last_wfs_check = None

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

    static_root = Path(__file__).resolve().parent / "static"
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
        return {
            "status": "ok" if active_kb else "error",
            "kb_loaded": active_kb is not None,
            "offer_count": len(active_kb.offers) if active_kb else 0,
            "source_kind": active_kb.source_kind if active_kb else None,
            "source_hash": active_kb.source_hash if active_kb else None,
            "data_release_id": active_kb.release_id if active_kb else None,
            "configured_provider": settings.rewrite_provider,
            "active_provider": effective,
            "llm_router_available": active_service.full_context_available if active_service else False,
            "full_context_fallback_available": active_service.full_context_available if active_service else False,
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
            "translations": (
                translation_summary(load_translation_store(settings), active_kb.offers)
                if active_kb
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
        except SpeechTranscriptionError as exc:
            event = "stt.timeout" if isinstance(exc, SpeechTranscriptionTimeoutError) else "stt.failed"
            LOGGER.warning(
                event,
                extra={"duration_ms": round((perf_counter() - started_at) * 1000, 2)},
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
                answer=NO_RESULTS.get(payload.language, NO_RESULTS[Language.DE]),
                language=payload.language,
                provider="template",
                status="error",
            )
        else:
            response = await active_service.query(payload)
        trace = response.interaction
        app.state.interaction_writer.write(
            InteractionRecord(
                session_id=response.session_id,
                language=payload.language,
                input_mode=payload.input_mode,
                user_query=payload.query,
                assistant_answer=response.answer,
                route=trace.route,
                source_ids=trace.source_ids,
                retrieval_result_count=trace.retrieval_result_count,
                acute_risk_detected=trace.acute_risk_detected,
                fallback_used=trace.fallback_used,
                data_release_id=trace.data_release_id,
            )
        )
        return response

    return app
