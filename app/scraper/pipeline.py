from __future__ import annotations

import json
import re
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


ADDRESS_LINE_RE = re.compile(
    r"\b(?:[A-ZÄÖÜ][\wÄÖÜäöüß.\-/]+(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß.\-/]+){0,4})\s+"
    r"(?:straße|strasse|str\.|weg|platz|allee|ring|ufer|gasse|markt|chaussee|pfad|damm|bogen|promenade)"
    r"\s*\d+[a-zA-Z]?(?:\s*[-/]\s*\d+[a-zA-Z]?)?(?:,\s*|\s+)\d{5}\s+[A-ZÄÖÜ][\wÄÖÜäöüß.\-/]+",
    re.IGNORECASE,
)
STREET_ONLY_RE = re.compile(
    r"\b(?:[A-ZÄÖÜ][\wÄÖÜäöüß.\-/]+(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß.\-/]+){0,4})\s+"
    r"(?:straße|strasse|str\.|weg|platz|allee|ring|ufer|gasse|markt|chaussee|pfad|damm|bogen|promenade)"
    r"\s*\d+[a-zA-Z]?(?:\s*[-/]\s*\d+[a-zA-Z]?)?",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
OPENING_HOURS_HINT_RE = re.compile(
    r"(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|mo\b|di\b|mi\b|do\b|fr\b|sa\b|so\b|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|opening|oeffnung|öffnungszeiten)",
    re.IGNORECASE,
)
NOTICE_HINT_RE = re.compile(r"(ferien|wartezeit|impressum|spendenkonto|herausgeber|druck)", re.IGNORECASE)


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
        extracted = repair_text(extracted.strip())
        title = extracted.splitlines()[0].strip("# ").strip() if extracted.splitlines() else "Untitled"
        return repair_text(title or "Untitled"), extracted

    soup = BeautifulSoup(html, "html.parser")
    title = repair_text((soup.title.string if soup.title and soup.title.string else "Untitled").strip())
    text = repair_text(" ".join(fragment.strip() for fragment in soup.get_text("\n").splitlines() if fragment.strip()))
    return title, text


def repair_text(text: str) -> str:
    if not text:
        return text
    if any(marker in text for marker in ("Ã", "â€", "Â")):
        try:
            repaired = text.encode("latin1").decode("utf-8")
            if repaired.count("Ã") < text.count("Ã"):
                return repaired
        except UnicodeError:
            return text
    return text


def build_markdown(source: SourceDefinition, title: str, text: str, generated_at: datetime) -> str:
    fields = extract_structured_fields(source, title, text)
    frontmatter = build_frontmatter(
        {
            "title": title,
            "category": source.category,
            "language": source.language,
            "publisher": source.publisher,
            "address": fields["address"],
            "opening_hours": fields["opening_hours"],
            "description": fields["description"],
            "tags": source.tags,
            "aliases": fields["aliases"],
            "source_url": source.url,
            "last_updated": generated_at.date().isoformat(),
        }
    )
    return "\n".join(
        [
            frontmatter,
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


def extract_structured_fields(source: SourceDefinition, title: str, text: str) -> dict[str, object]:
    lines = _clean_lines(text)
    return {
        "address": extract_address(lines),
        "opening_hours": extract_opening_hours(lines),
        "description": extract_description(lines, title),
        "aliases": build_aliases(source, title),
    }


def extract_address(lines: list[str]) -> str | None:
    for line in lines:
        match = ADDRESS_LINE_RE.search(line)
        if match:
            return _normalize_spaces(match.group(0))
    for line in lines:
        match = STREET_ONLY_RE.search(line)
        if match:
            return _normalize_spaces(match.group(0))
    return None


def extract_opening_hours(lines: list[str], limit: int = 4) -> list[str]:
    hours: list[str] = []
    include_next = False
    for line in lines:
        normalized = _normalize_spaces(line)
        if not normalized:
            continue
        if "öffnungszeiten" in normalized.casefold() or "oeffnungszeiten" in normalized.casefold():
            include_next = True
            continue
        if OPENING_HOURS_HINT_RE.search(normalized) and TIME_RE.search(normalized):
            normalized = _compact_hours_line(normalized)
            if normalized not in hours:
                hours.append(normalized)
                include_next = False
        elif include_next and TIME_RE.search(normalized):
            normalized = _compact_hours_line(normalized)
            if normalized not in hours:
                hours.append(normalized)
        else:
            include_next = False
        if len(hours) >= limit:
            break
    return hours


def extract_description(lines: list[str], title: str) -> str:
    normalized_title = _normalize_spaces(title).casefold()
    for line in lines:
        normalized = _normalize_spaces(line)
        if not normalized or normalized.casefold() == normalized_title:
            continue
        if normalized.startswith("[") and normalized.endswith("]"):
            continue
        if normalized.casefold() in {"[clients]", "clients", "unsere angebote", "angebote", "kontakt"}:
            continue
        if normalized_title in normalized.casefold():
            continue
        if TIME_RE.search(normalized) and len(normalized) < 40:
            continue
        if NOTICE_HINT_RE.search(normalized):
            continue
        return normalized[:280].rstrip()
    return _normalize_spaces(title)


def build_aliases(source: SourceDefinition, title: str) -> list[str]:
    aliases: set[str] = {tag.strip().lower() for tag in source.tags if tag.strip()}
    aliases.update(tokenize(title))
    aliases.update(tokenize(source.source_id.replace("-", " ")))
    aliases.add(title.strip().lower())
    return sorted(alias for alias in aliases if alias)


def build_frontmatter(fields: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _normalize_spaces(text: str) -> str:
    return " ".join(text.split()).strip()


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _normalize_spaces(raw_line)
        if not line:
            continue
        lines.append(line)
    return lines


def _compact_hours_line(line: str) -> str:
    lowered = line.casefold()
    if "wann ist" in lowered and "wie erreiche" in lowered:
        line = line.split("Wie erreiche", 1)[0].strip()
    if len(line) <= 180:
        return line
    match = re.search(r"(Montag.*?Uhr.*?(?:Feiertagen durchgehend|Wochenenden und Feiertagen durchgehend)?)", line)
    if match:
        return match.group(1).strip()
    return line[:177].rstrip() + "..."


def alias_terms(record: dict) -> set[str]:
    aliases = {alias.strip().lower() for alias in record.get("aliases", []) if alias.strip()}
    aliases.update({tag.strip().lower() for tag in record["tags"] if tag.strip()})
    aliases.update(tokenize(record["title"]))
    aliases.update(tokenize(record["page_id"].replace("-", " ")))
    return aliases


def validate_page_record(record: dict) -> None:
    required = [
        "page_id",
        "title",
        "category",
        "language",
        "source_url",
        "last_updated",
        "description",
        "aliases",
        "tags",
        "summary",
        "file_path",
    ]
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

        for record in records:
            record.pop("_raw_text", None)

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
            structured = extract_structured_fields(source, source.title or title, text)
            page_id = source.source_id
            file_path = f"{page_id}.md"
            record = {
                "page_id": page_id,
                "title": source.title or title,
                "category": source.category,
                "language": source.language,
                "source_url": source.url,
                "last_updated": generated_at.date().isoformat(),
                "publisher": source.publisher,
                "address": structured["address"],
                "opening_hours": structured["opening_hours"],
                "description": structured["description"],
                "tags": source.tags,
                "aliases": structured["aliases"],
                "summary": summarize_text(text),
                "file_path": file_path,
                "_raw_text": text,
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
