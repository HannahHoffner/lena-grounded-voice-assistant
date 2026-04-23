from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import url2pathname

import httpx
import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..models import Manifest, SourceDefinition
from ..retrieval import detail_tokens, normalize_text, tokenize
from .canonical import CanonicalStore, build_entity_signature, copy_runtime_sqlite, detect_conflict_fields
from .qc import create_build_quality_reviewer


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
LOOSE_ADDRESS_RE = re.compile(
    r"\b[A-ZÃ„Ã–Ãœ][\wÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ.\-/]*(?:\s+[A-ZÃ„Ã–Ãœ][\wÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ.\-/]*){0,4}"
    r"(?:straÃŸe|strasse|str\.|weg|platz|allee|ring|ufer|gasse|markt|chaussee|pfad|damm|bogen|promenade)"
    r"\s*\d+[a-zA-Z]?(?:\s*[-/]\s*\d+[a-zA-Z]?)?(?:,\s*|\s+)\d{5}\s+[A-ZÃ„Ã–Ãœ][\wÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ.\-/]+",
    re.IGNORECASE,
)
LOOSE_STREET_ONLY_RE = re.compile(
    r"\b[A-ZÃ„Ã–Ãœ][\wÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ.\-/]*(?:\s+[A-ZÃ„Ã–Ãœ][\wÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ.\-/]*){0,4}"
    r"(?:straÃŸe|strasse|str\.|weg|platz|allee|ring|ufer|gasse|markt|chaussee|pfad|damm|bogen|promenade)"
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
DISCOVERY_SERVICE_HINTS = (
    "ambulant",
    "angebot",
    "angebote",
    "ausgabestellen",
    "bahnhofsmission",
    "beratung",
    "brunnen",
    "hilfe",
    "konsum",
    "leistunge",
    "leistungen",
    "nothilfe",
    "notlage",
    "obdach",
    "oeffnungszeiten",
    "oeffentliche-toiletten",
    "sozial",
    "standort",
    "standorte",
    "streetwork",
    "suchthilfe",
    "tafel",
    "team-konsum",
    "team-wohnen",
    "toiletten",
    "trinkwasser",
    "unterbringung",
    "wohnungslos",
    "wohnen",
)
DISCOVERY_CATALOG_HINTS = (
    "angebote",
    "ausgabestellen",
    "hilfeundberatung",
    "hilfe-angebote",
    "leistungen",
    "service-portal",
    "soziale-notlagen",
    "standorte",
    "uebersicht",
    "unsere-angebote",
)
DISCOVERY_IGNORE_HINTS = (
    "aktuelles",
    "archiv",
    "career",
    "datenschutz",
    "donate",
    "download",
    "facebook",
    "faq",
    "foerderung",
    "impressum",
    "instagram",
    "jobs",
    "karriere",
    "leitbild",
    "linkedin",
    "newsletter",
    "news",
    "presse",
    "satzung",
    "spenden",
    "team",
    "termine",
    "ueber-uns",
    "ueberuns",
    "veranstaltungen",
    "youtube",
)
CONTACT_AGGREGATION_HINTS = ("ansprechpartner", "kontakt", "kontakte", "sprechzeiten", "team")
SECTION_IGNORE_HINTS = {
    "ansprechpartner",
    "anfahrt",
    "datenschutz",
    "download",
    "downloads",
    "faq",
    "impressum",
    "kontakt",
    "links",
    "mehr erfahren",
    "spenden",
    "team",
}
NON_HTML_DOWNLOAD_SUFFIXES = (
    ".doc",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
    ".svg",
    ".xls",
    ".xlsx",
    ".zip",
)
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

WEEKDAY_ORDER = ("mo", "di", "mi", "do", "fr", "sa", "so")
WEEKDAY_ALIASES: dict[str, tuple[str, ...]] = {
    "mo": ("mo", "montag", "monday"),
    "di": ("di", "dienstag", "tuesday"),
    "mi": ("mi", "mittwoch", "wednesday"),
    "do": ("do", "donnerstag", "thursday"),
    "fr": ("fr", "freitag", "friday"),
    "sa": ("sa", "samstag", "saturday"),
    "so": ("so", "sonntag", "sunday"),
}
DAY_RANGE_PATTERNS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("montag bis freitag", "mo bis fr", "mo-fr"), ("mo", "di", "mi", "do", "fr")),
    (("montag bis donnerstag", "mo bis do", "mo-do"), ("mo", "di", "mi", "do")),
    (("montag bis samstag", "mo bis sa", "mo-sa"), ("mo", "di", "mi", "do", "fr", "sa")),
    (("mo bis so", "mo-so", "montag bis sonntag"), ("mo", "di", "mi", "do", "fr", "sa", "so")),
)
EMBEDDED_COORDINATE_RE = re.compile(r"@(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)")
LEIPZIG_POSTAL_HINT_RE = re.compile(r"\b04[123]\d{2}\b")
LEIPZIG_COORDINATE_RANGE = {
    "lat_min": 51.26,
    "lat_max": 51.41,
    "lon_min": 12.20,
    "lon_max": 12.52,
}
LEIPZIG_ADDRESS_EXCLUDE_HINTS = ("markkleeberg", "markranstadt", "markranstaedt", "borna")


def _default_geo_overrides_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "scraper_sources" / "geo_overrides.json"


def _normalize_address_value(address: str | None) -> str | None:
    if not address:
        return None
    cleaned = str(address).replace("–", "-").replace(",", " ").strip()
    normalized = normalize_text(" ".join(cleaned.split()))
    return normalized or None


def _load_geo_overrides(path: Path | None) -> dict[str, dict[str, dict[str, Any]]]:
    target = path or _default_geo_overrides_path()
    if not target.exists():
        return {"by_entity_id": {}, "by_normalized_address": {}}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"by_entity_id": {}, "by_normalized_address": {}}
    by_entity_id = raw.get("by_entity_id", {}) if isinstance(raw, dict) else {}
    by_normalized_address = raw.get("by_normalized_address", {}) if isinstance(raw, dict) else {}
    if not isinstance(by_entity_id, dict):
        by_entity_id = {}
    if not isinstance(by_normalized_address, dict):
        by_normalized_address = {}
    return {
        "by_entity_id": {str(key): value for key, value in by_entity_id.items() if isinstance(value, dict)},
        "by_normalized_address": {str(key): value for key, value in by_normalized_address.items() if isinstance(value, dict)},
    }


def _looks_like_leipzig_address(address: str | None) -> bool:
    if not address:
        return False
    normalized = normalize_text(address)
    if any(excluded in normalized for excluded in LEIPZIG_ADDRESS_EXCLUDE_HINTS):
        return False
    return "leipzig" in normalized or bool(LEIPZIG_POSTAL_HINT_RE.search(address))


