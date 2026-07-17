"""Schnelle Integrationstests für zentrale Provider-Timeouts und Fallbacks."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import app.config as config
from app.config import Settings
from app.main import create_app
from app.models import Category, Language
from app.providers.llm import BlabladorProvider, ProviderTimeoutError
from app.speech import SpeechSynthesizer, SpeechSynthesisTimeoutError
from app.translate_offers import TranslationError, _post_blablador
from app.wfs_sync import WfsTimeoutError, sync_wfs


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    settings = Settings(
        app_root=tmp_path,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="blablador",
        blablador_base_url="https://provider.example/v1",
        blablador_api_key="test-token",
        blablador_model="test-model",
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        llm_router_timeout_seconds=0.02,
        llm_formulator_timeout_seconds=0.02,
        speech_transcription_base_url="https://speech.example/v1",
        speech_transcription_api_key="test-token",
        speech_transcription_model="test-stt",
        speech_transcription_timeout_seconds=0.02,
        speech_synthesis_provider="edge",
        speech_synthesis_timeout_seconds=0.02,
        wfs_auto_sync=False,
        wfs_connect_timeout_seconds=0.01,
        wfs_read_timeout_seconds=0.02,
        interaction_logging_enabled=True,
        interaction_log_path=tmp_path / "runtime" / "logs" / "interactions.jsonl",
    )
    return replace(settings, **overrides)


def _interaction(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_timeout_configuration_defaults_aliases_and_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    for name in (
        "LLM_ROUTER_TIMEOUT_SECONDS",
        "LLM_FORMULATOR_TIMEOUT_SECONDS",
        "STT_TIMEOUT_SECONDS",
        "TTS_TIMEOUT_SECONDS",
        "WFS_CONNECT_TIMEOUT_SECONDS",
        "WFS_READ_TIMEOUT_SECONDS",
        "BLABLADOR_TIMEOUT_SECONDS",
        "LENA_LLM_TIMEOUT_SECONDS",
        "SPEECH_TRANSCRIPTION_TIMEOUT_SECONDS",
        "LENA_STT_TIMEOUT_SECONDS",
        "SPEECH_SYNTHESIS_TIMEOUT_SECONDS",
        "LENA_TTS_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    loaded = config.load_settings()
    assert loaded.llm_router_timeout_seconds == 15
    assert loaded.llm_formulator_timeout_seconds == 30
    assert loaded.speech_transcription_timeout_seconds == 45
    assert loaded.speech_synthesis_timeout_seconds == 45
    assert loaded.wfs_connect_timeout_seconds == 10
    assert loaded.wfs_read_timeout_seconds == 30

    monkeypatch.setenv("LLM_ROUTER_TIMEOUT_SECONDS", "-1")
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "nan")
    invalid = config.load_settings()
    assert invalid.llm_router_timeout_seconds == 15
    assert invalid.speech_transcription_timeout_seconds == 45

    monkeypatch.setenv("LLM_ROUTER_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("LLM_FORMULATOR_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "0.4")
    monkeypatch.setenv("TTS_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("WFS_CONNECT_TIMEOUT_SECONDS", "0.6")
    monkeypatch.setenv("WFS_READ_TIMEOUT_SECONDS", "0.7")
    loaded = config.load_settings()
    assert (
        loaded.llm_router_timeout_seconds,
        loaded.llm_formulator_timeout_seconds,
        loaded.speech_transcription_timeout_seconds,
        loaded.speech_synthesis_timeout_seconds,
        loaded.wfs_connect_timeout_seconds,
        loaded.wfs_read_timeout_seconds,
    ) == (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)

    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, llm_router_timeout_seconds=0)
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, wfs_read_timeout_seconds=-1)
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, speech_synthesis_timeout_seconds=None)  # type: ignore[arg-type]


def test_router_timeout_uses_real_query_fallback_without_safety_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))
    provider: BlabladorProvider = app.state.service.blablador
    cancelled = asyncio.Event()
    query = "Wo bekomme ich vertrauliche Timeout-Mahlzeiten?"

    async def blocked_post(payload: dict) -> dict:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(provider, "_post", blocked_post)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post("/api/query", json={"query": query, "language": "de"})

    assert response.status_code == 200
    assert "112" not in response.json()["answer"]
    assert cancelled.is_set()
    assert "query.router.timeout" in caplog.text
    assert query not in caplog.text
    record = _interaction(app.state.interaction_writer.path)
    assert record["fallback_used"] is True
    assert record["acute_risk_detected"] is False
    assert record["assistant_answer"] == response.json()["answer"]


def test_formulator_timeout_uses_existing_template_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]
    calls = 0

    async def route_then_block(payload: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            route = {
                "intent": "food",
                "offer_ids": [offer.id],
                "needs_clarification": False,
                "out_of_scope": False,
                "acute_risk_detected": False,
            }
            return {"choices": [{"message": {"content": json.dumps(route)}}]}
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    monkeypatch.setattr(provider, "_post", route_then_block)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(
            "/api/query",
            json={"query": "Wo gibt es Essen?", "category": Category.FOOD.value},
        )

    assert response.status_code == 200
    assert response.json()["provider"] == "template"
    assert calls == 2
    assert "query.formulation.timeout" in caplog.text
    record = _interaction(app.state.interaction_writer.path)
    assert record["fallback_used"] is True
    assert record["assistant_answer"] == response.json()["answer"]


def test_llm_transport_failure_is_not_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = BlabladorProvider(_settings(tmp_path))
    calls = 0

    class FailingClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            request = httpx.Request("POST", "https://provider.example/v1/chat/completions")
            raise httpx.ConnectError("private transport detail", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", FailingClient)
    with pytest.raises(httpx.ConnectError):
        asyncio.run(provider._post({"model": "test"}))
    assert calls == 1


def test_stt_timeout_returns_503_and_creates_no_interaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))
    cancelled = asyncio.Event()

    class BlockingClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs):
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    monkeypatch.setattr(httpx, "AsyncClient", BlockingClient)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(
            "/api/speech/transcribe?language=de",
            content=b"audio",
            headers={"Content-Type": "audio/webm"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Speech transcription failed"
    assert cancelled.is_set()
    assert "stt.timeout" in caplog.text
    assert not app.state.interaction_writer.path.exists()


def test_edge_tts_timeout_keeps_existing_text_interaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path, rewrite_provider="template"))
    client = TestClient(app)
    text_response = client.post("/api/query", json={"query": "Wo bekomme ich Essen?"})
    before = app.state.interaction_writer.path.read_bytes()

    async def blocked_edge(self, text: str, *, language: Language) -> bytes:
        await asyncio.sleep(60)
        return b"unreachable"

    monkeypatch.setattr(SpeechSynthesizer, "_synthesize_edge", blocked_edge)
    with caplog.at_level(logging.INFO):
        speech_response = client.post(
            "/api/speech/synthesize",
            json={"text": text_response.json()["answer"], "language": "de"},
        )

    assert speech_response.status_code == 503
    assert "tts.timeout" in caplog.text
    assert app.state.interaction_writer.path.read_bytes() == before


def test_openai_tts_httpx_timeout_is_translated_to_stable_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        _settings(
            tmp_path,
            speech_synthesis_provider="openai",
            speech_synthesis_base_url="https://speech.example/v1",
            speech_synthesis_api_key="test-token",
            speech_synthesis_model="test-tts",
        )
    )

    class TimeoutClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, **kwargs):
            request = httpx.Request("POST", url)
            raise httpx.ReadTimeout("private TTS detail", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", TimeoutClient)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(
            "/api/speech/synthesize",
            json={"text": "Bitte 112 anrufen.", "language": "de"},
        )

    assert response.status_code == 503
    assert "tts.timeout" in caplog.text
    assert "private TTS detail" not in caplog.text


@pytest.mark.parametrize("error_type", [httpx.ConnectTimeout, httpx.ReadTimeout])
def test_wfs_timeouts_preserve_active_data_and_use_central_httpx_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[httpx.TimeoutException],
) -> None:
    active = tmp_path / "data" / "canonical" / "offers.json"
    active.parent.mkdir(parents=True)
    active.write_text("active-data", encoding="utf-8")
    settings = _settings(tmp_path, kb_path=active)
    captured: dict[str, object] = {}

    class TimeoutClient:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def get(self, url, **kwargs):
            request = httpx.Request("GET", url)
            raise error_type("private WFS detail", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", TimeoutClient)
    with pytest.raises(WfsTimeoutError):
        asyncio.run(sync_wfs(settings, promote=True))

    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == settings.wfs_connect_timeout_seconds
    assert timeout.read == settings.wfs_read_timeout_seconds
    assert active.read_text(encoding="utf-8") == "active-data"
    assert not (tmp_path / "runtime" / "wfs").exists()


def test_translation_provider_uses_formulator_total_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, llm_formulator_timeout_seconds=0.01)

    class BlockingClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs):
            await asyncio.sleep(60)

    monkeypatch.setattr(httpx, "AsyncClient", BlockingClient)
    with pytest.raises(TranslationError, match="timed out"):
        asyncio.run(_post_blablador(settings, {"model": "test"}))


def test_provider_timeout_error_remains_a_controlled_provider_error(tmp_path: Path) -> None:
    provider = BlabladorProvider(_settings(tmp_path))

    async def blocked_post(payload: dict) -> dict:
        await asyncio.sleep(60)
        return {}

    provider._post = blocked_post  # type: ignore[method-assign]
    with pytest.raises(ProviderTimeoutError):
        asyncio.run(
            provider.route(
                query="Essen",
                language=Language.DE,
                category=Category.FOOD,
                offers=[],
            )
        )
