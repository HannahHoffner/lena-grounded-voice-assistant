from __future__ import annotations

import json
from pathlib import Path

from .models import Manifest, PageMetadata, PublishedDataset


class KnowledgeBase:
    def __init__(self, published_root: Path) -> None:
        self.published_root = published_root
        self.index_root = published_root / "index"
        self.pages_root = published_root / "pages"
        self._pages_by_id: dict[str, PageMetadata] = {}
        self.dataset = self._load()

    def _load(self) -> PublishedDataset:
        manifest = Manifest.model_validate_json((self.index_root / "manifest.json").read_text(encoding="utf-8"))
        pages = [PageMetadata.model_validate(item) for item in json.loads((self.index_root / "pages.json").read_text(encoding="utf-8"))]
        aliases = json.loads((self.index_root / "aliases.json").read_text(encoding="utf-8"))
        self._pages_by_id = {page.page_id: page for page in pages}
        return PublishedDataset(manifest=manifest, pages=pages, aliases=aliases)

    def reload(self) -> None:
        self.dataset = self._load()

    def get_page(self, page_id: str) -> PageMetadata:
        return self._pages_by_id[page_id]

    def get_page_markdown(self, page_id: str) -> str:
        page = self.get_page(page_id)
        return (self.pages_root / Path(page.file_path).name).read_text(encoding="utf-8")
