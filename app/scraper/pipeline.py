from __future__ import annotations

import hashlib
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
PHONE_RE = re.compile(r"(?:(?:\+49|0)\d[\d\s()/.-]{6,}\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
OPENING_HOURS_HINT_RE = re.compile(
    r"(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|mo\b|di\b|mi\b|do\b|fr\b|sa\b|so\b|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|opening|oeffnung|öffnungszeiten)",
    re.IGNORECASE,
)
NOTICE_HINT_RE = re.compile(r"(ferien|wartezeit|impressum|spendenkonto|herausgeber|druck)", re.IGNORECASE)
REGISTRATION_HINT_RE = re.compile(r"(registrierung|anmeldung|aufnahme als kunde)", re.IGNORECASE)
WALK_IN_HINT_RE = re.compile(r"(offene sprechstunde|offene beratung|ohne termin)", re.IGNORECASE)
WOMEN_HINT_RE = re.compile(r"\b(frauen|frau)\b", re.IGNORECASE)
MEN_HINT_RE = re.compile(r"\b(maenner|männer|mann)\b", re.IGNORECASE)
FAMILY_HINT_RE = re.compile(r"\b(familien|kinder|jugend)\b", re.IGNORECASE)
SUSPICIOUS_ADDRESS_HINT_RE = re.compile(r"(verantwortliches amt|anschrift der stadt|stand:|auflage|herausgeber)", re.IGNORECASE)
LOW_SIGNAL_DESCRIPTION_RE = re.compile(r"^\[.*\]\(.*\)$|^(clients|kontakt|angebote|unsere angebote)$", re.IGNORECASE)
LANGUAGE_HINTS = {
    "de": {"deutsch", "german"},
    "en": {"englisch", "english"},
    "pl": {"polnisch", "polish"},
    "ro": {"rumänisch", "rumaenisch", "romanian"},
    "ru": {"russisch", "russian"},
}
GENERIC_ALIAS_TERMS = {
    "addiction",
    "angebot",
    "angebote",
    "beratung",
    "food",
    "families",
    "fuer",
    "general",
    "hilfe",
    "homeless",
    "housing",
    "katalog",
    "kontakt",
    "medical",
    "men",
    "mock",
    "notfallhilfe",
    "pdf",
    "service",
    "social",
    "support",
    "und",
    "unterkunft",
    "versorgung",
    "women",
}
TITLE_ALIAS_STOPWORDS = {
    "am",
    "an",
    "das",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "ein",
    "eine",
    "einer",
    "eines",
    "fuer",
    "fur",
    "im",
    "in",
    "mit",
    "und",
    "von",
    "zu",
}
PARENT_PAGE_DESCRIPTIONS: dict[str, str] = {
    "leipzig-schadensminimierung": "Uebersichtsseite zu Streetwork- und Schadensminimierungsangeboten in Leipzig.",
    "tafel-leipzig": "Uebersichtsseite mit Ausgabestellen der Tafel Leipzig.",
    "wohnungsnotfallhilfe-pdf": "Uebersichtsseite mit Angeboten der Wohnungsnotfallhilfe und Notunterbringung in Leipzig.",
}
SOURCE_RECORD_OVERRIDES: dict[str, dict[str, object]] = {
    "leipziger-oase": {
        "service_type": "day_center",
        "address": "Nuernberger Strasse 31, 04103 Leipzig",
        "opening_hours": [
            "Montag bis Freitag 08:00 bis 16:00 Uhr",
            "Samstag und Feiertage 09:00 bis 14:00 Uhr",
        ],
        "description": "Tageseinrichtung fuer wohnungslose Menschen mit Beratung, Dusch- und Waeschemoeglichkeiten sowie Imbiss.",
        "target_groups": ["homeless"],
        "phone": "0341 2682670",
        "aliases": ["Leipziger Oase", "Oase", "Kontaktstube", "Tageseinrichtung"],
    },
    "cabl-uvo": {
        "service_type": "medical_consultation",
        "address": None,
        "opening_hours": [],
        "description": "Medizinische Sprechstunden und mobile Versorgung fuer wohnungslose Menschen an mehreren Standorten in Leipzig.",
        "target_groups": ["homeless"],
        "requires_registration": None,
        "aliases": ["CABL", "UVO", "Medizinische Sprechstunden"],
    },
}
SERVICE_TYPE_RULES: tuple[tuple[set[str], str], ...] = (
    ({"tafel", "lebensmittel", "ausgabestellen", "mittagstisch", "mahlzeit"}, "food_distribution"),
    ({"uebernachtung", "notschlafstelle", "notunterkunft", "unterkunft"}, "overnight_shelter"),
    ({"sprechstunde", "medizin", "arzt", "gesundheit"}, "medical_consultation"),
    ({"kleiderkammer", "kleidung", "kleiderspenden"}, "clothing_support"),
    ({"streetwork", "strassensozialarbeit", "aufsuchend"}, "streetwork"),
    ({"beratung", "beratungstelle", "beratungszentrum"}, "counseling"),
)
WOHNUNGSNOTFALL_SERVICE_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "slug": "sozialdienst",
        "title": "Sozialdienst Wohnungsnotfallhilfe",
        "marker": "1 Sozialdienst",
        "service_type": "counseling",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Soziale Beratung und Unterstützung bei drohender oder bestehender Wohnungslosigkeit.",
        "aliases": ["sozialdienst", "wohnungsnotfallhilfe", "beratung wohnungslosigkeit"],
    },
    {
        "slug": "wirtschaftliche-wohnhilfen",
        "title": "Wirtschaftliche Wohnhilfen",
        "marker": "2.1 Wirtschaftliche Wohnhilfen",
        "service_type": "financial_housing_support",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Beratung und Unterstützung bei Miet- und Energieschulden.",
        "aliases": ["mietschulden", "energieschulden", "wirtschaftliche wohnhilfen"],
    },
    {
        "slug": "unterbringungsmanagement",
        "title": "Unterbringungsmanagement",
        "marker": "3.1 Träger Stadt Leipzig, Sozialamt, Abt. Soziale Wohnhilfen Unterbringungsmanagement",
        "service_type": "housing_placement",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Management von Notunterbringung und Beschaffung von Notunterkünften.",
        "aliases": ["unterbringungsmanagement", "notunterbringung", "notunterkünfte"],
    },
    {
        "slug": "uebernachtungshaus-maenner",
        "title": "Übernachtungshaus für wohnungslose Männer",
        "marker": "Übernachtungshaus für wohnungslose Männer",
        "service_type": "overnight_shelter",
        "category": "housing",
        "target_groups": ["homeless", "men"],
        "gender_access": "men",
        "description": "Unterkunft für wohnungslose Männer mit Grundversorgung und persönlicher Hilfe.",
        "aliases": ["männer", "übernachtungshaus männer", "notunterkunft männer"],
    },
    {
        "slug": "uebernachtungshaus-frauen-katalog",
        "title": "Übernachtungshaus für wohnungslose Frauen",
        "marker": "Übernachtungshaus für wohnungslose Frauen",
        "service_type": "overnight_shelter",
        "category": "housing",
        "target_groups": ["homeless", "women"],
        "gender_access": "women",
        "description": "Unterkunft für wohnungslose Frauen mit Grundversorgung und persönlicher Hilfe.",
        "aliases": ["frauen", "übernachtungshaus frauen", "notunterkunft frauen"],
    },
    {
        "slug": "alternative-i",
        "title": "Notschlafstelle Alternative I",
        "marker": "Notschlafstelle für drogenabhängige wohnungslose Menschen »Alternative I«",
        "service_type": "overnight_shelter",
        "category": "housing",
        "target_groups": ["homeless", "addiction"],
        "description": "Notschlafstelle für drogenabhängige wohnungslose Menschen.",
        "aliases": ["alternative i", "notschlafstelle", "drogenabhängig", "sankt georg"],
    },
    {
        "slug": "alternative-iii",
        "title": "Notschlafstelle Alternative III",
        "marker": "Notschlafstelle / Übernachtungshaus für drogenabhängige wohnungslose Menschen »Alternative III«",
        "service_type": "overnight_shelter",
        "category": "housing",
        "target_groups": ["homeless", "addiction"],
        "description": "Übernachtungshaus für drogenabhängige wohnungslose Menschen.",
        "aliases": ["alternative iii", "notschlafstelle", "drogenabhängig", "braunstraße"],
    },
    {
        "slug": "notunterbringung-psychisch-krank",
        "title": "Notunterbringung psychisch kranker wohnungsloser Menschen",
        "marker": "Notunterbringung psychisch kranker wohnungsloser Menschen",
        "service_type": "protected_housing",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Unterkunft und Vermittlung in passende Hilfen für psychisch kranke wohnungslose Menschen.",
        "aliases": ["psychisch krank", "notunterbringung psychisch krank", "das boot"],
    },
    {
        "slug": "kindernotdienst",
        "title": "Kindernotdienst",
        "marker": "7 Kindernotdienst",
        "service_type": "child_emergency_housing",
        "category": "housing",
        "target_groups": ["families"],
        "description": "Notunterbringung und Inobhutnahme für Kinder von 0 bis 12 Jahren.",
        "aliases": ["kindernotdienst", "kinder", "inobhutnahme"],
    },
    {
        "slug": "jugendnotdienst",
        "title": "Jugendnotdienst",
        "marker": "6 Jugendnotdienst",
        "service_type": "youth_emergency_housing",
        "category": "housing",
        "target_groups": ["families"],
        "description": "Notunterbringung und Inobhutnahme für Jugendliche von 12 bis 18 Jahren.",
        "aliases": ["jugendnotdienst", "jugendliche", "inobhutnahme"],
    },
    {
        "slug": "leipziger-oase-katalog",
        "title": "Leipziger Oase",
        "marker": "Ökumenische Kontaktstube für Wohnungslose »Leipziger Oase«",
        "service_type": "day_center",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Tagesaufenthalt mit Beratung, Körperpflege, Wäschepflege, Imbiss und Kleiderkammer.",
        "opening_hours": [
            "Montag bis Freitag 08:00 bis 16:00 Uhr",
            "Samstag und Feiertage 09:00 bis 14:00 Uhr",
        ],
        "aliases": ["oase", "kontaktstube", "tagesaufenthalt", "wäschepflege", "imbiss"],
    },
    {
        "slug": "eigene-wohnung",
        "title": "Modellprojekt Eigene Wohnung",
        "marker": "10 Modellprojekt »Eigene Wohnung«",
        "service_type": "housing_first",
        "category": "housing",
        "target_groups": ["homeless"],
        "description": "Housing-First-Projekt mit Vermittlung in eigenen Wohnraum.",
        "aliases": ["eigene wohnung", "housing first"],
    },
    {
        "slug": "bahnhofsmission-leipzig-katalog",
        "title": "Bahnhofsmission Leipzig",
        "marker": "Ökumenische Bahnhofsmission Leipzig",
        "service_type": "station_support",
        "category": "social",
        "target_groups": ["homeless"],
        "description": "Hilfe, Betreuung, Begegnung und Vermittlung am Bahnhof.",
        "aliases": ["bahnhofsmission", "hauptbahnhof", "hilfe am bahnhof"],
    },
    {
        "slug": "teekeller-quelle",
        "title": "Teekeller Quelle",
        "marker": "14 Teekeller Quelle",
        "service_type": "day_center",
        "category": "social",
        "target_groups": ["homeless"],
        "description": "Begegnungs-, Beratungs- und Bildungsangebot für Menschen in schwierigen Lebenslagen.",
        "aliases": ["teekeller quelle", "beratung", "nordplatz"],
    },
    {
        "slug": "blaues-cafe",
        "title": "Blaues Café",
        "marker": "15 »Blaues Cafe«",
        "service_type": "day_center",
        "category": "addiction",
        "target_groups": ["addiction"],
        "description": "Begegnungsstätte für suchtkranke und suchtgefährdete Menschen.",
        "aliases": ["blaues café", "begegnungsstätte", "blaues kreuz"],
    },
    {
        "slug": "insel",
        "title": "Tagestreff INSEL",
        "marker": "Tagestreff für wohnungslose Menschen »INSEL«",
        "service_type": "day_center",
        "category": "food",
        "target_groups": ["homeless"],
        "description": "Tagesaufenthalt mit Beratung, Körperpflege, Wäschepflege, Imbiss und warmer Mahlzeit.",
        "aliases": ["insel", "tagestreff", "warme mahlzeit", "imbiss"],
    },
)
SCHADENSMINIMIERUNG_SERVICE_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "slug": "schwanenteich",
        "title": "Streetwork Schwanenteich",
        "marker": "jeden Dienstag 17:00 bis 18:00 Uhr am Schwanenteich",
        "service_type": "streetwork_food_outreach",
        "category": "food",
        "target_groups": ["homeless", "addiction"],
        "description": "Streetwork am Schwanenteich mit Beratung, Information sowie Ausgabe von warmen Mahlzeiten und Getraenken.",
        "aliases": ["schwanenteich", "goethestrasse", "essen schwanenteich", "warme mahlzeit", "streetwork schwanenteich"],
        "address": "Goethestrasse / Schwanenteich, Leipzig",
        "opening_hours": ["Dienstag 17:00 bis 18:00 Uhr"],
    },
    {
        "slug": "lindenauer-markt",
        "title": "Streetwork Lindenauer Markt",
        "marker": "jeden Donnerstag 16:00 bis 17:30 Uhr auf dem Lindenauer Markt",
        "service_type": "streetwork_food_outreach",
        "category": "social",
        "target_groups": ["homeless", "addiction"],
        "description": "Streetwork am Lindenauer Markt mit warmen Getraenken, kleinen Snacks sowie Beratung.",
        "aliases": ["lindenauer markt", "snacks", "warme getraenke", "streetwork lindenauer markt"],
        "address": "Lindenauer Markt, Leipzig",
        "opening_hours": ["Donnerstag 16:00 bis 17:30 Uhr"],
    },
)


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
    return repair_text("\n".join(text_parts).strip())


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


