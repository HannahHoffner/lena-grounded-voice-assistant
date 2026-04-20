from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from urllib.request import url2pathname

import httpx
import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..models import Manifest, SourceDefinition
from ..retrieval import tokenize


def load_sources(path: Path) -> list[SourceDefinition]:
    return [SourceDefinition.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


async def fetch_source(source: SourceDefinition) -> str:
    parsed = urlparse(source.url)
    if parsed.scheme == "file":
        file_path = Path(url2pathname(parsed.path))
        if _is_pdf(source, content_type=None):
            return _extract_pdf(file_path.read_bytes())
        return file_path.read_text(encoding="utf-8")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(source.url)
        response.raise_for_status()
        if _is_pdf(source, response.headers.get("content-type")):
            return _extract_pdf(response.content)
        return response.text


def _is_pdf(source: SourceDefinition, content_type: str | None) -> bool:
    if source.format == "pdf":
        return True
    if source.format == "html":
        return False
    if content_type and "pdf" in content_type.lower():
        return True
    return source.url.lower().endswith(".pdf")


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def extract_content(html: str) -> tuple[str, str]:
    extracted = trafilatura.extract(html, include_comments=False, include_links=True)
    if extracted:
        title = extracted.splitlines()[0].strip("# ").strip() if extracted.splitlines() else "Untitled"
        return title or "Untitled", extracted.strip()

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title and soup.title.string else "Untitled").strip()
    text = " ".join(fragment.strip() for fragment in soup.get_text("\n").splitlines() if fragment.strip())
    return title, text


def build_markdown(source: SourceDefinition, title: str, text: str, generated_at: datetime) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- Source: {source.url}",
            f"- Generated: {generated_at.isoformat()}",
            "",
            text,
            "",
        ]
    )


def summarize_text(text: str, max_chars: int = 320) -> str:
    fragments: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        if line.startswith("[") and "](" in line:
            continue
        digit_ratio = sum(char.isdigit() for char in line) / max(len(line), 1)
        if digit_ratio > 0.2 and len(line) < 80:
            continue
        fragments.append(line)
        if sum(len(fragment) for fragment in fragments) >= max_chars:
            break

    summary = " ".join(fragments).strip()
    if len(summary) > max_chars:
        return summary[:max_chars].rstrip() + "..."
    return summary


def alias_terms(record: dict) -> set[str]:
    aliases = {tag.strip().lower() for tag in record["tags"] if tag.strip()}
    aliases.update(tokenize(record["title"]))
    aliases.update(tokenize(record["page_id"].replace("-", " ")))
    return aliases


def validate_page_record(record: dict) -> None:
    required = ["page_id", "title", "language", "source_url", "last_updated", "tags", "summary", "file_path"]
    missing = [field for field in required if not record.get(field)]
    if missing:
        raise ValueError(f"Invalid page record, missing: {', '.join(missing)}")


def publish_dataset(records: list[dict], pages: dict[str, str], output_root: Path) -> Manifest:
    generated_at = datetime.now(UTC)
    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        pages_root = temp_root / "pages"
        index_root = temp_root / "index"
        pages_root.mkdir(parents=True)
        index_root.mkdir(parents=True)

        for record in records:
            validate_page_record(record)
            page_name = Path(record["file_path"]).name
            (pages_root / page_name).write_text(pages[record["page_id"]], encoding="utf-8")

        manifest = Manifest(
            kb_version=generated_at.strftime("%Y%m%d%H%M%S"),
            generated_at=generated_at,
            source_count=len(records),
            page_count=len(records),
        )
        aliases = {}
        page_chunks = []
        for record in records:
            for alias in sorted(alias_terms(record)):
                aliases.setdefault(alias, []).append(record["page_id"])
            chunk_text = pages[record["page_id"]][:500]
            page_chunks.append({"chunk_id": f'{record["page_id"]}-0', "page_id": record["page_id"], "text": chunk_text})

        (index_root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (index_root / "pages.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        (index_root / "aliases.json").write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
        (index_root / "page_chunks.json").write_text(json.dumps(page_chunks, ensure_ascii=False, indent=2), encoding="utf-8")

        output_root.mkdir(parents=True, exist_ok=True)
        _sync_tree(pages_root, output_root / "pages")
        _sync_tree(index_root, output_root / "index")
        return manifest


def promote_dataset(source_root: Path, target_root: Path) -> Manifest:
    manifest_path = source_root / "index" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("No published scraper dataset found to promote.")
    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        shutil.copytree(source_root / "pages", temp_root / "pages")
        shutil.copytree(source_root / "index", temp_root / "index")
        target_root.mkdir(parents=True, exist_ok=True)
        _sync_tree(temp_root / "pages", target_root / "pages")
        _sync_tree(temp_root / "index", target_root / "index")
    return Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def _sync_tree(source_root: Path, target_root: Path) -> None:
    target_root.mkdir(parents=True, exist_ok=True)

    expected_files = {path.relative_to(source_root) for path in source_root.rglob("*") if path.is_file()}

    for source_file in source_root.rglob("*"):
        if not source_file.is_file():
            continue
        relative = source_file.relative_to(source_root)
        target_file = target_root / relative
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)

    for existing in sorted(target_root.rglob("*"), reverse=True):
        if existing.is_file():
            relative = existing.relative_to(target_root)
            if relative not in expected_files:
                try:
                    existing.unlink()
                except OSError:
                    # Windows/OneDrive/editor file handles should not block scraper publishing.
                    continue


async def run_pipeline(source_registry: Path, output_root: Path, raw_root: Path, reports_root: Path | None = None) -> Manifest:
    raw_root.mkdir(parents=True, exist_ok=True)
    if reports_root:
        reports_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)
    records: list[dict] = []
    pages: dict[str, str] = {}
    failures: list[dict] = []
    for source in load_sources(source_registry):
        try:
            html = await fetch_source(source)
            raw_snapshot = raw_root / f"{source.source_id}-{generated_at.strftime('%Y%m%d%H%M%S')}.html"
            raw_snapshot.write_text(html, encoding="utf-8")
            title, text = extract_content(html)
            page_id = source.source_id
            file_path = f"{page_id}.md"
            record = {
                "page_id": page_id,
                "title": source.title or title,
                "language": source.language,
                "source_url": source.url,
                "last_updated": generated_at.date().isoformat(),
                "tags": source.tags,
                "summary": summarize_text(text),
                "file_path": file_path,
            }
            records.append(record)
            pages[page_id] = build_markdown(source, record["title"], text, generated_at)
        except Exception as exc:
            failures.append({"source_id": source.source_id, "url": source.url, "error": str(exc)})
    if reports_root:
        report_path = reports_root / f"run-{generated_at.strftime('%Y%m%d%H%M%S')}.json"
        report_path.write_text(
            json.dumps(
                {
                    "generated_at": generated_at.isoformat(),
                    "success_count": len(records),
                    "failure_count": len(failures),
                    "failures": failures,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    if not records:
        raise RuntimeError("Scraper run produced no valid pages.")
    return publish_dataset(records, pages, output_root)
