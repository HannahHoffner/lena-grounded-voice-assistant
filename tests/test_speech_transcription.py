"""Regressionstests fuer den Browseraudio-zu-STT-Vertrag."""

from __future__ import annotations

import json
import logging
import asyncio
import io
import math
from fractions import Fraction
from pathlib import Path

import av
import httpx
import pytest
from fastapi.testclient import TestClient

import app.speech as speech
from app.config import Settings
from app.main import create_app
from app.models import Language
from app.speech import (
    SpeechTranscriber,
    SpeechTranscriptionAudioError,
    SpeechTranscriptionAudioTooLongError,
    SpeechTranscriptionProviderError,
)

ROOT = Path(__file__).resolve().parents[1]


def test_stt_failure_log_exposes_safe_cause_without_changing_public_error(monkeypatch, caplog):
    async def rejected(self, *args, **kwargs):
        raise SpeechTranscriptionProviderError(upstream_status=404)

    monkeypatch.setattr(SpeechTranscriber, "transcribe", rejected)
    with caplog.at_level(logging.WARNING):
        response = TestClient(create_app(_settings())).post(
            "/api/speech/transcribe", content=b"synthetic-audio", headers={"Content-Type": "audio/ogg"},
        )
    assert response.status_code == 503
    assert response.json() == {"detail": "Speech transcription failed"}
    assert "code=stt_provider_http_error upstream_status=404" in caplog.text
    assert "test-token" not in caplog.text


@pytest.mark.parametrize("payload", [[], None, {"text": []}, {"text": 123}, {"text": " "}])
def test_invalid_transcription_json_is_a_controlled_api_error(monkeypatch, payload) -> None:
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            return httpx.Response(
                200, content=json.dumps(payload), request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    app = create_app(_settings())
    response = TestClient(app).post(
        "/api/speech/transcribe", content=_browser_opus_audio(), headers={"Content-Type": "audio/webm"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Speech transcription failed"}


def _settings() -> Settings:
    return Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        speech_transcription_base_url="https://speech.example/v1",
        speech_transcription_api_key="test-token",
        speech_transcription_model="test-stt",
        wfs_auto_sync=False,
    )


def _browser_opus_audio(*, samples: int = 4_800, container_format: str = "webm") -> bytes:
    """Erzeugt rein synthetisches Browseraudio ohne Aufnahme oder Nutzerdaten."""

    output = io.BytesIO()
    with av.open(output, mode="w", format=container_format) as container:
        stream = container.add_stream("libopus", rate=48_000)
        stream.layout = "mono"
        frame = av.AudioFrame(format="s16", layout="mono", samples=samples)
        frame.sample_rate = 48_000
        frame.time_base = Fraction(1, 48_000)
        pcm = bytearray()
        for index in range(samples):
            value = int(4_000 * math.sin(2 * math.pi * 440 * index / 48_000))
            pcm.extend(value.to_bytes(2, "little", signed=True))
        frame.planes[0].update(bytes(pcm))
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return output.getvalue()


@pytest.mark.parametrize("container_format", ["webm", "ogg"])
def test_browser_audio_is_sent_as_pcm_wav_and_transcribes(
    monkeypatch: pytest.MonkeyPatch, container_format: str,
) -> None:
    captured: dict[str, object] = {}

    class RecordingClient:
        def __init__(self, **kwargs) -> None:
            captured["client_options"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["files"] = kwargs["files"]
            request = httpx.Request("POST", url)
            return httpx.Response(200, json={"text": "Ich brauche Hilfe"}, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", RecordingClient)
    response = TestClient(create_app(_settings())).post(
        "/api/speech/transcribe?language=de",
        content=_browser_opus_audio(container_format=container_format),
        headers={"Content-Type": f"audio/{container_format};codecs=opus"},
    )
    assert response.status_code == 200
    result = response.json()["text"]

    filename, payload, media_type = captured["files"]["file"]  # type: ignore[index]
    assert result == "Ich brauche Hilfe"
    assert (filename, media_type) == ("speech.wav", "audio/wav")
    assert payload.startswith(b"RIFF")
    assert b"WAVE" in payload[:16]


def test_invalid_audio_is_rejected_before_provider_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_client(**kwargs):
        raise AssertionError("Ungueltiges Audio darf den Provider nicht erreichen")

    monkeypatch.setattr(httpx, "AsyncClient", unexpected_client)
    with pytest.raises(SpeechTranscriptionAudioError, match="stt_audio_invalid"):
        asyncio.run(
            SpeechTranscriber(_settings()).transcribe(
                b"not-an-audio-container",
                content_type="audio/webm",
                language=Language.DE,
            )
        )


def test_decoded_audio_duration_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(speech, "_STT_MAX_SAMPLES", 100)
    with pytest.raises(SpeechTranscriptionAudioTooLongError, match="stt_audio_too_long"):
        speech._normalize_audio_to_wav(_browser_opus_audio())


def test_upstream_http_status_is_redacted_but_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RejectingClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, url, **kwargs):
            request = httpx.Request("POST", url)
            return httpx.Response(
                400,
                json={"detail": "private upstream decoder detail"},
                request=request,
            )

    monkeypatch.setattr(httpx, "AsyncClient", RejectingClient)
    with pytest.raises(SpeechTranscriptionProviderError) as caught:
        asyncio.run(
            SpeechTranscriber(_settings()).transcribe(
                _browser_opus_audio(),
                content_type="audio/webm",
                language=Language.DE,
            )
        )
    assert caught.value.code == "stt_provider_http_error"
    assert caught.value.upstream_status == 400
    assert "private" not in str(caught.value)


def test_endpoint_returns_422_for_undecodable_supported_audio() -> None:
    response = TestClient(create_app(_settings())).post(
        "/api/speech/transcribe?language=de",
        content=b"not-webm",
        headers={"Content-Type": "audio/webm;codecs=opus"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Audio could not be decoded"}