def _extract_embedded_coordinates(text: str | None) -> tuple[float, float] | None:
    if not text:
        return None
    match = EMBEDDED_COORDINATE_RE.search(text)
    if not match:
        return None
    latitude = float(match.group(1))
    longitude = float(match.group(2))
    if not (
        LEIPZIG_COORDINATE_RANGE["lat_min"] <= latitude <= LEIPZIG_COORDINATE_RANGE["lat_max"]
        and LEIPZIG_COORDINATE_RANGE["lon_min"] <= longitude <= LEIPZIG_COORDINATE_RANGE["lon_max"]
    ):
        return None
    return latitude, longitude


def _geo_payload(
    *,
    normalized_address: str | None,
    latitude: float | None,
    longitude: float | None,
    geo_status: str,
    geo_source: str | None = None,
    geo_confidence: float | None = None,
    geo_precision: str | None = None,
    geo_matched_label: str | None = None,
    geo_matched_address: str | None = None,
) -> dict[str, Any]:
    return {
        "normalized_address": normalized_address,
        "latitude": latitude,
        "longitude": longitude,
        "geo_status": geo_status,
        "geo_source": geo_source,
        "geo_confidence": geo_confidence,
        "geo_precision": geo_precision,
        "geo_matched_label": geo_matched_label,
        "geo_matched_address": geo_matched_address,
    }


async def _geocode_with_nominatim(
    *,
    geocoder_url: str,
    query: str,
    label: str,
) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "LENA-KB-Maintenance/1.0"}) as client:
            response = await client.get(
                geocoder_url,
                params={"q": query, "format": "jsonv2", "limit": 1},
            )
            response.raise_for_status()
            results = response.json()
    except Exception:
        return None

    if not isinstance(results, list) or not results:
        return None
    first = results[0]
    try:
        latitude = float(first["lat"])
        longitude = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (
        LEIPZIG_COORDINATE_RANGE["lat_min"] <= latitude <= LEIPZIG_COORDINATE_RANGE["lat_max"]
        and LEIPZIG_COORDINATE_RANGE["lon_min"] <= longitude <= LEIPZIG_COORDINATE_RANGE["lon_max"]
    ):
        return None
    return _geo_payload(
        normalized_address=_normalize_address_value(query),
        latitude=latitude,
        longitude=longitude,
        geo_status="approximate",
        geo_source="build_geocoder",
        geo_confidence=0.72,
        geo_precision="approximate",
        geo_matched_label=str(first.get("name") or label),
        geo_matched_address=str(first.get("display_name") or query),
    )


async def _resolve_geo_payload(
    record: dict[str, Any],
    *,
    raw_text: str | None,
    canonical_store: CanonicalStore | None,
    geo_overrides: dict[str, dict[str, dict[str, Any]]],
    build_geocoding_enabled: bool,
    build_geocoder_url: str,
) -> dict[str, Any]:
    normalized_address = _normalize_address_value(str(record.get("address") or "").strip() or None)
    if not normalized_address:
        return _geo_payload(normalized_address=None, latitude=None, longitude=None, geo_status="missing_address")

    override = geo_overrides["by_entity_id"].get(str(record["page_id"])) or geo_overrides["by_normalized_address"].get(normalized_address)
    if override:
        return _geo_payload(
            normalized_address=normalized_address,
            latitude=float(override["latitude"]) if override.get("latitude") is not None else None,
            longitude=float(override["longitude"]) if override.get("longitude") is not None else None,
            geo_status=str(override.get("geo_status") or "ready"),
            geo_source=str(override.get("geo_source") or "manual"),
            geo_confidence=float(override["geo_confidence"]) if override.get("geo_confidence") is not None else 1.0,
            geo_precision=str(override.get("geo_precision") or "exact"),
            geo_matched_label=str(override.get("geo_matched_label") or record.get("title") or ""),
            geo_matched_address=str(override.get("geo_matched_address") or record.get("address") or ""),
        )

    cached = canonical_store.get_entity_geo(str(record["page_id"])) if canonical_store else None
    if cached and cached.get("normalized_address") == normalized_address:
        return _geo_payload(
            normalized_address=normalized_address,
            latitude=float(cached["latitude"]) if cached.get("latitude") is not None else None,
            longitude=float(cached["longitude"]) if cached.get("longitude") is not None else None,
            geo_status=str(cached.get("geo_status") or "failed"),
            geo_source=str(cached["geo_source"]) if cached.get("geo_source") is not None else None,
            geo_confidence=float(cached["geo_confidence"]) if cached.get("geo_confidence") is not None else None,
            geo_precision=str(cached["geo_precision"]) if cached.get("geo_precision") is not None else None,
            geo_matched_label=str(cached["geo_matched_label"]) if cached.get("geo_matched_label") is not None else None,
            geo_matched_address=str(cached["geo_matched_address"]) if cached.get("geo_matched_address") is not None else None,
        )

    if not _looks_like_leipzig_address(str(record.get("address") or "")):
        return _geo_payload(normalized_address=normalized_address, latitude=None, longitude=None, geo_status="filtered_out")

    embedded_coordinates = _extract_embedded_coordinates(raw_text)
    if embedded_coordinates:
        return _geo_payload(
            normalized_address=normalized_address,
            latitude=embedded_coordinates[0],
            longitude=embedded_coordinates[1],
            geo_status="ready",
            geo_source="source_embedded",
            geo_confidence=0.9,
            geo_precision="exact",
            geo_matched_label=str(record.get("title") or ""),
            geo_matched_address=str(record.get("address") or ""),
        )

    if build_geocoding_enabled:
        geocoded = await _geocode_with_nominatim(
            geocoder_url=build_geocoder_url,
            query=str(record.get("address") or ""),
            label=str(record.get("title") or ""),
        )
        if geocoded:
            geocoded["normalized_address"] = normalized_address
            return geocoded

    return _geo_payload(normalized_address=normalized_address, latitude=None, longitude=None, geo_status="failed")


async def _enrich_record_geo(
    record: dict[str, Any],
    *,
    raw_text: str | None,
    canonical_store: CanonicalStore | None,
    geo_overrides: dict[str, dict[str, dict[str, Any]]],
    build_geocoding_enabled: bool,
    build_geocoder_url: str,
) -> None:
    geo_payload = await _resolve_geo_payload(
        record,
        raw_text=raw_text,
        canonical_store=canonical_store,
        geo_overrides=geo_overrides,
        build_geocoding_enabled=build_geocoding_enabled,
        build_geocoder_url=build_geocoder_url,
    )
    record.update(geo_payload)
    if canonical_store:
        canonical_store.upsert_entity_geo(entity_id=str(record["page_id"]), **geo_payload)


