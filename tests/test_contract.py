from __future__ import annotations

import json
from pathlib import Path

from app.kb import KnowledgeBase
from app.models import MapData, QueryAnswerResponse, PageMetadata


def test_published_contract_is_loadable() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "published"
    kb = KnowledgeBase(root)
    assert kb.dataset.manifest.page_count == len(kb.dataset.pages)
    assert kb.dataset.pages


def test_pages_json_matches_minimum_shape() -> None:
    pages_path = Path(__file__).resolve().parents[1] / "data" / "published" / "index" / "pages.json"
    pages = json.loads(pages_path.read_text(encoding="utf-8"))
    for item in pages:
        page = PageMetadata.model_validate(item)
        assert page.page_id
        assert page.category
        assert page.description
        assert page.aliases
        assert page.file_path.endswith(".md")


def test_query_answer_response_accepts_nullable_map_data() -> None:
    response = QueryAnswerResponse.model_validate(
        {
            "answer_text": "Test",
            "status": "ok",
            "provider": "template",
            "session_id": "session-1",
            "map_data": None,
        }
    )
    assert response.map_data is None

    mapped = QueryAnswerResponse.model_validate(
        {
            "answer_text": "Test",
            "status": "ok",
            "provider": "template",
            "session_id": "session-2",
            "map_data": {
                "origin": {
                    "id": "leipzig_hbf",
                    "label": "Leipzig Hauptbahnhof",
                    "address": "Willy-Brandt-Platz 5, 04109 Leipzig",
                    "latitude": 51.3465518,
                    "longitude": 12.3830858,
                },
                "destinations": [
                    {
                        "id": "leipziger-oase",
                        "page_id": "leipziger-oase",
                        "label": "Leipziger Oase",
                        "organization_label": "Diakonie Leipzig",
                        "service_type": "day_center",
                        "address": "Nuernberger Strasse 31, 04103 Leipzig",
                        "latitude": 51.3349456,
                        "longitude": 12.3840015,
                        "distance_meters": 1300,
                        "description": "Tageseinrichtung fuer wohnungslose Menschen.",
                        "opening_hours": ["Montag bis Freitag 08:00 bis 16:00 Uhr"],
                    }
                ],
                "selected_destination_id": "leipziger-oase",
            },
        }
    )
    assert isinstance(mapped.map_data, MapData)
    assert mapped.map_data.destinations[0].page_id == "leipziger-oase"


def test_published_dataset_contains_atomic_service_pages() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "published"
    kb = KnowledgeBase(root)
    page_ids = {page.page_id for page in kb.dataset.pages}
    assert "tafel-leipzig-zentrale-lindenau-west" in page_ids
    assert "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner" in page_ids
    assert "wohnungsnotfallhilfe-pdf-insel" in page_ids
    assert "leipzig-schadensminimierung-schwanenteich" in page_ids


def test_published_dataset_fixes_known_problem_pages() -> None:
    pages_path = Path(__file__).resolve().parents[1] / "data" / "published" / "index" / "pages.json"
    pages = json.loads(pages_path.read_text(encoding="utf-8"))
    by_id = {page["page_id"]: page for page in pages}

    leipziger_oase = by_id["leipziger-oase"]
    assert leipziger_oase["service_type"] == "day_center"
    assert leipziger_oase["address"] == "Nuernberger Strasse 31, 04103 Leipzig"
    assert leipziger_oase["phone"] == "0341 2682670"
    assert leipziger_oase["opening_hours"] == [
        "Montag bis Freitag 08:00 bis 16:00 Uhr",
        "Samstag und Feiertage 09:00 bis 14:00 Uhr",
    ]

    catalog_oase = by_id["wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"]
    assert catalog_oase["opening_hours"] == [
        "Montag bis Freitag 08:00 bis 16:00 Uhr",
        "Samstag und Feiertage 09:00 bis 14:00 Uhr",
    ]
    lowered_aliases = {alias.casefold() for alias in catalog_oase["aliases"]}
    assert "pdf" not in lowered_aliases
    assert "homeless" not in lowered_aliases

    cabl = by_id["cabl-uvo"]
    assert cabl["service_type"] == "medical_consultation"
    assert cabl["address"] is None
    assert cabl["opening_hours"] == []
    assert "multi_location_service" in cabl["validation_issues"]

    for page_id in ["wohnungsnotfallhilfe-pdf", "leipzig-schadensminimierung", "tafel-leipzig"]:
        page = by_id[page_id]
        assert page["service_type"] == "service_catalog"
        assert page["address"] is None
        assert page["opening_hours"] == []


def test_frontend_kiosk_controls_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "app" / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (root / "app" / "static" / "app.js").read_text(encoding="utf-8")

    for element_id in [
        "backButton",
        "homeButton",
        "changeLanguageButton",
        "cancelRequestButton",
        "helpButton",
        "emergencyNavButton",
        "endConversationButton",
        "textModeButton",
    ]:
        assert f'id="{element_id}"' in index_html
        assert element_id in app_js

    assert "toilet:" in app_js
    assert "shower:" in app_js
    assert "AbortController" in app_js
