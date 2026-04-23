from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_root: Path
    data_root: Path
    prompt_root: Path
    system_prompt_path: Path
    published_root: Path
    canonical_kb_path: Path
    scraper_workspace_root: Path
    scraper_published_root: Path
    scraper_raw_root: Path
    scraper_reports_root: Path
    scraper_intake_root: Path
    geo_overrides_path: Path
    runtime_root: Path
    transcripts_path: Path
    sessions_path: Path
    audio_root: Path
    source_registry: Path
    stt_provider: str
    rewrite_provider: str
    tts_provider: str
    ollama_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    piper_binary: str
    piper_voice_models: dict[str, str]
    minimum_match_threshold: float
    weak_match_threshold: float
    clarification_gap_threshold: float
    session_timeout_seconds: int
    bootstrap_runtime_from_scraper: bool
    build_qc_provider: str
    build_qc_model: str | None
    build_qc_base_url: str | None
    build_qc_api_key: str | None
    build_qc_enabled: bool
    build_geocoding_enabled: bool
    build_geocoder_url: str
    map_tile_url_template: str
    map_tile_attribution: str
    map_tile_max_zoom: int
    map_origin_id: str
    map_origin_label: str
    map_origin_address: str
    map_origin_latitude: float
    map_origin_longitude: float