def infer_entity_kind(record: dict[str, Any]) -> str:
    service_type = str(record.get("service_type") or "")
    category = str(record.get("category") or "")
    if service_type == "service_catalog":
        return "service_program"
    if category in {"documents", "reference"}:
        return "document_reference"
    if service_type.startswith("streetwork") or (record.get("address") and "," not in str(record.get("address")) and "leipzig" in normalize_text(str(record.get("address")))):
        return "mobile_service_slot"
    return "service_location"


def normalize_opening_hours(hours: list[str]) -> list[dict[str, Any]]:
    normalized_entries: list[dict[str, Any]] = []
    for raw_line in hours:
        line = _normalize_spaces(raw_line)
        if not line:
            continue
        lowered = normalize_text(line)
        weekdays: list[str] = []
        for triggers, expanded_days in DAY_RANGE_PATTERNS:
            if any(trigger in lowered for trigger in triggers):
                weekdays = list(expanded_days)
                break
        if not weekdays:
            for day_code, aliases in WEEKDAY_ALIASES.items():
                if any(alias in lowered for alias in aliases):
                    weekdays.append(day_code)
        times = TIME_RE.findall(line)
        entry: dict[str, Any] = {"text": line, "weekdays": weekdays}
        if len(times) >= 2:
            entry["open"] = times[0].replace(".", ":")
            entry["close"] = times[1].replace(".", ":")
        elif "24 stunden" in lowered or "ganztagig" in lowered or "ganztägig" in lowered:
            entry["open"] = "00:00"
            entry["close"] = "24:00"
        if "feiertag" in lowered:
            entry["note"] = "holiday"
        normalized_entries.append(entry)
    return normalized_entries


def _field_index_entries(record: dict[str, Any]) -> dict[str, set[str]]:
    entries: dict[str, set[str]] = defaultdict(set)
    page_id = record["page_id"]
    alias_values = [*record.get("aliases", []), record["title"], record["page_id"].replace("-", " ")]
    for alias in alias_values:
        normalized_alias = normalize_text(str(alias))
        if normalized_alias:
            entries["aliases"].add(normalized_alias)
        for token in tokenize(str(alias)):
            entries["aliases"].add(token)
    address = str(record.get("address") or "")
    if address:
        entries["address_terms"].add(normalize_text(address))
        for token in tokenize(address):
            entries["address_terms"].add(token)
        for token in detail_tokens(address):
            entries["address_terms"].add(token)
    service_type = str(record.get("service_type") or "")
    if service_type:
        entries["service_types"].add(normalize_text(service_type.replace("_", " ")))
        entries["service_types"].add(service_type)
    organization = str(record.get("organization") or record.get("publisher") or "")
    if organization:
        entries["organizations"].add(normalize_text(organization))
        for token in tokenize(organization):
            entries["organizations"].add(token)
    district = str(record.get("district") or "")
    if district:
        entries["districts"].add(normalize_text(district))
    for target_group in record.get("target_groups", []):
        entries["target_groups"].add(normalize_text(str(target_group)))
    entity_kind = str(record.get("entity_kind") or "")
    if entity_kind:
        entries["entity_kinds"].add(entity_kind)
    for hours_entry in record.get("opening_hours_normalized", []):
        for weekday in hours_entry.get("weekdays", []):
            entries["hours"].add(str(weekday))
        if hours_entry.get("open"):
            entries["hours"].add(str(hours_entry["open"]))
        if hours_entry.get("close"):
            entries["hours"].add(str(hours_entry["close"]))
        if hours_entry.get("text"):
            entries["hours"].add(normalize_text(str(hours_entry["text"])))
    family = record["title"].split(" - ", 1)[0].strip()
    if family:
        entries["families"].add(normalize_text(family))
    for key in list(entries):
        if not entries[key]:
            entries.pop(key, None)
    return {key: value for key, value in entries.items()}


def build_field_indexes(records: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    indexes: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for record in records:
        page_id = record["page_id"]
        for index_name, values in _field_index_entries(record).items():
            for value in values:
                indexes[index_name][value].add(page_id)
    return {
        index_name: {term: sorted(page_ids) for term, page_ids in terms.items()}
        for index_name, terms in indexes.items()
    }


def _record_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any] | None:
    if not previous:
        return {"change_type": "created", "page_id": current["page_id"]}
    changed_fields: dict[str, dict[str, Any]] = {}
    watched_fields = (
        "title",
        "address",
        "latitude",
        "longitude",
        "geo_status",
        "opening_hours",
        "description",
        "phone",
        "email",
        "requires_registration",
        "status",
        "review_status",
    )
    for field_name in watched_fields:
        if previous.get(field_name) != current.get(field_name):
            changed_fields[field_name] = {"before": previous.get(field_name), "after": current.get(field_name)}
    if not changed_fields:
        return None
    return {"change_type": "updated", "page_id": current["page_id"], "fields": changed_fields}


def load_sources(path: Path) -> list[SourceDefinition]:
    return [SourceDefinition.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


async def fetch_source_document(
    source: SourceDefinition,
    *,
    url: str | None = None,
    discovered_from: str | None = None,
) -> dict[str, Any]:
    target_url = url or source.url
    parsed = urlparse(target_url)
    if parsed.scheme == "file":
        file_path = Path(url2pathname(parsed.path))
        if _is_pdf(source, content_type=None):
            content = file_path.read_bytes()
            return {
                "text": _extract_pdf(content),
                "raw_text": content.decode("latin1", errors="ignore"),
                "content_type": "application/pdf",
                "final_url": target_url,
                "status_code": 200,
                "etag": None,
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC).isoformat(),
                "discovered_from": discovered_from,
            }
        html = file_path.read_text(encoding="utf-8")
        return {
            "text": html,
            "raw_text": html,
            "content_type": "text/html",
            "final_url": target_url,
            "status_code": 200,
            "etag": None,
            "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC).isoformat(),
            "discovered_from": discovered_from,
        }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(target_url)
        response.raise_for_status()
        if _is_pdf(source, response.headers.get("content-type")):
            extracted = _extract_pdf(response.content)
            return {
                "text": extracted,
                "raw_text": response.content.decode("latin1", errors="ignore"),
                "content_type": response.headers.get("content-type"),
                "final_url": str(response.url),
                "status_code": response.status_code,
                "etag": response.headers.get("etag"),
                "last_modified": response.headers.get("last-modified"),
                "discovered_from": discovered_from,
            }
        return {
            "text": response.text,
            "raw_text": response.text,
            "content_type": response.headers.get("content-type"),
            "final_url": str(response.url),
            "status_code": response.status_code,
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
            "discovered_from": discovered_from,
        }


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
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("h1"):
        fallback_title = repair_text(soup.find("h1").get_text(" ", strip=True))
    else:
        fallback_title = repair_text((soup.title.string if soup.title and soup.title.string else "Untitled").strip())
    extracted = trafilatura.extract(html, include_comments=False, include_links=True)
    if extracted:
        extracted = repair_text(extracted.strip())
        title = extracted.splitlines()[0].strip("# ").strip() if extracted.splitlines() else fallback_title
        if _looks_like_low_quality_title(title):
            title = fallback_title or title
        return repair_text(title or "Untitled"), extracted

    title = fallback_title
    text = repair_text(" ".join(fragment.strip() for fragment in soup.get_text("\n").splitlines() if fragment.strip()))
    return title, text


