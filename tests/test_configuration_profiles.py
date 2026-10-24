"""Explizite Dienstprofile, Konfigurationspriorität und datensparsame Diagnose.

Audit F-03/F-04 (23.10.2026): Ein Blablador-Zugang aktivierte stillschweigend
ein TTS-Ziel mit ``gpt-4o-mini-tts`` (live HTTP 404), native Starts nutzten
andere Defaults als Docker/.env.example, und ``.env.local`` überschrieb die
Prozessumgebung einschließlich CLI-Entscheidungen.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import app.config as config
from app.config import Settings, load_settings
from app.external_services import external_service_statuses
from app.main import create_app
from app.models import Language
from app.speech import SpeechSynthesisProviderError, SpeechSynthesizer
from tests.conftest import PROVIDER_ENV_NAMES, REAL_LOAD_ENV_FILE


ROOT = Path(__file__).resolve().parents[1]
SECRET = "sk-test-secret-value-1234567890"


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in (*PROVIDER_ENV_NAMES, *config.UNSUPPORTED_VARIABLES, "INTERACTION_LOGGING_ENABLED",
                 "WFS_AUTO_SYNC", "TECHNICAL_LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LENA_ENV_FILE_MODE", "disabled")
    return monkeypatch


def _blablador(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REWRITE_PROVIDER", "blablador")
    monkeypatch.setenv("BLABLADOR_BASE_URL", "https://llm.example.invalid/v1")
    monkeypatch.setenv("BLABLADOR_API_KEY", SECRET)
    monkeypatch.setenv("BLABLADOR_MODEL", "alias-fast")


def test_native_defaults_match_the_safe_container_profile(clean_env) -> None:
    settings = load_settings()
    assert settings.rewrite_provider == "template"
    assert settings.speech_transcription_provider == "disabled"
    assert settings.speech_synthesis_provider == "disabled"
    assert settings.map_provider == "osm"
    assert settings.interaction_logging_enabled is False
    assert settings.wfs_auto_sync is False
    assert settings.toilet_auto_sync is False and settings.drinking_fountain_auto_sync is False
    assert settings.configuration_warnings == ()


def test_llm_access_does_not_silently_enable_speech_services(clean_env) -> None:
    _blablador(clean_env)
    settings = load_settings()
    assert settings.blablador_configured
    assert not settings.speech_synthesis_configured
    assert not settings.speech_transcription_configured
    assert settings.speech_synthesis_base_url is None and settings.speech_synthesis_api_key is None
    assert settings.speech_synthesis_model is None
    assert not SpeechSynthesizer(settings).configured


def test_blablador_transcription_reuse_must_be_selected_explicitly(clean_env) -> None:
    _blablador(clean_env)
    clean_env.setenv("SPEECH_TRANSCRIPTION_PROVIDER", "blablador")
    settings = load_settings()
    assert settings.speech_transcription_configured
    assert settings.speech_transcription_model == config.BLABLADOR_TRANSCRIPTION_MODEL
    assert settings.speech_transcription_base_url == "https://llm.example.invalid/v1"
    status = external_service_statuses(settings, edge_client_installed=True)["speech_transcription"]
    assert (status.provider, status.configured) == ("blablador", True)


def test_incomplete_profiles_name_missing_variables_but_never_values(clean_env) -> None:
    clean_env.setenv("SPEECH_SYNTHESIS_PROVIDER", "openai")
    clean_env.setenv("SPEECH_SYNTHESIS_API_KEY", SECRET)
    clean_env.setenv("SPEECH_TRANSCRIPTION_PROVIDER", "blablador")
    statuses = external_service_statuses(load_settings(), edge_client_installed=True)
    synthesis = statuses["speech_synthesis"]
    assert (synthesis.configured, synthesis.reason) == (False, "incomplete_configuration")
    assert synthesis.missing == ("SPEECH_SYNTHESIS_BASE_URL", "SPEECH_SYNTHESIS_MODEL")
    assert statuses["speech_transcription"].missing == ("BLABLADOR_BASE_URL", "BLABLADOR_API_KEY")
    assert SECRET not in json.dumps({name: status.public() for name, status in statuses.items()})


def test_edge_is_an_explicit_external_profile(clean_env) -> None:
    clean_env.setenv("SPEECH_SYNTHESIS_PROVIDER", "edge")
    settings = load_settings()
    assert external_service_statuses(settings, edge_client_installed=True)["speech_synthesis"].configured
    missing = external_service_statuses(settings, edge_client_installed=False)["speech_synthesis"]
    assert (missing.configured, missing.reason) == (False, "client_library_missing")


def test_invalid_profiles_fall_back_safely_and_are_reported_by_name(clean_env) -> None:
    clean_env.setenv("REWRITE_PROVIDER", "ollama")
    clean_env.setenv("SPEECH_SYNTHESIS_PROVIDER", "gpt-4o-mini-tts")
    clean_env.setenv("MAP_PROVIDER", "google")
    clean_env.setenv("LENA_LLM_TEMPERATURE", "0.7")
    settings = load_settings()
    assert (settings.rewrite_provider, settings.speech_synthesis_provider, settings.map_provider) == (
        "template", "disabled", "osm",
    )
    assert set(settings.configuration_warnings) == {
        "invalid_value:REWRITE_PROVIDER",
        "invalid_value:SPEECH_SYNTHESIS_PROVIDER",
        "invalid_value:MAP_PROVIDER",
        "unsupported_variable:LENA_LLM_TEMPERATURE",
    }
    assert "0.7" not in repr(settings.configuration_warnings)


def test_process_environment_overrides_local_files_without_mutating_it(
    clean_env, tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("REWRITE_PROVIDER=blablador\nMAP_PROVIDER=disabled\nQUERY_MAX_CHARS=100\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("REWRITE_PROVIDER=blablador\nQUERY_MAX_CHARS=200\n", encoding="utf-8")
    clean_env.setattr(config, "_load_env_file", REAL_LOAD_ENV_FILE)
    clean_env.setattr(config, "checkout_root", lambda: tmp_path)
    clean_env.setenv("LENA_ENV_FILE_MODE", "enabled")
    clean_env.setenv("REWRITE_PROVIDER", "template")  # wie --rewrite-provider template
    before = dict(os.environ)
    settings = load_settings()
    assert settings.rewrite_provider == "template"  # Prozess > .env.local > .env
    assert settings.query_max_chars == 200  # .env.local > .env
    assert settings.map_provider == "disabled"  # nur in .env
    assert dict(os.environ) == before


def test_health_and_logs_contain_no_secret_values(clean_env, caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="blablador",
        blablador_base_url="https://llm.example.invalid/v1",
        blablador_api_key=SECRET,
        blablador_model="alias-fast",
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        speech_synthesis_base_url="https://tts.example.invalid/v1",
        speech_synthesis_api_key=SECRET,
        speech_synthesis_model="tts-model",
        configuration_warnings=("unsupported_variable:LENA_LLM_TEMPERATURE",),
    )
    with caplog.at_level(logging.INFO):
        client = TestClient(create_app(settings))
        body = client.get("/api/health").text
        client_config = client.get("/api/client-config").text
    assert SECRET not in body and SECRET not in client_config and SECRET not in caplog.text
    assert "tts.example.invalid" not in body
    events = {(record.getMessage(), getattr(record, "service", None)) for record in caplog.records}
    assert ("config.external_service", "speech_synthesis") in events
    assert any(record.getMessage() == "config.warning" and record.setting == "LENA_LLM_TEMPERATURE"
               for record in caplog.records)
    services = json.loads(body)["external_services"]
    assert services["speech_synthesis"] == {
        "provider": "openai", "configured": True, "reason": "configured", "model": "tts-model",
        "missing": [], "availability": "not_checked",
    }


def test_missing_tts_model_on_endpoint_is_a_controlled_503_not_a_crash(
    clean_env, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    # Nachbildung des Auditbefunds: kompatibler Endpunkt ohne das TTS-Modell.
    class NotFoundClient:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def post(self, url, **_kwargs):
            return httpx.Response(404, json={"detail": "No backend"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", NotFoundClient)
    settings = Settings(
        app_root=ROOT, kb_path=ROOT / "data" / "canonical" / "offers.json", rewrite_provider="template",
        blablador_base_url=None, blablador_api_key=None, blablador_model=None,
        blablador_timeout_seconds=1, blablador_max_context_chars=50_000,
        speech_synthesis_base_url="https://tts.example.invalid/v1", speech_synthesis_api_key=SECRET,
        speech_synthesis_model="gpt-4o-mini-tts",
    )
    with pytest.raises(SpeechSynthesisProviderError) as caught:
        import asyncio
        asyncio.run(SpeechSynthesizer(settings).synthesize("LENA.", language=Language.DE))
    assert (caught.value.code, caught.value.upstream_status) == ("tts_provider_http_error", 404)
    assert SECRET not in str(caught.value)


def test_map_tiles_can_be_disabled_for_offline_or_data_minimal_operation(clean_env) -> None:
    base = Settings(
        app_root=ROOT, kb_path=ROOT / "data" / "canonical" / "offers.json", rewrite_provider="template",
        blablador_base_url=None, blablador_api_key=None, blablador_model=None,
        blablador_timeout_seconds=1, blablador_max_context_chars=50_000,
    )
    osm = TestClient(create_app(base)).get("/api/client-config").json()
    assert osm["map"]["tile_provider"] == "osm" and "openstreetmap" in osm["map"]["tile_url_template"]
    disabled = TestClient(create_app(replace(base, map_provider="disabled"))).get("/api/client-config").json()
    assert disabled["map"] == {"tile_provider": "disabled", "tile_url_template": None, "attribution": None}
    assert disabled["speech"]["server_synthesis_available"] is False


def test_every_variable_in_env_example_is_read_by_the_application() -> None:
    """Keine tote Konfiguration in der Vorlage (Audit C-25/C-27)."""
    names = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", (ROOT / ".env.example").read_text(encoding="utf-8"), re.MULTILINE))
    source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "app").rglob("*.py"))
    unread = sorted(name for name in names if f'"{name}"' not in source)
    assert names and unread == []


def test_service_check_separates_configuration_from_model_availability(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from app import service_check

    def inventory(url, **_kwargs):
        assert url.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "alias-fast"}, {"id": "faster-whisper-large-v3"}]},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", inventory)
    settings = Settings(
        app_root=ROOT, kb_path=ROOT / "data" / "canonical" / "offers.json", rewrite_provider="blablador",
        blablador_base_url="https://llm.example.invalid/v1", blablador_api_key=SECRET, blablador_model="alias-fast",
        blablador_timeout_seconds=1, blablador_max_context_chars=50_000,
        speech_transcription_provider="blablador", speech_transcription_base_url="https://llm.example.invalid/v1",
        speech_transcription_api_key=SECRET, speech_transcription_model="faster-whisper-large-v3",
        # Das im Audit vererbte, am Endpunkt nicht vorhandene TTS-Modell:
        speech_synthesis_base_url="https://llm.example.invalid/v1", speech_synthesis_api_key=SECRET,
        speech_synthesis_model="gpt-4o-mini-tts", map_provider="disabled",
    )
    report = service_check.check_services(settings)
    assert report["llm"]["result"] == "ok"
    assert report["speech_transcription"]["result"] == "ok"
    assert report["speech_synthesis"] == {
        "provider": "openai", "configured": True, "result": "model_not_listed",
        "models_not_listed": ["gpt-4o-mini-tts"],
    }
    assert report["map_tiles"]["result"] == "skipped_disabled"
    assert SECRET not in json.dumps(report) and "example.invalid" not in json.dumps(report)

    monkeypatch.setattr(service_check, "load_settings", lambda: settings)
    assert service_check.main([]) == 1
    assert SECRET not in capsys.readouterr().out


def test_service_check_passes_when_everything_optional_is_disabled(clean_env) -> None:
    from app import service_check

    report = service_check.check_services(load_settings())
    assert {entry["result"] for entry in report.values()} <= {"skipped_disabled", "browser_side_not_checked"}
