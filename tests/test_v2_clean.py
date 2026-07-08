from __future__ import annotations

import io
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Language, TemporalContext
from app.v2.kb import V2KnowledgeBase
from app.v2.main import _apply_v2_provider_defaults, create_v2_app
from app.v2.service import V2AnswerService, _availability_for_offer, _heuristic_intent


SOURCE_URL = "https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung"
ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "v2" / "curated_kb" / "offers.json"


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    return TestClient(create_v2_app())


def test_v1_app_remains_default(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    client = TestClient(create_app())

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "variant" not in body
    assert body["kb_version"]


def test_v2_health_reports_separate_runtime(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["variant"] == "v2"
    assert body["authoritative_source_url"] == SOURCE_URL
    assert body["kb_path"].endswith("data\\v2\\curated_kb\\offers.json") or body["kb_path"].endswith("data/v2/curated_kb/offers.json")
    assert body["stt_configured_provider"] == "mock"
    assert body["rewrite_provider"] == "v2_clean"
    assert body["configured_rewrite_provider"] == "template"
    assert body["llm_active"] is False
    assert body["llm_api_key_configured"] is False
    assert body["v2_prompt_loaded"] is True
    assert body["v2_prompt_path"].endswith("system_prompt_v2.md")
    assert body["tts_configured_provider"] == "mock"
    assert body["voices"]["de"]["female_preferred"] is True
    assert body["map"]["leaflet_available"] is True
    assert body["last_transcript_source"] is None


def test_v2_health_reports_llm_active_for_blablador_config(monkeypatch) -> None:
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "blablador")
    monkeypatch.setenv("LENA_LLM_API_KEY", "test-token")
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    client = TestClient(create_v2_app())

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["llm_active"] is True
    assert body["rewrite_model"] == "alias-large"
    assert body["v2_prompt_loaded"] is True


def test_v2_startup_defaults_prefer_blablador_stt_and_tts(monkeypatch) -> None:
    for key in (
        "LENA_REWRITE_PROVIDER",
        "LENA_LLM_BASE_URL",
        "LENA_LLM_MODEL",
        "LENA_STT_PROVIDER",
        "LENA_TTS_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    _apply_v2_provider_defaults()

    assert os.environ["LENA_REWRITE_PROVIDER"] == "blablador"
    assert os.environ["LENA_LLM_BASE_URL"] == "https://api.blablador.fz-juelich.de/v1/"
    assert os.environ["LENA_LLM_MODEL"] == "alias-large"
    assert os.environ["LENA_STT_PROVIDER"] == "faster_whisper"
    assert os.environ["LENA_TTS_PROVIDER"] == "piper"


def test_v2_kb_is_one_source_reviewed_subset() -> None:
    kb = V2KnowledgeBase(KB_PATH)
    offers = kb.v2_dataset.offers

    assert len(offers) >= 25
    assert kb.v2_dataset.authoritative_source_url == SOURCE_URL
    assert not any("tafel" in f"{offer.offer_id} {offer.name}".casefold() for offer in offers)
    assert not any(offer.category == "emergency_system" for offer in offers)
    for offer in offers:
        assert offer.review_status in {"reviewed", "published"}
        assert offer.source_url == SOURCE_URL
        assert offer.source_evidence
        assert offer.reviewer
        assert offer.reviewed_at


def test_v2_alternative_iii_contains_source_detail_fields_for_map() -> None:
    kb = V2KnowledgeBase(KB_PATH)
    offer = kb.get_offer("alternative-iii-notschlafstelle")
    page = kb.get_page("alternative-iii-notschlafstelle")

    assert offer.address == "Braunstraße 28A, 04347 Leipzig"
    assert offer.phone == "0341 30879740"
    assert offer.email == "zfdalternative3@sanktgeorg.de"
    assert offer.website
    assert "Montag - Freitag: 18:00 - 10:00 Uhr" in offer.opening_times
    assert "Wochenende und Feiertag ganztägig geöffnet" in offer.opening_times
    assert offer.coordinates is not None
    assert page.entity_kind == "service_location"
    assert page.address == offer.address
    assert page.latitude == offer.coordinates.latitude


def test_v2_all_offers_have_detail_locations_for_maps() -> None:
    kb = V2KnowledgeBase(KB_PATH)

    missing = [
        offer.offer_id
        for offer in kb.v2_dataset.offers
        if offer.is_user_offer and not (offer.address and offer.coordinates and offer.detail_source_urls)
    ]

    assert missing == []


def test_v2_all_offers_have_annotated_card_summary_keywords_and_facts() -> None:
    kb = V2KnowledgeBase(KB_PATH)

    missing = [
        offer.offer_id
        for offer in kb.v2_dataset.offers
        if offer.is_user_offer and not (offer.card_summary and offer.retrieval_keywords and offer.facts)
    ]

    assert missing == []


def test_v2_symbol_config_keeps_speech_outside_help_categories(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.get("/api/symbol/config?language=de")
    assert response.status_code == 200
    categories = response.json()["categories"]
    ids = [item["id"] for item in categories]
    labels = [item["label"] for item in categories]
    assert ids == ["food", "sleep", "medical", "advice", "emergency"]
    assert labels[:4] == ["Essen", "Schlafen", "Medizin", "Beratung allgemein"]
    assert "speech" not in ids
    assert "chat" not in ids


def test_v2_static_ui_has_separate_talk_panel_and_transcript_review() -> None:
    html = (ROOT / "app" / "v2" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "v2" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'class="symbol-grid v2-home-symbol-grid"' in html
    assert 'id="symbolGrid"' in html
    assert 'id="talkPanel"' in html
    assert 'id="transcriptReview"' in html
    assert 'id="mapPanel"' in html
    assert 'id="answerMap"' in html
    assert 'id="textPanel"' in html and 'id="textPanel" aria-labelledby="textTitle" hidden' in html
    assert 'id="textModeButton"' in html
    assert 'id="transcriptReview" aria-labelledby="reviewTitle" hidden' in html
    assert "Sprich mit mir" in html
    assert "Zurück" in html
    assert "Anhören" in html
    assert "Zurueck" not in html
    assert "Anhoeren" not in html
    assert "Spracheingabe ist ein Modus" not in html
    assert "Direkt waehlen" not in html
    assert "aria-label=\"Anfrage abbrechen\"" in html
    assert "aria-label=\"Sitzung beenden\"" in html
    assert "/leaflet/leaflet.css" in html
    assert "/leaflet/leaflet.js" in html
    assert "function iconMarkup" in js
    assert "openTextInput" in js
    assert "textModeButton" in js
    assert "\"[]\"" not in js
    assert "bed: \"bed\"" not in js
    assert ".filter((item) => item.id !== \"emergency\")" in js
    assert "sendQuery(byId(\"transcriptInput\").value)" in js
    assert "is-selected" in js
    assert "is-loading" in js
    assert "aria-busy" in js
    assert "renderMap(data.map_data)" in js
    assert "marker.on(\"click\"" in js
    assert "mapPopup(destination)" in js
    assert "selectOffer(card.page_id" in js
    assert "metaChip(\"map\", copy().chipPlace" in js
    assert "metaChip(\"clock\", copy().chipTime" in js
    assert "metaChip(\"phone\", copy().chipPhone" in js
    assert "markerStyle(" in js
    assert "circleMarker" in js
    assert "lena-map-marker--selected" in js
    assert 'navBack: "Back"' in js
    assert 'navStart: "Nachalo"' in js
    assert 'answerTitle: "Answer"' in js
    assert "function resetInteractionState" in js
    assert "function goHome" in js
    assert "function goBack" in js
    assert "speakIntroOnce" in js
    assert "function speakText" in js
    assert "function speakWithBrowser" in js
    assert "speechSynthesis" in js
    assert "await speakText(state.lastAnswer)" in js
    assert "await speakText(text)" in js
    assert 'showMain(button.dataset.language || "de", { speakIntro: true })' in js
    assert "copy().detailsShown" in js
    assert "card.description || card.card_summary" in js
    assert "(card.opening_hours || []).join" in js
    assert "timeSummaryText(card.opening_hours || [])" in js
    assert "function usefulTimes" in js
    assert "offer-card__speak" in js
    assert "cardSpeechText(card)" in js
    assert "void speakText(cardSpeechText(card))" in js


def test_v2_kb_visible_fields_use_german_umlauts() -> None:
    dataset = json.loads((ROOT / "data" / "v2" / "curated_kb" / "offers.json").read_text(encoding="utf-8"))
    offers = {offer["offer_id"]: offer for offer in dataset["offers"]}

    alternative = offers["alternative-iii-notschlafstelle"]
    assert "Zentrum für Drogenhilfe" in alternative["name"]
    assert "Braunstraße" in alternative["address"]
    assert "Übernachtung" in alternative["card_summary"]
    assert "Für Frauen und Männer" in alternative["requirements"]

    leutzsch = offers["uebernachtungshaus-maenner-leutzsch"]
    assert leutzsch["name"] == "Übernachtungshaus Rücke"
    assert leutzsch["address"] == "Rückmarsdorfer Straße 5-7, 04179 Leipzig"
    assert leutzsch["phone"] == "0341 1234504"
    assert leutzsch["requirements"] == "Volljährig, männlich und wohnungslos."
    assert "volljährige wohnungslose Männer" in leutzsch["card_summary"]


def test_v2_css_preserves_hidden_steps() -> None:
    css = (ROOT / "app" / "v2" / "static" / "styles.css").read_text(encoding="utf-8")

    assert "[hidden]" in css
    assert "display: none !important" in css
    assert ".screen {" in css
    assert ".meta-chip__label" in css
    assert ".meta-chip__icon" in css


def test_v2_prompt_file_exists_and_sets_guardrails() -> None:
    prompt = (ROOT / "data" / "prompts" / "system_prompt_v2.md").read_text(encoding="utf-8")

    assert "selected UI language" in prompt
    assert "informal" in prompt
    assert "`du`" in prompt
    assert "Do not invent" in prompt
    assert "medical diagnosis" in prompt


def test_v2_food_answer_is_informal_and_source_grounded(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/query/answer", json={"transcript": "Ich brauche Essen.", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "du" in body["answer_text"].casefold()
    assert "Sie" not in body["answer_text"]
    assert body["retrieved_page_ids"][0] == "hilfebus"
    assert SOURCE_URL in body["sources"]
    assert body["answer_evidence"]
    assert body["last_checked"] == "2026-06-15"
    assert body["map_data"]["destinations"]


def test_v2_selected_language_is_used_for_answer(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/query/answer", json={"transcript": "I need somewhere to sleep tonight.", "language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert not body["answer_text"].startswith("I cannot promise")
    assert "Who needs a place to sleep?" in body["answer_text"]
    assert "0152 33661087" in body["answer_text"]
    assert body["follow_up_options"]
    assert body["cards"]
    assert body["retrieved_page_ids"]


def test_v2_sleep_query_uses_short_structured_mode(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/query/answer", json={"transcript": "Wo kann ich am Mittwoch schlafen?", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert not body["answer_text"].startswith("Ich kann keinen freien Platz versprechen")
    assert "Für wen suchst du einen Schlafplatz?" in body["answer_text"]
    assert "0152 33661087" in body["answer_text"]
    assert body["follow_up_options"]
    assert body["cards"]
    assert body["map_data"]["destinations"]
    assert body["retrieved_page_ids"][:3] == [
        "soziale-wohnhilfen-notunterbringung",
        "uebernachtungshaus-maenner-leutzsch",
        "hilfebus",
    ]
    assert "Wichtig: Für Frauen und Männer" not in body["answer_text"]


def test_v2_sleep_target_follow_up_prioritizes_women_shelter(monkeypatch) -> None:
    client = _client(monkeypatch)

    first = client.post("/api/query/answer", json={"transcript": "Wo kann ich schlafen?", "language": "de"}).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Ich bin eine Frau", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["retrieved_page_ids"][0] == "aww-frauen-uebernachtungshaus"
    assert second["cards"][0]["page_id"] == "aww-frauen-uebernachtungshaus"
    assert "Wohnungslose Frauen" in second["cards"][0]["target_groups"]


def test_v2_sleep_target_follow_up_prioritizes_ruecke_for_men(monkeypatch) -> None:
    client = _client(monkeypatch)

    first = client.post("/api/query/answer", json={"transcript": "Wo kann ich schlafen?", "language": "de"}).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Ich bin ein Mann", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["retrieved_page_ids"][0] == "uebernachtungshaus-maenner-leutzsch"
    assert second["cards"][0]["title"] == "Rücke"


def test_v2_sleep_target_follow_up_prioritizes_drug_use_shelters(monkeypatch) -> None:
    client = _client(monkeypatch)

    first = client.post("/api/query/answer", json={"transcript": "Wo kann ich schlafen?", "language": "de"}).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Drogengebrauch / Konsum", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["retrieved_page_ids"][:2] == ["alternative-i-notschlafstelle", "alternative-iii-notschlafstelle"]
    assert "Drogengebrauch" in second["answer_text"]


def test_v2_symbol_cards_localize_visible_description(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "medical", "language": "ru"})

    assert response.status_code == 200
    body = response.json()
    cabl = next(card for card in body["cards"] if card["page_id"] == "cabl-clearingstelle")
    assert "Pomoshch lyudyam" in cabl["description"]
    assert "Clearingstelle für Menschen" not in cabl["description"]
    assert cabl["services_provided"]
    assert all("Sozialberatung" not in service for service in cabl["services_provided"])


def test_v2_food_answer_stays_short_and_cards_use_primary_phone(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/query/answer", json={"transcript": "Ich brauche Essen.", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert "Herr Tino" not in body["answer_text"]
    assert "Diakonisches Werk Innere Mission" not in body["answer_text"]
    assert "Tippe auf eine Karte" in body["answer_text"]
    hilfebus = next(card for card in body["cards"] if card["page_id"] == "hilfebus")
    assert hilfebus["title"] == "Hilfebus"
    assert hilfebus["phone"] == "0152 33661087 (nur zu Einsatzzeiten)"
    assert ";" not in hilfebus["phone"]


def test_v2_rejects_verbose_llm_answer_with_phone_details(monkeypatch) -> None:
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "blablador")
    monkeypatch.setenv("LENA_LLM_API_KEY", "test-token")
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")

    async def no_intent(self, fallback, conversation_context, temporal_context):
        return None

    async def verbose_answer(self, transcript, language, intent, offers, deterministic, conversation_context, temporal_context):
        return (
            "Hier kannst du nach Essen oder Getränken fragen: Hilfebus Adresse: Demmeringstraße 32, "
            "04177 Leipzig. Telefon: 0152 33661087; 0175 6758041. Diakonie Streetwork Telefon: 0151 56382800."
        )

    monkeypatch.setattr(V2AnswerService, "_llm_intent", no_intent)
    monkeypatch.setattr(V2AnswerService, "_llm_answer", verbose_answer)
    client = TestClient(create_v2_app())

    response = client.post("/api/query/answer", json={"transcript": "Ich brauche Essen.", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer_text"].startswith("Ich habe Orte für Essen")
    assert "Telefon:" not in body["answer_text"]
    assert "0152" not in body["answer_text"]


def test_v2_medical_symbol_includes_local_stand_times_and_drug_help(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "medical", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    page_ids = [card["page_id"] for card in body["cards"]]
    assert "uvo-medical-outreach" in page_ids
    assert "kontaktcafe-alternative-i" in page_ids or "alternative-i-notschlafstelle" in page_ids
    uvo = next(card for card in body["cards"] if card["page_id"] == "uvo-medical-outreach")
    assert any("Hauptbahnhof" in value or "Köhlerstraße" in value for value in uvo["opening_hours"])
    assert any("Mittwoch" in value and "Hauptbahnhof" in value for value in uvo["opening_hours"])
    assert any("Freitag" in value and "Köhlerstraße" in value for value in uvo["opening_hours"])
    assert any("Sonntag" in value and "Hauptbahnhof" in value for value in uvo["opening_hours"])
    drug_card = next(card for card in body["cards"] if card["page_id"] in {"kontaktcafe-alternative-i", "alternative-i-notschlafstelle"})
    text = " ".join([drug_card["description"], *drug_card["services_provided"]])
    assert "Spritzen" in text or "Konsummittel" in text or "Safer Use" in text


def test_v2_safe_team_wohnen_shows_all_known_times_and_map_points(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "food", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    safe = next(card for card in body["cards"] if card["page_id"] == "safe-team-wohnen")
    assert "Büro" in safe["description"]
    assert "Mi/Fr" in safe["description"]
    assert any("Demmeringstraße" in value for value in safe["opening_hours"])
    assert any("Schwanenteich" in value for value in safe["opening_hours"])
    assert any("Hauptbahnhof" in value for value in safe["opening_hours"])
    safe_destinations = [destination for destination in body["map_data"]["destinations"] if destination["page_id"] == "safe-team-wohnen"]
    assert len(safe_destinations) >= 3
    assert any("Demmeringstraße" in destination["address"] for destination in safe_destinations)


def test_v2_target_groups_are_not_raw_keyword_tokens(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "food", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    all_groups = [group for card in body["cards"] for group in card["target_groups"]]
    assert all("adults" not in group and "homeless" not in group for group in all_groups)


def test_v2_self_description_is_deterministic_and_localized(monkeypatch) -> None:
    client = _client(monkeypatch)

    german = client.post("/api/query/answer", json={"transcript": "Wer bist du?", "language": "de"}).json()
    english = client.post("/api/query/answer", json={"transcript": "Who are you?", "language": "en"}).json()

    assert german["status"] == "self_description"
    assert "Ich bin LENA" in german["answer_text"]
    assert "Wissensbasis" not in german["answer_text"]
    assert english["status"] == "self_description"
    assert "I am LENA" in english["answer_text"]
    assert "knowledge base" not in english["answer_text"].casefold()


def test_v2_out_of_scope_is_short_and_domain_bound(monkeypatch) -> None:
    client = _client(monkeypatch)

    joke = client.post("/api/query/answer", json={"transcript": "Tell me a joke", "language": "en"}).json()
    capital = client.post("/api/query/answer", json={"transcript": "What is the capital of France?", "language": "en"}).json()

    assert joke["status"] == "out_of_scope"
    assert "support services in Leipzig" in joke["answer_text"]
    assert "knowledge base" not in joke["answer_text"].casefold()
    assert capital["status"] == "out_of_scope"


def test_v2_follow_up_context_handles_topic_shift(monkeypatch) -> None:
    client = _client(monkeypatch)

    first = client.post("/api/query/answer", json={"transcript": "Ich brauche Essen.", "language": "de"}).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Und wo kann ich schlafen?", "language": "de", "session_id": first["session_id"]},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "ok"
    assert body["session_id"] == first["session_id"]
    assert any("nacht" in page_id or "unterbringung" in page_id or "uebernachtung" in page_id for page_id in body["retrieved_page_ids"])


def test_v2_referential_follow_up_keeps_previous_context(monkeypatch) -> None:
    client = _client(monkeypatch)

    first = client.post("/api/query/answer", json={"transcript": "Ich brauche Essen.", "language": "de"}).json()
    second = client.post(
        "/api/query/answer",
        json={"transcript": "Gibt es das heute?", "language": "de", "session_id": first["session_id"]},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["status"] == "ok"
    assert body["session_id"] == first["session_id"]
    assert set(body["retrieved_page_ids"]) & set(first["retrieved_page_ids"])


def test_v2_emergency_is_deterministic_and_not_an_offer(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "emergency", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "crisis"
    assert body["static_response"] is True
    assert body["cards"] == []
    assert body["retrieved_page_ids"] == []
    assert "112" in body["answer_text"]


def test_v2_mock_stt_does_not_hardcode_food_transcript(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("speech.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        data={"language": "de"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["transcript"] == ""
    assert body["text"] == ""
    assert body["language"] == "de"
    assert "Wo kann ich heute essen" not in body["detail"]
    health = client.get("/api/health").json()
    assert health["last_transcript_source"] == "mock_unavailable"


def test_v2_debug_transcript_is_explicit_only(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("speech.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        data={"language": "de", "debug_transcript": "Ich brauche Medizin."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["transcript"] == "Ich brauche Medizin."
    assert body["text"] == "Ich brauche Medizin."
    assert body["language"] == "de"
    health = client.get("/api/health").json()
    assert health["last_transcript_source"] == "debug_transcript"
    assert health["last_transcript_language"] == "de"


def test_v2_tts_endpoint_fails_gracefully_with_mock_provider(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post(
        "/api/speech/synthesize",
        json={"text": "Ich bin LENA.", "language": "de"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["provider"] == "mock"
    assert body["audio_url"] is None


def test_v2_symbol_food_returns_cards_and_map(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "food", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["cards"]
    assert body["map_data"]["destinations"]
    assert any(destination["page_id"] in {"hilfebus", "bahnhofsmission"} for destination in body["map_data"]["destinations"])
    assert any(card["page_id"] == "safe-team-wohnen" for card in body["cards"])
    assert any("Schwanenteich" in destination["address"] for destination in body["map_data"]["destinations"])
    hilfebus = next(card for card in body["cards"] if card["page_id"] == "hilfebus")
    assert hilfebus["title"] == "Hilfebus"
    assert hilfebus["description"].startswith("Mobile Hilfe täglich 18-23 Uhr")
    assert hilfebus["description"] == hilfebus["card_summary"]
    assert hilfebus["phone"] == "0152 33661087 (nur zu Einsatzzeiten)"
    assert any("Täglich" in value and "18:00 - 23:00" in value for value in hilfebus["opening_hours"])
    assert any("Sonntag" in value and "Hauptbahnhof" in value for value in hilfebus["opening_hours"])
    health = client.get("/api/health").json()
    assert health["last_map_destination_count"] >= 1


def test_v2_symbol_advice_includes_safe_schwanenteich(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "advice", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert "safe-team-wohnen" in [card["page_id"] for card in body["cards"]]
    assert any(destination["page_id"] == "safe-team-wohnen" and "Schwanenteich" in destination["address"] for destination in body["map_data"]["destinations"])


def test_v2_time_availability_handles_current_day_examples() -> None:
    kb = V2KnowledgeBase(KB_PATH)
    tuesday_before_evening = TemporalContext(
        now_iso="2026-06-16T16:30:00+02:00",
        date_iso="2026-06-16",
        weekday_index=1,
        weekday_en="Tuesday",
        weekday_de="Dienstag",
        is_weekend=False,
        month=6,
        season="summer",
    )
    sunday_evening = TemporalContext(
        now_iso="2026-06-21T20:30:00+02:00",
        date_iso="2026-06-21",
        weekday_index=6,
        weekday_en="Sunday",
        weekday_de="Sonntag",
        is_weekend=True,
        month=6,
        season="summer",
    )

    today_intent = _heuristic_intent("Wo bekomme ich heute Essen?", Language.DE)
    safe_team = kb.get_offer("safe-team-wohnen")
    hilfebus = kb.get_offer("hilfebus")

    assert _availability_for_offer(safe_team, tuesday_before_evening, today_intent).status == "available_today_later"
    assert _availability_for_offer(hilfebus, tuesday_before_evening, today_intent).status == "available_today_later"
    assert _availability_for_offer(hilfebus, sunday_evening, today_intent).status == "open_now"


def test_v2_symbol_sleep_maps_alternative_iii(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "sleep", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    alt_card = next(card for card in body["cards"] if card["page_id"] == "alternative-iii-notschlafstelle")
    assert alt_card["address"] == "Braunstraße 28A, 04347 Leipzig"
    assert alt_card["phone"] == "0341 30879740"
    assert alt_card["email"] == "zfdalternative3@sanktgeorg.de"
    assert alt_card["has_map_location"] is True
    destinations = body["map_data"]["destinations"]
    assert any(destination["page_id"] == "alternative-iii-notschlafstelle" for destination in destinations)
    assert len(destinations) >= 5
    assert body["map_data"]["origin"]["label"] == "Leipzig Hauptbahnhof"


def test_v2_sleep_cards_keep_fixed_opening_times(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "sleep", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    ruecke = next(card for card in body["cards"] if card["page_id"] == "uebernachtungshaus-maenner-leutzsch")
    alternative = next(card for card in body["cards"] if card["page_id"] == "alternative-i-notschlafstelle")
    assert ruecke["opening_hours"][0] != "Zeiten bitte prüfen"
    assert any("16:00 - 08:00" in value for value in ruecke["opening_hours"])
    assert alternative["opening_hours"][0] != "Zeiten bitte prüfen"
    assert any("18:00 - 10:00" in value for value in alternative["opening_hours"])


def test_v2_medical_and_addiction_queries_stay_inside_v2_kb(monkeypatch) -> None:
    client = _client(monkeypatch)

    medical = client.post("/api/query/answer", json={"transcript": "Ich brauche einen Arzt.", "language": "de"}).json()
    addiction = client.post("/api/query/answer", json={"transcript": "Ich brauche Hilfe mit Drogen.", "language": "de"}).json()

    assert "uvo-medical-outreach" in medical["retrieved_page_ids"] or "cabl-clearingstelle" in medical["retrieved_page_ids"]
    assert any(page_id.startswith(("safe-team", "kontaktcafe")) for page_id in addiction["retrieved_page_ids"])
    assert all("tafel" not in page_id for page_id in [*medical["retrieved_page_ids"], *addiction["retrieved_page_ids"]])


def test_v2_retrieval_uses_annotated_keywords(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/query/answer", json={"transcript": "Ich brauche einen anonymen Behandlungsschein.", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert "cabl-clearingstelle" in body["retrieved_page_ids"]
