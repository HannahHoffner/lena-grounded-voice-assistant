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


def test_specific_schwanenteich_query_hits_atomic_streetwork_page() -> None:
    engine = _engine()
    results = engine.retrieve("schwanenteich essen", Language.DE)
    assert results
    assert results[0].page_id == "leipzig-schadensminimierung-schwanenteich"


def test_exact_address_query_prefers_matching_house_number() -> None:
    engine = _engine()
    results = engine.retrieve("nuernberger strasse 31", Language.DE)
    assert results
    assert results[0].page_id in {"leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"}
    assert results[0].page_id != "diakonie-kleiderkammern"


def test_specific_location_query_prefers_atomic_tafel_page() -> None:
    engine = _engine()
    results = engine.retrieve("tafel lindenau", Language.DE)
    assert results
    assert results[0].page_id == "tafel-leipzig-zentrale-lindenau-west"


def test_supported_language_shower_queries_retrieve_hygiene_relevant_pages() -> None:
    engine = _engine()
    expectations = [
        ("gdzie moge wziac prysznic", Language.PL),
        ("unde pot face dus", Language.RO),
        ("gde ya mogu pomytsya", Language.RU),
    ]
    valid_top_ids = {
        "leipziger-oase",
        "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog",
        "wohnungsnotfallhilfe-pdf-insel",
        "oeffentliche-toiletten",
    }
    for query, language in expectations:
        results = engine.retrieve(query, language)
        assert results, query
        assert results[0].page_id in valid_top_ids, (query, results[0].page_id)
