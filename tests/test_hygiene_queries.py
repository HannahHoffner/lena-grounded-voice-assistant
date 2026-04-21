from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.kb import KnowledgeBase
from app.main import create_app
from app.models import Language
from app.retrieval import RetrievalEngine


def _engine() -> RetrievalEngine:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    return RetrievalEngine(kb)


def test_shower_query_prefers_oase_or_insel_over_generic_schadensminimierung() -> None:
    engine = _engine()
    results = engine.retrieve("Wo kann ich duschen?", Language.DE)

    assert results
    assert results[0].page_id in {
        "leipziger-oase",
        "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog",
        "wohnungsnotfallhilfe-pdf-insel",
    }
    assert results[0].page_id != "leipzig-schadensminimierung"


def test_shower_answer_is_not_led_by_generic_schadensminimierung(monkeypatch) -> None:
    monkeypatch.setenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "false")
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "template")
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/query/answer", json={"transcript": "Wo kann ich duschen?", "language": "de"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrieved_page_ids"][0] != "leipzig-schadensminimierung"
    assert "Schadensminimierung ist eine passende Anlaufstelle" not in body["answer_text"]
