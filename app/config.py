from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
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
    maintenance_root: Path
    maintenance_reports_root: Path
    manual_overrides_path: Path
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
    llm_base_url: str | None
    llm_api_key: str | None = field(repr=False)
    llm_model: str
    llm_timeout_seconds: float
    llm_max_tokens: int
    llm_temperature: float
    llm_fallback_provider: str
    llm_eval_mode: bool
    piper_binary: str
    piper_voice_models: dict[str, str]
    piper_voice_configs: dict[str, str]
    piper_default_voice_model: str | None
    piper_default_voice_config: str | None
    tts_normalize_umlauts: bool
    minimum_match_threshold: float
    weak_match_threshold: float
    clarification_gap_threshold: float
    session_timeout_seconds: int
    timezone: str
    bootstrap_runtime_from_scraper: bool
    build_qc_provider: str
    build_qc_model: str | None
    build_qc_base_url: str | None
    build_qc_api_key: str | None = field(repr=False)
    build_qc_enabled: bool
    maintenance_enforce_promote_review: bool
    maintenance_allow_needs_review_promote: bool
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


def load_settings(env_file: Path | None = None) -> Settings:
    app_root = Path(__file__).resolve().parent.parent
    env = _load_local_env(env_file or _default_env_path(app_root))
    data_root = app_root / "data"
    default_piper_binary = _default_piper_binary(app_root)
    default_piper_voice_models = _default_piper_voice_models(data_root)
    piper_voice_models = _load_piper_voice_models(env, default_piper_voice_models)
    piper_voice_configs = _load_piper_voice_configs(env)
    prompt_root = data_root / "prompts"
    raw_system_prompt_path = Path(env.get("LENA_SYSTEM_PROMPT_PATH", str(prompt_root / "system_prompt.md")))
    system_prompt_path = raw_system_prompt_path if raw_system_prompt_path.is_absolute() else app_root / raw_system_prompt_path
    published_root = data_root / "published"
    canonical_kb_path = data_root / "canonical" / "kb.sqlite3"
    scraper_workspace_root = data_root / "scraper_workspace"
    scraper_published_root = scraper_workspace_root / "published"
    scraper_raw_root = scraper_workspace_root / "raw"
    scraper_reports_root = scraper_workspace_root / "reports"
    scraper_intake_root = scraper_workspace_root / "intake"
    maintenance_root = data_root / "maintenance"
    maintenance_reports_root = maintenance_root / "reports"
    manual_overrides_path = maintenance_root / "manual_overrides.json"
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
    maintenance_root.mkdir(parents=True, exist_ok=True)
    maintenance_reports_root.mkdir(parents=True, exist_ok=True)
    canonical_kb_path.parent.mkdir(parents=True, exist_ok=True)

    rewrite_provider = env.get("LENA_REWRITE_PROVIDER", "ollama")
    llm_base_url = env.get("LENA_LLM_BASE_URL")
    if rewrite_provider == "blablador" and not llm_base_url:
        llm_base_url = "https://api.blablador.fz-juelich.de/v1/"

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
        maintenance_root=maintenance_root,
        maintenance_reports_root=maintenance_reports_root,
        manual_overrides_path=manual_overrides_path,
        geo_overrides_path=geo_overrides_path,
        runtime_root=runtime_root,
        transcripts_path=transcripts_path,
        sessions_path=sessions_path,
        audio_root=audio_root,
        source_registry=source_registry,
        stt_provider=env.get("LENA_STT_PROVIDER", "faster_whisper"),
        rewrite_provider=rewrite_provider,
        tts_provider=env.get("LENA_TTS_PROVIDER", _default_tts_provider(default_piper_binary, default_piper_voice_models)),
        ollama_url=env.get("LENA_OLLAMA_URL", "http://127.0.0.1:11434"),
        ollama_model=env.get("LENA_OLLAMA_MODEL", "translategemma:4b"),
        ollama_timeout_seconds=float(env.get("LENA_OLLAMA_TIMEOUT_SECONDS", "45")),
        llm_base_url=llm_base_url,
        llm_api_key=env.get("LENA_LLM_API_KEY") or None,
        llm_model=env.get("LENA_LLM_MODEL", "alias-large"),
        llm_timeout_seconds=float(env.get("LENA_LLM_TIMEOUT_SECONDS", "60")),
        llm_max_tokens=int(env.get("LENA_LLM_MAX_TOKENS", "800")),
        llm_temperature=float(env.get("LENA_LLM_TEMPERATURE", "0")),
        llm_fallback_provider=env.get("LENA_LLM_FALLBACK_PROVIDER", "template"),
        llm_eval_mode=env.get("LENA_LLM_EVAL_MODE", "false").lower() in {"1", "true", "yes", "on"},
        piper_binary=env.get("LENA_PIPER_BINARY", str(default_piper_binary)),
        piper_voice_models=piper_voice_models,
        piper_voice_configs=piper_voice_configs,
        piper_default_voice_model=env.get("LENA_PIPER_DEFAULT_VOICE") or piper_voice_models.get("default"),
        piper_default_voice_config=env.get("LENA_PIPER_DEFAULT_VOICE_CONFIG") or piper_voice_configs.get("default"),
        tts_normalize_umlauts=env.get("LENA_TTS_NORMALIZE_UMLAUTS", "false").lower() in {"1", "true", "yes", "on"},
        minimum_match_threshold=float(env.get("LENA_MINIMUM_MATCH_THRESHOLD", "0.08")),
        weak_match_threshold=float(env.get("LENA_WEAK_MATCH_THRESHOLD", "0.18")),
        clarification_gap_threshold=float(env.get("LENA_CLARIFICATION_GAP_THRESHOLD", "0.03")),
        session_timeout_seconds=int(env.get("LENA_SESSION_TIMEOUT_SECONDS", "300")),
        timezone=env.get("LENA_TIMEZONE", "Europe/Berlin"),
        bootstrap_runtime_from_scraper=env.get("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "true").lower() in {"1", "true", "yes", "on"},
        build_qc_provider=env.get("LENA_BUILD_QC_PROVIDER", "disabled"),
        build_qc_model=env.get("LENA_BUILD_QC_MODEL") or None,
        build_qc_base_url=env.get("LENA_BUILD_QC_BASE_URL") or None,
        build_qc_api_key=env.get("LENA_BUILD_QC_API_KEY") or None,
        build_qc_enabled=env.get("LENA_BUILD_QC_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        maintenance_enforce_promote_review=env.get("LENA_MAINTENANCE_ENFORCE_PROMOTE_REVIEW", "true").lower() in {"1", "true", "yes", "on"},
        maintenance_allow_needs_review_promote=env.get("LENA_MAINTENANCE_ALLOW_NEEDS_REVIEW_PROMOTE", "false").lower() in {"1", "true", "yes", "on"},
        build_geocoding_enabled=env.get("LENA_BUILD_GEOCODING_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
        build_geocoder_url=env.get("LENA_BUILD_GEOCODER_URL", "https://nominatim.openstreetmap.org/search"),
        map_tile_url_template=env.get("LENA_MAP_TILE_URL_TEMPLATE", "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
        map_tile_attribution=env.get(
            "LENA_MAP_TILE_ATTRIBUTION",
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        ),
        map_tile_max_zoom=int(env.get("LENA_MAP_TILE_MAX_ZOOM", "16")),
        map_origin_id=env.get("LENA_MAP_ORIGIN_ID", "leipzig_hbf"),
        map_origin_label=env.get("LENA_MAP_ORIGIN_LABEL", "Leipzig Hauptbahnhof"),
        map_origin_address=env.get("LENA_MAP_ORIGIN_ADDRESS", "Willy-Brandt-Platz 5, 04109 Leipzig"),
        map_origin_latitude=float(env.get("LENA_MAP_ORIGIN_LATITUDE", "51.3465518")),
        map_origin_longitude=float(env.get("LENA_MAP_ORIGIN_LONGITUDE", "12.3830858")),
    )


def _load_json_mapping(raw: str) -> dict[str, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value}


def _load_piper_voice_models(env: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    voices = _load_json_mapping(env.get("LENA_PIPER_VOICE_MODELS", json.dumps(defaults)))
    for language in _supported_piper_languages():
        value = env.get(f"LENA_PIPER_VOICE_{language.upper()}")
        if value:
            voices[language] = value
    default_voice = env.get("LENA_PIPER_DEFAULT_VOICE")
    if default_voice:
        voices["default"] = default_voice
    return voices


def _load_piper_voice_configs(env: dict[str, str]) -> dict[str, str]:
    configs = _load_json_mapping(env.get("LENA_PIPER_VOICE_CONFIGS", "{}"))
    for language in _supported_piper_languages():
        value = env.get(f"LENA_PIPER_VOICE_CONFIG_{language.upper()}")
        if value:
            configs[language] = value
    default_config = env.get("LENA_PIPER_DEFAULT_VOICE_CONFIG")
    if default_config:
        configs["default"] = default_config
    return configs


def _supported_piper_languages() -> tuple[str, ...]:
    return ("de", "en", "pl", "ro", "ru")


def _default_env_path(app_root: Path) -> Path:
    configured = os.getenv("LENA_ENV_FILE")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else app_root / path
    return app_root / ".env"


def _load_local_env(path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if not path.exists():
        return env
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return env
    for line in lines:
        parsed = _parse_env_line(line)
        if not parsed:
            continue
        key, value = parsed
        env.setdefault(key, value)
    return env


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = _strip_inline_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
        if line.strip().split("=", 1)[1].strip().startswith('"'):
            value = value.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
    return key, value


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value


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
