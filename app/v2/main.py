from __future__ import annotations

import math
import os
import re
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import load_settings
from ..models import (
    KnowledgeAnswer,
    Language,
    MapData,
    MapDestination,
    MapOrigin,
    QueryAnswerResponse,
    QueryRequest,
    SessionEndRequest,
    SessionEndResponse,
    SymbolActionRequest,
    SymbolActionResponse,
    SymbolCategory,
    SymbolConfigResponse,
    SymbolResultCard,
    SynthesizeRequest,
    SynthesizeResponse,
    TranscribeResponse,
)
from ..providers.stt import create_stt_provider
from ..providers.tts import create_tts_provider
from ..sessions import SessionManager, SessionStore
from ..temporal import build_temporal_context
from ..transcripts import TranscriptStore
from .kb import V2KnowledgeBase
from .models import V2Category, V2Offer
from .presentation import display_name, primary_phone
from .service import V2AnswerService, retrieve_for_symbols


def create_v2_app() -> FastAPI:
    _apply_v2_provider_defaults()
    settings = load_settings()
    app_root = settings.app_root
    kb_path = _v2_kb_path(app_root)
    kb = V2KnowledgeBase(kb_path)
    transcript_store = TranscriptStore(settings.runtime_root / "v2_transcripts.jsonl")
    session_store = SessionStore(settings.runtime_root / "v2_sessions.json")
    session_manager = SessionManager(session_store, kb, timeout_seconds=settings.session_timeout_seconds)
    stt_provider = create_stt_provider(settings.stt_provider)
    voice_models = _v2_voice_models(settings)
    tts_provider = create_tts_provider(
        settings.tts_provider,
        binary=settings.piper_binary,
        voice_models=voice_models,
        voice_configs=settings.piper_voice_configs,
        default_voice_model=settings.piper_default_voice_model,
        default_voice_config=settings.piper_default_voice_config,
        normalize_umlauts=settings.tts_normalize_umlauts,
    )
    answer_service = V2AnswerService(settings)

    app = FastAPI(title="LENA v2 Clean Prototype", version="0.2.0")
    app.state.settings = settings
    app.state.kb = kb
    app.state.session_manager = session_manager
    app.state.session_store = session_store
    app.state.transcript_store = transcript_store
    app.state.stt_provider = stt_provider
    app.state.tts_provider = tts_provider
    app.state.rewrite_provider = answer_service
    app.state.v2_kb_path = kb_path

    static_root = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_root), name="v2-static")
    leaflet_root = settings.app_root / "app" / "static" / "vendor" / "leaflet"
    if leaflet_root.exists():
        app.mount("/leaflet", StaticFiles(directory=leaflet_root), name="v2-leaflet")
    audio_root = settings.audio_root / "v2"
    audio_root.mkdir(parents=True, exist_ok=True)
    app.mount("/runtime/audio", StaticFiles(directory=audio_root), name="v2-runtime-audio")
    app.state.last_transcript_source = None
    app.state.last_transcript_language = None
    app.state.last_map_destination_count = 0

    @app.get("/api/health")
    async def health() -> dict:
        stt_health = app.state.stt_provider.health()
        tts_health = app.state.tts_provider.health()
        return {
            "status": "ok",
            "variant": "v2",
            "kb_version": app.state.kb.dataset.manifest.kb_version,
            "kb_path": str(app.state.v2_kb_path),
            "authoritative_source_url": app.state.kb.v2_dataset.authoritative_source_url,
            "source_hash": app.state.kb.v2_dataset.source_hash,
            "source_last_checked": app.state.kb.source_last_checked,
            "stt_provider": app.state.stt_provider.name,
            "stt_configured_provider": stt_health["configured_provider"],
            "stt_ready": stt_health["ready"],
            "rewrite_provider": app.state.rewrite_provider.name,
            "configured_rewrite_provider": app.state.settings.rewrite_provider,
            "rewrite_model": app.state.rewrite_provider.model_name,
            "llm_active": app.state.rewrite_provider.uses_llm,
            "llm_base_url_configured": bool(app.state.settings.llm_base_url),
            "llm_api_key_configured": bool(app.state.settings.llm_api_key),
            "v2_prompt_loaded": app.state.rewrite_provider.prompt_loaded,
            "v2_prompt_path": str(app.state.rewrite_provider.system_prompt_path),
            "tts_provider": app.state.tts_provider.name,
            "tts_configured_provider": tts_health["configured_provider"],
            "tts_ready": tts_health["ready"],
            "speech": {"stt": stt_health, "tts": tts_health},
            "last_transcript_source": app.state.last_transcript_source,
            "last_transcript_language": app.state.last_transcript_language,
            "last_map_destination_count": app.state.last_map_destination_count,
            "map": {
                "tile_url_template": app.state.settings.map_tile_url_template,
                "tile_attribution": app.state.settings.map_tile_attribution,
                "tile_max_zoom": app.state.settings.map_tile_max_zoom,
                "leaflet_available": leaflet_root.exists(),
            },
            "voices": _voice_report(voice_models),
        }

    @app.post("/api/speech/transcribe", response_model=TranscribeResponse)
    async def transcribe(
        audio: UploadFile = File(...),
        language: str = Form(...),
        debug_transcript: str | None = Form(default=None),
    ) -> TranscribeResponse:
        selected_language: Language | None = None
        try:
            selected_language = Language(language)
            if app.state.stt_provider.name == "mock" and not debug_transcript:
                app.state.last_transcript_source = "mock_unavailable"
                app.state.last_transcript_language = language
                return TranscribeResponse(
                    transcript="",
                    text="",
                    language=selected_language,
                    provider=app.state.stt_provider.name,
                    status="error",
                    detail="Mock STT is active. Real speech transcription is unavailable; type your request or provide an explicit debug_transcript.",
                )
            transcript = await app.state.stt_provider.transcribe(audio, selected_language, debug_transcript=debug_transcript)
            app.state.last_transcript_source = "debug_transcript" if debug_transcript else app.state.stt_provider.name
            app.state.last_transcript_language = language
            return TranscribeResponse(
                transcript=transcript,
                text=transcript,
                language=selected_language,
                provider=app.state.stt_provider.name,
                status="ok",
            )
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            app.state.last_transcript_source = "error"
            app.state.last_transcript_language = language
            return TranscribeResponse(
                transcript="",
                text="",
                language=selected_language,
                provider=app.state.stt_provider.name,
                status="error",
                detail=str(exc),
            )

    @app.post("/api/query/answer", response_model=QueryAnswerResponse)
    async def answer_query(payload: QueryRequest) -> QueryAnswerResponse:
        temporal_context = build_temporal_context(timezone=app.state.settings.timezone)
        session_resolution = app.state.session_manager.prepare_request(payload)
        session_payload = payload.model_copy(update={"session_id": session_resolution.session.session_id})
        answer = await app.state.rewrite_provider.answer(
            payload.transcript,
            payload.language,
            app.state.kb,
            conversation_context=session_resolution.context,
            temporal_context=temporal_context,
        )
        response = QueryAnswerResponse(
            answer_text=answer.answer_text,
            status=answer.status,
            weak_match=answer.weak_match,
            clarification_needed=answer.clarification_needed,
            clarification_question=answer.clarification_question,
            out_of_scope=answer.out_of_scope,
            self_description=answer.self_description,
            crisis_mode=answer.crisis_mode,
            retrieved_page_ids=answer.retrieved_page_ids,
            map_data=answer.map_data or _build_v2_map_data(answer, app.state.kb, app.state.settings, payload.language),
            provider=app.state.rewrite_provider.name,
            model=app.state.rewrite_provider.model_name,
            session_id=session_resolution.session.session_id,
            session_status=session_resolution.session.status,
            session_event=session_resolution.session_event,
            session_message=session_resolution.session_message,
            temporal_context=temporal_context,
            sources=answer.sources,
            last_checked=answer.last_checked,
            answer_evidence=answer.answer_evidence,
            requirements=answer.requirements,
            cards=_cards_for_answer(answer, app.state.kb, payload.language, temporal_context, payload.transcript),
            follow_up_options=answer.follow_up_options,
        )
        app.state.last_map_destination_count = len(response.map_data.destinations) if response.map_data else 0
        updated_session = app.state.session_manager.record_turn(session_resolution.session, session_payload, response, session_resolution.context)
        response.session_status = updated_session.status
        return response

    @app.get("/api/symbol/config", response_model=SymbolConfigResponse)
    async def symbol_config(language: Language = Language.DE) -> SymbolConfigResponse:
        return SymbolConfigResponse(language=language, categories=_symbol_categories(language))

    @app.post("/api/symbol/answer", response_model=SymbolActionResponse)
    async def symbol_answer(payload: SymbolActionRequest) -> SymbolActionResponse:
        temporal_context = build_temporal_context(timezone=app.state.settings.timezone)
        session_query = QueryRequest(transcript=payload.category_id, language=payload.language, session_id=payload.session_id)
        session_resolution = app.state.session_manager.prepare_request(session_query)
        if payload.category_id == "emergency":
            answer = KnowledgeAnswer(answer_text=_emergency_text(payload.language), status="crisis", crisis_mode=True)
            cards: list[SymbolResultCard] = []
        else:
            category = _category_for_symbol(payload.category_id)
            ranked = retrieve_for_symbols(app.state.kb, category, limit=6)
            offers = [item.offer for item in ranked]
            answer = KnowledgeAnswer(
                answer_text=_symbol_answer_text(payload.language, category, offers),
                status="ok" if offers else "unknown",
                retrieved_page_ids=[offer.offer_id for offer in offers],
                sources=_sources(offers),
                last_checked=_last_checked(offers),
                answer_evidence=_evidence(offers),
                requirements=[offer.requirements for offer in offers if offer.requirements],
            )
            cards = [_card_for_offer(offer, payload.language, temporal_context) for offer in offers]
        map_data = _build_v2_map_data(answer, app.state.kb, app.state.settings, payload.language)
        response = SymbolActionResponse(
            answer_text=answer.answer_text,
            status=answer.status,
            category_id=payload.category_id,
            substep_id=payload.substep_id,
            cards=cards,
            retrieved_page_ids=answer.retrieved_page_ids,
            map_data=map_data,
            static_response=payload.category_id == "emergency",
            session_id=session_resolution.session.session_id,
            session_status=session_resolution.session.status,
            session_event=session_resolution.session_event,
            session_message=session_resolution.session_message,
            temporal_context=temporal_context,
            sources=answer.sources,
            last_checked=answer.last_checked,
            answer_evidence=answer.answer_evidence,
            requirements=answer.requirements,
            follow_up_options=answer.follow_up_options,
        )
        app.state.last_map_destination_count = len(response.map_data.destinations) if response.map_data else 0
        query_response = QueryAnswerResponse(
            answer_text=response.answer_text,
            status=response.status,
            crisis_mode=response.status == "crisis",
            retrieved_page_ids=response.retrieved_page_ids,
            map_data=response.map_data,
            provider=response.provider,
            model=response.model,
            session_id=response.session_id,
            session_status=response.session_status,
            session_event=response.session_event,
            session_message=response.session_message,
            temporal_context=temporal_context,
            sources=response.sources,
            last_checked=response.last_checked,
            answer_evidence=response.answer_evidence,
            requirements=response.requirements,
            cards=response.cards,
            follow_up_options=response.follow_up_options,
        )
        updated_session = app.state.session_manager.record_turn(session_resolution.session, session_query, query_response, session_resolution.context)
        response.session_status = updated_session.status
        return response

    @app.post("/api/session/end", response_model=SessionEndResponse)
    async def end_session(payload: SessionEndRequest) -> SessionEndResponse:
        ended = app.state.session_manager.end_session(payload.session_id)
        message = ended.last_session_message if ended and ended.last_session_message else "Conversation ended."
        return SessionEndResponse(status="ok", session_id=payload.session_id, session_message=message)

    @app.post("/api/speech/synthesize", response_model=SynthesizeResponse)
    async def synthesize(payload: SynthesizeRequest) -> SynthesizeResponse:
        try:
            audio_url = await app.state.tts_provider.synthesize(payload.text, payload.language, audio_root)
        except Exception as exc:  # pragma: no cover - provider/runtime dependent
            return SynthesizeResponse(status="error", provider=app.state.tts_provider.name, detail=str(exc))
        if not audio_url:
            return SynthesizeResponse(status="unavailable", provider=app.state.tts_provider.name)
        return SynthesizeResponse(status="ok", provider=app.state.tts_provider.name, audio_url=audio_url)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_root / "index.html")

    return app