def _normalize_crawl_url(url: str) -> str:
    parsed = urlparse(url.strip())
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
    ]
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/") or parsed.path,
            parsed.params,
            urlencode(filtered_query, doseq=True),
            "",
        )
    )
    return normalized.rstrip("/")


def _matches_patterns(value: str, patterns: list[str]) -> bool:
    lowered = value.casefold()
    return any(pattern.casefold() in lowered for pattern in patterns)


def _is_discovery_noise(value: str) -> bool:
    return _matches_patterns(value, list(DISCOVERY_IGNORE_HINTS))


def _contains_service_hint(value: str) -> bool:
    return _matches_patterns(value, list(DISCOVERY_SERVICE_HINTS))


def _looks_like_low_quality_title(value: str) -> bool:
    normalized = _normalize_spaces(value)
    if not normalized:
        return True
    if ADDRESS_LINE_RE.search(normalized) or LOOSE_ADDRESS_RE.search(normalized):
        return True
    if TIME_RE.search(normalized) or EMAIL_RE.search(normalized) or PHONE_RE.search(normalized):
        return True
    return len(normalized) > 120


def _is_heading_like(line: str) -> bool:
    normalized = _normalize_spaces(line)
    if not normalized or len(normalized) > 90:
        return False
    lowered = normalized.casefold()
    if lowered in SECTION_IGNORE_HINTS:
        return False
    if any(hint in lowered for hint in SECTION_IGNORE_HINTS):
        return False
    if any(token in normalized for token in (":", ";", "@", "http://", "https://")):
        return False
    if ADDRESS_LINE_RE.search(normalized) or STREET_ONLY_RE.search(normalized):
        return False
    if TIME_RE.search(normalized) or EMAIL_RE.search(normalized) or PHONE_RE.search(normalized):
        return False
    return len(normalized.split()) <= 9


def _extract_heading_sections(raw_html: str) -> list[dict[str, str]]:
    if "<" not in raw_html:
        return []
    soup = BeautifulSoup(raw_html, "html.parser")
    sections: list[dict[str, str]] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        heading_text = _normalize_spaces(heading.get_text(" ", strip=True))
        if not _is_heading_like(heading_text):
            continue
        chunks: list[str] = []
        for sibling in heading.next_siblings:
            sibling_name = getattr(sibling, "name", None)
            if sibling_name and str(sibling_name).lower() in {"h1", "h2", "h3", "h4"}:
                break
            if hasattr(sibling, "get_text"):
                chunk = sibling.get_text(" ", strip=True)
            else:
                chunk = str(sibling).strip()
            normalized_chunk = _normalize_spaces(chunk)
            if normalized_chunk:
                chunks.append(normalized_chunk)
        section_text = "\n".join(chunks).strip()
        if section_text:
            sections.append({"heading": heading_text, "text": repair_text(section_text)})
    return sections


