from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _client(monkeypatch) -> TestClient:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    monkeypatch.setenv("LENA_STT_PROVIDER", "mock")
    monkeypatch.setenv("LENA_TTS_PROVIDER", "mock")
    return TestClient(create_app())


def test_symbol_config_contains_all_languages_and_sleep_substeps(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.get("/api/symbol/config?language=ru")

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "ru"
    sleep = next(item for item in body["categories"] if item["id"] == "sleep")
    assert sleep["label"]
    assert {item["id"] for item in sleep["substeps"]} == {"men", "women", "young", "unsure"}
    assert next(item for item in body["categories"] if item["id"] == "emergency")["result_mode"] == "static"


def test_sleep_symbol_routes_men_to_mens_shelter_with_map(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "sleep", "substep_id": "men", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "symbol"
    assert body["cards"][0]["page_id"] == "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner"
    assert body["cards"][0]["has_map_location"] is True
    assert body["map_data"] is not None
    assert body["map_data"]["destinations"][0]["page_id"] == "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner"


def test_sleep_symbol_routes_women_to_womens_shelter(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "sleep", "substep_id": "women", "language": "en"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["cards"][0]["page_id"] == "wohnungsnotfallhilfe-pdf-uebernachtungshaus-frauen-katalog"
    assert "112" not in body["answer_text"]


def test_food_symbol_returns_food_cards_without_claiming_open_now(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "food", "language": "en"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["cards"]
    assert body["retrieved_page_ids"][0].startswith("tafel-leipzig")
    assert "open now" not in body["answer_text"].casefold()


def test_hygiene_shower_symbol_prefers_day_centers(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "hygiene", "substep_id": "shower", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    page_ids = [card["page_id"] for card in body["cards"]]
    assert {"leipziger-oase", "wohnungsnotfallhilfe-pdf-insel"} & set(page_ids)
    assert "leipzig-schadensminimierung" not in page_ids
    assert sum(1 for card in body["cards"] if card["title"] == "Leipziger Oase") == 1


def test_hygiene_toilet_symbol_returns_costed_public_toilet_map_points(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "hygiene", "substep_id": "toilet", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["map_data"] is not None
    assert len(body["map_data"]["destinations"]) == 21
    assert body["map_data"]["destinations"][0]["service_type"] == "public_toilet"
    descriptions = " ".join(card["description"] or "" for card in body["cards"])
    map_descriptions = " ".join(item["description"] or "" for item in body["map_data"]["destinations"])
    assert "50 Cent" in descriptions
    assert "kostenfrei" in map_descriptions
    assert body["no_map_reason"] is None


def test_emergency_symbol_is_static_and_has_no_map(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "emergency", "language": "en"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "crisis"
    assert body["static_response"] is True
    assert "112" in body["answer_text"]
    assert "110" in body["answer_text"]
    assert body["map_data"] is None
    assert body["cards"] == []
    assert body["retrieved_page_ids"] == ["notfallkontakte", "telefonseelsorge-leipzig"]


def test_water_symbol_returns_official_fountain_map_points(monkeypatch) -> None:
    client = _client(monkeypatch)

    response = client.post("/api/symbol/answer", json={"category_id": "water", "language": "en"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["map_data"] is not None
    assert len(body["map_data"]["destinations"]) == 35
    assert body["map_data"]["destinations"][0]["service_type"] == "drinking_fountain"
    assert body["cards"][0]["page_id"] == body["map_data"]["destinations"][0]["id"]
    assert body["no_map_reason"] is None
