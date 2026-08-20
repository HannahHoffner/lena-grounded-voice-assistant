"""Integrationstests für HTTP-Eingabegrenzen und sichere Serverbindung."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.__main__ import build_parser, validate_bind_host
import app.config as config
from app.config import Settings
from app.main import create_app
from app.models import Language
from app.speech import SpeechSynthesizer, SpeechTranscriber


ROOT = Path(__file__).resolve().parents[1]


def _settings(**overrides: object) -> Settings:
    settings = Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        speech_transcription_base_url="https://example.invalid/v1",
        speech_transcription_api_key="test-token",
        speech_transcription_model="test-model",
        interaction_logging_enabled=False,
    )
    return replace(settings, **overrides)


def test_query_limit_accepts_boundary_and_rejects_next_character() -> None:
    client = TestClient(create_app(_settings(query_max_chars=10)))

    assert client.post("/api/query", json={"query": "a" * 10}).status_code == 200
    response = client.post("/api/query", json={"query": "a" * 11})

    assert response.status_code == 422
    assert response.json()["detail"] == "Query text too long"


def test_category_only_query_remains_valid() -> None:
    app = create_app(_settings())
    response = TestClient(app).post(
        "/api/query",
        json={"query": "", "category": "food", "language": "de"},
    )

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises.
    hilfebus_offer = next(offer for offer in app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    assert response.status_code == 200
    assert [card["id"] for card in response.json()["cards"]] == [hilfebus_offer.id]
    assert response.json()["answer_type"] == "technical_fallback"
    assert "112" in response.json()["answer"]


def test_stt_accepts_exact_limit_and_calls_existing_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"count": 0}

    async def transcribe(self: SpeechTranscriber, audio: bytes, *, content_type: str, language: Language) -> str:
        called["count"] += 1
        assert audio == b"1234"
        assert content_type == "audio/webm"
        return "Essen"

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe)
    response = TestClient(create_app(_settings(speech_transcription_max_bytes=4))).post(
        "/api/speech/transcribe?language=de",
        content=b"1234",
        headers={"Content-Type": "audio/webm;codecs=opus"},
    )

    assert response.status_code == 200
    assert called["count"] == 1


def test_stt_rejects_declared_oversize_before_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    async def transcribe(*args, **kwargs) -> str:
        raise AssertionError("Oversize-Audio darf den Provider nicht erreichen")

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe)
    response = TestClient(create_app(_settings(speech_transcription_max_bytes=4))).post(
        "/api/speech/transcribe",
        content=b"12345",
        headers={"Content-Type": "audio/webm"},
    )

    assert response.status_code == 413


def test_stt_rejects_streamed_oversize_without_content_length(monkeypatch: pytest.MonkeyPatch) -> None:
    async def transcribe(*args, **kwargs) -> str:
        raise AssertionError("Chunked Oversize-Audio darf den Provider nicht erreichen")

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe)

    def chunks():
        yield b"123"
        yield b"45"

    response = TestClient(create_app(_settings(speech_transcription_max_bytes=4))).post(
        "/api/speech/transcribe",
        content=chunks(),
        headers={"Content-Type": "audio/ogg"},
    )

    assert response.status_code == 413


@pytest.mark.parametrize(
    ("content", "content_type", "status"),
    [(b"", "audio/webm", 422), (b"audio", "application/octet-stream", 415)],
)
def test_stt_rejects_empty_or_unsupported_audio(content: bytes, content_type: str, status: int) -> None:
    response = TestClient(create_app(_settings())).post(
        "/api/speech/transcribe",
        content=content,
        headers={"Content-Type": content_type},
    )

    assert response.status_code == status


def test_tts_limit_accepts_boundary_and_uses_typed_language(monkeypatch: pytest.MonkeyPatch) -> None:
    async def synthesize(self: SpeechSynthesizer, text: str, *, language: Language) -> bytes:
        assert text == "1234"
        assert language == Language.EN
        return b"audio"

    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize)
    app = create_app(_settings(speech_synthesis_max_chars=4))
    session = app.state.service.sessions.resolve(
        None,
        Language.EN,
        app.state.service.kb.runtime_kb_fingerprint or "",
    )
    session = app.state.service.sessions.add_turn(session, question="test", answer="1234")
    response = TestClient(app).post(
        "/api/speech/synthesize",
        json={"text": "1234", "language": "en", "session_id": session.session_id},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "12345", "language": "de"},
        {"text": "   ", "language": "de"},
        {"text": "Hallo", "language": "unsupported"},
    ],
)
def test_tts_rejects_invalid_payload_before_provider(
    payload: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def synthesize(*args, **kwargs) -> bytes:
        raise AssertionError("Ungültiges TTS darf den Provider nicht erreichen")

    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize)
    response = TestClient(create_app(_settings(speech_synthesis_max_chars=4))).post(
        "/api/speech/synthesize",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_loopback_hosts_are_allowed_by_default(host: str) -> None:
    assert validate_bind_host(host, allow_public=False) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.10", "lena.internal"])
def test_non_loopback_hosts_require_explicit_public_flag(host: str) -> None:
    with pytest.raises(ValueError, match="--allow-public"):
        validate_bind_host(host, allow_public=False)
    assert validate_bind_host(host, allow_public=True) == host


def test_cli_defaults_to_local_binding_without_public_flag() -> None:
    args = build_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.allow_public is False


def test_environment_limits_are_clamped_to_safe_absolute_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("QUERY_MAX_CHARS", "999999")
    monkeypatch.setenv("SPEECH_TRANSCRIPTION_MAX_BYTES", "1")
    monkeypatch.setenv("SPEECH_SYNTHESIS_MAX_CHARS", "invalid")

    loaded = config.load_settings()

    assert loaded.query_max_chars == 10_000
    assert loaded.speech_transcription_max_bytes == 1024
    assert loaded.speech_synthesis_max_chars == 4000


def test_hbf_coordinates_are_read_atomically_as_a_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("HBF_LATITUDE", "51.28")
    monkeypatch.setenv("HBF_LONGITUDE", "12.62")

    loaded = config.load_settings()

    assert loaded.hbf_latitude == 51.28
    assert loaded.hbf_longitude == 12.62


def test_hbf_coordinates_fall_back_to_default_when_pair_is_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("HBF_LATITUDE", "0.0")
    monkeypatch.setenv("HBF_LONGITUDE", "0.0")

    loaded = config.load_settings()

    assert loaded.hbf_latitude == 51.34556
    assert loaded.hbf_longitude == 12.38222


def test_hbf_coordinates_fall_back_to_default_when_only_one_value_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "_load_env_file", lambda *args, **kwargs: None)
    monkeypatch.setenv("HBF_LATITUDE", "51.28")
    monkeypatch.delenv("HBF_LONGITUDE", raising=False)

    loaded = config.load_settings()

    assert loaded.hbf_latitude == 51.34556
    assert loaded.hbf_longitude == 12.38222


def test_settings_rejects_an_explicit_out_of_range_hbf_coordinate() -> None:
    with pytest.raises(ValueError, match="hbf_latitude"):
        _settings(hbf_latitude=0.0, hbf_longitude=0.0)
