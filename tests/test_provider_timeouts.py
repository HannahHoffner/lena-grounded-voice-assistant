"""Schnelle Integrationstests für zentrale Provider-Timeouts und Fallbacks."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

import app.config as config
from app.config import Settings
from app.main import create_app
from app.models import Category, Language
from app.providers.llm import BlabladorProvider, InterpreterError
from app.speech import SpeechSynthesizer, SpeechSynthesisTimeoutError
from app.translate_offers import TranslationError, _post_blablador
from app.wfs_sync import WfsTimeoutError, sync_wfs


ROOT = Path(__file__).resolve().parents[1]


def _interpretation_payload(need: str = "food") -> dict[str, object]:
    return {
            "contract_version": "4",
        "need": need,
        "explicit_service_requests": [],
        "scope_status": "in_scope",
        "input_language": "de",
        "explicit_facts": {
            "age": None,
            "gender": "unknown",
            "drug_use": "unknown",
            "no_social_benefit_entitlement": "unknown",
            "district": None,
            "requested_day": None,
            "requested_time": None,
        },
        "uncertain_hints": [],
        "potentially_missing_information": [],
        "clarification_may_be_needed": False,
        "acute_risk_status": "not_detected",
    }


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
        llm_interpreter_timeout_seconds=0.02,
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


def test_timeout_configuration_defaults_and_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    for name in (
        "LLM_INTERPRETER_TIMEOUT_SECONDS",
        "LLM_SELECTOR_TIMEOUT_SECONDS",
        "LLM_FORMULATOR_TIMEOUT_SECONDS",
        "LLM_REQUEST_BUDGET_SECONDS",
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
    assert loaded.llm_interpreter_timeout_seconds == 15
    assert loaded.llm_selector_timeout_seconds == 10
    assert loaded.llm_formulator_timeout_seconds == 30
    assert loaded.llm_request_budget_seconds == 45
    assert loaded.speech_transcription_timeout_seconds == 45
    assert loaded.speech_synthesis_timeout_seconds == 45
    assert loaded.wfs_connect_timeout_seconds == 10
    assert loaded.wfs_read_timeout_seconds == 30

    monkeypatch.setenv("LLM_INTERPRETER_TIMEOUT_SECONDS", "-1")
    monkeypatch.setenv("LLM_REQUEST_BUDGET_SECONDS", "inf")
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "nan")
    invalid = config.load_settings()
    assert invalid.llm_interpreter_timeout_seconds == 15
    assert invalid.llm_request_budget_seconds == 45
    assert invalid.speech_transcription_timeout_seconds == 45

    monkeypatch.setenv("LLM_INTERPRETER_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("LLM_SELECTOR_TIMEOUT_SECONDS", "0.25")
    monkeypatch.setenv("LLM_FORMULATOR_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("LLM_REQUEST_BUDGET_SECONDS", "0.35")
    monkeypatch.setenv("STT_TIMEOUT_SECONDS", "0.4")
    monkeypatch.setenv("TTS_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("WFS_CONNECT_TIMEOUT_SECONDS", "0.6")
    monkeypatch.setenv("WFS_READ_TIMEOUT_SECONDS", "0.7")
    loaded = config.load_settings()
    assert (
        loaded.llm_interpreter_timeout_seconds,
        loaded.llm_selector_timeout_seconds,
        loaded.llm_formulator_timeout_seconds,
        loaded.llm_request_budget_seconds,
        loaded.speech_transcription_timeout_seconds,
        loaded.speech_synthesis_timeout_seconds,
        loaded.wfs_connect_timeout_seconds,
        loaded.wfs_read_timeout_seconds,
    ) == (0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7)

    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, llm_interpreter_timeout_seconds=0)
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, llm_selector_timeout_seconds=float("nan"))
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, llm_request_budget_seconds=0)
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, wfs_read_timeout_seconds=-1)
    with pytest.raises(ValueError, match="positive finite"):
        replace(loaded, speech_synthesis_timeout_seconds=None)  # type: ignore[arg-type]


def test_interpreter_timeout_fails_closed_with_conditional_safety_guidance(
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
    body = response.json()
    assert body["status"] == "error"
    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises, sofern die Wissensbasis ihn
    # liefert; der bedingte 112-Hinweis bleibt dabei erhalten.
    offer = next(offer for offer in app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    assert [card["id"] for card in body["cards"]] == [offer.id]
    assert body["map_data"] is None
    assert "112" in body["answer"]
    assert body["answer_type"] == "technical_fallback"
    assert cancelled.is_set()
    assert "query.interpreter.failed" in caplog.text
    assert any(
        getattr(record, "error_code", None) == "interpreter_timeout"
        for record in caplog.records
    )
    assert query not in caplog.text
    record = _interaction(app.state.interaction_writer.path)
    assert record["fallback_used"] is True
    assert record["acute_risk_detected"] is False
    assert record["interpreter_error_code"] == "interpreter_timeout"
    assert record["assistant_answer"] == body["answer"]


def test_formulator_timeout_uses_existing_template_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]
    # Eingefroren auf Montag 10:00, da die Food-Selektion ein geöffnetes
    # Angebot voraussetzt; ohne feste Uhr hängt der Testerfolg von der realen
    # Tageszeit ab (WP9C).
    app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    calls = 0

    async def interpret_then_block(payload: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            route = _interpretation_payload()
            return {"choices": [{"message": {"content": json.dumps(route)}}]}
        if calls == 2:
            user = json.loads(payload["messages"][1]["content"])
            selected = user["candidates"][0]["id"]
            result = {
                "contract_version": "1",
                "selection_status": "selected",
                "selected_ids": [selected],
            }
            return {"choices": [{"message": {"content": json.dumps(result)}}]}
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    monkeypatch.setattr(provider, "_post", interpret_then_block)
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(
            "/api/query",
            json={"query": "Wo gibt es Essen?", "category": Category.FOOD.value},
        )

    assert response.status_code == 200
    assert response.json()["provider"] == "template"
    assert calls == 3
    assert "query.formulation.failed" in caplog.text
    record = _interaction(app.state.interaction_writer.path)
    assert record["fallback_used"] is True
    assert record["formulator_fallback_used"] is True
    assert record["formulator_error_code"] == "formulator_timeout"
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
    monkeypatch.setattr("app.speech._normalize_audio_to_wav", lambda audio: b"RIFF-test-wav")

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
            json={
                "text": text_response.json()["answer"],
                "language": "de",
                "session_id": text_response.json()["session_id"],
            },
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
    service = app.state.service
    session = service.sessions.resolve(None, Language.DE, service.kb.runtime_kb_fingerprint or "")
    session = service.sessions.add_turn(session, question="test", answer="Bitte 112 anrufen.")
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post(
            "/api/speech/synthesize",
            json={
                "text": "Bitte 112 anrufen.",
                "language": "de",
                "session_id": session.session_id,
            },
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
    with pytest.raises(TranslationError, match="translation_timeout"):
        asyncio.run(_post_blablador(settings, {"model": "test"}))


def test_interpreter_timeout_has_a_controlled_error_code(tmp_path: Path) -> None:
    provider = BlabladorProvider(_settings(tmp_path))

    async def blocked_post(payload: dict) -> dict:
        await asyncio.sleep(60)
        return {}

    provider._post = blocked_post  # type: ignore[method-assign]
    with pytest.raises(InterpreterError, match="interpreter_timeout"):
        asyncio.run(
            provider.interpret_query(
                query="Essen",
                language=Language.DE,
                category=Category.FOOD,
                aliases=[],
            )
        )