def _apply_v2_provider_defaults() -> None:
    os.environ.setdefault("LENA_REWRITE_PROVIDER", "blablador")
    os.environ.setdefault("LENA_LLM_BASE_URL", "https://api.blablador.fz-juelich.de/v1/")
    os.environ.setdefault("LENA_LLM_MODEL", "alias-large")
    os.environ.setdefault("LENA_STT_PROVIDER", "faster_whisper")
    os.environ.setdefault("LENA_TTS_PROVIDER", "piper")


def _v2_kb_path(app_root: Path) -> Path:
    raw = os.getenv("LENA_V2_KB_PATH", "data/v2/curated_kb/offers.json")
    path = Path(raw)
    return path if path.is_absolute() else app_root / path


def _build_v2_map_data(answer: KnowledgeAnswer | QueryAnswerResponse, kb: V2KnowledgeBase, settings, language: Language = Language.DE) -> MapData | None:
    if answer.status not in {"ok", "weak_match"}:
        return None
    origin = MapOrigin(
        id=settings.map_origin_id,
        label=settings.map_origin_label,
        address=settings.map_origin_address,
        latitude=settings.map_origin_latitude,
        longitude=settings.map_origin_longitude,
    )
    destinations: list[MapDestination] = []
    seen: set[str] = set()
    for page_id in answer.retrieved_page_ids:
        try:
            offer = kb.get_offer(page_id)
        except KeyError:
            continue
        points = offer.map_points or []
        if points:
            for point in points:
                key = f"{offer.offer_id}:{point.point_id}"
                if key in seen:
                    continue
                seen.add(key)
                destinations.append(
                    MapDestination(
                        id=key,
                        page_id=offer.offer_id,
                        label=point.label or display_name(offer),
                        organization_label=offer.organization,
                        service_type=offer.subcategory or offer.category,
                        address=point.address,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        distance_meters=_distance_meters(origin.latitude, origin.longitude, point.latitude, point.longitude),
                        description=_localized_point_note(point.note, language),
                        opening_hours=point.opening_hours,
                    )
                )
        elif offer.coordinates and offer.address:
            key = offer.offer_id
            if key in seen:
                continue
            seen.add(key)
            destinations.append(
                MapDestination(
                    id=key,
                    page_id=offer.offer_id,
                    label=display_name(offer),
                    organization_label=offer.organization,
                    service_type=offer.subcategory or offer.category,
                    address=offer.address,
                    latitude=offer.coordinates.latitude,
                    longitude=offer.coordinates.longitude,
                    distance_meters=_distance_meters(
                        origin.latitude,
                        origin.longitude,
                        offer.coordinates.latitude,
                        offer.coordinates.longitude,
                    ),
                    description=_localized_offer_summary(offer, language),
                    opening_hours=offer.all_times[:4],
                )
            )
        if len(destinations) >= 10:
            break
    if not destinations:
        return None
    return MapData(origin=origin, destinations=destinations[:10], selected_destination_id=destinations[0].id)


