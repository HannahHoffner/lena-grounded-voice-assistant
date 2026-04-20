from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.scraper.pipeline import promote_dataset, run_pipeline


def test_scraper_publishes_valid_dataset(tmp_path) -> None:
    source_html = tmp_path / "source.html"
    source_html.write_text(
        "<html><head><title>Sample Help</title></head><body><h1>Sample Help</h1><p>Food and shower support.</p></body></html>",
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "sample-help",
                    "title": "Sample Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "en",
                    "tags": ["food", "shower"],
                }
            ]
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "published"
    raw_root = tmp_path / "raw"
    reports_root = tmp_path / "reports"

    manifest = asyncio.run(
        run_pipeline(source_registry=source_registry, output_root=output_root, raw_root=raw_root, reports_root=reports_root)
    )

    assert manifest.page_count == 1
    assert (output_root / "index" / "manifest.json").exists()
    assert (output_root / "pages" / "sample-help.md").exists()
    page_markdown = (output_root / "pages" / "sample-help.md").read_text(encoding="utf-8")
    assert page_markdown.startswith("---\n")
    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    assert pages[0]["category"] == "general"
    assert pages[0]["description"]
    assert pages[0]["aliases"]
    aliases = json.loads((output_root / "index" / "aliases.json").read_text(encoding="utf-8"))
    assert "sample" in aliases
    assert any(reports_root.iterdir())


def test_promote_dataset_copies_workspace_to_runtime(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    runtime = tmp_path / "runtime"
    (workspace / "pages").mkdir(parents=True)
    (workspace / "index").mkdir(parents=True)
    (workspace / "pages" / "sample.md").write_text("# Sample", encoding="utf-8")
    manifest = {
        "kb_version": "test-version",
        "generated_at": "2026-04-19T12:00:00Z",
        "source_count": 1,
        "page_count": 1,
    }
    (workspace / "index" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (workspace / "index" / "pages.json").write_text("[]", encoding="utf-8")
    (workspace / "index" / "aliases.json").write_text("{}", encoding="utf-8")
    (workspace / "index" / "page_chunks.json").write_text("[]", encoding="utf-8")

    result = promote_dataset(workspace, runtime)

    assert result.kb_version == "test-version"
    assert (runtime / "pages" / "sample.md").exists()
