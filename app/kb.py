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
        pages = self._load_pages()
        aliases = self._load_aliases()
        field_indexes = self._load_field_indexes()
        self._pages_by_id = {page.page_id: page for page in pages}
        return PublishedDataset(manifest=manifest, pages=pages, aliases=aliases, field_indexes=field_indexes)

    def _load_pages(self) -> list[PageMetadata]:
        entities_path = self.index_root / "entities.jsonl"
        if entities_path.exists():
            pages: list[PageMetadata] = []
            for raw_line in entities_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                pages.append(PageMetadata.model_validate_json(line))
            if pages:
                return pages
        return [
            PageMetadata.model_validate(item)
            for item in json.loads((self.index_root / "pages.json").read_text(encoding="utf-8"))
        ]

    def _load_aliases(self) -> dict[str, list[str]]:
        alias_path = self.index_root / "alias_index.json"
        if alias_path.exists():
            return json.loads(alias_path.read_text(encoding="utf-8"))
        return json.loads((self.index_root / "aliases.json").read_text(encoding="utf-8"))

    def _load_field_indexes(self) -> dict[str, dict[str, list[str]]]:
        indexes_root = self.index_root / "field_indexes"
        if not indexes_root.exists():
            return {}
        field_indexes: dict[str, dict[str, list[str]]] = {}
        for path in sorted(indexes_root.glob("*.json")):
            try:
                field_indexes[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return field_indexes

    def reload(self) -> None:
        self.dataset = self._load()

    def get_page(self, page_id: str) -> PageMetadata:
        return self._pages_by_id[page_id]

    def get_page_markdown(self, page_id: str) -> str:
        page = self.get_page(page_id)
        return (self.pages_root / Path(page.file_path).name).read_text(encoding="utf-8")

    def get_index_hits(self, index_name: str, term: str) -> list[str]:
        return list(self.dataset.field_indexes.get(index_name, {}).get(term, []))