def _cards_for_answer(answer: KnowledgeAnswer, kb: V2KnowledgeBase, language: Language, temporal_context, request_text: str = "") -> list[SymbolResultCard]:
    cards: list[SymbolResultCard] = []
    for page_id in answer.retrieved_page_ids[:8]:
        try:
            offer = kb.get_offer(page_id)
        except KeyError:
            continue
        cards.append(_card_for_offer(offer, language, temporal_context, request_text))
    return cards


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(radius_m * c))


def _v2_voice_models(settings) -> dict[str, str]:
    voices = dict(settings.piper_voice_models)
    if not os.getenv("LENA_PIPER_VOICE_DE"):
        candidate = settings.data_root / "voices" / "piper" / "de_DE-ramona-low.onnx"
        if candidate.exists():
            voices["de"] = str(candidate)
    return voices


def _voice_report(voice_models: dict[str, str]) -> dict[str, dict[str, str | bool | None]]:
    desired_female = {"de": "de_DE-ramona-low"}
    report: dict[str, dict[str, str | bool | None]] = {}
    for language in ("de", "en", "pl", "ro", "ru"):
        model = voice_models.get(language)
        name = Path(model).stem if model else None
        report[language] = {
            "model": model,
            "female_preferred": True,
            "female_configured": bool(name and desired_female.get(language) == name),
            "limitation": None if name and desired_female.get(language) == name else "Female local Piper voice not confirmed; using configured local fallback.",
        }
    return report


def _symbol_categories(language: Language) -> list[SymbolCategory]:
    definitions = [
        ("food", "food", {"de": "Essen", "en": "Food", "pl": "Jedzenie", "ro": "Mancare", "ru": "Eda"}, 10),
        ("sleep", "bed", {"de": "Schlafen", "en": "Sleep", "pl": "Nocleg", "ro": "Somn", "ru": "Nochleg"}, 20),
        ("medical", "medical", {"de": "Medizin", "en": "Medical", "pl": "Medycyna", "ro": "Medical", "ru": "Meditsina"}, 30),
        ("advice", "help", {"de": "Beratung allgemein", "en": "General advice", "pl": "Porada ogolna", "ro": "Consiliere generala", "ru": "Obshchaya konsultatsiya"}, 40),
        ("emergency", "alert", {"de": "Notfall", "en": "Emergency", "pl": "Alarm", "ro": "Urgenta", "ru": "Srochno"}, 50),
    ]
    return [
        SymbolCategory(id=item_id, icon=icon, label=labels.get(language.value, labels["de"]), priority=priority, result_mode="static" if item_id == "emergency" else "cards-map")
        for item_id, icon, labels, priority in definitions
    ]


def _category_for_symbol(symbol_id: str) -> V2Category:
    return {
        "food": "food",
        "sleep": "sleep",
        "medical": "medical",
        "advice": "general_advice",
    }.get(symbol_id, "general_advice")  # type: ignore[return-value]


