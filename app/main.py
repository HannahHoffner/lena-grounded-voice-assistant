from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .kb import KnowledgeBase
from .models import (
    ConversationContext,
    QueryAnswerResponse,
    QueryRequest,
    SynthesizeRequest,
    SynthesizeResponse,
    TranscriptEvent,
    TranscribeResponse,
)
from .providers.rewrite import create_rewrite_provider
from .providers.stt import create_stt_provider
from .providers.tts import create_tts_provider
from .retrieval import normalize_text
from .scraper.pipeline import promote_dataset, run_pipeline
from .transcripts import TranscriptStore


REFERENTIAL_TERMS = (" it ", " there ", " that place", " this place", "dort", "da", "diese stelle", "dieser ort")
ALTERNATIVE_TERMS = ("another", "other", "different", "else", "another place", "andere", "weiteres", "alternative")


def create_app() -> FastAPI:
    settings = load_settings()
    if settings.bootstrap_runtime_from_scraper:
        _bootstrap_runtime_kb(settings.published_root, settings.scraper_published_root)
    app = FastAPI(title="LENA Prototype", version="0.1.0")

    kb = KnowledgeBase(settings.published_root)
    transcript_store = TranscriptStore(settings.transcripts_path)
    stt_provider = create_stt_provider(settings.stt_provider)
    rewrite_provider = create_rewrite_provider(
        settings.rewrite_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        ollama_timeout_seconds=settings.ollama_timeout_seconds,
        minimum_match_threshold=settings.minimum_match_threshold,
        weak_match_threshold=settings.weak_match_threshold,
        clarification_gap_threshold=settings.clarification_gap_threshold,
        system_prompt_path=settings.system_prompt_path,
    )
    tts_provider = create_tts_provider(settings.tts_provider, binary=settings.piper_binary)

    app.state.settings = settings
    app.state.kb = kb
    app.state.transcript_store = transcript_store
    app.state.stt_provider = stt_provider
    app.state.rewrite_provider = rewrite_provider
    app.state.tts_provider = tts_provider

    static_root = settings.app_root / "app" / "static"
    app.mount("/static", StaticFiles(directory=static_root), name="static")
    app.mount("/runtime/audio", StaticFiles(directory=settings.audio_root), name="runtime-audio")

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "kb_version": app.state.kb.dataset.manifest.kb_version,
            "stt_provider": app.state.stt_provider.name,
            "rewrite_provider": app.state.rewrite_provider.name,
            "rewrite_model": app.state.rewrite_provider.model_name,
            "llm_active": app.state.rewrite_provider.uses_llm,
            "tts_provider": app.state.tts_provider.name,
        }

    @app.post("/api/speech/transcribe", response_model=TranscribeResponse)
    async def transcribe(
        audio: UploadFile = File(...),
        language: str = Form(...),
        debug_transcript: str | None = Form(default=None),
    ) -> TranscribeResponse:
        try:
            transcript = await app.state.stt_provider.transcribe(audio, language, debug_transcript=debug_transcript)
            return TranscribeResponse(transcript=transcript, provider=app.state.stt_provider.name, status="ok")
        except Exception as exc:  # pragma: no cover - depends on runtime provider
            return TranscribeResponse(transcript="", provider=app.state.stt_provider.name, status="error", detail=str(exc))

    @app.post("/api/query/answer", response_model=QueryAnswerResponse)
    async def answer_query(payload: QueryRequest) -> QueryAnswerResponse:
        session_id = payload.session_id or uuid.uuid4().hex
        session_payload = payload.model_copy(update={"session_id": session_id})
        recent_events = app.state.transcript_store.recent_events(session_id, limit=3)
        conversation_context = _build_conversation_context(session_payload, recent_events, app.state.kb)
        answer = await app.state.rewrite_provider.answer(
            payload.transcript,
            payload.language,
            app.state.kb,
            conversation_context=conversation_context,
        )
        response = QueryAnswerResponse(
            answer_text=answer.answer_text,
            status=answer.status,
            weak_match=answer.weak_match,
            clarification_needed=answer.clarification_needed,
            clarification_question=answer.clarification_question,
            retrieved_page_ids=answer.retrieved_page_ids,
            provider=app.state.rewrite_provider.name,
            model=app.state.rewrite_provider.model_name,
            session_id=session_id,
        )
        _store_event(
            app.state.transcript_store,
            session_payload,
            response,
            resolved_transcript=conversation_context.resolved_transcript,
            kb_version=app.state.kb.dataset.manifest.kb_version,
            rewrite_provider=app.state.rewrite_provider.name,
            rewrite_model=app.state.rewrite_provider.model_name,
            stt_provider=app.state.stt_provider.name,
            tts_provider=app.state.tts_provider.name,
        )
        return response

    @app.post("/api/speech/synthesize", response_model=SynthesizeResponse)
    async def synthesize(payload: SynthesizeRequest) -> SynthesizeResponse:
        try:
            audio_url = await app.state.tts_provider.synthesize(payload.text, payload.language, app.state.settings.audio_root)
        except Exception as exc:  # pragma: no cover - depends on runtime provider
            return SynthesizeResponse(status="error", provider=app.state.tts_provider.name, detail=str(exc))
        if not audio_url:
            return SynthesizeResponse(status="unavailable", provider=app.state.tts_provider.name)
        return SynthesizeResponse(status="ok", provider=app.state.tts_provider.name, audio_url=audio_url)

    @app.post("/api/admin/scrape/run")
    async def scrape_run() -> dict:
        manifest = await run_pipeline(
            source_registry=settings.source_registry,
            output_root=settings.scraper_published_root,
            raw_root=settings.scraper_raw_root,
            reports_root=settings.scraper_reports_root,
        )
        return {
            "status": "ok",
            "workspace": "scraper",
            "kb_version": manifest.kb_version,
            "page_count": manifest.page_count,
        }

    @app.post("/api/admin/published/promote")
    async def promote_published() -> dict:
        manifest = promote_dataset(settings.scraper_published_root, settings.published_root)
        app.state.kb.reload()
        return {"status": "ok", "kb_version": manifest.kb_version, "workspace": "runtime"}

    @app.post("/api/admin/transcripts/clear")
    async def clear_transcripts() -> dict:
        app.state.transcript_store.clear()
        return {"status": "ok"}

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_root / "index.html")

    return app


