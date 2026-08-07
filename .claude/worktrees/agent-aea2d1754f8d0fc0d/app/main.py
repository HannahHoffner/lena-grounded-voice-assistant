"""FastAPI-Einstiegspunkt und HTTP-Adapter der LENA-Anwendung."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .i18n import load_translation_store, translation_summary
from .kb_loader import KnowledgeBase, KnowledgeBaseError, load_knowledge_base
from .models import Language, QueryRequest, QueryResponse
from .service import NO_RESULTS, QueryService
from .speech import SpeechSynthesizer, SpeechSynthesisError, SpeechTranscriber, SpeechTranscriptionError
from .wfs_sync import load_wfs_state, sync_wfs


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
    kb: KnowledgeBase | None = None
    kb_error = False
    try:
        kb = load_knowledge_base(settings.kb_path)
    except KnowledgeBaseError:
        kb_error = True

    service = QueryService(settings, kb) if kb else None
    speech_transcriber = SpeechTranscriber(settings)
    speech_synthesizer = SpeechSynthesizer(settings)

    async def wfs_loop(app: FastAPI) -> None:
        while True:
            try:
                result = await sync_wfs(settings, promote=settings.wfs_auto_promote)
                app.state.last_wfs_check = {
                    "status": "ok",
                    "checked_at": result.checked_at,
                    "changed": result.changed,
                    "promoted": result.promoted,
                }
                if result.promoted:
                    refreshed = load_knowledge_base(settings.kb_path)
                    app.state.kb = refreshed
                    app.state.service = QueryService(settings, refreshed)
                    app.state.kb_error = False
            except Exception:  # pragma: no cover - network/runtime dependent
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
    app.state.last_wfs_check = None

    @app.middleware("http")
    async def prevent_dev_cache(request, call_next):
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
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
        audio = await request.body()
        content_type = request.headers.get("content-type", "audio/webm").split(";", 1)[0]
        try:
            text = await app.state.speech_transcriber.transcribe(
                audio,
                content_type=content_type,
                language=language,
            )
        except SpeechTranscriptionError as exc:
            raise HTTPException(status_code=503, detail="Speech transcription failed") from exc
        return {"text": text}

    @app.post("/api/speech/synthesize")
    async def synthesize_speech(payload: dict[str, object]) -> Response:
        text = str(payload.get("text") or "")
        try:
            language = Language(str(payload.get("language") or Language.DE.value))
        except ValueError:
            language = Language.DE
        try:
            audio = await app.state.speech_synthesizer.synthesize(text, language=language)
        except SpeechSynthesisError as exc:
            raise HTTPException(status_code=503, detail="Speech synthesis failed") from exc
        return Response(content=audio, media_type=app.state.speech_synthesizer.media_type)

    @app.post("/api/query", response_model=QueryResponse)
    async def answer_query(payload: QueryRequest) -> QueryResponse:
        active_service = app.state.service
        if not active_service:
            return QueryResponse(
                answer=NO_RESULTS.get(payload.language, NO_RESULTS[Language.DE]),
                language=payload.language,
                provider="template",
                status="error",
            )
        return await active_service.query(payload)

    return app