def _symbol_answer_text(language: Language, category: V2Category, offers: list[V2Offer]) -> str:
    if not offers:
        return {"de": "Dazu habe ich keine sichere Information.", "en": "I do not have safe information for that."}.get(language.value, "I do not have safe information for that.")
    intro = {
        "food": {
            "de": "Ich habe Orte für Essen oder Getränke gefunden.",
            "en": "I found places for food or drinks.",
            "pl": "Znalazłam miejsca z jedzeniem albo napojami.",
            "ro": "Am găsit locuri pentru mâncare sau băuturi.",
            "ru": "Ya nashla mesta s edoy ili napitkami.",
        },
        "sleep": {
            "de": "Ich habe Orte für Schlafen oder Notunterkunft gefunden.",
            "en": "I found places for sleep or emergency accommodation.",
            "pl": "Znalazłam miejsca do spania albo noclegu awaryjnego.",
            "ro": "Am găsit locuri pentru dormit sau cazare de urgență.",
            "ru": "Ya nashla mesta dlya nochlega ili srochnogo razmeshcheniya.",
        },
        "medical": {
            "de": "Ich habe medizinische Hilfe gefunden.",
            "en": "I found medical help.",
            "pl": "Znalazłam pomoc medyczną.",
            "ro": "Am găsit ajutor medical.",
            "ru": "Ya nashla meditsinskuyu pomoshch.",
        },
        "general_advice": {
            "de": "Ich habe Beratung gefunden.",
            "en": "I found advice services.",
            "pl": "Znalazłam miejsca z poradą.",
            "ro": "Am găsit servicii de consiliere.",
            "ru": "Ya nashla mesta dlya konsultatsii.",
        },
    }.get(category, CATEGORY_SUMMARY_TEXT["other_source_listed"])
    hint = {
        "de": "Brauchst du mehr Informationen? Tippe auf eine Karte. Dort siehst du Ort, Zeit und Telefon.",
        "en": "Do you need more information? Tap a card. It shows place, time, and phone.",
        "pl": "Czy potrzebujesz więcej informacji? Naciśnij kartę. Tam jest miejsce, czas i telefon.",
        "ro": "Ai nevoie de mai multe informații? Apasă pe un card. Acolo vezi locul, ora și telefonul.",
        "ru": "Nuzhno bolshe informatsii? Nazhmi na kartochku. Tam est mesto, vremya i telefon.",
    }
    return f"{_t(intro, language)} {_t(hint, language)}"


CATEGORY_SUMMARY_TEXT = {
    "food": {
        "de": "Hier gibt es Essen, Getränke oder Lebensmittel.",
        "en": "Food, drinks, or groceries.",
        "pl": "Jedzenie, napoje albo produkty spożywcze.",
        "ro": "Mâncare, băuturi sau alimente.",
        "ru": "Eda, napitki ili produkty.",
    },
    "sleep": {
        "de": "Hier kannst du nach einem Schlafplatz fragen.",
        "en": "You can ask here for a place to sleep.",
        "pl": "Tu możesz zapytać o miejsce do spania.",
        "ro": "Aici poți întreba despre un loc de dormit.",
        "ru": "Zdes mozhno sprosit pro mesto dlya sna.",
    },
    "medical": {
        "de": "Hier gibt es medizinische Hilfe oder Beratung.",
        "en": "Medical help or advice.",
        "pl": "Pomoc medyczna albo porada.",
        "ro": "Ajutor medical sau consiliere.",
        "ru": "Meditsinskaya pomoshch ili konsultatsiya.",
    },
    "general_advice": {
        "de": "Hier bekommst du Beratung und Unterstützung.",
        "en": "Advice and support.",
        "pl": "Porada i wsparcie.",
        "ro": "Consiliere și sprijin.",
        "ru": "Konsultatsiya i podderzhka.",
    },
    "addiction": {
        "de": "Hier gibt es Hilfe bei Drogen, Konsum oder Sucht.",
        "en": "Help with drugs, use, or addiction.",
        "pl": "Pomoc przy narkotykach, używaniu albo uzależnieniu.",
        "ro": "Ajutor pentru droguri, consum sau dependență.",
        "ru": "Pomoshch po narkotikam, potrebleniyu ili zavisimosti.",
    },
    "hygiene": {
        "de": "Hier gibt es Duschen, Waschen oder Hygiene.",
        "en": "Showers, washing, or hygiene.",
        "pl": "Prysznic, pranie albo higiena.",
        "ro": "Dușuri, spălat sau igienă.",
        "ru": "Dush, stirka ili gigiena.",
    },
    "other_source_listed": {
        "de": "Hier gibt es Unterstützung.",
        "en": "Support is available here.",
        "pl": "Tutaj jest dostępne wsparcie.",
        "ro": "Aici este disponibil sprijin.",
        "ru": "Zdes dostupna pomoshch.",
    },
}

CATEGORY_SERVICE_TEXT = {
    key: {lang: value.rstrip(".") for lang, value in values.items()}
    for key, values in CATEGORY_SUMMARY_TEXT.items()
}

