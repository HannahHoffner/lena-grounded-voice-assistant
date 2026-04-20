from __future__ import annotations

import os
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_providers(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    monkeypatch.setenv("LENA_WEAK_MATCH_THRESHOLD", "0.2")
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["stt_provider"] == "mock"
    assert body["rewrite_provider"] == "template"
    assert body["rewrite_model"] is None
    assert body["llm_active"] is False


def test_answer_endpoint_returns_weak_match_or_ok(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "Leipziger Oase", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "weak_match"}
    assert body["answer_text"]
    assert body["retrieved_page_ids"]


def test_unknown_query_returns_unknown(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "astronomy telescope orbit", "language": "en"})
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"


def test_answer_endpoint_can_clarify(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "help", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_needed"
    assert "what kind of help" in body["answer_text"].lower()


def test_answer_endpoint_surfaces_relevant_page_passage(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "oeffnungszeiten oase", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "08:00" in body["answer_text"]
    assert body["model"] is None


def test_answer_endpoint_supports_cross_language_food_lookup(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "where can i get food", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0] == "tafel-leipzig"
    assert "Tafel Leipzig" in body["answer_text"]


def test_answer_endpoint_prefers_debt_counseling_page(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "hilfe bei schulden", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0] == "caritas-schuldnerberatung"
    assert "Schuldner" in body["answer_text"]


def test_transcribe_endpoint_accepts_form_language_string(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    app = create_app()
    client = TestClient(app)

    audio_path = tmp_path / "sample.wav"
    with wave.open(str(audio_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 1600)

    with audio_path.open("rb") as handle:
        response = client.post(
            "/api/speech/transcribe",
            files={"audio": ("sample.wav", handle, "audio/wav")},
            data={"language": "de"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"
    assert body["transcript"]