def build_markdown(record: dict, text: str, generated_at: datetime) -> str:
    frontmatter = build_frontmatter(
        {
            "title": record["title"],
            "category": record["category"],
            "service_type": record["service_type"],
            "language": record["language"],
            "publisher": record.get("publisher"),
            "address": record.get("address"),
            "opening_hours": record.get("opening_hours", []),
            "description": record.get("description", ""),
            "target_groups": record.get("target_groups", []),
            "gender_access": record.get("gender_access"),
            "walk_in": record.get("walk_in"),
            "requires_registration": record.get("requires_registration"),
            "languages": record.get("languages", []),
            "phone": record.get("phone"),
            "email": record.get("email"),
            "tags": record.get("tags", []),
            "aliases": record.get("aliases", []),
            "review_status": record.get("review_status", "published"),
            "validation_issues": record.get("validation_issues", []),
            "source_url": record["source_url"],
            "source_snapshot_path": record.get("source_snapshot_path"),
            "source_content_hash": record.get("source_content_hash"),
            "source_last_seen": record.get("source_last_seen"),
            "source_updated_at": record.get("source_updated_at"),
            "last_updated": record["last_updated"],
        }
    )
    return "\n".join(
        [
            frontmatter,
            f"# {record['title']}",
            "",
            f"- Source: {record['source_url']}",
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
    phones = extract_phone_numbers(lines)
    emails = extract_emails(lines)
    return {
        "address": extract_address(lines),
        "opening_hours": extract_opening_hours(lines),
        "description": extract_description(lines, title),
        "aliases": build_aliases(source, title),
        "service_type": infer_service_type(source, title, text),
        "target_groups": infer_target_groups(source, title, text),
        "gender_access": infer_gender_access(source, title, text),
        "walk_in": infer_walk_in(text),
        "requires_registration": infer_requires_registration(text),
        "languages": infer_languages(source, text),
        "phone": phones[0] if phones else None,
        "email": emails[0] if emails else None,
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
    aliases: set[str] = {title.strip()}
    aliases.update(tag.strip() for tag in source.tags if tag.strip())
    aliases.update(
        token
        for token in tokenize(title)
        if token not in TITLE_ALIAS_STOPWORDS and token not in GENERIC_ALIAS_TERMS
    )
    return _sanitize_aliases(aliases)


def extract_phone_numbers(lines: list[str]) -> list[str]:
    phones: list[str] = []
    for line in lines:
        for match in PHONE_RE.findall(line):
            normalized = _normalize_spaces(match)
            if normalized not in phones:
                phones.append(normalized)
    return phones


def extract_emails(lines: list[str]) -> list[str]:
    emails: list[str] = []
    for line in lines:
        for match in EMAIL_RE.findall(line):
            normalized = match.strip()
            if normalized not in emails:
                emails.append(normalized)
    return emails


def infer_service_type(source: SourceDefinition, title: str, text: str) -> str:
    if source.service_type != "general":
        return source.service_type
    token_set = set(tokenize(" ".join([title, text, *source.tags])))
    for triggers, service_type in SERVICE_TYPE_RULES:
        if token_set & triggers:
            return service_type
    return source.category if source.category != "general" else "general"


def infer_target_groups(source: SourceDefinition, title: str, text: str) -> list[str]:
    groups = {group.strip().lower() for group in source.target_groups if group.strip()}
    normalized = " ".join([title, text]).casefold()
    if WOMEN_HINT_RE.search(normalized):
        groups.add("women")
    if MEN_HINT_RE.search(normalized):
        groups.add("men")
    if FAMILY_HINT_RE.search(normalized):
        groups.add("families")
    if "wohnungslos" in normalized or "obdachlos" in normalized:
        groups.add("homeless")
    if "sucht" in normalized or "drogen" in normalized:
        groups.add("addiction")
    return sorted(groups)


def infer_gender_access(source: SourceDefinition, title: str, text: str) -> str | None:
    if source.gender_access:
        return source.gender_access
    normalized = " ".join([title, text]).casefold()
    if WOMEN_HINT_RE.search(normalized) and not MEN_HINT_RE.search(normalized):
        return "women"
    if MEN_HINT_RE.search(normalized) and not WOMEN_HINT_RE.search(normalized):
        return "men"
    return None


def infer_walk_in(text: str) -> bool | None:
    if WALK_IN_HINT_RE.search(text):
        return True
    return None


def infer_requires_registration(text: str) -> bool | None:
    if REGISTRATION_HINT_RE.search(text):
        return True
    return None


def infer_languages(source: SourceDefinition, text: str) -> list[str]:
    languages = set(source.languages)
    normalized = text.casefold()
    for code, hints in LANGUAGE_HINTS.items():
        if any(hint in normalized for hint in hints):
            languages.add(code)
    return sorted(languages)


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


def _sanitize_aliases(values: set[str] | list[str] | tuple[str, ...]) -> list[str]:
    cleaned: list[str] = []
    for raw_value in values:
        normalized = _normalize_spaces(str(raw_value)).strip(" ,;:-")
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in GENERIC_ALIAS_TERMS:
            continue
        if " " not in lowered and len(lowered) < 4 and lowered not in {"uvo"}:
            continue
        if lowered not in {item.casefold() for item in cleaned}:
            cleaned.append(normalized)
    return sorted(cleaned, key=str.casefold)


def _apply_parent_page_cleanup(record: dict) -> None:
    record["service_type"] = "service_catalog"
    record["address"] = None
    record["opening_hours"] = []
    description = PARENT_PAGE_DESCRIPTIONS.get(record["page_id"])
    if description:
        record["description"] = description
    record["aliases"] = _sanitize_aliases(record.get("aliases", []))


def _apply_source_record_overrides(record: dict) -> None:
    overrides = SOURCE_RECORD_OVERRIDES.get(record["page_id"])
    if not overrides:
        return
    for key, value in overrides.items():
        record[key] = value
    if overrides.get("aliases"):
        merged_aliases = [*record.get("aliases", []), *overrides["aliases"]]
        record["aliases"] = _sanitize_aliases(merged_aliases)
    if record["page_id"] == "cabl-uvo":
        issues = [issue for issue in record.get("validation_issues", []) if issue != "suspicious_opening_hours"]
        issues.append("multi_location_service")
        record["validation_issues"] = sorted(set(issues))
        record["review_status"] = "needs_review"


def alias_terms(record: dict) -> set[str]:
    aliases = {alias.strip().lower() for alias in record.get("aliases", []) if alias.strip()}
    aliases.update(
        tag.strip().lower()
        for tag in record["tags"]
        if tag.strip() and tag.strip().lower() not in GENERIC_ALIAS_TERMS
    )
    aliases.update(
        group.strip().lower()
        for group in record.get("target_groups", [])
        if group.strip() and group.strip().lower() not in GENERIC_ALIAS_TERMS
    )
    aliases.update(tokenize(record["title"]))
    aliases.update(tokenize(record["page_id"].replace("-", " ")))
    aliases.update(
        token for token in tokenize(record.get("service_type", "")) if token not in GENERIC_ALIAS_TERMS
    )
    return {alias for alias in aliases if alias and alias not in GENERIC_ALIAS_TERMS}


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


def validate_extracted_record(record: dict) -> tuple[str, list[str]]:
    issues: list[str] = []
    description = str(record.get("description", "")).strip()
    address = str(record.get("address") or "").strip()
    opening_hours = [str(item).strip() for item in record.get("opening_hours", []) if str(item).strip()]
    is_parent_page = record.get("service_type") == "service_catalog"

    if not address and not is_parent_page:
        issues.append("missing_address")
    elif SUSPICIOUS_ADDRESS_HINT_RE.search(address):
        issues.append("suspicious_address")

    if not opening_hours and not is_parent_page:
        issues.append("missing_opening_hours")
    elif any(not TIME_RE.search(item) for item in opening_hours):
        issues.append("suspicious_opening_hours")

    if not description or LOW_SIGNAL_DESCRIPTION_RE.search(description) or NOTICE_HINT_RE.search(description):
        issues.append("low_signal_description")

    if record.get("category") in {"documents", "reference"}:
        issues.append("non_service_document")

    severe = {"suspicious_address", "suspicious_opening_hours", "low_signal_description"}
    review_status = "needs_review" if severe & set(issues) else "published"
    return review_status, issues


def _load_existing_records(output_root: Path) -> dict[str, dict]:
    pages_path = output_root / "index" / "pages.json"
    if not pages_path.exists():
        return {}
    try:
        pages = json.loads(pages_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {item["page_id"]: item for item in pages if isinstance(item, dict) and item.get("page_id")}


def _build_record(
    source: SourceDefinition,
    page_id: str,
    title: str,
    file_path: str,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
    *,
    address: str | None,
    opening_hours: list[str],
    description: str,
    aliases: list[str],
    service_type: str,
    target_groups: list[str],
    gender_access: str | None,
    walk_in: bool | None,
    requires_registration: bool | None,
    languages: list[str],
    phone: str | None,
    email: str | None,
) -> dict:
    is_parent_page = page_id == source.source_id and source.entity_mode != "single"
    if is_parent_page:
        service_type = "service_catalog"
    record = {
        "page_id": page_id,
        "title": title,
        "category": source.category,
        "service_type": service_type,
        "language": source.language,
        "source_url": source.url,
        "last_updated": generated_at.date().isoformat(),
        "publisher": source.publisher,
        "address": address,
        "opening_hours": opening_hours,
        "description": description,
        "target_groups": target_groups,
        "gender_access": gender_access,
        "walk_in": walk_in,
        "requires_registration": requires_registration,
        "languages": languages,
        "phone": phone,
        "email": email,
        "tags": source.tags,
        "aliases": aliases,
        "source_snapshot_path": raw_snapshot_path,
        "source_content_hash": source_content_hash,
        "source_last_seen": generated_at.isoformat(),
        "source_updated_at": None,
        "summary": summarize_text(text),
        "file_path": file_path,
        "_raw_text": text,
    }
    if is_parent_page:
        _apply_parent_page_cleanup(record)
    review_status, validation_issues = validate_extracted_record(record)
    record["review_status"] = review_status
    record["validation_issues"] = validation_issues
    _apply_source_record_overrides(record)
    return record


def _expand_source_records(
    source: SourceDefinition,
    title: str,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    structured = extract_structured_fields(source, source.title or title, text)
    base_record = _build_record(
        source,
        page_id=source.source_id,
        title=source.title or title,
        file_path=f"{source.source_id}.md",
        text=text,
        generated_at=generated_at,
        raw_snapshot_path=raw_snapshot_path,
        source_content_hash=source_content_hash,
        address=structured["address"],
        opening_hours=structured["opening_hours"],
        description=structured["description"],
        aliases=structured["aliases"],
        service_type=structured["service_type"],
        target_groups=structured["target_groups"],
        gender_access=structured["gender_access"],
        walk_in=structured["walk_in"],
        requires_registration=structured["requires_registration"],
        languages=structured["languages"],
        phone=structured["phone"],
        email=structured["email"],
    )
    records = [base_record]
    if source.entity_mode == "location_list":
        records.extend(_expand_location_records(source, text, generated_at, raw_snapshot_path, source_content_hash))
    elif source.entity_mode == "service_catalog":
        records.extend(_expand_service_catalog_records(source, text, generated_at, raw_snapshot_path, source_content_hash))
    return records


def _expand_location_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    if source.source_id != "tafel-leipzig":
        return []
    return _expand_tafel_location_records(source, text, generated_at, raw_snapshot_path, source_content_hash)


def _expand_service_catalog_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    if source.source_id == "wohnungsnotfallhilfe-pdf":
        return _expand_wohnungsnotfallhilfe_records(source, text, generated_at, raw_snapshot_path, source_content_hash)
    if source.source_id == "leipzig-schadensminimierung":
        return _expand_schadensminimierung_records(source, text, generated_at, raw_snapshot_path, source_content_hash)
    return []


def _expand_wohnungsnotfallhilfe_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    catalog_text = _normalize_spaces(text)
    records: list[dict] = []
    definitions = list(WOHNUNGSNOTFALL_SERVICE_DEFINITIONS)
    marker_positions: list[tuple[int, dict[str, object]]] = []
    for definition in definitions:
        marker = str(definition["marker"])
        position = catalog_text.find(marker)
        if position == -1:
            continue
        marker_positions.append((position, definition))

    marker_positions.sort(key=lambda item: item[0])
    for index, (start, definition) in enumerate(marker_positions):
        end = marker_positions[index + 1][0] if index + 1 < len(marker_positions) else len(catalog_text)
        section_text = catalog_text[start:end].strip()
        if not section_text:
            continue

        title = str(definition["title"])
        slug = str(definition["slug"])
        aliases = sorted(
            {
                *build_aliases(source, title),
                *[str(alias).strip().lower() for alias in definition.get("aliases", []) if str(alias).strip()],
            }
        )
        target_groups = sorted({*source.target_groups, *[str(group) for group in definition.get("target_groups", [])]})
        gender_access = definition.get("gender_access")
        location_source = SourceDefinition.model_validate(
            {
                **source.model_dump(),
                "source_id": f"{source.source_id}-{slug}",
                "title": title,
                "service_type": definition["service_type"],
                "category": definition["category"],
                "target_groups": target_groups,
                "gender_access": gender_access,
                "entity_mode": "single",
            }
        )
        structured = extract_structured_fields(location_source, title, section_text)
        address = _extract_catalog_address(section_text) or structured["address"]
        opening_hours = list(definition.get("opening_hours") or _extract_catalog_hours(section_text) or structured["opening_hours"])
        record = _build_record(
            location_source,
            page_id=f"{source.source_id}-{slug}",
            title=title,
            file_path=f"{source.source_id}-{slug}.md",
            text=section_text,
            generated_at=generated_at,
            raw_snapshot_path=raw_snapshot_path,
            source_content_hash=source_content_hash,
            address=address,
            opening_hours=opening_hours,
            description=str(definition["description"]),
            aliases=aliases,
            service_type=str(definition["service_type"]),
            target_groups=target_groups,
            gender_access=str(gender_access) if gender_access else None,
            walk_in=structured["walk_in"],
            requires_registration=structured["requires_registration"],
            languages=structured["languages"],
            phone=structured["phone"],
            email=structured["email"],
        )
        if record["address"] and "Anschrift Burgplatz 1" in record["address"]:
            record["validation_issues"].append("imprint_address")
            record["review_status"] = "needs_review"
        records.append(record)
    return records


def _expand_schadensminimierung_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    catalog_text = _normalize_spaces(text)
    records: list[dict] = []
    marker_positions: list[tuple[int, dict[str, object]]] = []
    for definition in SCHADENSMINIMIERUNG_SERVICE_DEFINITIONS:
        marker = str(definition["marker"])
        position = catalog_text.find(marker)
        if position == -1:
            continue
        marker_positions.append((position, definition))

    marker_positions.sort(key=lambda item: item[0])
    for index, (start, definition) in enumerate(marker_positions):
        next_start = marker_positions[index + 1][0] if index + 1 < len(marker_positions) else len(catalog_text)
        section_start = max(0, start - 260)
        section_text = catalog_text[section_start:next_start].strip()
        if not section_text:
            continue

        title = str(definition["title"])
        slug = str(definition["slug"])
        target_groups = sorted({*source.target_groups, *[str(group) for group in definition.get("target_groups", [])]})
        aliases = sorted(
            {
                *build_aliases(source, title),
                *[str(alias).strip().lower() for alias in definition.get("aliases", []) if str(alias).strip()],
            }
        )
        location_source = SourceDefinition.model_validate(
            {
                **source.model_dump(),
                "source_id": f"{source.source_id}-{slug}",
                "title": title,
                "service_type": definition["service_type"],
                "category": definition["category"],
                "target_groups": target_groups,
                "entity_mode": "single",
            }
        )
        structured = extract_structured_fields(location_source, title, section_text)
        record = _build_record(
            location_source,
            page_id=f"{source.source_id}-{slug}",
            title=title,
            file_path=f"{source.source_id}-{slug}.md",
            text=section_text,
            generated_at=generated_at,
            raw_snapshot_path=raw_snapshot_path,
            source_content_hash=source_content_hash,
            address=str(definition["address"]) if definition.get("address") else structured["address"],
            opening_hours=list(definition.get("opening_hours") or structured["opening_hours"]),
            description=str(definition["description"]),
            aliases=aliases,
            service_type=str(definition["service_type"]),
            target_groups=target_groups,
            gender_access=structured["gender_access"],
            walk_in=structured["walk_in"],
            requires_registration=structured["requires_registration"],
            languages=structured["languages"],
            phone=structured["phone"],
            email=structured["email"],
        )
        records.append(record)
    return records


def _extract_catalog_address(section_text: str) -> str | None:
    match = re.search(
        r"Anschrift\s+(.+?\d{5}\s+[A-ZÄÖÜa-zäöüß][\wÄÖÜäöüß.\-/]+)",
        section_text,
    )
    if not match:
        return None
    return _normalize_spaces(match.group(1))


def _extract_catalog_hours(section_text: str) -> list[str]:
    match = re.search(
        r"(?:Öffnungszeiten|Oeffnungszeiten)\s+(.+?)(?:\s+(?:Ansprechpartner|Ansprechpartnerin|Ansprechpartner/-in|Hausleiterin|Hausleiter|Träger|www\.|Telefon|E-Mail|Mail))",
        section_text,
    )
    if not match:
        return []
    content = _normalize_spaces(match.group(1))
    if not content:
        return []
    parts = re.split(r"\s+(?=(?:Mo|Di|Mi|Do|Fr|Sa|So|Täglich|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag))", content)
    cleaned = [_compact_hours_line(part.strip(" ,;")) for part in parts if TIME_RE.search(part) or "24 Stunden" in part]
    return cleaned[:4]


def _expand_tafel_location_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
) -> list[dict]:
    lines = _clean_lines(text)
    address_pattern = re.compile(r".+,\s*\d{5}\s+.+")
    records: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not address_pattern.fullmatch(line):
            index += 1
            continue

        address = line
        if index == 0:
            index += 1
            continue
        location_name = lines[index - 1]
        if location_name in {"Telefon:", "Unsere Ausgabestellen"} or len(location_name) < 3:
            index += 1
            continue

        hours: list[str] = []
        phone: str | None = None
        section_lines = [location_name, address]
        look_ahead = index + 1
        while look_ahead < len(lines):
            candidate = lines[look_ahead]
            if address_pattern.fullmatch(candidate):
                break
            if candidate in {"[Clients]", "Bitte bringen Sie folgende Unterlagen zur Anmeldung mit."}:
                break
            if TIME_RE.search(candidate):
                hours.append(candidate)
            if not phone:
                match = PHONE_RE.search(candidate)
                if match:
                    phone = _normalize_spaces(match.group(0))
            section_lines.append(candidate)
            if "[.. Zur Ausgabestelle]" in candidate:
                break
            look_ahead += 1

        location_slug = _slugify(location_name)
        location_text = "\n".join(section_lines)
        location_record = _build_record(
            source,
            page_id=f"{source.source_id}-{location_slug}",
            title=f"{source.title} - {location_name}",
            file_path=f"{source.source_id}-{location_slug}.md",
            text=location_text,
            generated_at=generated_at,
            raw_snapshot_path=raw_snapshot_path,
            source_content_hash=source_content_hash,
            address=address,
            opening_hours=hours[:4],
            description="Lebensmittelausgabe der Tafel Leipzig.",
            aliases=sorted({*build_aliases(source, f"{source.title} {location_name}"), *tokenize(location_name)}),
            service_type="food_distribution",
            target_groups=sorted({*source.target_groups, "food"}),
            gender_access=source.gender_access,
            walk_in=None,
            requires_registration=True,
            languages=source.languages,
            phone=phone,
            email=None,
        )
        location_record["review_status"] = "published"
        location_record["validation_issues"] = []
        records.append(location_record)
        index = look_ahead + 1
    return records


def _slugify(text: str) -> str:
    normalized = text.casefold()
    normalized = normalized.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "item"


def _build_page_chunks(records: list[dict], pages: dict[str, str]) -> list[dict]:
    page_chunks: list[dict] = []
    for record in records:
        markdown = pages[record["page_id"]]
        if markdown.startswith("---\n") and "\n---\n" in markdown:
            markdown = markdown.split("\n---\n", 1)[1]
        chunk_lines = [line.strip() for line in markdown.splitlines() if line.strip()]
        chunk_text = []
        chunk_index = 0
        for line in chunk_lines:
            chunk_text.append(line)
            if len(" ".join(chunk_text)) >= 280:
                page_chunks.append(
                    {
                        "chunk_id": f'{record["page_id"]}-{chunk_index}',
                        "page_id": record["page_id"],
                        "text": " ".join(chunk_text)[:400],
                    }
                )
                chunk_index += 1
                chunk_text = []
        if chunk_text:
            page_chunks.append(
                {
                    "chunk_id": f'{record["page_id"]}-{chunk_index}',
                    "page_id": record["page_id"],
                    "text": " ".join(chunk_text)[:400],
                }
            )
    return page_chunks


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
            source_count=len({record["source_url"] for record in records}),
            page_count=len(records),
        )
        aliases = {}
        page_chunks = _build_page_chunks(records, pages)
        for record in records:
            for alias in sorted(alias_terms(record)):
                aliases.setdefault(alias, []).append(record["page_id"])

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
    previous_records = _load_existing_records(output_root)
    records: list[dict] = []
    pages: dict[str, str] = {}
    failures: list[dict] = []
    changed_page_ids: list[str] = []
    unchanged_page_ids: list[str] = []
    for source in load_sources(source_registry):
        try:
            html = await fetch_source(source)
            raw_snapshot = raw_root / f"{source.source_id}-{generated_at.strftime('%Y%m%d%H%M%S')}.html"
            raw_snapshot.write_text(html, encoding="utf-8")
            source_content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
            title, text = extract_content(html)
            expanded_records = _expand_source_records(
                source,
                title,
                text,
                generated_at,
                raw_snapshot.relative_to(raw_root.parent).as_posix(),
                source_content_hash,
            )
            for record in expanded_records:
                previous = previous_records.get(record["page_id"])
                if previous and previous.get("source_content_hash") == source_content_hash:
                    unchanged_page_ids.append(record["page_id"])
                else:
                    changed_page_ids.append(record["page_id"])
                records.append(record)
                pages[record["page_id"]] = build_markdown(record, record["_raw_text"], generated_at)
        except Exception as exc:
            failures.append({"source_id": source.source_id, "url": source.url, "error": str(exc)})
    removed_page_ids = sorted(set(previous_records) - {record["page_id"] for record in records})
    if reports_root:
        report_path = reports_root / f"run-{generated_at.strftime('%Y%m%d%H%M%S')}.json"
        report_path.write_text(
            json.dumps(
                {
                    "generated_at": generated_at.isoformat(),
                    "success_count": len(records),
                    "failure_count": len(failures),
                    "changed_count": len(changed_page_ids),
                    "unchanged_count": len(unchanged_page_ids),
                    "removed_count": len(removed_page_ids),
                    "changed_page_ids": sorted(changed_page_ids),
                    "unchanged_page_ids": sorted(unchanged_page_ids),
                    "removed_page_ids": removed_page_ids,
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