SHORT_SUMMARY_TEXT = {
    "hilfebus": {
        "de": "Mobile Hilfe täglich 18-23 Uhr: Essen, Getränke, warme Kleidung und Vermittlung zu Notübernachtung. Sonntag 20-21 Uhr Suppenausgabe am Hauptbahnhof.",
        "en": "Mobile help daily 6-11 pm: food, drinks, warm clothes, and referral to emergency accommodation. Sunday 8-9 pm soup at the main station.",
        "pl": "Mobilna pomoc codziennie 18-23: jedzenie, napoje, ciepłe ubrania i skierowanie do noclegu awaryjnego. Niedziela 20-21 zupa przy dworcu.",
        "ro": "Ajutor mobil zilnic 18-23: mâncare, băuturi, haine calde și îndrumare spre cazare de urgență. Duminică 20-21 supă la gară.",
        "ru": "Mobilnaya pomoshch ezhednevno 18-23: eda, napitki, teplaya odezhda i napravlenie k srochnomu nochlegu. Voskresene 20-21 sup u vokzala.",
    },
    "safe-team-wohnen": {
        "de": "Hilfe bei Wohnung, Geld, Konsum, Gesundheit und Behörden. Büro: Di 10-16 Uhr Demmeringstraße. Standzeiten: Di 17-18 Uhr Schwanenteich, Mi/Fr 10-16 Uhr Hauptbahnhof.",
        "en": "Help with housing, money, substance use, health, and offices. Office: Tue 10-4 at Demmeringstraße. Outreach: Tue 5-6 at Schwanenteich, Wed/Fri 10-4 at the main station.",
        "pl": "Pomoc z mieszkaniem, pieniędzmi, używaniem substancji, zdrowiem i urzędami. Biuro: wt. 10-16 Demmeringstraße. Punkty: wt. 17-18 Schwanenteich, śr./pt. 10-16 dworzec.",
        "ro": "Ajutor cu locuința, banii, consumul, sănătatea și instituțiile. Birou: marți 10-16 Demmeringstraße. Puncte: marți 17-18 Schwanenteich, miercuri/vineri 10-16 gara principală.",
        "ru": "Pomoshch s zhilyem, dengami, upotrebleniem, zdorovyem i uchrezhdeniyami. Ofis: vt 10-16 Demmeringstraße. Tochki: vt 17-18 Schwanenteich, sr/pt 10-16 vokzal.",
    },
    "diakonie-streetwork": {
        "de": "Beratung, Information und warme Mahlzeiten/Getränke dienstags am Schwanenteich.",
        "en": "Advice, information, and warm meals/drinks on Tuesdays at Schwanenteich.",
        "pl": "Porada, informacja i ciepłe posiłki/napoje we wtorki przy Schwanenteich.",
        "ro": "Consiliere, informații și mese/băuturi calde marțea la Schwanenteich.",
        "ru": "Konsultatsiya, informatsiya i goryachaya eda/napitki po vtornikam u Schwanenteich.",
    },
    "safe-team-konsum": {
        "de": "Beratung zu Drogen/Konsum mit warmen Getränken und kleinen Snacks an lokalen Standzeiten.",
        "en": "Advice about drugs/substance use with warm drinks and small snacks at local stand times.",
        "pl": "Porada o narkotykach/używaniu, ciepłe napoje i małe przekąski w lokalnych punktach.",
        "ro": "Consiliere despre droguri/consum, băuturi calde și gustări mici la puncte locale.",
        "ru": "Konsultatsiya po narkotikam/upotrebleniyu, teplye napitki i zakuski v lokalnykh tochkakh.",
    },
    "uvo-medical-outreach": {
        "de": "Aufsuchende medizinische Hilfe mit Medibus an festen Standzeiten.",
        "en": "Outreach medical help with a Medibus at fixed local stand times.",
        "pl": "Mobilna pomoc medyczna z Medibusem w stałych miejscach i godzinach.",
        "ro": "Ajutor medical mobil cu Medibus la ore și locuri fixe.",
        "ru": "Vyezdnaya meditsinskaya pomoshch s Medibus v fiksirovannykh mestakh i vremya.",
    },
    "cabl-clearingstelle": {
        "de": "Hilfe für Menschen ohne regulären Zugang zum Gesundheitssystem. Beratung und anonyme Behandlungsscheine.",
        "en": "Help for people without regular access to the health system. Advice and anonymous treatment certificates.",
        "pl": "Pomoc dla osób bez regularnego dostępu do systemu zdrowia. Porada i anonimowe zaświadczenia medyczne.",
        "ro": "Ajutor pentru persoane fără acces regulat la sistemul medical. Consiliere și certificate medicale anonime.",
        "ru": "Pomoshch lyudyam bez obychnogo dostupa k sisteme zdravookhraneniya. Konsultatsiya i anonimnye meditsinskie spravki.",
    },
    "kontaktcafe-alternative-i": {
        "de": "Kontaktcafé mit Mittagessen, Dusche, Beratung, Konsummitteln/Spritzen, Kondomen und medizinischer Notversorgung.",
        "en": "Contact café with lunch, shower, advice, safer-use supplies/syringes, condoms, and emergency medical help.",
        "pl": "Kawiarnia kontaktowa z obiadem, prysznicem, poradą, materiałami safer use/strzykawkami, prezerwatywami i pomocą medyczną.",
        "ro": "Cafenea de contact cu prânz, duș, consiliere, materiale safer-use/seringi, prezervative și ajutor medical de urgență.",
        "ru": "Kontakt-kafe s obedom, dushem, konsultatsiey, safer-use materialami/shpritsami, prezervativami i meditsinskoy neotlozhnoy pomoshchyu.",
    },
    "alternative-i-notschlafstelle": {
        "de": "Notschlafstelle mit Dusche, Waschen, Beratung, Safer Use, Konsummitteln/Spritzen und medizinischer Notversorgung.",
        "en": "Emergency sleeping place with shower, washing, advice, safer-use supplies/syringes, and emergency medical help.",
        "pl": "Nocleg awaryjny z prysznicem, praniem, poradą, materiałami safer use/strzykawkami i pomocą medyczną.",
        "ro": "Loc de dormit de urgență cu duș, spălat, consiliere, materiale safer-use/seringi și ajutor medical.",
        "ru": "Srochnyy nochleg s dushem, stirkoy, konsultatsiey, safer-use materialami/shpritsami i meditsinskoy pomoshchyu.",
    },
    "mobile-alternative": {
        "de": "Mobile Drogenhilfe mit Beratung, Safer Use, Hygiene, Kondomen und Spritzentausch an lokalen Standzeiten.",
        "en": "Mobile drug help with advice, safer use, hygiene, condoms, and syringe exchange at local stand times.",
        "pl": "Mobilna pomoc narkotykowa: porada, safer use, higiena, prezerwatywy i wymiana strzykawek.",
        "ro": "Ajutor mobil pentru droguri: consiliere, safer use, igienă, prezervative și schimb de seringi.",
        "ru": "Mobilnaya narkopomoshch: konsultatsiya, safer use, gigiena, prezervativy i obmen shpritsov.",
    },
}

TARGET_GROUP_TRANSLATIONS = [
    (("adults", "erwachsene"), {"de": "Erwachsene", "en": "Adults", "pl": "Dorośli", "ro": "Adulți", "ru": "Vzroslye"}),
    (("homeless", "obdach", "wohnungslos", "without housing", "without fixed housing"), {"de": "Menschen ohne Unterkunft", "en": "People without housing", "pl": "Osoby bez mieszkania", "ro": "Persoane fără locuință", "ru": "Lyudi bez zhilya"}),
    (("housing problems", "wohnungsnot"), {"de": "Menschen in Wohnungsnot", "en": "People with housing problems", "pl": "Osoby w kryzysie mieszkaniowym", "ro": "Persoane cu probleme locative", "ru": "Lyudi s zhilishchnymi problemami"}),
    (("addiction", "sucht"), {"de": "Menschen mit Fragen zu Sucht", "en": "People with addiction questions", "pl": "Osoby z pytaniami o uzależnienie", "ro": "Persoane cu întrebări despre dependență", "ru": "Lyudi s voprosami o zavisimosti"}),
    (("drugs", "substance", "drogen", "konsum"), {"de": "Menschen, die Drogen konsumieren", "en": "People who use substances", "pl": "Osoby używające substancji", "ro": "Persoane care consumă substanțe", "ru": "Lyudi, upotreblyayushchie veshchestva"}),
    (("women", "frauen"), {"de": "Frauen", "en": "Women", "pl": "Kobiety", "ro": "Femei", "ru": "Zhenshchiny"}),
    (("men", "maenner", "männer"), {"de": "Männer", "en": "Men", "pl": "Mężczyźni", "ro": "Bărbați", "ru": "Muzhchiny"}),
]

