"""Einheitliche, secretfreie Statusbeschreibung aller externen Dienste.

LENA nutzt bis zu vier externe Dienstarten: das LLM für Interpretation,
Auswahl und Formulierung, serverseitige Spracherkennung (STT),
Sprachausgabe (TTS) und Kartenkacheln im Browser. Jede Dienstart besitzt ein
explizites Profil. Dieses Modul leitet aus den Einstellungen ab, ob ein Profil
*vollständig konfiguriert* ist und – falls nicht – welcher Konfigurationsname
fehlt. Es prüft keine Erreichbarkeit; ``configured`` ist ausdrücklich keine
Verfügbarkeitszusage (siehe ``python -m app.service_check``).

Die Ausgabe enthält nur Profilnamen, Modellkennungen und Variablennamen, nie
URLs mit Zugangsdaten, Tokens oder Nutzerdaten.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    """Konfigurationszustand genau einer externen Dienstart."""

    service: str
    provider: str
    configured: bool
    reason: str
    model: str | None = None
    missing: tuple[str, ...] = ()

    def public(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "configured": self.configured,
            "reason": self.reason,
            "model": self.model if self.configured else None,
            "missing": list(self.missing),
        }


def _missing(pairs: tuple[tuple[str, object], ...]) -> tuple[str, ...]:
    return tuple(name for name, value in pairs if not value)


def llm_status(settings: Settings) -> ServiceStatus:
    if settings.rewrite_provider != "blablador":
        return ServiceStatus("llm", "template", False, "disabled_by_profile")
    missing = _missing((
        ("BLABLADOR_BASE_URL", settings.blablador_base_url),
        ("BLABLADOR_API_KEY", settings.blablador_api_key),
        ("BLABLADOR_MODEL", settings.blablador_model),
    ))
    if missing:
        return ServiceStatus("llm", "blablador", False, "incomplete_configuration", missing=missing)
    return ServiceStatus("llm", "blablador", True, "configured", model=settings.blablador_model)


def transcription_status(settings: Settings) -> ServiceStatus:
    provider = settings.speech_transcription_provider
    if provider == "disabled":
        return ServiceStatus("speech_transcription", provider, False, "disabled_by_profile")
    missing = _missing((
        ("SPEECH_TRANSCRIPTION_BASE_URL", settings.speech_transcription_base_url),
        ("SPEECH_TRANSCRIPTION_API_KEY", settings.speech_transcription_api_key),
        ("SPEECH_TRANSCRIPTION_MODEL", settings.speech_transcription_model),
    ))
    if provider == "blablador":
        # Das Profil übernimmt ausdrücklich den Blablador-Zugang; fehlende
        # Werte werden unter ihren tatsächlich zu setzenden Namen gemeldet.
        missing = tuple(
            name.replace("SPEECH_TRANSCRIPTION_BASE_URL", "BLABLADOR_BASE_URL")
            .replace("SPEECH_TRANSCRIPTION_API_KEY", "BLABLADOR_API_KEY")
            for name in missing
        )
    if missing:
        return ServiceStatus("speech_transcription", provider, False, "incomplete_configuration", missing=missing)
    return ServiceStatus(
        "speech_transcription", provider, True, "configured", model=settings.speech_transcription_model,
    )


def synthesis_status(settings: Settings, *, edge_client_installed: bool) -> ServiceStatus:
    provider = settings.speech_synthesis_provider
    if provider == "disabled":
        return ServiceStatus("speech_synthesis", provider, False, "disabled_by_profile")
    if provider == "edge":
        if not edge_client_installed:
            return ServiceStatus("speech_synthesis", provider, False, "client_library_missing", missing=("edge-tts",))
        return ServiceStatus("speech_synthesis", provider, True, "configured", model="edge-neural-voices")
    missing = _missing((
        ("SPEECH_SYNTHESIS_BASE_URL", settings.speech_synthesis_base_url),
        ("SPEECH_SYNTHESIS_API_KEY", settings.speech_synthesis_api_key),
        ("SPEECH_SYNTHESIS_MODEL", settings.speech_synthesis_model),
    ))
    if missing:
        return ServiceStatus("speech_synthesis", provider, False, "incomplete_configuration", missing=missing)
    return ServiceStatus("speech_synthesis", provider, True, "configured", model=settings.speech_synthesis_model)


def map_tiles_status(settings: Settings) -> ServiceStatus:
    if settings.map_provider == "disabled":
        return ServiceStatus("map_tiles", "disabled", False, "disabled_by_profile")
    return ServiceStatus("map_tiles", settings.map_provider, True, "configured")


def external_service_statuses(settings: Settings, *, edge_client_installed: bool) -> dict[str, ServiceStatus]:
    statuses = (
        llm_status(settings),
        transcription_status(settings),
        synthesis_status(settings, edge_client_installed=edge_client_installed),
        map_tiles_status(settings),
    )
    return {status.service: status for status in statuses}
