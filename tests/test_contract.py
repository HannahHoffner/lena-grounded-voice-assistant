from __future__ import annotations

import json
from pathlib import Path

from app.kb import KnowledgeBase
from app.models import PageMetadata


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
        assert page.file_path.endswith(".md")