SERVICE_TRANSLATIONS = [
    (("anonyme behandlung", "behandlungsschein", "gesundheitssystem"), {"de": "anonyme Behandlungsscheine", "en": "anonymous treatment certificates", "pl": "anonimowe zaświadczenia medyczne", "ro": "certificate medicale anonime", "ru": "anonimnye meditsinskie spravki"}),
    (("medizinische notversorgung", "medizinische versorgung", "aerztliche", "arzt", "medibus"), {"de": "medizinische Hilfe", "en": "medical help", "pl": "pomoc medyczna", "ro": "ajutor medical", "ru": "meditsinskaya pomoshch"}),
    (("sozialberatung", "beratung", "information"), {"de": "Beratung", "en": "advice", "pl": "porada", "ro": "consiliere", "ru": "konsultatsiya"}),
    (("uebernacht", "notschlaf", "schlafplatz", "schlafen"), {"de": "Schlafplatz", "en": "place to sleep", "pl": "miejsce do spania", "ro": "loc de dormit", "ru": "mesto dlya sna"}),
    (("warmes essen", "warme mahlzeit", "mahlzeit", "mittag", "fruehstueck", "broetchen", "lebensmittel", "suppe"), {"de": "Essen", "en": "food", "pl": "jedzenie", "ro": "mâncare", "ru": "eda"}),
    (("getraenk", "kaffee", "tee", "wasser"), {"de": "Getränke", "en": "drinks", "pl": "napoje", "ro": "băuturi", "ru": "napitki"}),
    (("kleidung", "decken", "schlafsaecke", "schlafsack"), {"de": "warme Kleidung", "en": "warm clothes", "pl": "ciepłe ubrania", "ro": "haine călduroase", "ru": "teplaya odezhda"}),
    (("dusche", "duschen", "waesche", "waschen", "hygiene"), {"de": "Duschen oder Waschen", "en": "showers or washing", "pl": "prysznic albo pranie", "ro": "duș sau spălat", "ru": "dush ili stirka"}),
    (("postadresse", "postadress"), {"de": "Postadresse", "en": "postal address", "pl": "adres pocztowy", "ro": "adresă poștală", "ru": "pochtovyy adres"}),
    (("behoerden", "aemter", "finanzen", "wohnung", "vermittlung"), {"de": "Hilfe mit Behörden und Vermittlung", "en": "help with offices and referrals", "pl": "pomoc w urzędach i przekierowanie", "ro": "ajutor cu instituții și îndrumare", "ru": "pomoshch s uchrezhdeniyami i napravlenie"}),
    (("konsummittel", "konsumutensilien", "spritzen", "spritzentausch", "erstbesteck"), {"de": "Konsummittel und Spritzen", "en": "safer-use supplies and syringes", "pl": "materiały safer use i strzykawki", "ro": "materiale safer-use și seringi", "ru": "materialy safer use i shpritsy"}),
    (("safer use", "safer sex", "konsumutensilien", "kondom", "erstbesteck"), {"de": "Safer Use und Kondome", "en": "safer use supplies and condoms", "pl": "materiały safer use i prezerwatywy", "ro": "materiale safer use și prezervative", "ru": "materialy safer use i prezervativy"}),
]

REQ_CALL_FIRST = {
    "de": "Telefonische Terminvereinbarung notwendig.",
    "en": "Call first to make an appointment.",
    "pl": "Najpierw zadzwoń i umów termin.",
    "ro": "Sună mai întâi pentru programare.",
    "ru": "Snachala pozvoni i dogovoris o vremeni.",
}
REQ_AGE_18 = {
    "de": "Ab 18 Jahren.",
    "en": "For adults from age 18.",
    "pl": "Dla osób dorosłych od 18 lat.",
    "ro": "Pentru adulți de la 18 ani.",
    "ru": "Dlya vzroslykh s 18 let.",
}
REQ_CHECK = {
    "de": "Bitte Voraussetzungen prüfen.",
    "en": "Please check the requirements with the service.",
    "pl": "Sprawdź warunki w tej placówce.",
    "ro": "Verifică condițiile la acest serviciu.",
    "ru": "Utochni usloviya v etoy sluzhbe.",
}
POINT_NOTE_SCHWANENTEICH = {
    "de": "Beratung, Information, warme Mahlzeiten und Getränke.",
    "en": "Advice, information, warm meals, and drinks.",
    "pl": "Porada, informacja, ciepłe posiłki i napoje.",
    "ro": "Consiliere, informații, mese calde și băuturi.",
    "ru": "Konsultatsiya, informatsiya, goryachaya eda i napitki.",
}
POINT_NOTE_SOUP = {
    "de": "Suppenausgabe an der Westseite des Hauptbahnhofs.",
    "en": "Soup distribution at the west side of the main station.",
    "pl": "Wydawanie zupy po zachodniej stronie dworca głównego.",
    "ro": "Distribuire de supă pe partea de vest a gării principale.",
    "ru": "Razdacha supa na zapadnoy storone glavnogo vokzala.",
}
POINT_NOTE_SNACKS = {
    "de": "Warme Getränke, kleine Snacks und Gesprächsangebot.",
    "en": "Warm drinks, small snacks, and a chance to talk.",
    "pl": "Ciepłe napoje, małe przekąski i możliwość rozmowy.",
    "ro": "Băuturi calde, gustări mici și posibilitate de discuție.",
    "ru": "Teplie napitki, nebolshie zakuski i razgovor.",
}
SLEEP_TIME_CHECK = {
    "de": "Zeiten bitte prüfen",
    "en": "Please check times",
    "pl": "Sprawdź godziny",
    "ro": "Verifică programul",
    "ru": "Prover vremya",
}


def _card_for_offer(offer: V2Offer, language: Language, temporal_context=None, request_text: str = "") -> SymbolResultCard:
    primary_point = offer.map_points[0] if offer.map_points else None
    opening_hours = _card_opening_hours(offer)
    if offer.category == "sleep":
        hint = _sleep_availability_hint(opening_hours, language, temporal_context, request_text)
        if hint:
            opening_hours = [hint, *opening_hours]
    return SymbolResultCard(
        page_id=offer.offer_id,
        title=display_name(offer),
        category=offer.category,
        service_type=offer.subcategory or offer.category,
        address=primary_point.address if primary_point else offer.address,
        location=offer.location,
        opening_hours=opening_hours,
        phone=primary_phone(offer),
        email=offer.email,
        website=offer.website,
        description=_localized_offer_summary(offer, language),
        card_summary=_localized_offer_summary(offer, language),
        action={
            "de": "Tippe auf den Ort für mehr Infos.",
            "en": "You can ask there for help.",
            "pl": "Mozesz tam zapytac o pomoc.",
            "ro": "Poti cere ajutor acolo.",
            "ru": "Tam mozhno sprosit pomoshch.",
        }.get(language.value, "You can ask there for help."),
        target_groups=_localized_target_groups(offer, language),
        requirements=_localized_requirement(offer, language),
        services_provided=_localized_services(offer, language),
        notes=_localized_note(offer, language),
        last_updated=offer.last_checked,
        has_map_location=bool(primary_point or (offer.address and offer.coordinates)),
    )


