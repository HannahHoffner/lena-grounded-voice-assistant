"""Aktive, secretfreie Erreichbarkeits- und Fähigkeitsprüfung externer Dienste.

``/api/health`` meldet nur, ob ein Dienstprofil vollständig *konfiguriert* ist.
Dieses Kommando prüft getrennt davon, ob der konfigurierte Endpunkt erreichbar
ist und das konfigurierte Modell tatsächlich anbietet::

    python -m app.service_check                 # Modellinventar (GET /models)
    python -m app.service_check --synthesize    # zusätzlich ein TTS-Aufruf "LENA."

Es werden nur feste synthetische Inhalte gesendet, nie Nutzerdaten. Die Ausgabe
ist JSON mit Profil, Ergebnis und gegebenenfalls HTTP-Status; URLs, Tokens und
Antworttexte erscheinen nicht. Exitcode 0 bedeutet, dass jedes *aktivierte*
Profil die Prüfung bestanden hat; deaktivierte Profile werden übersprungen.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx

from .config import Settings, load_settings
from .external_services import external_service_statuses
from .models import Language
from .speech import SpeechSynthesisError, SpeechSynthesizer


TIMEOUT_SECONDS = 15.0


def _model_inventory(base_url: str, api_key: str) -> tuple[set[str] | None, dict[str, Any]]:
    try:
        response = httpx.get(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return None, {"result": "unreachable", "error_type": type(exc).__name__}
    if response.status_code != 200:
        return None, {"result": "http_error", "upstream_status": response.status_code}
    try:
        payload = response.json()
        models = {str(item["id"]) for item in payload.get("data", []) if isinstance(item, dict) and "id" in item}
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, {"result": "invalid_inventory"}
    return models, {"result": "reachable"}


def _check_models(base_url: str, api_key: str, required: list[str]) -> dict[str, Any]:
    models, outcome = _model_inventory(base_url, api_key)
    if models is None:
        return outcome
    missing = sorted({model for model in required if model not in models})
    if missing:
        return {"result": "model_not_listed", "models_not_listed": missing}
    return {"result": "ok"}


def check_services(settings: Settings, *, synthesize: bool = False) -> dict[str, dict[str, Any]]:
    synthesizer = SpeechSynthesizer(settings)
    statuses = external_service_statuses(settings, edge_client_installed=synthesizer.edge_client_installed)
    report: dict[str, dict[str, Any]] = {}
    for name, status in statuses.items():
        entry: dict[str, Any] = {"provider": status.provider, "configured": status.configured}
        if status.reason == "disabled_by_profile":
            entry["result"] = "skipped_disabled"
        elif not status.configured:
            entry.update({"result": "not_configured", "missing": list(status.missing)})
        elif name == "llm":
            required = [
                settings.effective_interpreter_model, settings.effective_selector_model,
                settings.effective_formulator_model,
            ]
            entry.update(_check_models(
                settings.blablador_base_url or "", settings.blablador_api_key or "",
                [model for model in required if model],
            ))
        elif name == "speech_transcription":
            entry.update(_check_models(
                settings.speech_transcription_base_url or "", settings.speech_transcription_api_key or "",
                [settings.speech_transcription_model or ""],
            ))
        elif name == "speech_synthesis":
            if settings.speech_synthesis_provider == "openai":
                entry.update(_check_models(
                    settings.speech_synthesis_base_url or "", settings.speech_synthesis_api_key or "",
                    [settings.speech_synthesis_model or ""],
                ))
            else:
                entry["result"] = "not_checked_without_synthesize"
            if synthesize:
                try:
                    audio = asyncio.run(synthesizer.synthesize("LENA.", language=Language.DE))
                    entry["synthesis"] = {"result": "ok", "audio_bytes": len(audio)}
                except SpeechSynthesisError as exc:
                    entry["synthesis"] = {"result": exc.code, "upstream_status": exc.upstream_status}
                if entry.get("result") == "not_checked_without_synthesize":
                    entry["result"] = entry["synthesis"]["result"]
        else:
            # Kartenkacheln lädt ausschließlich der Browser; der Server prüft sie nicht.
            entry["result"] = "browser_side_not_checked"
        report[name] = entry
    return report


def _passed(entry: dict[str, Any]) -> bool:
    if entry["result"] in {"skipped_disabled", "browser_side_not_checked"}:
        return True
    synthesis = entry.get("synthesis")
    return entry["result"] == "ok" and (synthesis is None or synthesis["result"] == "ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check configured external LENA services without secrets.")
    parser.add_argument("--synthesize", action="store_true", help="Send one synthetic TTS request ('LENA.').")
    args = parser.parse_args(argv)
    report = check_services(load_settings(), synthesize=args.synthesize)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(_passed(entry) for entry in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