def load_settings() -> Settings:
    app_root = Path(__file__).resolve().parent.parent
    data_root = app_root / "data"
    default_piper_binary = _default_piper_binary(app_root)
    default_piper_voice_models = _default_piper_voice_models(data_root)
    prompt_root = data_root / "prompts"
    raw_system_prompt_path = Path(os.getenv("LENA_SYSTEM_PROMPT_PATH", prompt_root / "system_prompt.md"))
    system_prompt_path = raw_system_prompt_path if raw_system_prompt_path.is_absolute() else app_root / raw_system_prompt_path
    published_root = data_root / "published"
    canonical_kb_path = data_root / "canonical" / "kb.sqlite3"
    scraper_workspace_root = data_root / "scraper_workspace"
    scraper_published_root = scraper_workspace_root / "published"
    scraper_raw_root = scraper_workspace_root / "raw"
    scraper_reports_root = scraper_workspace_root / "reports"
    scraper_intake_root = scraper_workspace_root / "intake"
    geo_overrides_path = data_root / "scraper_sources" / "geo_overrides.json"
    runtime_root = data_root / "runtime"
    transcripts_path = runtime_root / "transcripts.jsonl"
    sessions_path = runtime_root / "sessions.json"
    audio_root = runtime_root / "audio"
    source_registry = data_root / "scraper_sources" / "sources.json"

    runtime_root.mkdir(parents=True, exist_ok=True)
    audio_root.mkdir(parents=True, exist_ok=True)
    prompt_root.mkdir(parents=True, exist_ok=True)
    scraper_workspace_root.mkdir(parents=True, exist_ok=True)
    scraper_published_root.mkdir(parents=True, exist_ok=True)
    scraper_raw_root.mkdir(parents=True, exist_ok=True)
    scraper_reports_root.mkdir(parents=True, exist_ok=True)
    scraper_intake_root.mkdir(parents=True, exist_ok=True)
    canonical_kb_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_root=app_root,
        data_root=data_root,
        prompt_root=prompt_root,
        system_prompt_path=system_prompt_path,
        published_root=published_root,
        canonical_kb_path=canonical_kb_path,
        scraper_workspace_root=scraper_workspace_root,
        scraper_published_root=scraper_published_root,
        scraper_raw_root=scraper_raw_root,
        scraper_reports_root=scraper_reports_root,
        scraper_intake_root=scraper_intake_root,
        geo_overrides_path=geo_overrides_path,
        runtime_root=runtime_root,
        transcripts_path=transcripts_path,
        sessions_path=sessions_path,
        audio_root=audio_root,
        source_registry=source_registry,
        stt_provider=os.getenv("LENA_STT_PROVIDER", "faster_whisper"),
        rewrite_provider=os.getenv("LENA_REWRITE_PROVIDER", "ollama"),
        tts_provider=os.getenv("LENA_TTS_PROVIDER", _default_tts_provider(default_piper_binary, default_piper_voice_models)),
        ollama_url=os.getenv("LENA_OLLAMA_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("LENA_OLLAMA_MODEL", "translategemma:4b"),
        ollama_timeout_seconds=float(os.getenv("LENA_OLLAMA_TIMEOUT_SECONDS", "45")),
        piper_binary=os.getenv("LENA_PIPER_BINARY", str(default_piper_binary)),
        piper_voice_models=_load_json_mapping(os.getenv("LENA_PIPER_VOICE_MODELS", json.dumps(default_piper_voice_models))),
        minimum_match_threshold=float(os.getenv("LENA_MINIMUM_MATCH_THRESHOLD", "0.08")),
        weak_match_threshold=float(os.getenv("LENA_WEAK_MATCH_THRESHOLD", "0.18")),
        clarification_gap_threshold=float(os.getenv("LENA_CLARIFICATION_GAP_THRESHOLD", "0.03")),
        session_timeout_seconds=int(os.getenv("LENA_SESSION_TIMEOUT_SECONDS", "300")),
        bootstrap_runtime_from_scraper=os.getenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "true").lower() in {"1", "true", "yes", "on"},
        build_qc_provider=os.getenv("LENA_BUILD_QC_PROVIDER", "disabled"),
        build_qc_model=os.getenv("LENA_BUILD_QC_MODEL") or None,
        build_qc_base_url=os.getenv("LENA_BUILD_QC_BASE_URL") or None,
        build_qc_api_key=os.getenv("LENA_BUILD_QC_API_KEY") or None,
        build_qc_enabled=os.getenv("LENA_BUILD_QC_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        build_geocoding_enabled=os.getenv("LENA_BUILD_GEOCODING_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        build_geocoder_url=os.getenv("LENA_BUILD_GEOCODER_URL", "https://nominatim.openstreetmap.org/search"),
        map_tile_url_template=os.getenv("LENA_MAP_TILE_URL_TEMPLATE", "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
        map_tile_attribution=os.getenv(
            "LENA_MAP_TILE_ATTRIBUTION",
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        ),
        map_tile_max_zoom=int(os.getenv("LENA_MAP_TILE_MAX_ZOOM", "16")),
        map_origin_id=os.getenv("LENA_MAP_ORIGIN_ID", "leipzig_hbf"),
        map_origin_label=os.getenv("LENA_MAP_ORIGIN_LABEL", "Leipzig Hauptbahnhof"),
        map_origin_address=os.getenv("LENA_MAP_ORIGIN_ADDRESS", "Willy-Brandt-Platz 5, 04109 Leipzig"),
        map_origin_latitude=float(os.getenv("LENA_MAP_ORIGIN_LATITUDE", "51.3465518")),
        map_origin_longitude=float(os.getenv("LENA_MAP_ORIGIN_LONGITUDE", "12.3830858")),
    )


def _load_json_mapping(raw: str) -> dict[str, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value}


def _default_piper_binary(app_root: Path) -> Path:
    local_binary = app_root / "tools" / "piper" / "piper" / "piper.exe"
    if local_binary.exists():
        return local_binary
    return Path("piper")


def _default_piper_voice_models(data_root: Path) -> dict[str, str]:
    voices_root = data_root / "voices" / "piper"
    candidates = {
        "de": [
            "de_DE-thorsten-high.onnx",
            "de_DE-thorsten-medium.onnx",
            "de_DE-ramona-low.onnx",
            "de_DE-kerstin-low.onnx",
            "de_DE-eva_k-x_low.onnx",
        ],
        "en": ["en_GB-alan-medium.onnx"],
        "pl": ["pl_PL-darkman-medium.onnx"],
        "ro": ["ro_RO-mihai-medium.onnx"],
        "ru": ["ru_RU-ruslan-medium.onnx"],
    }
    selected: dict[str, str] = {}
    for language, filenames in candidates.items():
        for filename in filenames:
            candidate = voices_root / filename
            if candidate.exists():
                selected[language] = str(candidate)
                break
    return selected


def _default_tts_provider(piper_binary: Path, piper_voice_models: dict[str, str]) -> str:
    if piper_binary.exists() and piper_voice_models:
        return "piper"
    return "mock"