def _card_opening_hours(offer: V2Offer) -> list[str]:
    if offer.offer_id == "hilfebus":
        return [
            "Täglich: 18:00 - 23:00 Uhr mobiler Einsatz, stadtweit",
            "Sonntag: 20:00 - 21:00 Uhr Hauptbahnhof Westseite mit Suppenausgabe",
        ]
    if offer.offer_id == "safe-team-wohnen":
        return [
            "Dienstag: 10:00 - 16:00 Uhr Büro Demmeringstraße",
            "Dienstag: 17:00 - 18:00 Uhr Schwanenteich",
            "Mittwoch und Freitag: 10:00 - 16:00 Uhr Hauptbahnhof",
        ]
    values: list[str] = []
    for value in [*offer.opening_times, *offer.einsatzzeiten]:
        _append_display_time(values, value)
    for point in offer.map_points:
        for value in point.opening_hours:
            label = point.label.split(":", 1)[-1].strip() if point.label else ""
            time_text = f"{value} {label}".strip() if label and label not in value else value
            _append_display_time(values, time_text)
    return values


def _append_display_time(values: list[str], value: str | None) -> None:
    if not value:
        return
    text = " ".join(str(value).split()).strip()
    normalized = _normalize_for_translation(text)
    if not text or text.endswith(":") or normalized.startswith("standzeiten:"):
        return
    if normalized.startswith("einsatzgebiete") or "instagramkanal" in normalized:
        return
    if len(text) > 180:
        return
    has_time_signal = bool(
        re.search(r"\b\d{1,2}[:.]\d{2}\b", text)
        or any(day in normalized for day in ("montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag", "taeglich", "taglich"))
        or any(term in normalized for term in ("ganzt", "terminvereinbarung", "flexibilitaet", "flexibilität"))
    )
    if has_time_signal and text not in values:
        values.append(text)


def _localized_offer_summary(offer: V2Offer, language: Language) -> str:
    known = SHORT_SUMMARY_TEXT.get(offer.offer_id)
    if known:
        return _t(known, language)
    if language == Language.DE:
        return offer.card_summary or offer.short_description
    services = _localized_services(offer, language, limit=4)
    if services:
        return _t(
            {
                "de": offer.card_summary or offer.short_description,
                "en": f"You can ask here for: {', '.join(services)}.",
                "pl": f"Tu możesz zapytać o: {', '.join(services)}.",
                "ro": f"Aici poți întreba despre: {', '.join(services)}.",
                "ru": f"Zdes mozhno sprosit pro: {', '.join(services)}.",
            },
            language,
        )
    return _t(CATEGORY_SUMMARY_TEXT.get(offer.category, CATEGORY_SUMMARY_TEXT["other_source_listed"]), language)


def _localized_services(offer: V2Offer, language: Language, *, limit: int = 4) -> list[str]:
    result: list[str] = []
    for value in offer.services_provided:
        translated = value if language == Language.DE else _translate_service_item(value, language)
        if translated and translated not in result:
            result.append(translated)
        if len(result) >= limit:
            break
    if not result:
        result.append(_t(CATEGORY_SERVICE_TEXT.get(offer.category, CATEGORY_SERVICE_TEXT["other_source_listed"]), language))
    return result


def _localized_target_groups(offer: V2Offer, language: Language) -> list[str]:
    if offer.offer_id == "uebernachtungshaus-maenner-leutzsch":
        return [_t({"de": "Volljährige wohnungslose Männer", "en": "Adult men without housing", "pl": "Dorośli mężczyźni bez mieszkania", "ro": "Bărbați adulți fără locuință", "ru": "Vzroslye muzhchiny bez zhilya"}, language)]
    if "frauen" in offer.offer_id:
        return [_t({"de": "Wohnungslose Frauen", "en": "Women without housing", "pl": "Kobiety bez mieszkania", "ro": "Femei fără locuință", "ru": "Zhenshchiny bez zhilya"}, language)]
    if offer.offer_id in {"alternative-i-notschlafstelle", "alternative-iii-notschlafstelle"}:
        return [_t({"de": "Drogengebrauchende Erwachsene", "en": "Adults who use substances", "pl": "Dorośli używający substancji", "ro": "Adulți care consumă substanțe", "ru": "Vzroslye, upotreblyayushchie veshchestva"}, language)]
    if offer.offer_id == "soziale-wohnhilfen-notunterbringung":
        return [_t({"de": "Menschen in Wohnungsnot / ohne Unterkunft", "en": "People in housing emergency / without accommodation", "pl": "Osoby w kryzysie mieszkaniowym / bez noclegu", "ro": "Persoane în urgență locativă / fără cazare", "ru": "Lyudi v zhilishchnom krizise / bez nochlega"}, language)]
    if offer.offer_id == "hilfebus":
        return [_t({"de": "Obdachlose Menschen / Menschen ohne Unterkunft", "en": "People without housing / without accommodation", "pl": "Osoby bez dachu nad głową / bez noclegu", "ro": "Persoane fără adăpost / fără cazare", "ru": "Lyudi bez doma / bez nochlega"}, language)]
    result: list[str] = []
    for value in offer.target_group:
        translated = _translate_target_group(value, language)
        if translated and translated not in result:
            result.append(translated)
        if len(result) >= 2:
            break
    return result


def _translate_target_group(value: str, language: Language) -> str | None:
    normalized = _normalize_for_translation(value)
    if not normalized:
        return None
    for keywords, translations in TARGET_GROUP_TRANSLATIONS:
        if any(keyword in normalized for keyword in keywords):
            return _t(translations, language)
    if language == Language.DE:
        return value if not re.fullmatch(r"[a-z_ ,/-]+", value) else None
    return None


def _translate_service_item(value: str, language: Language) -> str | None:
    normalized = _normalize_for_translation(value)
    if not normalized or normalized in {"food", "sleep", "advice", "medical", "hygiene", "emergency_accommodation"}:
        return None
    for keywords, translations in SERVICE_TRANSLATIONS:
        if any(keyword in normalized for keyword in keywords):
            return _t(translations, language)
    return None