def _bootstrap_runtime_kb(runtime_root: Path, scraper_root: Path) -> None:
    runtime_manifest = _read_manifest(runtime_root / "index" / "manifest.json")
    scraper_manifest = _read_manifest(scraper_root / "index" / "manifest.json")
    if not scraper_manifest:
        return
    runtime_version = runtime_manifest.get("kb_version", "") if runtime_manifest else ""
    scraper_version = scraper_manifest.get("kb_version", "")
    if not runtime_manifest or runtime_version.startswith("fixture-"):
        if scraper_version and not scraper_version.startswith("fixture-"):
            promote_dataset(scraper_root, runtime_root)


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _store_event(
    store: TranscriptStore,
    payload: QueryRequest,
    response: QueryAnswerResponse,
    resolved_transcript: str,
    kb_version: str,
    rewrite_provider: str,
    rewrite_model: str | None,
    stt_provider: str,
    tts_provider: str,
) -> None:
    store.append(
        TranscriptEvent(
            timestamp=__import__("datetime").datetime.now(__import__("datetime").UTC),
            session_id=payload.session_id or uuid.uuid4().hex,
            language=payload.language,
            transcript=payload.transcript,
            resolved_transcript=resolved_transcript,
            retrieved_page_ids=response.retrieved_page_ids,
            answer_text=response.answer_text,
            status=response.status,
            weak_match=response.weak_match,
            kb_version=kb_version,
            rewrite_provider=rewrite_provider,
            rewrite_model=rewrite_model,
            stt_provider=stt_provider,
            tts_provider=tts_provider,
        )
    )


def _build_conversation_context(
    payload: QueryRequest,
    recent_events: list[TranscriptEvent],
    kb: KnowledgeBase,
) -> ConversationContext:
    session_id = payload.session_id or uuid.uuid4().hex
    context = ConversationContext(session_id=session_id, resolved_transcript=payload.transcript)
    if not recent_events:
        return context

    latest = recent_events[-1]
    latest_titles = []
    for page_id in latest.retrieved_page_ids[:3]:
        try:
            latest_titles.append(kb.get_page(page_id).title)
        except KeyError:
            continue

    history_summary = f"Previous user request: {latest.transcript}"
    if latest_titles:
        history_summary += f"\nPrevious result pages: {', '.join(latest_titles)}"
    context.history_summary = history_summary
    normalized = f" {normalize_text(payload.transcript)} "

    if _is_alternative_followup(normalized):
        anchor_event = _find_anchor_event(recent_events)
        context.follow_up_mode = "alternative"
        context.excluded_page_ids = latest.retrieved_page_ids[:1]
        context.preferred_page_ids = anchor_event.retrieved_page_ids[1:3]
        context.reference_page_ids = anchor_event.retrieved_page_ids[:3]
        context.history_summary = f"Previous user request: {anchor_event.transcript}"
        if anchor_event.retrieved_page_ids:
            anchor_titles = []
            for page_id in anchor_event.retrieved_page_ids[:3]:
                try:
                    anchor_titles.append(kb.get_page(page_id).title)
                except KeyError:
                    continue
            if anchor_titles:
                context.history_summary += f"\nPrevious result pages: {', '.join(anchor_titles)}"
        context.resolved_transcript = f"{payload.transcript} {anchor_event.transcript}"
        return context

    if _is_referential_followup(normalized):
        context.follow_up_mode = "referential"
        context.preferred_page_ids = latest.retrieved_page_ids[:1]
        context.reference_page_ids = latest.retrieved_page_ids[:1]
        context.resolved_transcript = " ".join([payload.transcript, *latest_titles[:1]]).strip()

    return context


def _is_referential_followup(normalized_transcript: str) -> bool:
    return any(term in normalized_transcript for term in REFERENTIAL_TERMS)


def _is_alternative_followup(normalized_transcript: str) -> bool:
    return any(term in normalized_transcript for term in ALTERNATIVE_TERMS)


def _find_anchor_event(recent_events: list[TranscriptEvent]) -> TranscriptEvent:
    for event in reversed(recent_events):
        normalized = f" {normalize_text(event.transcript)} "
        if not _is_referential_followup(normalized) and not _is_alternative_followup(normalized):
            return event
    return recent_events[-1]
