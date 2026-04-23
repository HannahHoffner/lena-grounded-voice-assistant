from __future__ import annotations

from pathlib import Path

from app.config import load_settings
from app.kb import KnowledgeBase
from app.maps import MapBuilder
from app.models import KnowledgeAnswer


def _kb() -> KnowledgeBase:
    return KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")


def test_map_builder_dedupes_catalog_and_detail_variants() -> None:
    kb = _kb()
    builder = MapBuilder(load_settings())
    answer = KnowledgeAnswer(
        answer_text="Leipziger Oase",
        status="ok",
        retrieved_page_ids=["leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"],
    )

    map_data = builder.build_for_answer(answer, kb)

    assert map_data is not None
    assert len(map_data.destinations) == 1
    assert map_data.destinations[0].page_id == "leipziger-oase"


def test_map_builder_computes_distance_from_hauptbahnhof() -> None:
    kb = _kb()
    builder = MapBuilder(load_settings())
    answer = KnowledgeAnswer(
        answer_text="Bahnhofsmission Leipzig",
        status="ok",
        retrieved_page_ids=["wohnungsnotfallhilfe-pdf-bahnhofsmission-leipzig-katalog"],
    )

    map_data = builder.build_for_answer(answer, kb)

    assert map_data is not None
    assert map_data.origin.id == "leipzig_hbf"
    assert map_data.destinations[0].distance_meters is not None
    assert 100 <= map_data.destinations[0].distance_meters <= 400


def test_map_builder_skips_non_geocoded_or_out_of_scope_results() -> None:
    kb = _kb()
    builder = MapBuilder(load_settings())
    answer = KnowledgeAnswer(
        answer_text="Tafel Markkleeberg",
        status="ok",
        retrieved_page_ids=["tafel-leipzig-markkleeberg"],
    )

    map_data = builder.build_for_answer(answer, kb)

    assert map_data is None
