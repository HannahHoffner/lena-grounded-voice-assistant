from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Language, TemporalContext
from app.v2.kb import V2KnowledgeBase
from app.v2.main import create_v2_app
from app.v2.service import _availability_for_offer, _heuristic_intent


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
    assert body["rewrite_provider"] == "v2_clean"
    assert body["llm_active"] is False
    assert body["v2_prompt_loaded"] is True
    assert body["v2_prompt_path"].endswith("system_prompt_v2.md")
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
    assert "copy().detailsShown" in js
    assert "card.description || card.card_summary" in js


def test_v2_kb_visible_fields_use_german_umlauts() -> None:
    dataset = json.loads((ROOT / "data" / "v2" / "curated_kb" / "offers.json").read_text(encoding="utf-8"))
    offers = {offer["offer_id"]: offer for offer in dataset["offers"]}

    alternative = offers["alternative-iii-notschlafstelle"]
    assert "Zentrum für Drogenhilfe" in alternative["name"]
    assert "Braunstraße" in alternative["address"]
    assert "Übernachtung" in alternative["card_summary"]
    assert "Für Frauen und Männer" in alternative["requirements"]

    leutzsch = offers["uebernachtungshaus-maenner-leutzsch"]
    assert "Übernachtungshaus für wohnungslose Männer" == leutzsch["name"]
    assert "Rückmarsdorfer Straße" in leutzsch["address"]
    assert "5,00 €" in leutzsch["cost"]


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
    assert "I cannot promise" in body["answer_text"]
    assert body["retrieved_page_ids"]
    assert "hilfebus" not in body["retrieved_page_ids"][:2]


def test_v2_symbol_cards_localize_visible_description(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "medical", "language": "ru"})

    assert response.status_code == 200
    body = response.json()
    cabl = next(card for card in body["cards"] if card["page_id"] == "cabl-clearingstelle")
    assert "Zdes mozhno sprosit" in cabl["description"]
    assert "Clearingstelle für Menschen" not in cabl["description"]
    assert cabl["services_provided"]
    assert all("Sozialberatung" not in service for service in cabl["services_provided"])


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
    health = client.get("/api/health").json()
    assert health["last_transcript_source"] == "debug_transcript"
    assert health["last_transcript_language"] == "de"


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
    assert hilfebus["card_summary"].startswith("Hilfebus für obdachlose Menschen")
    assert hilfebus["description"] == hilfebus["card_summary"]
    assert hilfebus["phone"].startswith("0152 33661087")
    assert "nur zu Einsatzzeiten" in hilfebus["phone"]
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
