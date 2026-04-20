from __future__ import annotations

from pathlib import Path

from app.kb import KnowledgeBase
from app.models import Language
from app.retrieval import RetrievalEngine


def _engine() -> RetrievalEngine:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    return RetrievalEngine(kb)


def test_umlaut_query_matches_same_top_page() -> None:
    engine = _engine()
    ascii_results = engine.retrieve("uebernachtung haus", Language.DE)
    umlaut_results = engine.retrieve("\u00fcbernachtung haus", Language.DE)
    assert ascii_results
    assert umlaut_results
    assert ascii_results[0].page_id == "uebernachtungshaus-ruecke"
    assert umlaut_results[0].page_id == ascii_results[0].page_id


def test_exact_page_id_query_beats_partial_title_match() -> None:
    engine = _engine()
    results = engine.retrieve("gesundheitsamt", Language.DE)
    assert results
    assert results[0].page_id == "gesundheitsamt"
