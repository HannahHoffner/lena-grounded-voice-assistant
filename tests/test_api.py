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
    assert body["stt_configured_provider"] == "mock"
    assert body["stt_ready"] is True
    assert body["rewrite_provider"] == "template"
    assert body["rewrite_model"] is None
    assert body["llm_active"] is False
    assert body["tts_provider"] == "mock"
    assert body["tts_configured_provider"] == "mock"
    assert body["tts_ready"] is True
    assert body["speech"]["stt"]["active_provider"] == "mock"
    assert body["speech"]["tts"]["active_provider"] == "mock"


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
    assert body["session_id"]


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


def test_shower_answer_includes_concrete_place_details(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "Wo kann ich duschen?", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Leipziger Oase" in body["answer_text"]
    assert "08:00" in body["answer_text"]
    assert "Nuernberger Strasse 31" in body["answer_text"] or "Nürnberger Straße 31" in body["answer_text"]


def test_location_answer_includes_address_for_specific_place(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "wo ist leipziger oase", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Leipziger Oase" in body["answer_text"]
    assert "Nuernberger Strasse 31" in body["answer_text"] or "Nürnberger Straße 31" in body["answer_text"]


def test_answer_endpoint_supports_cross_language_food_lookup(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "where can i get food", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert "Tafel Leipzig" in body["answer_text"]
    assert body["answer_text"].count("You can go to") <= 1


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


def test_session_follow_up_prefers_previous_place(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "where can i get food in leipzig", "language": "en", "session_id": "session-1"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "is it open today?", "language": "en", "session_id": "session-1"},
    ).json()

    assert first["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert second["retrieved_page_ids"][0] == first["retrieved_page_ids"][0]
    assert second["session_id"] == "session-1"


def test_session_alternative_request_prefers_different_place(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "where can i get food in leipzig", "language": "en", "session_id": "session-2"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "is there another place?", "language": "en", "session_id": "session-2"},
    ).json()

    assert first["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert second["retrieved_page_ids"][0] != first["retrieved_page_ids"][0]


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
