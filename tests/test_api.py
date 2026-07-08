from __future__ import annotations

import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.stt import create_stt_provider


def test_frontend_copy_does_not_expose_internal_knowledge_base_terms() -> None:
    static_root = Path(__file__).resolve().parents[1] / "app" / "static"
    frontend_text = "\n".join(
        [
            (static_root / "app.js").read_text(encoding="utf-8"),
            (static_root / "index.html").read_text(encoding="utf-8"),
        ]
    )

    assert "Wissensbasis" not in frontend_text
    assert "knowledge base" not in frontend_text
    assert "baze wiedzy" not in frontend_text
    assert "baza locala de cunostinte" not in frontend_text
    assert "baze znanii" not in frontend_text
    assert "download the app" not in frontend_text
    assert "search online" not in frontend_text
    assert "google maps" not in frontend_text.casefold()
    assert "app herunterladen" not in frontend_text.casefold()
    assert "online suchen" not in frontend_text.casefold()


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
    assert body["speech"]["stt"]["real_audio"] is False
    assert body["speech"]["tts"]["active_provider"] == "mock"
    assert body["speech"]["tts"]["audio_output"] is False


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
    response = client.post("/api/query/answer", json={"transcript": "qwertz asdf yxv", "language": "en"})
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"


def test_self_description_query_returns_deterministic_answer(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "Who are you?", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "self_description"
    assert body["self_description"] is True
    assert "LENA" in body["answer_text"]
    assert "Leipzig" in body["answer_text"]
    assert body["retrieved_page_ids"] == []


def test_out_of_scope_query_redirects_to_supported_topics(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "How do telescopes work?", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "out_of_scope"
    assert body["out_of_scope"] is True
    assert "Leipzig" in body["answer_text"]
    assert "local help services" in body["answer_text"]


def test_crisis_query_bypasses_normal_answering(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "I want to kill myself", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "crisis"
    assert body["crisis_mode"] is True
    assert "112" in body["answer_text"]
    assert "110" in body["answer_text"]
    assert "emergency services" in body["answer_text"]
    assert "notfallkontakte" in body["retrieved_page_ids"]


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
    assert "Duschen" in body["answer_text"] or "Koerperpflege" in body["answer_text"]
    assert "Nuernberger Strasse 31" in body["answer_text"] or "Nürnberger Straße 31" in body["answer_text"]


def test_toilet_query_returns_public_toilet_map(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "wo sind toiletten?", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "City-Toiletten" in body["answer_text"]
    assert "Lene-Voigt-Park" in body["answer_text"]
    assert body["map_data"] is not None
    assert len(body["map_data"]["destinations"]) == 21
    assert any(destination["label"] == "Lene-Voigt-Park" for destination in body["map_data"]["destinations"])


def test_free_toilet_query_returns_lene_voigt_park_map(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "wo kann ich umsonst aufs klo?", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "Kostenfrei" in body["answer_text"]
    assert "Lene-Voigt-Park" in body["answer_text"]
    assert body["map_data"] is not None
    assert body["map_data"]["selected_destination_id"] == "toilet-0021"
    assert [destination["label"] for destination in body["map_data"]["destinations"]] == ["Lene-Voigt-Park"]


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
    assert "ist in" in body["answer_text"] or "Adresse ist" in body["answer_text"]
    assert "Nuernberger Strasse 31" in body["answer_text"] or "Nürnberger Straße 31" in body["answer_text"]
    assert body["map_data"]["origin"]["id"] == "leipzig_hbf"
    assert len(body["map_data"]["destinations"]) == 1
    assert body["map_data"]["destinations"][0]["page_id"] in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}


def test_cold_query_returns_ruecke_with_address_not_addressless_bridge(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/query/answer", json={"transcript": "Mir ist kalt", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0] == "uebernachtungshaus-ruecke"
    assert "Übernachtungshaus Rücke" in body["answer_text"]
    assert "Rückmarsdorfer Str. 5-7" in body["answer_text"]
    assert "Heilsarmee" not in body["answer_text"]
    assert "Bruecke" not in body["answer_text"]
    assert "keine genaue Adresse" not in body["answer_text"]


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
    lowered = body["answer_text"].casefold()
    assert "download the app" not in lowered
    assert "check the website" not in lowered
    assert "search online" not in lowered
    assert "google maps" not in lowered


def test_food_overview_answer_can_return_multiple_map_markers(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "where can i get food in leipzig", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["map_data"] is not None
    assert len(body["map_data"]["destinations"]) >= 2
    destination_ids = {item["page_id"] for item in body["map_data"]["destinations"]}
    assert "tafel-leipzig-markkleeberg" not in destination_ids
    lowered = body["answer_text"].casefold()
    assert "download the app" not in lowered
    assert "check the website" not in lowered
    assert "search online" not in lowered


def test_non_map_statuses_return_null_map_data(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    unknown = client.post("/api/query/answer", json={"transcript": "qwertz asdf yxv", "language": "en"}).json()
    clarify = client.post("/api/query/answer", json={"transcript": "help", "language": "en"}).json()
    crisis = client.post("/api/query/answer", json={"transcript": "I want to kill myself", "language": "en"}).json()
    out_of_scope = client.post("/api/query/answer", json={"transcript": "How do telescopes work?", "language": "en"}).json()

    assert unknown["map_data"] is None
    assert clarify["map_data"] is None
    assert crisis["map_data"] is None
    assert out_of_scope["map_data"] is None


def test_out_of_leipzig_place_is_not_rendered_as_map_destination(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "tafel markkleeberg", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_page_ids"][0] == "tafel-leipzig-markkleeberg"
    assert body["map_data"] is None


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


def test_missing_detail_answer_says_so_naturally(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "wie ist die adresse von cabl", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0] == "cabl-uvo"
    assert "keine genaue Adresse" in body["answer_text"] or "nicht klar" in body["answer_text"]


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
        json={"transcript": "is it open today?", "language": "en", "session_id": first["session_id"]},
    ).json()

    assert first["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert second["retrieved_page_ids"][0] == first["retrieved_page_ids"][0]
    assert second["session_id"] == first["session_id"]


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
        json={"transcript": "is there another place?", "language": "en", "session_id": first["session_id"]},
    ).json()

    assert first["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert second["retrieved_page_ids"][0] != first["retrieved_page_ids"][0]


def test_session_follow_up_keeps_same_place_for_hours_question(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "Wo kann ich duschen?", "language": "de", "session_id": "session-3"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Ist es sonntags offen?", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert first["retrieved_page_ids"][0] in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}
    assert second["retrieved_page_ids"][0] in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}
    assert "keine eigenen Öffnungszeiten" in second["answer_text"]


def test_session_follow_up_keeps_same_place_for_address_question(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "Wo kann ich duschen?", "language": "de", "session_id": "session-4"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Wie ist die Adresse?", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["retrieved_page_ids"][0] in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}
    assert (
        "Nuernberger Strasse 31" in second["answer_text"]
        or "Nürnberger Straße 31" in second["answer_text"]
        or "NÃ¼rnberger StraÃŸe 31" in second["answer_text"]
    )


def test_session_alternative_follow_up_avoids_same_place_family(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "Wo kann ich duschen?", "language": "de", "session_id": "session-5"},
    ).json()
    client.post(
        "/api/query/answer",
        json={"transcript": "Wie ist die Adresse?", "language": "de", "session_id": first["session_id"]},
    ).json()
    third = client.post(
        "/api/query/answer",
        json={"transcript": "Gibt es noch einen anderen Ort?", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert first["retrieved_page_ids"][0] in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}
    assert third["retrieved_page_ids"][0] not in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}


def test_end_session_endpoint_marks_conversation_ended(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "Wo kann ich duschen?", "language": "de"},
    ).json()
    ended = client.post("/api/session/end", json={"session_id": first["session_id"]})

    assert ended.status_code == 200
    body = ended.json()
    assert body["session_id"] == first["session_id"]
    assert body["session_status"] == "ended"
    assert body["session_event"] == "ended_reset"


def test_appointment_follow_up_stays_grounded_on_cabl(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "What is CABL?", "language": "en"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Do I need an appointment?", "language": "en", "session_id": first["session_id"]},
    ).json()

    assert second["session_event"] == "continued"
    assert second["session_id"] == first["session_id"]
    assert second["retrieved_page_ids"][0] == "cabl-uvo"
    assert second["status"] == "ok"


def test_unrelated_query_resets_and_returns_out_of_scope(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/api/query/answer",
        json={"transcript": "Where can I shower?", "language": "en"},
    ).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "How do telescopes work?", "language": "en", "session_id": first["session_id"]},
    ).json()

    assert second["session_event"] == "context_reset"
    assert second["session_id"] != first["session_id"]
    assert second["status"] == "out_of_scope"
    assert second["out_of_scope"] is True
    assert second["retrieved_page_ids"] == []


def test_crisis_query_supports_german_response(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/query/answer", json={"transcript": "Ich will sterben", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "crisis"
    assert body["crisis_mode"] is True
    assert "112" in body["answer_text"]
    assert "110" in body["answer_text"]


def test_transcribe_endpoint_returns_graceful_error_for_mock_without_debug(monkeypatch, tmp_path: Path) -> None:
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
    assert body["status"] == "error"
    assert body["provider"] == "mock"
    assert body["transcript"] == ""
    assert body["text"] == ""
    assert body["language"] == "de"
    assert "Mock STT cannot transcribe real audio" in body["detail"]


def test_transcribe_endpoint_accepts_debug_transcript(monkeypatch, tmp_path: Path) -> None:
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
            data={"language": "de", "debug_transcript": "Ich brauche Medizin."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"
    assert body["transcript"] == "Ich brauche Medizin."
    assert body["text"] == body["transcript"]
    assert body["language"] == "de"


def test_faster_whisper_provider_falls_back_gracefully(monkeypatch) -> None:
    def fail_init(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("missing local whisper model")

    monkeypatch.setattr("app.providers.stt.FasterWhisperProvider", fail_init)

    provider = create_stt_provider("faster_whisper")
    health = provider.health()

    assert provider.name == "mock"
    assert health["configured_provider"] == "faster_whisper"
    assert health["ready"] is False
    assert health["real_audio"] is False
    assert health["fallback_from"] == "faster_whisper"
    assert "missing local whisper model" in str(health["detail"])


def test_synthesize_endpoint_returns_unavailable_when_piper_assets_are_missing(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "piper")
    monkeypatch.setenv("LENA_PIPER_BINARY", "C:/missing/piper.exe")
    monkeypatch.setenv("LENA_PIPER_VOICE_DE", "C:/missing/de.onnx")
    app = create_app()
    client = TestClient(app)

    health = client.get("/api/health").json()
    assert health["tts_provider"] == "mock"
    assert health["tts_configured_provider"] == "piper"
    assert health["tts_ready"] is False

    response = client.post("/api/speech/synthesize", json={"text": "Ich bin LENA.", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["provider"] == "mock"
    assert body["audio_url"] is None