def _extract_text_sections(text: str) -> list[dict[str, str]]:
    lines = _clean_lines(text)
    if len(lines) < 4:
        return []
    sections: list[dict[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in lines[1:]:
        if _is_heading_like(line):
            if current_heading and current_lines:
                sections.append({"heading": current_heading, "text": "\n".join(current_lines)})
            current_heading = line
            current_lines = []
            continue
        if current_heading:
            current_lines.append(line)
    if current_heading and current_lines:
        sections.append({"heading": current_heading, "text": "\n".join(current_lines)})
    return sections


def _section_looks_service_like(section: dict[str, str]) -> bool:
    heading = section["heading"]
    text = section["text"]
    combined = f"{heading}\n{text}"
    if _is_discovery_noise(heading) or _is_discovery_noise(text[:200]):
        return False
    return bool(
        extract_address(_clean_lines(combined))
        or extract_opening_hours(_clean_lines(combined))
        or extract_phone_numbers(_clean_lines(combined))
        or extract_emails(_clean_lines(combined))
        or _contains_service_hint(combined)
    )


def _service_sections(raw_html: str, text: str) -> list[dict[str, str]]:
    sections = [section for section in _extract_heading_sections(raw_html) if _section_looks_service_like(section)]
    if len(sections) >= 2:
        return sections
    fallback_sections = [section for section in _extract_text_sections(text) if _section_looks_service_like(section)]
    if len(fallback_sections) > len(sections):
        sections = fallback_sections
    deduplicated: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for section in sections:
        section_key = normalize_text(f"{section['heading']} {section['text'][:180]}")
        if section_key in seen_keys:
            continue
        seen_keys.add(section_key)
        deduplicated.append(section)
    return deduplicated


def classify_discovered_page(
    source: SourceDefinition,
    url: str,
    title: str,
    text: str,
    raw_content: str,
) -> dict[str, Any]:
    normalized_url = _normalize_crawl_url(url)
    normalized_title = normalize_text(title)
    normalized_text = normalize_text(text)
    combined = " ".join(part for part in (normalized_url, normalized_title, normalized_text[:1600]) if part)
    lines = _clean_lines(text)
    address_candidates = {
        _normalize_spaces(match.group(0))
        for pattern in (LOOSE_ADDRESS_RE, ADDRESS_LINE_RE, LOOSE_STREET_ONLY_RE, STREET_ONLY_RE)
        for match in pattern.finditer(text)
    }
    opening_hours = extract_opening_hours(lines, limit=8)
    phones = extract_phone_numbers(lines)
    emails = extract_emails(lines)
    sections = _service_sections(raw_content, text)
    section_count = len(sections)
    hours_section_count = sum(1 for section in sections if extract_opening_hours(_clean_lines(section["text"]), limit=6))
    reasons: list[str] = []

    if _is_discovery_noise(normalized_url) or _is_discovery_noise(normalized_title):
        reasons.append("noise_path_or_title")
        return {"policy": "ignore", "reasons": reasons, "service_sections": []}

    if normalized_url.casefold().endswith(NON_HTML_DOWNLOAD_SUFFIXES):
        reasons.append("non_html_download")
        return {"policy": "ignore", "reasons": reasons, "service_sections": []}

    if any(hint in combined for hint in CONTACT_AGGREGATION_HINTS) and len(address_candidates) == 0 and len(phones) + len(emails) >= 2:
        reasons.append("contact_aggregation")
        return {"policy": "ignore", "reasons": reasons, "service_sections": sections}

    if len(address_candidates) >= 2:
        reasons.append("multiple_addresses")
    if section_count >= 2:
        reasons.append("repeated_service_blocks")
    if hours_section_count >= 2:
        reasons.append("multiple_opening_hours_sections")
    if _matches_patterns(combined, list(DISCOVERY_CATALOG_HINTS)):
        reasons.append("catalog_path_or_title")

    if {"multiple_addresses", "repeated_service_blocks"} & set(reasons):
        return {"policy": "catalog", "reasons": reasons, "service_sections": sections}

    if "catalog_path_or_title" in reasons and section_count >= 1:
        return {"policy": "catalog", "reasons": reasons, "service_sections": sections}

    atomic_signals = bool(address_candidates or opening_hours or phones or emails or _contains_service_hint(combined))
    if not atomic_signals:
        reasons.append("low_service_signal")
        return {"policy": "ignore", "reasons": reasons, "service_sections": sections}

    reasons.append("single_service_signal")
    return {"policy": "atomic", "reasons": reasons, "service_sections": sections}


def _apply_discovered_page_policy(
    source: SourceDefinition,
    assessment: dict[str, Any],
) -> SourceDefinition:
    policy = str(assessment.get("policy") or "atomic")
    if policy == "catalog":
        return SourceDefinition.model_validate(
            {
                **source.model_dump(),
                "entity_mode": "service_catalog",
                "entity_expectation": "service_catalog",
            }
        )
    return SourceDefinition.model_validate(
        {
            **source.model_dump(),
            "entity_mode": "single",
            "entity_expectation": source.entity_expectation or "service_location",
        }
    )


def discover_internal_links(html: str, source: SourceDefinition, base_url: str) -> list[str]:
    if source.crawl_depth <= 0 or _is_pdf(source, content_type=None):
        return []
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc.casefold()
    allowed_domains = {base_domain, *[domain.casefold() for domain in source.allowed_domains]}
    discovered: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https", "file"}:
            continue
        if parsed.scheme in {"http", "https"} and parsed.netloc.casefold() not in allowed_domains:
            continue
        normalized_url = _normalize_crawl_url(absolute)
        normalized_lower = normalized_url.casefold()
        is_pdf_link = normalized_lower.endswith(".pdf")
        if is_pdf_link and not source.follow_pdf_links:
            continue
        if not is_pdf_link and normalized_lower.endswith(NON_HTML_DOWNLOAD_SUFFIXES):
            continue
        if source.exclude_patterns and any(pattern.casefold() in normalized_lower for pattern in source.exclude_patterns):
            continue
        if _is_discovery_noise(normalized_lower):
            continue
        anchor_text = normalize_text(
            " ".join(
                value
                for value in (
                    anchor.get_text(" ", strip=True),
                    str(anchor.get("title") or "").strip(),
                    str(anchor.get("aria-label") or "").strip(),
                )
                if value
            )
        )
        if anchor_text and _is_discovery_noise(anchor_text):
            continue
        if source.include_patterns and not any(pattern.casefold() in normalized_lower for pattern in source.include_patterns):
            if not any(pattern.casefold() in anchor_text for pattern in source.include_patterns):
                continue
        if is_pdf_link and not (_contains_service_hint(normalized_lower) or _contains_service_hint(anchor_text)):
            continue
        if not is_pdf_link and not source.include_patterns and not (
            _contains_service_hint(normalized_lower) or _contains_service_hint(anchor_text)
        ):
            continue
        if normalized_url not in discovered:
            discovered.append(normalized_url)
    return discovered


def _discovered_source_id(source: SourceDefinition, url: str, depth: int) -> str:
    parsed = urlparse(url)
    slug_basis = Path(parsed.path).stem or Path(parsed.path).name or parsed.netloc or "link"
    slug = _slugify(slug_basis)
    suffix = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{source.source_id}-crawl-{depth}-{slug}-{suffix}"


def _build_discovered_source(source: SourceDefinition, url: str, depth: int) -> SourceDefinition:
    normalized_url = url.rstrip("/")
    format_hint: str = "pdf" if normalized_url.casefold().endswith(".pdf") else "html"
    inherited_service_type = source.service_type if source.service_type != "service_catalog" else "general"
    inherited_entity_mode = source.entity_mode if source.entity_mode == "single" else "single"
    return SourceDefinition.model_validate(
        {
            **source.model_dump(),
            "source_id": _discovered_source_id(source, normalized_url, depth),
            "title": "",
            "url": normalized_url,
            "format": format_hint,
            "source_type": "pdf" if format_hint == "pdf" else "html",
            "service_type": inherited_service_type,
            "entity_mode": inherited_entity_mode,
        }
    )


async def _crawl_documents(
    source: SourceDefinition,
    known_source_urls: set[str] | None = None,
) -> tuple[list[tuple[SourceDefinition, dict[str, Any], int]], list[str], list[dict[str, Any]]]:
    queue: list[tuple[SourceDefinition, int, str | None]] = [(source, 0, None)]
    crawled: list[tuple[SourceDefinition, dict[str, Any], int]] = []
    discovered_urls: list[str] = []
    crawl_decisions: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_source_ids: set[str] = set()
    known_urls = set(known_source_urls or set())
    known_urls.add(_normalize_crawl_url(source.url))

    while queue:
        current_source, depth, discovered_from = queue.pop(0)
        current_url = _normalize_crawl_url(current_source.url)
        if current_url in seen_urls or current_source.source_id in seen_source_ids:
            continue
        seen_urls.add(current_url)
        seen_source_ids.add(current_source.source_id)

        document = await fetch_source_document(current_source, discovered_from=discovered_from)
        final_url = _normalize_crawl_url(str(document.get("final_url") or current_source.url))
        seen_urls.add(final_url)
        effective_source = current_source
        if depth > 0:
            title, text = extract_content(str(document["text"]))
            assessment = classify_discovered_page(
                source,
                final_url,
                title,
                text,
                str(document.get("raw_text") or document["text"]),
            )
            crawl_decisions.append(
                {
                    "url": final_url,
                    "policy": assessment["policy"],
                    "reasons": assessment.get("reasons", []),
                    "source_id": current_source.source_id,
                    "discovered_from": discovered_from,
                }
            )
            if assessment["policy"] == "ignore":
                continue
            effective_source = _apply_discovered_page_policy(current_source, assessment)
            document["extracted_title"] = title
            document["extracted_text"] = text
            document["child_page_policy"] = assessment["policy"]
            document["child_page_policy_reasons"] = assessment.get("reasons", [])
        crawled.append((effective_source, document, depth))

        if depth >= source.crawl_depth:
            continue
        content_type = str(document.get("content_type") or "")
        if "html" not in content_type.casefold():
            continue

        child_urls = discover_internal_links(str(document.get("raw_text") or document["text"]), source, final_url)
        for child_url in child_urls:
            normalized_child = _normalize_crawl_url(child_url)
            if normalized_child in seen_urls or normalized_child in known_urls:
                continue
            discovered_urls.append(normalized_child)
            queue.append((_build_discovered_source(source, normalized_child, depth + 1), depth + 1, final_url))
            known_urls.add(normalized_child)

    return crawled, discovered_urls, crawl_decisions


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
            "entity_id": record["page_id"],
            "entity_kind": record.get("entity_kind"),
            "status": record.get("status"),
            "parent_entity_id": record.get("parent_entity_id"),
            "organization": record.get("organization"),
            "title": record["title"],
            "canonical_title": record.get("canonical_title") or record["title"],
            "category": record["category"],
            "service_type": record["service_type"],
            "language": record["language"],
            "publisher": record.get("publisher"),
            "address": record.get("address"),
            "normalized_address": record.get("normalized_address"),
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "geo_status": record.get("geo_status"),
            "geo_source": record.get("geo_source"),
            "geo_confidence": record.get("geo_confidence"),
            "geo_precision": record.get("geo_precision"),
            "district": record.get("district"),
            "opening_hours": record.get("opening_hours", []),
            "opening_hours_normalized": record.get("opening_hours_normalized", []),
            "description": record.get("description", ""),
            "target_groups": record.get("target_groups", []),
            "eligibility": record.get("eligibility"),
            "gender_access": record.get("gender_access"),
            "walk_in": record.get("walk_in"),
            "requires_registration": record.get("requires_registration"),
            "appointment_required": record.get("appointment_required"),
            "languages": record.get("languages", []),
            "phone": record.get("phone"),
            "email": record.get("email"),
            "tags": record.get("tags", []),
            "aliases": record.get("aliases", []),
            "confidence": record.get("confidence"),
            "source_trust_tier": record.get("source_trust_tier"),
            "conflict_fields": record.get("conflict_fields", []),
            "stale": record.get("stale"),
            "source_urls": record.get("source_urls", []),
            "source_document_refs": record.get("source_document_refs", []),
            "review_status": record.get("review_status", "published"),
            "validation_issues": record.get("validation_issues", []),
            "source_url": record["source_url"],
            "source_snapshot_path": record.get("source_snapshot_path"),
            "source_content_hash": record.get("source_content_hash"),
            "source_last_seen": record.get("source_last_seen"),
            "source_updated_at": record.get("source_updated_at"),
            "last_verified": record.get("last_verified"),
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
        match = LOOSE_ADDRESS_RE.search(line)
        if match:
            return _normalize_spaces(match.group(0))
    for line in lines:
        match = ADDRESS_LINE_RE.search(line)
        if match:
            return _normalize_spaces(match.group(0))
    for line in lines:
        match = LOOSE_STREET_ONLY_RE.search(line)
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
    opening_hours_normalized = normalize_opening_hours(opening_hours)
    record = {
        "entity_id": page_id,
        "page_id": page_id,
        "entity_kind": "service_program" if is_parent_page else "service_location",
        "status": "active",
        "parent_entity_id": source.source_id if (page_id != source.source_id and source.entity_mode != "single") else None,
        "organization": source.publisher,
        "title": title,
        "canonical_title": title,
        "category": source.category,
        "service_type": service_type,
        "language": source.language,
        "source_url": source.url,
        "source_urls": [source.url],
        "source_document_refs": [raw_snapshot_path],
        "last_updated": generated_at.date().isoformat(),
        "last_verified": generated_at.isoformat(),
        "publisher": source.publisher,
        "address": address,
        "normalized_address": _normalize_address_value(address),
        "latitude": None,
        "longitude": None,
        "geo_status": "missing_address" if not address else None,
        "geo_source": None,
        "geo_confidence": None,
        "geo_precision": None,
        "district": None,
        "opening_hours": opening_hours,
        "opening_hours_normalized": opening_hours_normalized,
        "description": description,
        "target_groups": target_groups,
        "eligibility": None,
        "gender_access": gender_access,
        "walk_in": walk_in,
        "requires_registration": requires_registration,
        "appointment_required": requires_registration,
        "languages": languages,
        "phone": phone,
        "email": email,
        "tags": source.tags,
        "aliases": aliases,
        "confidence": 0.94,
        "source_trust_tier": source.trust_tier,
        "conflict_fields": [],
        "stale": False,
        "superseded_by": None,
        "merged_into": None,
        "source_snapshot_path": raw_snapshot_path,
        "source_content_hash": source_content_hash,
        "source_last_seen": generated_at.isoformat(),
        "source_updated_at": None,
        "summary": summarize_text(text),
        "file_path": file_path,
        "_raw_text": text,
    }
    if not record["summary"]:
        record["summary"] = description or title
    if is_parent_page:
        _apply_parent_page_cleanup(record)
        record["entity_kind"] = "service_program"
    review_status, validation_issues = validate_extracted_record(record)
    record["review_status"] = review_status
    record["validation_issues"] = validation_issues
    _apply_source_record_overrides(record)
    record["opening_hours_normalized"] = normalize_opening_hours(record.get("opening_hours", []))
    record["appointment_required"] = record.get("requires_registration")
    record["entity_kind"] = infer_entity_kind(record)
    record["entity_signature"] = build_entity_signature(record)
    return record


def _expand_source_records(
    source: SourceDefinition,
    title: str,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
    raw_content: str | None = None,
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
        records.extend(
            _expand_service_catalog_records(
                source,
                text,
                generated_at,
                raw_snapshot_path,
                source_content_hash,
                raw_content=raw_content,
            )
        )
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
    *,
    raw_content: str | None = None,
) -> list[dict]:
    if source.source_id == "wohnungsnotfallhilfe-pdf":
        return _expand_wohnungsnotfallhilfe_records(source, text, generated_at, raw_snapshot_path, source_content_hash)
    if source.source_id == "leipzig-schadensminimierung":
        return _expand_schadensminimierung_records(source, text, generated_at, raw_snapshot_path, source_content_hash)
    return _expand_generic_catalog_records(
        source,
        text,
        generated_at,
        raw_snapshot_path,
        source_content_hash,
        raw_content=raw_content,
    )


def _expand_generic_catalog_records(
    source: SourceDefinition,
    text: str,
    generated_at: datetime,
    raw_snapshot_path: str,
    source_content_hash: str,
    *,
    raw_content: str | None = None,
) -> list[dict]:
    sections = _service_sections(raw_content or text, text)
    if len(sections) < 2:
        return []

    records: list[dict] = []
    seen_slugs: set[str] = set()
    for index, section in enumerate(sections, start=1):
        title = _normalize_spaces(section["heading"])
        if not title:
            continue
        slug = _slugify(title) or f"section-{index}"
        if slug in seen_slugs:
            slug = f"{slug}-{index}"
        seen_slugs.add(slug)
        section_text = section["text"].strip()
        if not section_text:
            continue

        section_lines = _clean_lines(section_text)
        address = extract_address(section_lines)
        opening_hours = extract_opening_hours(section_lines, limit=6)
        phones = extract_phone_numbers(section_lines)
        emails = extract_emails(section_lines)
        if not any((address, opening_hours, phones, emails)):
            continue

        location_source = SourceDefinition.model_validate(
            {
                **source.model_dump(),
                "source_id": f"{source.source_id}-{slug}",
                "title": title,
                "service_type": infer_service_type(source, title, section_text),
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
            address=address or structured["address"],
            opening_hours=opening_hours or structured["opening_hours"],
            description=structured["description"],
            aliases=structured["aliases"],
            service_type=str(structured["service_type"]),
            target_groups=structured["target_groups"],
            gender_access=structured["gender_access"],
            walk_in=structured["walk_in"],
            requires_registration=structured["requires_registration"],
            languages=structured["languages"],
            phone=phones[0] if phones else structured["phone"],
            email=emails[0] if emails else structured["email"],
        )
        record["parent_entity_id"] = source.source_id
        record["confidence"] = min(float(record.get("confidence") or 0.94), 0.84)
        if "generic_catalog_split" not in record["validation_issues"]:
            record["validation_issues"].append("generic_catalog_split")
        if record["review_status"] == "published" and not record.get("address"):
            record["review_status"] = "needs_review"
        records.append(record)
    return records


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

def _resolve_manual_sources(source: SourceDefinition, source_registry_root: Path, intake_root: Path | None) -> list[SourceDefinition]:
    manual_sources: list[SourceDefinition] = []
    for index, manual_file in enumerate(source.manual_files):
        candidate = Path(manual_file)
        if not candidate.is_absolute():
            registry_relative = source_registry_root / manual_file
            if registry_relative.exists():
                candidate = registry_relative
            elif intake_root:
                intake_relative = intake_root / manual_file
                if intake_relative.exists():
                    candidate = intake_relative
        if not candidate.exists():
            continue
        manual_sources.append(
            SourceDefinition.model_validate(
                {
                    **source.model_dump(),
                    "source_id": f"{source.source_id}-manual-{index + 1}",
                    "title": f"{source.title} manual {index + 1}",
                    "url": candidate.resolve().as_uri(),
                    "source_type": "manual",
                    "format": "pdf" if candidate.suffix.casefold() == ".pdf" else "html",
                    "entity_mode": "single",
                }
            )
        )
    return manual_sources


def publish_dataset(
    records: list[dict],
    pages: dict[str, str],
    output_root: Path,
    *,
    canonical_db_path: Path | None = None,
    document_count: int = 0,
    entity_diffs: list[dict[str, Any]] | None = None,
) -> Manifest:
    generated_at = datetime.now(UTC)
    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        pages_root = temp_root / "pages"
        index_root = temp_root / "index"
        field_indexes_root = index_root / "field_indexes"
        pages_root.mkdir(parents=True)
        index_root.mkdir(parents=True)
        field_indexes_root.mkdir(parents=True)

        for record in records:
            validate_page_record(record)
            page_name = Path(record["file_path"]).name
            (pages_root / page_name).write_text(pages[record["page_id"]], encoding="utf-8")

        aliases: dict[str, list[str]] = {}
        for record in records:
            for alias in sorted(alias_terms(record)):
                aliases.setdefault(alias, []).append(record["page_id"])
        aliases = {term: sorted(set(page_ids)) for term, page_ids in aliases.items()}
        field_indexes = build_field_indexes(records)
        field_indexes.setdefault("aliases", aliases)

        manifest = Manifest(
            kb_version=generated_at.strftime("%Y%m%d%H%M%S"),
            generated_at=generated_at,
            source_count=len({record["source_url"] for record in records}),
            page_count=len(records),
            document_count=document_count,
            entity_count=len(records),
            canonical_db="index/runtime_snapshot.sqlite" if canonical_db_path else None,
            index_artifacts=[
                "manifest.json",
                "pages.json",
                "aliases.json",
                "entities.jsonl",
                "alias_index.json",
                "field_indexes",
                "runtime_snapshot.sqlite" if canonical_db_path else "",
            ],
        )
        manifest.index_artifacts = [item for item in manifest.index_artifacts if item]

        serialized_records: list[dict[str, Any]] = []
        for record in records:
            serialized = dict(record)
            serialized.pop("_raw_text", None)
            serialized_records.append(serialized)

        (index_root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        (index_root / "pages.json").write_text(json.dumps(serialized_records, ensure_ascii=False, indent=2), encoding="utf-8")
        (index_root / "aliases.json").write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
        (index_root / "alias_index.json").write_text(json.dumps(field_indexes.get("aliases", aliases), ensure_ascii=False, indent=2), encoding="utf-8")
        (index_root / "entities.jsonl").write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in serialized_records) + "\n",
            encoding="utf-8",
        )
        if entity_diffs is not None:
            (index_root / "entity_diffs.json").write_text(json.dumps(entity_diffs, ensure_ascii=False, indent=2), encoding="utf-8")
        for index_name, values in field_indexes.items():
            (field_indexes_root / f"{index_name}.json").write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        if canonical_db_path and canonical_db_path.exists():
            copy_runtime_sqlite(canonical_db_path, temp_root)

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


async def run_pipeline(
    source_registry: Path,
    output_root: Path,
    raw_root: Path,
    reports_root: Path | None = None,
    *,
    canonical_db_path: Path | None = None,
    intake_root: Path | None = None,
    build_qc_enabled: bool = False,
    build_qc_provider: str = "disabled",
    build_qc_model: str | None = None,
    build_qc_base_url: str | None = None,
    build_qc_api_key: str | None = None,
    geo_overrides_path: Path | None = None,
    build_geocoding_enabled: bool = False,
    build_geocoder_url: str = "https://nominatim.openstreetmap.org/search",
) -> Manifest:
    raw_root.mkdir(parents=True, exist_ok=True)
    if reports_root:
        reports_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)
    previous_records = _load_existing_records(output_root)
    source_registry_root = source_registry.parent
    records: list[dict] = []
    pages: dict[str, str] = {}
    failures: list[dict] = []
    changed_page_ids: list[str] = []
    unchanged_page_ids: list[str] = []
    discovered_document_urls: list[str] = []
    crawl_decisions: list[dict[str, Any]] = []
    qc_reviewer = create_build_quality_reviewer(
        enabled=build_qc_enabled,
        provider=build_qc_provider,
        model=build_qc_model,
        base_url=build_qc_base_url,
        api_key=build_qc_api_key,
    )
    geo_overrides = _load_geo_overrides(geo_overrides_path)
    canonical_store = CanonicalStore(canonical_db_path) if canonical_db_path else None
    try:
        expanded_sources: list[SourceDefinition] = []
        for source in load_sources(source_registry):
            expanded_sources.append(source)
            expanded_sources.extend(_resolve_manual_sources(source, source_registry_root, intake_root))
        known_source_urls = {_normalize_crawl_url(item.url) for item in expanded_sources}
        for source in expanded_sources:
            if canonical_store:
                canonical_store.upsert_source(source)
            try:
                crawled_documents, newly_discovered_urls, new_crawl_decisions = await _crawl_documents(
                    source,
                    known_source_urls=known_source_urls,
                )
                for discovered_url in newly_discovered_urls:
                    if discovered_url not in discovered_document_urls:
                        discovered_document_urls.append(discovered_url)
                crawl_decisions.extend(new_crawl_decisions)

                for current_source, document, _depth in crawled_documents:
                    if canonical_store and current_source.source_id != source.source_id:
                        canonical_store.upsert_source(current_source)

                    raw_snapshot = raw_root / f"{current_source.source_id}-{generated_at.strftime('%Y%m%d%H%M%S')}.html"
                    raw_snapshot.write_text(str(document["text"]), encoding="utf-8")
                    source_content_hash = hashlib.sha256(str(document["text"]).encode("utf-8")).hexdigest()
                    raw_text = str(document.get("raw_text") or document["text"])
                    if document.get("content_type") and "html" in str(document.get("content_type")).casefold():
                        title = str(document.get("extracted_title") or "")
                        text = str(document.get("extracted_text") or "")
                        if not title or not text:
                            title, text = extract_content(str(document["text"]))
                    else:
                        title = current_source.title or source.title or "Untitled"
                        text = repair_text(str(document["text"]))

                    document_id = None
                    if canonical_store:
                        document_id = canonical_store.insert_document(
                            source_id=current_source.source_id,
                            source_url=current_source.url,
                            canonical_url=str(document.get("final_url") or current_source.url),
                            mime_type=document.get("content_type"),
                            raw_hash=hashlib.sha256(raw_text.encode("utf-8", errors="ignore")).hexdigest(),
                            normalized_hash=hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest(),
                            http_status=document.get("status_code"),
                            raw_path=raw_snapshot.relative_to(raw_root.parent).as_posix(),
                            content_excerpt=text[:1000],
                            discovered_from=document.get("discovered_from"),
                            etag=document.get("etag"),
                            last_modified=document.get("last_modified"),
                        )

                    expanded_records = _expand_source_records(
                        current_source,
                        title,
                        text,
                        generated_at,
                        raw_snapshot.relative_to(raw_root.parent).as_posix(),
                        source_content_hash,
                        raw_content=raw_text,
                    )
                    for record in expanded_records:
                        await _enrich_record_geo(
                            record,
                            raw_text=raw_text,
                            canonical_store=canonical_store,
                            geo_overrides=geo_overrides,
                            build_geocoding_enabled=build_geocoding_enabled,
                            build_geocoder_url=build_geocoder_url,
                        )
                        record["source_urls"] = sorted({source.url, current_source.url, str(document.get("final_url") or current_source.url)})
                        if document_id is not None:
                            record["source_document_refs"] = [f"document:{document_id}", record["source_snapshot_path"]]
                        if document.get("child_page_policy") == "catalog" and record["page_id"] != current_source.source_id:
                            record["confidence"] = min(float(record.get("confidence") or 0.94), 0.82)
                        if document.get("child_page_policy") == "catalog" and "child_catalog_page" not in record["validation_issues"]:
                            record["validation_issues"].append("child_catalog_page")
                        previous = previous_records.get(record["page_id"])
                        if previous and previous.get("source_content_hash") == source_content_hash:
                            unchanged_page_ids.append(record["page_id"])
                        else:
                            changed_page_ids.append(record["page_id"])
                        records.append(record)
                        pages[record["page_id"]] = build_markdown(record, record["_raw_text"], generated_at)
                        if canonical_store:
                            canonical_store.upsert_entity(record, current_source)
                            if document_id is not None:
                                canonical_store.record_claims(record, document_id)
                            canonical_store.record_entity_version(record)
                            canonical_store.record_review(record)
            except Exception as exc:
                failures.append({"source_id": source.source_id, "url": source.url, "error": str(exc)})

        conflict_fields = detect_conflict_fields(records)
        for record in records:
            conflicts = conflict_fields.get(record["page_id"], [])
            if not conflicts:
                continue
            record["conflict_fields"] = conflicts
            if "conflicting_claims" not in record["validation_issues"]:
                record["validation_issues"].append("conflicting_claims")
            record["review_status"] = "needs_review"
            record["confidence"] = min(float(record.get("confidence") or 0.94), 0.7)

        removed_page_ids = sorted(set(previous_records) - {record["page_id"] for record in records})
        entity_diffs = [
            diff
            for diff in (_record_diff(previous_records.get(record["page_id"]), record) for record in records)
            if diff is not None
        ]
        entity_diffs.extend({"change_type": "removed", "page_id": page_id} for page_id in removed_page_ids)
        changed_records = [record for record in records if record["page_id"] in set(changed_page_ids)]
        qc_suggestions = await qc_reviewer.review(changed_records)
        if canonical_store:
            canonical_store.mark_removed_entities(removed_page_ids)
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
                        "discovered_document_count": len(discovered_document_urls),
                        "discovered_document_urls": discovered_document_urls,
                        "crawl_decision_count": len(crawl_decisions),
                        "crawl_decisions": crawl_decisions,
                        "entity_diffs": entity_diffs,
                        "build_qc_provider": qc_reviewer.name,
                        "build_qc_suggestion_count": len(qc_suggestions),
                        "build_qc_suggestions": qc_suggestions,
                        "failures": failures,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        if not records:
            raise RuntimeError("Scraper run produced no valid pages.")
        return publish_dataset(
            records,
            pages,
            output_root,
            canonical_db_path=canonical_db_path,
            document_count=canonical_store.document_count() if canonical_store else len(expanded_sources),
            entity_diffs=entity_diffs,
        )
    finally:
        if canonical_store:
            canonical_store.close()