def _localized_requirement(offer: V2Offer, language: Language) -> str | None:
    if language == Language.DE:
        return offer.requirements
    text = _normalize_for_translation(offer.requirements or "")
    if not text:
        return None
    if "telefonische terminvereinbarung" in text:
        return _t(REQ_CALL_FIRST, language)
    if "vollendeten 18" in text or "ab 18" in text:
        return _t(REQ_AGE_18, language)
    return _t(REQ_CHECK, language)


def _localized_note(offer: V2Offer, language: Language) -> str | None:
    if language == Language.DE:
        return offer.notes
    return None


def _localized_point_note(note: str | None, language: Language) -> str | None:
    if not note:
        return None
    if language == Language.DE:
        return note
    normalized = _normalize_for_translation(note)
    if "schwanenteich" in normalized or ("warme mahlzeiten" in normalized and "getraenk" in normalized):
        return _t(POINT_NOTE_SCHWANENTEICH, language)
    if "suppenausgabe" in normalized:
        return _t(POINT_NOTE_SOUP, language)
    if "kleine snacks" in normalized:
        return _t(POINT_NOTE_SNACKS, language)
    return None


def _normalize_for_translation(value: str) -> str:
    return value.casefold().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def _t(values: dict[str, str], language: Language) -> str:
    return values.get(language.value) or values["de"]


def _sleep_availability_hint(opening_hours: list[str], language: Language, temporal_context, request_text: str = "") -> str | None:
    if not opening_hours:
        return _t(SLEEP_TIME_CHECK, language)
    normalized_request = _normalize_for_translation(request_text)
    asks_for_time = bool(
        any(term in normalized_request for term in ("heute", "today", "tonight", "heute nacht", "jetzt"))
        or _requested_weekday_name(request_text, language, temporal_context)
    )
    day_name = _requested_weekday_name(request_text, language, temporal_context)
    start = _first_start_time(opening_hours)
    if any("ganzt" in _normalize_for_translation(value) for value in opening_hours):
        if day_name:
            return _t(
                {
                    "de": f"{day_name}: ganztägig",
                    "en": f"{day_name}: open all day",
                    "pl": f"{day_name}: cały dzień",
                    "ro": f"{day_name}: toată ziua",
                    "ru": f"{day_name}: ves den",
                },
                language,
            )
    if start:
        if day_name:
            return _t(
                {
                    "de": f"{day_name} ab {start} Uhr",
                    "en": f"{day_name} from {start}",
                    "pl": f"{day_name} od {start}",
                    "ro": f"{day_name} de la {start}",
                    "ru": f"{day_name} s {start}",
                },
                language,
            )
        if request_text and any(term in normalized_request for term in ("heute", "today", "tonight", "heute nacht", "jetzt")):
            return _t(
                {
                    "de": f"Heute ab {start} Uhr",
                    "en": f"Today from {start}",
                    "pl": f"Dzisiaj od {start}",
                    "ro": f"Azi de la {start}",
                    "ru": f"Segodnya s {start}",
                },
                language,
            )
    return _t(SLEEP_TIME_CHECK, language) if asks_for_time else None


def _requested_weekday_name(request_text: str, language: Language, temporal_context) -> str | None:
    normalized = _normalize_for_translation(request_text)
    names = [
        ("montag", {"de": "Montag", "en": "Monday", "pl": "Poniedziałek", "ro": "Luni", "ru": "Ponedelnik"}),
        ("dienstag", {"de": "Dienstag", "en": "Tuesday", "pl": "Wtorek", "ro": "Marți", "ru": "Vtornik"}),
        ("mittwoch", {"de": "Mittwoch", "en": "Wednesday", "pl": "Środa", "ro": "Miercuri", "ru": "Sreda"}),
        ("donnerstag", {"de": "Donnerstag", "en": "Thursday", "pl": "Czwartek", "ro": "Joi", "ru": "Chetverg"}),
        ("freitag", {"de": "Freitag", "en": "Friday", "pl": "Piątek", "ro": "Vineri", "ru": "Pyatnitsa"}),
        ("samstag", {"de": "Samstag", "en": "Saturday", "pl": "Sobota", "ro": "Sâmbătă", "ru": "Subbota"}),
        ("sonntag", {"de": "Sonntag", "en": "Sunday", "pl": "Niedziela", "ro": "Duminică", "ru": "Voskresene"}),
    ]
    english = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for index, (de_name, localized) in enumerate(names):
        if de_name in normalized or english[index] in normalized:
            return localized.get(language.value, localized["de"])
    if temporal_context and any(term in normalized for term in ("heute", "today", "tonight", "jetzt")):
        localized = names[temporal_context.weekday_index][1]
        return localized.get(language.value, localized["de"])
    return None


def _first_start_time(opening_hours: list[str]) -> str | None:
    for value in opening_hours:
        match = re.search(r"\b(\d{1,2})[:.](\d{2})\b", value)
        if match:
            return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    return None


def _emergency_text(language: Language) -> str:
    return {
        "de": "Akute Gefahr: Ruf sofort 112. Bei Gewalt oder Gefahr durch andere Menschen ruf 110. Bleib nicht allein.",
        "en": "Immediate danger: call 112 now. For violence or danger from another person, call 110. Do not stay alone.",
        "pl": "Bezposrednie zagrozenie: dzwon 112. Przy przemocy dzwon 110. Nie zostawaj sam.",
        "ro": "Pericol imediat: suna la 112. Pentru violenta suna la 110. Nu ramane singur.",
        "ru": "Srochnaya opasnost: zvoni 112. Pri nasilii zvoni 110. Ne ostavaysya odin.",
    }.get(language.value, "Immediate danger: call 112 now.")


def _sources(offers: list[V2Offer]) -> list[str]:
    result: list[str] = []
    for offer in offers:
        for source in [offer.source_url, *offer.detail_source_urls]:
            if source not in result:
                result.append(source)
    return result


def _last_checked(offers: list[V2Offer]) -> str | None:
    values = [offer.last_checked for offer in offers if offer.last_checked]
    return max(values) if values else None


def _evidence(offers: list[V2Offer]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for offer in offers:
        for item in offer.source_evidence[:3]:
            rows.append({"offer_id": offer.offer_id, "field_name": item.field_name, "source_url": item.source_url, "checked_at": item.checked_at})
    return rows
