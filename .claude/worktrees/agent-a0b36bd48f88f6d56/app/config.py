"""Lädt die datei- und umgebungsbasierte Laufzeitkonfiguration von LENA.

Lokale Werte werden aus ``.env`` und anschließend mit höherer Priorität aus
``.env.local`` gelesen. Das Modul protokolliert oder überträgt keine Geheimnisse.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

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
    session_timeout_seconds: int = 180
    speech_transcription_base_url: str | None = None
    speech_transcription_api_key: str | None = None
    speech_transcription_model: str | None = None
    speech_transcription_timeout_seconds: float = 45.0
    speech_synthesis_base_url: str | None = None
    speech_synthesis_api_key: str | None = None
    speech_synthesis_model: str | None = None
    speech_synthesis_provider: str = "edge"
    speech_synthesis_voice: str = "alloy"
    speech_synthesis_response_format: str = "mp3"
    speech_synthesis_timeout_seconds: float = 45.0
    wfs_url: str = "https://geodienste.leipzig.de/l3/OpenData/wohnungslosenhilfe/wfs"
    wfs_auto_sync: bool = False
    wfs_auto_promote: bool = False
    wfs_check_interval_hours: float = 24.0

    @property
    def blablador_configured(self) -> bool:
        return bool(
            self.rewrite_provider == "blablador"
            and self.blablador_base_url
            and self.blablador_api_key
            and self.blablador_model
        )

    @property
    def speech_transcription_configured(self) -> bool:
        return bool(
            self.speech_transcription_base_url
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
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            if override:
                os.environ[name] = value
            else:
                os.environ.setdefault(name, value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _resolve_app_root() -> Path:
    """Ermittelt den Root für Konfiguration und versionierte Laufzeitdaten.

    Im Checkout liegen Paket und ``data`` unter demselben Projekt-Root. Ein
    Wheel installiert das Paket dagegen nach ``site-packages`` und die bewusst
    veränderbaren Fachdateien unter das Präfix der virtuellen Umgebung. Der
    Präfix-Fallback wird nur verwendet, wenn dort die kanonische Wissensbasis
    tatsächlich vorhanden ist.
    """
    checkout_root = Path(__file__).resolve().parents[1]
    if (checkout_root / "data" / "canonical" / "offers.json").is_file():
        return checkout_root

    installed_root = Path(sys.prefix).resolve()
    if (installed_root / "data" / "canonical" / "offers.json").is_file():
        return installed_root
    return checkout_root


def load_settings() -> Settings:
    """Lädt Einstellungen und wendet sichere Standards und Untergrenzen an.

    Returns:
        Vollständig aufgelöste Einstellungen mit absoluten Projektpfaden.

    Side Effects:
        Lädt Werte aus ``.env`` und ``.env.local`` in ``os.environ``.
    """
    app_root = _resolve_app_root()
    _load_env_file(app_root / ".env")
    _load_env_file(app_root / ".env.local", override=True)

    provider = (_optional_env("REWRITE_PROVIDER", "LENA_REWRITE_PROVIDER") or "template").lower()
    if provider not in {"template", "blablador"}:
        provider = "template"

    try:
        timeout = max(
            1.0,
            float(_optional_env("BLABLADOR_TIMEOUT_SECONDS", "LENA_LLM_TIMEOUT_SECONDS") or "30"),
        )
    except ValueError:
        timeout = 30.0
    try:
        max_context_chars = max(10000, int(os.getenv("BLABLADOR_MAX_CONTEXT_CHARS", "50000")))
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
            30,
            int(_optional_env("SESSION_TIMEOUT_SECONDS", "LENA_SESSION_TIMEOUT_SECONDS") or "180"),
        )
    except ValueError:
        session_timeout_seconds = 180
    try:
        speech_timeout = max(
            5.0,
            float(_optional_env("SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS", "LENA_STT_TIMEOUT_SECONDS") or "45"),
        )
    except ValueError:
        speech_timeout = 45.0
    speech_base_url = _optional_env("SPEECH_TRANSCRIPTION_BASE_URL", "LENA_STT_BASE_URL")
    speech_api_key = _optional_env("SPEECH_TRANSCRIPTION_API_KEY", "LENA_STT_API_KEY")
    speech_model = _optional_env("SPEECH_TRANSCRIPTION_MODEL", "LENA_STT_MODEL")
    try:
        synthesis_timeout = max(
            5.0,
            float(_optional_env("SPEECH_SYNTHESIS_TIMEOUT_SECONDS", "LENA_TTS_TIMEOUT_SECONDS") or "45"),
        )
    except ValueError:
        synthesis_timeout = 45.0
    synthesis_base_url = _optional_env("SPEECH_SYNTHESIS_BASE_URL", "LENA_TTS_BASE_URL")
    synthesis_api_key = _optional_env("SPEECH_SYNTHESIS_API_KEY", "LENA_TTS_API_KEY")
    synthesis_model = _optional_env("SPEECH_SYNTHESIS_MODEL", "LENA_TTS_MODEL")
    synthesis_provider = (
        _optional_env("SPEECH_SYNTHESIS_PROVIDER", "LENA_TTS_PROVIDER")
        or ("openai" if synthesis_base_url or synthesis_api_key or synthesis_model else "edge")
    ).lower()
    if synthesis_provider not in {"edge", "openai"}:
        synthesis_provider = "edge"

    return Settings(
        app_root=app_root,
        kb_path=Path(
            _optional_env("LENA_KB_PATH")
            or app_root / "data" / "canonical" / "offers.json"
        ),
        rewrite_provider=provider,
        blablador_base_url=_optional_env("BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL"),
        blablador_api_key=_optional_env("BLABLADOR_API_KEY", "LENA_LLM_API_KEY"),
        blablador_model=_optional_env("BLABLADOR_MODEL", "LENA_LLM_MODEL"),
        blablador_timeout_seconds=timeout,
        blablador_max_context_chars=max_context_chars,
        blablador_max_tokens=max_tokens,
        session_timeout_seconds=session_timeout_seconds,
        speech_transcription_base_url=speech_base_url or _optional_env("BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL"),
        speech_transcription_api_key=speech_api_key or _optional_env("BLABLADOR_API_KEY", "LENA_LLM_API_KEY"),
        speech_transcription_model=speech_model or "whisper-large-v3",
        speech_transcription_timeout_seconds=speech_timeout,
        speech_synthesis_base_url=(
            synthesis_base_url
            or (_optional_env("BLABLADOR_BASE_URL", "LENA_LLM_BASE_URL") if synthesis_provider == "openai" else None)
        ),
        speech_synthesis_api_key=(
            synthesis_api_key
            or (_optional_env("BLABLADOR_API_KEY", "LENA_LLM_API_KEY") if synthesis_provider == "openai" else None)
        ),
        speech_synthesis_model=synthesis_model or ("gpt-4o-mini-tts" if synthesis_provider == "openai" else None),
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
        wfs_auto_sync=_env_bool("WFS_AUTO_SYNC", True),
        wfs_auto_promote=_env_bool("WFS_AUTO_PROMOTE", False),
        wfs_check_interval_hours=_env_float("WFS_CHECK_INTERVAL_HOURS", 24.0, 1.0),
    )
