"""Lädt die kanonische JSON-Wissensbasis und unterstützt Markdown-Importe."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .models import OfferRecord


SECTION_RE = re.compile(
    r"(?ms)^###\s+(?P<number>\d+)\.\s+(?P<title>[^\r\n]+)\r?\n"
    r"(?P<body>.*?)(?=^---\s*$|\Z)"
)
FIELD_RE = re.compile(r"^\*\*(?P<label>[^*]+):\*\*\s*(?P<inline>.*)$")
TIME_RE = re.compile(r"\b\d{1,2}\s*[:.]\s*\d{2}\b")
WEEKDAY_RE = re.compile(
    r"\b(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|wochenende|feiertag)\b",
    re.IGNORECASE,
)


class KnowledgeBaseError(RuntimeError):
    """Signalisiert fehlende, unlesbare oder strukturell ungültige KB-Daten."""
    pass


@dataclass(frozen=True)
class KnowledgeBase:
    """Geladener, unveränderlicher Laufzeitdatenbestand mit Quellenmetadaten."""
    path: Path
    source_hash: str
    offers: list[OfferRecord]
    source_kind: str = "markdown"
    metadata: dict[str, object] = field(default_factory=dict)

    def by_id(self) -> dict[str, OfferRecord]:
        return {offer.id: offer for offer in self.offers}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.replace("ß", "ss")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:56] or "angebot"


def _clean_value(line: str) -> str:
    value = line.strip()
    if value.startswith("- "):
        return value[2:].strip()
    return value


def _parse_fields(body: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current_label: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        match = FIELD_RE.match(line)
        if match:
            current_label = match.group("label").strip()
            fields.setdefault(current_label, [])
            inline = match.group("inline").strip()
            if inline:
                fields[current_label].append(inline)
            continue
        if current_label and line:
            fields[current_label].append(_clean_value(line))
    return fields


def _first(fields: dict[str, list[str]], label: str) -> str | None:
    values = fields.get(label, [])
    return values[0] if values else None


def _extract_standzeiten(fields: dict[str, list[str]]) -> list[str]:
    extracted: list[str] = []
    for label in ("Angebote", "Öffnungszeiten", "Sonstige Hinweise"):
        active = False
        for value in fields.get(label, []):
            if "standzeit" in value.casefold():
                active = True
                extracted.append(value)
                continue
            if active and (TIME_RE.search(value) or WEEKDAY_RE.search(value)):
                extracted.append(value)
                continue
            if active:
                active = False
    return list(dict.fromkeys(extracted))


def parse_markdown(markdown: str) -> list[OfferRecord]:
    """Parst nummerierte Angebotsabschnitte aus dem unterstützten Markdownformat.

    Args:
        markdown: Vollständiger Inhalt der Wissensbasisdatei.

    Returns:
        Normalisierte Angebote in der Reihenfolge des Quelldokuments.

    Raises:
        KnowledgeBaseError: Wenn keine gültigen Angebotsabschnitte vorhanden sind.
    """
    offers: list[OfferRecord] = []
    for match in SECTION_RE.finditer(markdown):
        source_index = int(match.group("number"))
        source_title = match.group("title").strip()
        body = match.group("body").rstrip()
        raw_text = f"### {source_index}. {source_title}\n{body}".rstrip()
        fields = _parse_fields(body)
        name = _first(fields, "Name")
        category = _first(fields, "Kategorie")
        description = _first(fields, "Kurzbeschreibung")
        if not name or not category or not description or not raw_text:
            raise KnowledgeBaseError(f"Offer section {source_index} lacks a required source field")
        offers.append(
            OfferRecord(
                id=f"offer-{source_index:03d}-{_slugify(source_title)}",
                source_index=source_index,
                source_title=source_title,
                name=name,
                source_category=category,
                short_description=description,
                district=_first(fields, "Stadtbezirk / Ortsteil"),
                address=_first(fields, "Adresse"),
                header_address=_first(fields, "Adresse laut Kopfzeile"),
                services=list(fields.get("Angebote", [])),
                opening_hours_raw=list(fields.get("Öffnungszeiten", [])),
                standzeiten_raw=_extract_standzeiten(fields),
                phone_numbers=list(fields.get("Telefon", [])),
                emails=list(fields.get("E-Mail", [])),
                website=_first(fields, "Internetseite"),
                notes=list(fields.get("Sonstige Hinweise", [])),
                raw_fields=fields,
                raw_text=raw_text,
            )
        )
    if not offers:
        raise KnowledgeBaseError("No offer sections were parsed")
    ids = [offer.id for offer in offers]
    if len(ids) != len(set(ids)):
        raise KnowledgeBaseError("Parsed offer IDs are not unique")
    return offers


def load_knowledge_base(path: Path) -> KnowledgeBase:
    """Lädt JSON oder Markdown anhand des Dateiinhalts in eine Wissensbasis.

    Raises:
        KnowledgeBaseError: Wenn die Datei fehlt, nicht lesbar oder ungültig ist.
    """
    if not path.is_file():
        raise KnowledgeBaseError(f"Markdown source not found: {path}")
    source_bytes = path.read_bytes()
    if path.suffix.casefold() == ".json":
        try:
            payload = json.loads(source_bytes.decode("utf-8"))
            offers = [OfferRecord.model_validate(item) for item in payload["offers"]]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise KnowledgeBaseError("Canonical JSON source is invalid") from exc
        if not offers or len({offer.id for offer in offers}) != len(offers):
            raise KnowledgeBaseError("Canonical JSON contains no offers or duplicate IDs")
        source = payload.get("source", {})
        source_hash = str(source.get("content_hash") or hashlib.sha256(source_bytes).hexdigest())
        return KnowledgeBase(
            path=path,
            source_hash=source_hash,
            offers=offers,
            source_kind="wfs",
            metadata={key: value for key, value in payload.items() if key != "offers"},
        )
    try:
        markdown = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeBaseError("Markdown source is not valid UTF-8") from exc
    return KnowledgeBase(
        path=path,
        source_hash=hashlib.sha256(source_bytes).hexdigest(),
        offers=parse_markdown(markdown),
        source_kind="markdown",
    )
