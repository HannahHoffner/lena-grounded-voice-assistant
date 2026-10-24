"""Lädt die datei- und umgebungsbasierte Laufzeitkonfiguration von LENA.

Priorität (niedrig nach hoch): eingebaute Defaults < ``.env`` < ``.env.local``
< Prozessumgebung. Eine CLI-Option wie ``--rewrite-provider`` setzt die
Prozessumgebung und gewinnt deshalb immer. Die lokalen Dateien werden nur im
Checkout gesucht, nicht im aktuellen Arbeitsverzeichnis einer Wheel-
Installation, und mit ``LENA_ENV_FILE_MODE=disabled`` vollständig ignoriert.
Die Prozessumgebung wird beim Laden nicht verändert.

Externe Dienste besitzen explizite Profile (``REWRITE_PROVIDER``,
``SPEECH_TRANSCRIPTION_PROVIDER``, ``SPEECH_SYNTHESIS_PROVIDER``,
``MAP_PROVIDER``). Kein Profil übernimmt stillschweigend Zugangsdaten eines
anderen Dienstes. Ungültige Werte und nicht unterstützte Variablennamen werden
als ``configuration_warnings`` (nur Variablennamen, nie Werte) gemeldet.
Das Modul protokolliert oder überträgt keine Geheimnisse.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from contextvars import ContextVar
from pathlib import Path

from .resources import bootstrap_data_root, checkout_root, packaged_bootstrap_data_root
from .spatial import is_valid_leipzig_coordinate

LLM_PROVIDERS = frozenset({"template", "blablador"})
TRANSCRIPTION_PROVIDERS = frozenset({"disabled", "blablador", "openai"})
SYNTHESIS_PROVIDERS = frozenset({"disabled", "edge", "openai"})
MAP_PROVIDERS = frozenset({"osm", "disabled"})
# Auf dem Blablador-Endpunkt registrierte STT-Kennung (GET /v1/models,
# geprüft 14.08. und 23.10.2026). "whisper-large-v3" existiert dort nicht.
BLABLADOR_TRANSCRIPTION_MODEL = "faster-whisper-large-v3"
# Früher dokumentierte oder lokal verwendete Namen ohne Leser im Code. Sie
# werden gemeldet statt still ignoriert (Audit C-27).
UNSUPPORTED_VARIABLES = ("LENA_LLM_TEMPERATURE", "LENA_LLM_FALLBACK_PROVIDER")

_ENVIRONMENT: ContextVar[dict[str, str] | None] = ContextVar("lena_configuration", default=None)


def _getenv(name: str, default: str | None = None) -> str | None:
    values = _ENVIRONMENT.get()
    return (os.environ if values is None else values).get(name, default)


@dataclass(frozen=True)
class Settings:
    """Unveränderliche, validierte Konfiguration aller Laufzeitkomponenten."""
    app_root: Path
    kb_path: Path
    rewrite_provider: str
    blablador_base_url: str | None
    blablador_api_key: str | None
    blablador_model: str | None
    blablador_timeout_seconds: float
    blablador_max_context_chars: int
    blablador_max_tokens: int = 1200
    blablador_interpreter_model: str | None = None
    blablador_selector_model: str | None = None
    blablador_formulator_model: str | None = None
    session_timeout_seconds: int = 180
    session_max_entries: int = 500
    query_max_chars: int = 1000
    speech_transcription_max_bytes: int = 10 * 1024 * 1024
    speech_synthesis_max_chars: int = 4000
    speech_transcription_base_url: str | None = None
    speech_transcription_api_key: str | None = None
    speech_transcription_model: str | None = None
    speech_transcription_timeout_seconds: float = 45.0
    # None = aus den Werten abgeleitet: eigene STT-Werte wählen "openai",
    # sonst "disabled". "blablador" übernimmt den LLM-Zugang nur ausdrücklich.
    speech_transcription_provider: str | None = None
    speech_synthesis_base_url: str | None = None
    speech_synthesis_api_key: str | None = None
    speech_synthesis_model: str | None = None
    # None = aus den Werten abgeleitet: eigene TTS-Werte wählen "openai",
    # sonst "disabled". Edge-TTS ist ein eigener externer Dienst und wird nur
    # ausdrücklich gewählt.
    speech_synthesis_provider: str | None = None
    speech_synthesis_voice: str = "alloy"
    speech_synthesis_response_format: str = "mp3"
    speech_synthesis_timeout_seconds: float = 45.0
    wfs_url: str = "https://geodienste.leipzig.de/l3/OpenData/wohnungslosenhilfe/wfs"
    wfs_auto_sync: bool = False
    wfs_auto_promote: bool = False
    wfs_check_interval_hours: float = 24.0
    llm_interpreter_timeout_seconds: float = 15.0
    llm_selector_timeout_seconds: float = 10.0
    llm_formulator_timeout_seconds: float = 30.0
    llm_request_budget_seconds: float = 45.0
    translation_runtime_policy: str = "reviewed_or_machine"
    wfs_connect_timeout_seconds: float = 10.0
    wfs_read_timeout_seconds: float = 30.0
    toilet_source_url: str = (
        "https://geodaten.leipzig.de/open_data/organisationseinheit/"
        "Amt_fuer_Geoinformation_und_Bodenordnung/Toilettenstandorte/"
        "Oeffentliche_Toiletten_Stadt_Leipzig.csv"
    )
    toilet_auto_sync: bool = False
    toilet_auto_promote: bool = False
    toilet_check_interval_seconds: int = 86_400
    toilet_connect_timeout_seconds: float = 10.0
    toilet_read_timeout_seconds: float = 30.0
    drinking_fountain_source_url: str = (
        "https://www.google.com/maps/d/kml?"
        "mid=1X3y_V9KdgtfsEucc4T-tmNV_hYe8rdEP&forcekml=1"
    )
    drinking_fountain_source_page_url: str = (
        "https://www.l.de/wasserwerke/leipziger-wasser/trinkwasserbrunnen/"
    )
    drinking_fountain_boundary_url: str = (
        "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/"
        "02.1_Dez1_Allgemeine_Verwaltung/12_Statistik_und_Wahlen/Geodaten/"
        "StatistischeBezirke_Leipzig_UTM33N.json"
    )
    drinking_fountain_auto_sync: bool = False
    drinking_fountain_auto_promote: bool = False
    drinking_fountain_check_interval_seconds: int = 86_400
    drinking_fountain_connect_timeout_seconds: float = 10.0
    drinking_fountain_read_timeout_seconds: float = 30.0
    hbf_latitude: float = 51.34556
    hbf_longitude: float = 12.38222
    map_provider: str = "osm"
    technical_log_level: str = "INFO"
    interaction_logging_enabled: bool = False
    interaction_log_path: Path | None = None
    bootstrap_data_dir: Path | None = None
    data_dir: Path | None = None
    runtime_dir: Path | None = None
    curation_path: Path | None = None
    configuration_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Verhindert nicht positive oder nicht endliche Laufzeitgrenzen."""
        object.__setattr__(self, "bootstrap_data_dir", self.bootstrap_data_dir or self.app_root / "data")
        object.__setattr__(self, "data_dir", self.data_dir or self.app_root / "data")
        object.__setattr__(self, "runtime_dir", self.runtime_dir or self.app_root / "runtime")
        if self.speech_transcription_provider is None:
            object.__setattr__(self, "speech_transcription_provider", "openai" if (
                self.speech_transcription_base_url or self.speech_transcription_api_key
                or self.speech_transcription_model
            ) else "disabled")
        if self.speech_synthesis_provider is None:
            object.__setattr__(self, "speech_synthesis_provider", "openai" if (
                self.speech_synthesis_base_url or self.speech_synthesis_api_key or self.speech_synthesis_model
            ) else "disabled")
        if self.map_provider not in MAP_PROVIDERS:
            raise ValueError("MAP_PROVIDER must be osm or disabled")
        if self.speech_transcription_provider not in TRANSCRIPTION_PROVIDERS:
            raise ValueError("SPEECH_TRANSCRIPTION_PROVIDER must be disabled, blablador or openai")
        if self.speech_synthesis_provider not in SYNTHESIS_PROVIDERS:
            raise ValueError("SPEECH_SYNTHESIS_PROVIDER must be disabled, edge or openai")
        if self.toilet_auto_promote:
            raise ValueError("TOILET_AUTO_PROMOTE is not supported in the prototype")
        if self.drinking_fountain_auto_promote:
            raise ValueError("DRINKING_FOUNTAIN_AUTO_PROMOTE is not supported in the prototype")
        timeout_fields = (
            "blablador_timeout_seconds",
            "speech_transcription_timeout_seconds",
            "speech_synthesis_timeout_seconds",
            "llm_interpreter_timeout_seconds",
            "llm_selector_timeout_seconds",
            "llm_formulator_timeout_seconds",
            "llm_request_budget_seconds",
            "wfs_connect_timeout_seconds",
            "wfs_read_timeout_seconds",
            "toilet_connect_timeout_seconds",
            "toilet_read_timeout_seconds",
            "drinking_fountain_connect_timeout_seconds",
            "drinking_fountain_read_timeout_seconds",
        )
        for field_name in timeout_fields:
            value = getattr(self, field_name)
            try:
                valid = math.isfinite(value) and value > 0
            except TypeError:
                valid = False
            if not valid:
                raise ValueError(f"{field_name} must be a positive finite number")
        for field_name in (
            "session_timeout_seconds",
            "session_max_entries",
            "toilet_check_interval_seconds",
            "drinking_fountain_check_interval_seconds",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if not is_valid_leipzig_coordinate(self.hbf_latitude, self.hbf_longitude):
            raise ValueError("hbf_latitude/hbf_longitude must be a valid Leipzig-area coordinate")
        if self.translation_runtime_policy not in {
            "reviewed_only",
            "reviewed_or_machine",
            "source_language_fallback",
        }:
            raise ValueError("translation_runtime_policy is invalid")

    @property
    def blablador_configured(self) -> bool:
        return bool(
            self.rewrite_provider == "blablador"
            and self.blablador_base_url
            and self.blablador_api_key
            and self.blablador_model
        )

    @property
    def effective_interpreter_model(self) -> str | None:
        """Modell, das ``BlabladorProvider`` für die Interpreterstufe tatsächlich sendet."""
        return self.blablador_interpreter_model or self.blablador_model

    @property
    def effective_selector_model(self) -> str | None:
        """Modell, das ``BlabladorProvider`` für die Selectorstufe tatsächlich sendet."""
        return self.blablador_selector_model or self.blablador_model

    @property
    def effective_formulator_model(self) -> str | None:
        """Modell, das ``BlabladorProvider`` für die Formulatorstufe tatsächlich sendet."""
        return self.blablador_formulator_model or self.blablador_model

    @property
    def speech_transcription_configured(self) -> bool:
        return bool(
            self.speech_transcription_provider != "disabled"
            and self.speech_transcription_base_url
            and self.speech_transcription_api_key
            and self.speech_transcription_model
        )

    @property
    def speech_synthesis_configured(self) -> bool:
        if self.speech_synthesis_provider == "edge":
            return True
        return bool(
            self.speech_synthesis_provider == "openai"
            and self.speech_synthesis_base_url
            and self.speech_synthesis_api_key
            and self.speech_synthesis_model
        )


def _optional_env(*names: str) -> str | None:
    for name in names:
        value = _getenv(name, "").strip()
        if value:
            return value
    return None


def _load_env_file(path: Path) -> dict[str, str]:
    """Read local configuration without changing the process environment."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip():
            values[name.strip()] = value.strip().strip('"').strip("'")
    return values



def _env_bool(name: str, default: bool) -> bool:
    value = _getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        value = float(_getenv(name, str(default)))
    except ValueError:
        return default
    if not math.isfinite(value) or value < minimum:
        return default
    return value


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """Liest einen Integer und begrenzt ihn auf den sicheren Betriebsbereich."""
    try:
        value = int(_getenv(name, str(default)))
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _hbf_coordinates(default_latitude: float, default_longitude: float) -> tuple[float, float]:
    """Liest die Hbf-Referenzkoordinate atomar; ungültige oder unvollständige Werte fallen auf den Standard zurück."""
    raw_latitude = _optional_env("HBF_LATITUDE")
    raw_longitude = _optional_env("HBF_LONGITUDE")
    if raw_latitude is None or raw_longitude is None:
        return default_latitude, default_longitude
    try:
        latitude = float(raw_latitude)
        longitude = float(raw_longitude)
    except ValueError:
        return default_latitude, default_longitude
    if not is_valid_leipzig_coordinate(latitude, longitude):
        return default_latitude, default_longitude
    return latitude, longitude


def _default_external_root() -> Path:
    """Bestimmt ohne Zusatzabhängigkeit eine benutzerspezifische Datenwurzel."""
    local_app_data = _getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).expanduser().resolve() / "LENA"
    return Path.home().resolve() / ".local" / "share" / "lena"


def _configured_path(name: str, default: Path) -> Path:
    value = _getenv(name, "").strip()
    if not value:
        return default.resolve()
    path = Path(value).expanduser()
    return (path if path.is_absolute() else Path.cwd() / path).resolve()


def load_settings() -> Settings:
    """Löst Defaults < .env < .env.local < Prozessumgebung ohne globale Mutation auf."""
    app_root = (checkout_root() or _default_external_root()).resolve()
    values: dict[str, str] = {}
    if os.getenv("LENA_ENV_FILE_MODE", "enabled").strip().casefold() != "disabled":
        for filename in (".env", ".env.local"):
            values.update(_load_env_file(app_root / filename) or {})
    values.update(os.environ)
    token = _ENVIRONMENT.set(values)
    try:
        return _settings_from_environment(app_root)
    finally:
        _ENVIRONMENT.reset(token)


def _choice(
    names: tuple[str, ...], allowed: frozenset[str], default: str, warnings: list[str],
) -> str:
    """Liest ein Profil; ungültige Werte fallen auf den sicheren Default zurück."""
    raw = _optional_env(*names)
    if raw is None:
        return default
    value = raw.casefold()
    if value not in allowed:
        warnings.append(f"invalid_value:{names[0]}")
        return default
    return value


def _settings_from_environment(app_root: Path) -> Settings:
    warnings: list[str] = [
        f"unsupported_variable:{name}" for name in UNSUPPORTED_VARIABLES if _getenv(name) is not None
    ]
    bootstrap_root = bootstrap_data_root()
    runtime_dir = _configured_path("LENA_RUNTIME_DIR", app_root / "runtime")
    data_dir = _configured_path("LENA_DATA_DIR", app_root / "data")
    external_curation = data_dir / "curation" / "social_offers.json"
    bootstrap_curation = bootstrap_root / "curation" / "social_offers.json"
    if not bootstrap_curation.is_file():
        bootstrap_curation = packaged_bootstrap_data_root() / "curation" / "social_offers.json"
    default_curation = external_curation if external_curation.is_file() else bootstrap_curation

    provider = _choice(("REWRITE_PROVIDER", "LENA_REWRITE_PROVIDER"), LLM_PROVIDERS, "template", warnings)

    legacy_llm_timeout = _optional_env("BLABLADOR_TIMEOUT_SECONDS", "LENA_LLM_TIMEOUT_SECONDS")
    try:
        timeout = float(legacy_llm_timeout or "30")
        if not math.isfinite(timeout) or timeout < 1.0:
            raise ValueError
    except ValueError:
        timeout = 30.0
    interpreter_timeout_default = timeout if legacy_llm_timeout else 15.0
    interpreter_timeout_raw = _optional_env(
        "LLM_INTERPRETER_TIMEOUT_SECONDS",
    )
    try:
        llm_interpreter_timeout = float(interpreter_timeout_raw or interpreter_timeout_default)
        if not math.isfinite(llm_interpreter_timeout) or llm_interpreter_timeout < 0.1:
            raise ValueError
    except ValueError:
        llm_interpreter_timeout = interpreter_timeout_default
    llm_formulator_timeout = _env_float(
        "LLM_FORMULATOR_TIMEOUT_SECONDS",
        timeout if legacy_llm_timeout else 30.0,
        0.1,
    )
    try:
        max_context_chars = max(10000, int(_getenv("BLABLADOR_MAX_CONTEXT_CHARS", "50000")))
    except ValueError:
        max_context_chars = 50000
    try:
        max_tokens = max(
            200,
            int(_optional_env("BLABLADOR_MAX_TOKENS", "LENA_LLM_MAX_TOKENS") or "1200"),
        )
    except ValueError:
        max_tokens = 1200
    try:
        session_timeout_seconds = max(
            1,
            int(_optional_env("SESSION_TIMEOUT_SECONDS", "LENA_SESSION_TIMEOUT_SECONDS") or "180"),
        )
    except ValueError:
        session_timeout_seconds = 180
    try:
        speech_timeout = float(
            _optional_env("STT_TIMEOUT_SECONDS", "SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS", "LENA_STT_TIMEOUT_SECONDS")
            or "45"
        )
        if not math.isfinite(speech_timeout) or speech_timeout < 0.1:
            raise ValueError
    except ValueError:
        speech_timeout = 45.0
    speech_base_url = _optional_env("SPEECH_TRANSCRIPTION_BASE_URL", "LENA_STT_BASE_URL")
    speech_api_key = _optional_env("SPEECH_TRANSCRIPTION_API_KEY", "LENA_STT_API_KEY")
    speech_model = _optional_env("SPEECH_TRANSCRIPTION_MODEL", "LENA_STT_MODEL")
    try:
        synthesis_timeout = float(
            _optional_env("TTS_TIMEOUT_SECONDS", "SPEECH_SYNTHESIS_TIMEOUT_SECONDS", "LENA_TTS_TIMEOUT_SECONDS")
            or "45"
        )
        if not math.isfinite(synthesis_timeout) or synthesis_timeout < 0.1:
            raise ValueError
    except ValueError:
        synthesis_timeout = 45.0
    synthesis_base_url = _optional_env("SPEECH_SYNTHESIS_BASE_URL", "LENA_TTS_BASE_URL")
    synthesis_api_key = _optional_env("SPEECH_SYNTHESIS_API_KEY", "LENA_TTS_API_KEY")
    synthesis_model = _optional_env("SPEECH_SYNTHESIS_MODEL", "LENA_TTS_MODEL")
    synthesis_provider = _choice(
        ("SPEECH_SYNTHESIS_PROVIDER", "LENA_TTS_PROVIDER"),
        SYNTHESIS_PROVIDERS,
        "openai" if synthesis_base_url or synthesis_api_key or synthesis_model else "disabled",
        warnings,
    )
    transcription_provider = _choice(
        ("SPEECH_TRANSCRIPTION_PROVIDER", "LENA_STT_PROVIDER"),
        TRANSCRIPTION_PROVIDERS,
        "openai" if speech_base_url or speech_api_key or speech_model else "disabled",
        warnings,
    )
    if transcription_provider == "blablador":
        # Ausdrücklich gewählte Wiederverwendung des LLM-Zugangs; eigene
        # STT-Werte haben Vorrang, das Modell hat einen geprüften Default.
        speech_base_url = speech_base_url or _optional_env("BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL")
        speech_api_key = speech_api_key or _optional_env("BLABLADOR_API_KEY", "LENA_LLM_API_KEY")
        speech_model = speech_model or BLABLADOR_TRANSCRIPTION_MODEL
    map_provider = _choice(("MAP_PROVIDER",), MAP_PROVIDERS, "osm", warnings)
    technical_log_level = (_optional_env("TECHNICAL_LOG_LEVEL") or "INFO").upper()
    if technical_log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        warnings.append("invalid_value:TECHNICAL_LOG_LEVEL")
        technical_log_level = "INFO"
    configured_interaction_path = _optional_env("INTERACTION_LOG_PATH")
    hbf_latitude, hbf_longitude = _hbf_coordinates(51.34556, 12.38222)

    return Settings(
        app_root=app_root,
        kb_path=Path(
            _optional_env("LENA_KB_PATH")
            or bootstrap_root / "canonical" / "offers.json"
        ),
        rewrite_provider=provider,
        blablador_base_url=_optional_env("BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL"),
        blablador_api_key=_optional_env("BLABLADOR_API_KEY", "LENA_LLM_API_KEY"),
        blablador_model=_optional_env("BLABLADOR_MODEL", "LENA_LLM_MODEL"),
        blablador_timeout_seconds=timeout,
        blablador_max_context_chars=max_context_chars,
        blablador_max_tokens=max_tokens,
        # Per-stage model overrides. Unset -> BlabladorProvider falls back to blablador_model.
        # Lets strict-JSON stages (interpreter/selector) use a faster/cheaper model while the
        # formulator keeps a larger model for answer quality, without a shared timeout/model tradeoff.
        blablador_interpreter_model=_optional_env("BLABLADOR_INTERPRETER_MODEL"),
        blablador_selector_model=_optional_env("BLABLADOR_SELECTOR_MODEL"),
        blablador_formulator_model=_optional_env("BLABLADOR_FORMULATOR_MODEL"),
        session_timeout_seconds=session_timeout_seconds,
        session_max_entries=_env_int("SESSION_MAX_ENTRIES", 500, 1, 100_000),
        query_max_chars=_env_int("QUERY_MAX_CHARS", 1000, 1, 10_000),
        speech_transcription_max_bytes=_env_int(
            "SPEECH_TRANSCRIPTION_MAX_BYTES",
            10 * 1024 * 1024,
            1024,
            25 * 1024 * 1024,
        ),
        speech_synthesis_max_chars=_env_int(
            "SPEECH_SYNTHESIS_MAX_CHARS",
            4000,
            1,
            20_000,
        ),
        speech_transcription_base_url=speech_base_url,
        speech_transcription_api_key=speech_api_key,
        speech_transcription_model=speech_model,
        speech_transcription_timeout_seconds=speech_timeout,
        speech_transcription_provider=transcription_provider,
        speech_synthesis_base_url=synthesis_base_url,
        speech_synthesis_api_key=synthesis_api_key,
        speech_synthesis_model=synthesis_model,
        speech_synthesis_provider=synthesis_provider,
        speech_synthesis_voice=_optional_env("SPEECH_SYNTHESIS_VOICE", "LENA_TTS_VOICE") or "alloy",
        speech_synthesis_response_format=(
            _optional_env("SPEECH_SYNTHESIS_RESPONSE_FORMAT", "LENA_TTS_RESPONSE_FORMAT") or "mp3"
        ),
        speech_synthesis_timeout_seconds=synthesis_timeout,
        wfs_url=(
            _optional_env("WFS_URL")
            or "https://geodienste.leipzig.de/l3/OpenData/wohnungslosenhilfe/wfs"
        ),
        wfs_auto_sync=_env_bool("WFS_AUTO_SYNC", False),
        wfs_auto_promote=_env_bool("WFS_AUTO_PROMOTE", False),
        wfs_check_interval_hours=_env_float("WFS_CHECK_INTERVAL_HOURS", 24.0, 1.0),
        llm_interpreter_timeout_seconds=llm_interpreter_timeout,
        llm_selector_timeout_seconds=_env_float("LLM_SELECTOR_TIMEOUT_SECONDS", 10.0, 0.1),
        llm_formulator_timeout_seconds=llm_formulator_timeout,
        llm_request_budget_seconds=_env_float("LLM_REQUEST_BUDGET_SECONDS", 45.0, 0.1),
        translation_runtime_policy=(
            _optional_env("TRANSLATION_RUNTIME_POLICY") or "reviewed_or_machine"
        ).casefold(),
        wfs_connect_timeout_seconds=_env_float("WFS_CONNECT_TIMEOUT_SECONDS", 10.0, 0.1),
        wfs_read_timeout_seconds=_env_float("WFS_READ_TIMEOUT_SECONDS", 30.0, 0.1),
        toilet_source_url=(
            _optional_env("TOILET_SOURCE_URL")
            or "https://geodaten.leipzig.de/open_data/organisationseinheit/"
            "Amt_fuer_Geoinformation_und_Bodenordnung/Toilettenstandorte/"
            "Oeffentliche_Toiletten_Stadt_Leipzig.csv"
        ),
        toilet_auto_sync=_env_bool("TOILET_AUTO_SYNC", False),
        toilet_auto_promote=_env_bool("TOILET_AUTO_PROMOTE", False),
        toilet_check_interval_seconds=_env_int(
            "TOILET_SYNC_INTERVAL_SECONDS",
            _env_int("TOILET_INTERVAL_SECONDS", 86_400, 300, 31_536_000),
            300,
            31_536_000,
        ),
        toilet_connect_timeout_seconds=_env_float("TOILET_CONNECT_TIMEOUT_SECONDS", 10.0, 0.1),
        toilet_read_timeout_seconds=_env_float("TOILET_READ_TIMEOUT_SECONDS", 30.0, 0.1),
        drinking_fountain_source_url=(
            _optional_env("DRINKING_FOUNTAIN_SOURCE_URL")
            or "https://www.google.com/maps/d/kml?"
            "mid=1X3y_V9KdgtfsEucc4T-tmNV_hYe8rdEP&forcekml=1"
        ),
        drinking_fountain_source_page_url=(
            _optional_env("DRINKING_FOUNTAIN_SOURCE_PAGE_URL")
            or "https://www.l.de/wasserwerke/leipziger-wasser/trinkwasserbrunnen/"
        ),
        drinking_fountain_boundary_url=(
            _optional_env("DRINKING_FOUNTAIN_BOUNDARY_URL")
            or "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/"
            "02.1_Dez1_Allgemeine_Verwaltung/12_Statistik_und_Wahlen/Geodaten/"
            "StatistischeBezirke_Leipzig_UTM33N.json"
        ),
        drinking_fountain_auto_sync=_env_bool("DRINKING_FOUNTAIN_AUTO_SYNC", False),
        drinking_fountain_auto_promote=_env_bool("DRINKING_FOUNTAIN_AUTO_PROMOTE", False),
        drinking_fountain_check_interval_seconds=_env_int(
            "DRINKING_FOUNTAIN_SYNC_INTERVAL_SECONDS",
            86_400,
            300,
            31_536_000,
        ),
        drinking_fountain_connect_timeout_seconds=_env_float(
            "DRINKING_FOUNTAIN_CONNECT_TIMEOUT_SECONDS", 10.0, 0.1
        ),
        drinking_fountain_read_timeout_seconds=_env_float(
            "DRINKING_FOUNTAIN_READ_TIMEOUT_SECONDS", 30.0, 0.1
        ),
        hbf_latitude=hbf_latitude,
        hbf_longitude=hbf_longitude,
        map_provider=map_provider,
        technical_log_level=technical_log_level,
        interaction_logging_enabled=_env_bool("INTERACTION_LOGGING_ENABLED", False),
        interaction_log_path=(
            Path(configured_interaction_path)
            if configured_interaction_path and Path(configured_interaction_path).is_absolute()
            else runtime_dir
            / (
                configured_interaction_path.removeprefix("runtime/").removeprefix("runtime\\")
                if configured_interaction_path
                else "logs/interactions.jsonl"
            )
        ),
        bootstrap_data_dir=bootstrap_root,
        data_dir=data_dir,
        runtime_dir=runtime_dir,
        curation_path=_configured_path("LENA_CURATION_PATH", default_curation),
        configuration_warnings=tuple(dict.fromkeys(warnings)),
    )
