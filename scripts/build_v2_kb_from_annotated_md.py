from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ANNOTATION_SOURCE = "data/wissensbasis_hilfsangebote_leipzig_annotiert.md"
CHECKED_AT = "2026-06-15"
REVIEWER = "Codex annotated Markdown import"
REVIEWED_AT = "2026-06-15T00:00:00+02:00"

URL_LIKE_KEYS = {
    "source_url",
    "detail_source_urls",
    "website",
    "snapshot_path",
    "source_hash",
}

GERMAN_DISPLAY_REPLACEMENTS = (
    ("Strassensozialarbeit", "Straßensozialarbeit"),
    ("strassensozialarbeit", "straßensozialarbeit"),
    ("Strasse", "Straße"),
    ("strasse", "straße"),
    ("fuer", "für"),
    ("Fuer", "Für"),
    ("Ueber", "Über"),
    ("ueber", "über"),
    ("Oekumenische", "Ökumenische"),
    ("oekumenische", "ökumenische"),
    ("Oeffnungszeiten", "Öffnungszeiten"),
    ("oeffnungszeiten", "öffnungszeiten"),
    ("geoeffnet", "geöffnet"),
    ("taeglich", "täglich"),
    ("hauptsaechlich", "hauptsächlich"),
    ("aerztliche", "ärztliche"),
    ("Aerztliche", "Ärztliche"),
    ("Maenner", "Männer"),
    ("maenner", "männer"),
    ("Plaetze", "Plätze"),
    ("plaetze", "plätze"),
    ("Waesche", "Wäsche"),
    ("waesche", "wäsche"),
    ("Unterstuetzung", "Unterstützung"),
    ("unterstuetzung", "unterstützung"),
    ("persoenlich", "persönlich"),
    ("Persoenlich", "Persönlich"),
    ("Behoerden", "Behörden"),
    ("behoerden", "behörden"),
    ("Aemter", "Ämter"),
    ("aemter", "ämter"),
    ("weiterfuehrend", "weiterführend"),
    ("Weiterfuehrend", "Weiterführend"),
    ("Bewaeltigung", "Bewältigung"),
    ("bewaeltigung", "bewältigung"),
    ("Maedchen", "Mädchen"),
    ("maedchen", "mädchen"),
    ("Gruenau", "Grünau"),
    ("Suedost", "Südost"),
    ("Loessnig", "Lößnig"),
    ("Doelitz-Doesen", "Dölitz-Dösen"),
    ("Nuernberger", "Nürnberger"),
    ("Rueckmarsdorfer", "Rückmarsdorfer"),
    ("Koehler", "Köhler"),
    ("regulaeren", "regulären"),
    ("Regulaeren", "Regulären"),
    ("selbstaendig", "selbständig"),
    ("Selbstaendig", "Selbständig"),
    ("Notuebernachtung", "Notübernachtung"),
    ("notuebernachtung", "notübernachtung"),
    ("Ueberlebenshilfe", "Überlebenshilfe"),
)


NAME_TO_OFFER_ID = {
    "Mobile Jugendarbeit Leipzig e. V. - Team Westen": "mobile-jugendarbeit-westen",
    "Mobile Jugendarbeit Leipzig e. V. - Team Gruenau": "mobile-jugendarbeit-gruenau",
    "Mobile Jugendarbeit Leipzig e. V. - Team Suedost": "mobile-jugendarbeit-suedost",
    "Jugendhaus Leipzig e.V. Projekt suedpol Mobile Jugendarbeit (Connewitz)": "suedpol-connewitz",
    "Jugendhaus Leipzig e.V. Projekt suedpol Mobile Jugendarbeit (Loessnig)": "suedpol-loessnig",
    "Safe-Strassensozialarbeit fuer Erwachsene - HilfebusSZL Suchtzentrum gGmbH": "hilfebus",
    "Caritasverband Leipzig e.V. Oekumenische Bahnhofsmission Leipzig": "bahnhofsmission",
    "CABL e. V. - Clearingstelle und anonymer Behandlungsschein Leipzig e. V.": "cabl-clearingstelle",
    "UVO - Umfeldnahe Versorgung von Menschen ohne festen Wohnsitz": "uvo-medical-outreach",
    "Sozialamt - Abteilung Soziale Wohnhilfen": "soziale-wohnhilfen-wohnungsnotfallhilfe",
    "Sozialamt - Sachgebiet Wohnungsnotfallhilfe": "soziale-wohnhilfen-wohnungsnotfallhilfe",
    "Sozialamt - Sachgebiet Wohnen": "soziale-wohnhilfen-wohnen",
    "Sozialamt - Sachgebiet Notunterbringung": "soziale-wohnhilfen-notunterbringung",
    "Zentrum fuer Drogenhilfe Notschlafstelle fuer drogenkonsumierende Obdachlose Alternative III": "alternative-iii-notschlafstelle",
    "Zentrum fuer Drogenhilfe Notschlafstelle fuer drogenkonsumierende Obdachlose Alternative I": "alternative-i-notschlafstelle",
    "Uebernachtungshaus fuer wohnungslose Maenner Alt-West / Leutzsch": "uebernachtungshaus-maenner-leutzsch",
    "Advent-Wohlfahrtswerk e. V. Uebernachtungshaus fuer wohnungslose Frauen": "aww-frauen-uebernachtungshaus",
    "SZL Suchtzentrum gGmbH Tagestreff Insel": "tagestreff-insel",
    "Diakonisches Werk Innere Mission Leipzig e. V. Leipziger Oase": "leipziger-oase",
    "Zentrum fuer Drogenhilfe, Kontaktcafe, Alternative I": "kontaktcafe-alternative-i",
    "Safe-Strassensozialarbeit fuer Erwachsene - Team KonsumSZL Suchtzentrum gGmbH": "safe-team-konsum",
    "Safe-Strassensozialarbeit fuer Erwachsene - Team WohnenSZL Suchtzentrum gGmbH": "safe-team-wohnen",
    "Diakonisches Werk Innere Mission Leipzig e. V.": "diakonie-streetwork",
    "Zentrum fuer Drogenhilfe, mobile Alternative": "mobile-alternative",
    "TiMMi ToHelp e. V. - Projekt Care Bags": "timmi-care-bags",
    "Strassensozialarbeit am Amt fuer Jugend und Familie - Streetwork Mitte": "streetwork-mitte",
    "Strassensozialarbeit am Amt fuer Jugend und Familie - Streetwork Ost": "streetwork-ost",
    "Strassensozialarbeit am Amt fuer Jugend und Familie - Streetwork Nord": "streetwork-nord",
    "MachtLos e. V.": "machtlos",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the reviewed LENA v2 KB from the annotated Markdown master file.")
    parser.add_argument("--input", type=Path, default=Path(ANNOTATION_SOURCE))
    parser.add_argument("--kb", type=Path, default=Path("data/v2/curated_kb/offers.json"))
    args = parser.parse_args()

    sections = parse_annotated_markdown(args.input)
    dataset = json.loads(args.kb.read_text(encoding="utf-8"))
    offers_by_id = {offer["offer_id"]: offer for offer in dataset["offers"]}
    touched: set[str] = set()
    unmatched: list[str] = []

    for section in sections:
        offer_id = resolve_offer_id(section)
        if not offer_id:
            unmatched.append(section.title)
            continue
        if offer_id not in offers_by_id:
            unmatched.append(section.title)
            continue
        apply_section(offers_by_id[offer_id], section, dataset.get("source_hash"))
        touched.add(offer_id)

    missing = sorted(set(offers_by_id) - touched)
    if unmatched or missing:
        raise SystemExit(f"Could not fully build v2 KB. unmatched={unmatched}; missing={missing}")

    args.kb.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {len(touched)} offers from {args.input}")


class Section:
    def __init__(self, title: str, body: str) -> None:
        self.title = display_text(title)
        self.fields = parse_fields(body)


def parse_annotated_markdown(path: Path) -> list[Section]:
    text = path.read_text(encoding="utf-8-sig")
    matches = list(re.finditer(r"^###\s+\d+\.\s+(.+?)\s*$", text, flags=re.MULTILINE))
    sections: list[Section] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(Section(match.group(1), text[start:end]))
    return sections


def parse_fields(body: str) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        heading = re.match(r"^\*\*(.+?):\*\*(?:\s*(.*))?$", line)
        if heading:
            current = key_text(heading.group(1))
            value = clean_inline_value(heading.group(2) or "")
            fields.setdefault(current, [])
            if value:
                fields[current].append(value)
            continue
        if current and line.startswith("- "):
            fields.setdefault(current, []).append(display_text(line[2:]))
        elif current and line:
            fields.setdefault(current, []).append(display_text(line))
    return fields


def clean_inline_value(value: str) -> str:
    return display_text(value.strip())


def resolve_offer_id(section: Section) -> str | None:
    names = [section.title, *section.fields.get("Name", [])]
    if any(normalize_key(name) == "uebernachtungshaus fuer wohnungslose maenner" for name in names):
        address = " ".join(section.fields.get("Adresse", []) + section.fields.get("Adresse laut Kopfzeile", []))
        normalized_address = normalize_key(address)
        if "helenenstrasse" in normalized_address:
            return "uebernachtungshaus-maenner-sued"
        if "rueckmarsdorfer" in normalized_address:
            return "uebernachtungshaus-maenner-leutzsch"
    for name in names:
        if name in NAME_TO_OFFER_ID:
            return NAME_TO_OFFER_ID[name]
    normalized_mapping = {normalize_key(name): offer_id for name, offer_id in NAME_TO_OFFER_ID.items()}
    for name in names:
        offer_id = normalized_mapping.get(normalize_key(name))
        if offer_id:
            return offer_id
    return None


def apply_section(offer: dict[str, Any], section: Section, source_hash: str | None) -> None:
    fields = section.fields
    name = first(fields, "Name")
    address = first(fields, "Adresse")
    location = first(fields, "Stadtbezirk / Ortsteil")
    short_description = first(fields, "Kurzbeschreibung")
    card_summary = first(fields, "Karten-Kurzbeschreibung")
    keywords = split_keywords(first(fields, "Retrieval-Keywords"))
    angebote = fields.get("Angebote", [])
    opening = fields.get("Oeffnungszeiten", [])
    hints = fields.get("Sonstige Hinweise", [])
    emails = fields.get("E-Mail", [])
    phones = fields.get("Telefon", [])
    contacts = fields.get("Ansprechpartner/-in", [])
    website = first(fields, "Internetseite")

    if name:
        offer["name"] = name
    if address:
        offer["address"] = normalize_address(address)
    if location:
        offer["location"] = location
    if short_description:
        offer["short_description"] = short_description
    if card_summary:
        offer["card_summary"] = card_summary
    if keywords:
        offer["retrieval_keywords"] = keywords
    if angebote:
        offer["services_provided"] = angebote
    if opening:
        offer["opening_times"] = opening

    stand_times = [item for item in [*hints, *angebote] if looks_like_time_hint(item)]
    if stand_times:
        offer["einsatzzeiten"] = unique([*offer.get("einsatzzeiten", []), *stand_times])
    if phones:
        offer["phone"] = "; ".join(phones)
        offer["phone_reachable_when"] = None
    if emails:
        offer["email"] = "; ".join(emails)
    if contacts:
        offer["contact_people"] = contacts
    if website:
        offer["website"] = website
    offer["notes"] = "; ".join(hints) if hints else None

    apply_known_source_annotations(offer)
    offer["facts"] = compact_dict(
        {
            "angebote": angebote,
            "oeffnungszeiten": opening,
            "einsatzzeiten": offer.get("einsatzzeiten", []),
            "standorte": [point["address"] for point in offer.get("map_points", [])],
            "telefon": phones,
            "email": emails,
            "ansprechpartner": contacts,
            "website": website,
            "hinweise": hints,
            "karten_kurzbeschreibung": card_summary,
        }
    )
    apply_known_fact_annotations(offer)
    offer["review_status"] = "reviewed"
    offer["reviewer"] = REVIEWER
    offer["reviewed_at"] = REVIEWED_AT
    normalize_offer_display_fields(offer)

    evidence_items = [
        evidence("card_summary", offer.get("card_summary"), source_hash),
        evidence("retrieval_keywords", ", ".join(offer.get("retrieval_keywords", keywords)), source_hash),
        evidence("facts", json.dumps(offer["facts"], ensure_ascii=False), source_hash),
    ]
    set_evidence(offer, [item for item in evidence_items if item["evidence_text"]])


def apply_known_fact_annotations(offer: dict[str, Any]) -> None:
    if offer.get("offer_id") == "uebernachtungshaus-maenner-leutzsch":
        facts = offer.setdefault("facts", {})
        facts["oeffnungszeiten"] = offer.get("opening_times", [])
        facts["telefon"] = ["0341 1234504"]
        facts["zielgruppe"] = ["volljährig, männlich und wohnungslos"]
        facts["karten_kurzbeschreibung"] = offer.get("card_summary")


def apply_known_source_annotations(offer: dict[str, Any]) -> None:
    offer_id = offer.get("offer_id")
    if offer_id == "safe-team-wohnen":
        offer["card_summary"] = (
            "SAFE Team Wohnen: Hilfe bei Wohnungs- und Obdachlosigkeit, Geld, Konsum, Gesundheit und Behörden. "
            "Bürozeit Dienstag 10:00-16:00 Uhr Demmeringstraße 32. "
            "Standzeiten: Dienstag 17:00-18:00 Uhr Schwanenteich, Mittwoch und Freitag 10:00-16:00 Uhr Hauptbahnhof."
        )
        offer["services_provided"] = unique(
            [
                *offer.get("services_provided", []),
                "Beratung und Information",
                "Ausgabe von warmen Mahlzeiten und Getränken",
            ]
        )
        offer["retrieval_keywords"] = unique(
            [
                *offer.get("retrieval_keywords", []),
                "essen",
                "warmes essen",
                "warme mahlzeiten",
                "getränke",
                "schwanenteich",
                "goethestraße",
            ]
        )
        offer["einsatzzeiten"] = unique(
            [
                "Dienstag 17:00-18:00 Uhr Schwanenteich / Goethestraße: Beratung, Information, warme Mahlzeiten und Getränke",
                *offer.get("einsatzzeiten", []),
            ]
        )
        offer["map_points"] = [
            {
                "point_id": "buero-demmeringstrasse",
                "label": "SAFE Team Wohnen: Büro Demmeringstraße",
                "address": "Demmeringstraße 32, 04177 Leipzig",
                "latitude": 51.3379213,
                "longitude": 12.3323055,
                "opening_hours": ["Dienstag: 10:00 - 16:00 Uhr (Bürozeit)"],
                "note": "Bürozeit. Beratung zu Wohnen, Geld, Konsum, Gesundheit und Behörden.",
            },
            {
                "point_id": "schwanenteich",
                "label": "SAFE Team Wohnen: Schwanenteich",
                "address": "Goethestraße / Schwanenteich, 04109 Leipzig",
                "latitude": 51.3407649,
                "longitude": 12.3805417,
                "opening_hours": ["Dienstag: 17:00 - 18:00 Uhr"],
                "note": "Beratung, Information, warme Mahlzeiten und Getränke.",
            },
            {
                "point_id": "hauptbahnhof",
                "label": "SAFE Team Wohnen: Hauptbahnhof",
                "address": "Hauptbahnhof, Westseite, Kurt-Schumacher-Straße, 04109 Leipzig",
                "latitude": 51.3453411,
                "longitude": 12.3787712,
                "opening_hours": ["Mittwoch und Freitag: 10:00 - 16:00 Uhr"],
                "note": "Streetwork-Standzeit am Hauptbahnhof.",
            },
        ]
    elif offer_id == "diakonie-streetwork":
        offer["card_summary"] = (
            "Diakonie Streetwork: Beratung, Information und Ausgabe von warmen Mahlzeiten/Getränken "
            "Dienstag 17:00-18:00 Uhr an der Goethestraße/Schwanenteich. Außerdem mobile Kleiderkammer."
        )
        offer["services_provided"] = unique(
            [
                *offer.get("services_provided", []),
                "Beratung und Information",
                "Ausgabe von warmen Mahlzeiten und Getränken",
            ]
        )
        offer["retrieval_keywords"] = unique(
            [
                *offer.get("retrieval_keywords", []),
                "warmes essen",
                "warme mahlzeiten",
                "getränke",
                "schwanenteich",
            ]
        )
        offer["map_points"] = [
            {
                "point_id": "schwanenteich",
                "label": "Diakonie Streetwork: Schwanenteich",
                "address": "Goethestraße / Schwanenteich, 04109 Leipzig",
                "latitude": 51.3407649,
                "longitude": 12.3805417,
                "opening_hours": ["Dienstag: 17:00 - 18:00 Uhr"],
                "note": "Beratung, Information, warme Mahlzeiten und Getränke in Kooperation mit SAFE.",
            }
        ]
    elif offer_id == "safe-team-konsum":
        offer["map_points"] = [
            {
                "point_id": "lindenauer-markt",
                "label": "SAFE Team Konsum: Lindenauer Markt",
                "address": "Lindenauer Markt, 04177 Leipzig",
                "latitude": 51.3374275,
                "longitude": 12.3338098,
                "opening_hours": ["Donnerstag: 16:00 - 17:30 Uhr"],
                "note": "Warme Getränke, kleine Snacks und Gesprächsangebot.",
            }
        ]
    elif offer_id == "uebernachtungshaus-maenner-leutzsch":
        flyer_url = "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/02.5_Dez5_Jugend_Soziales_Gesundheit_Schule/50_Sozialamt/Wohnungsnotfallhilfe_und_Notunterbringung/Flyer_%c3%9cbernachtungshaus_R%c3%bccke.pdf"
        offer["name"] = "Übernachtungshaus Rücke"
        offer["address"] = "Rückmarsdorfer Straße 5-7, 04179 Leipzig"
        offer["phone"] = "0341 1234504"
        offer["target_group"] = ["homeless", "men", "adults"]
        offer["requirements"] = "Volljährig, männlich und wohnungslos."
        offer["opening_times"] = [
            "Montag - Freitag: 16:00 - 08:00 Uhr",
            "Samstag, Sonntag und Feiertag: ganztägig",
        ]
        offer["card_summary"] = (
            "Übernachtungshaus Rücke für volljährige wohnungslose Männer. "
            "Adresse Rückmarsdorfer Straße 5-7. Geöffnet Montag bis Freitag 16:00-08:00 Uhr, "
            "Wochenende und Feiertag ganztägig."
        )
        offer["retrieval_keywords"] = unique([*offer.get("retrieval_keywords", []), "rücke", "ruecke", "rückmarsdorfer straße 5-7", "volljährige wohnungslose männer"])
        offer["detail_source_urls"] = unique([*offer.get("detail_source_urls", []), flyer_url])
    elif offer_id == "hilfebus":
        offer["phone"] = "0152 33661087 (nur zu Einsatzzeiten des Busses)"
        offer["phone_reachable_when"] = "Nur zu Einsatzzeiten des Hilfebusses."
        offer["map_points"] = [
            {
                "point_id": "hauptbahnhof-westseite",
                "label": "Hilfebus: Hauptbahnhof Westseite",
                "address": "Hauptbahnhof, Westseite, Kurt-Schumacher-Straße, 04109 Leipzig",
                "latitude": 51.3453411,
                "longitude": 12.3787712,
                "opening_hours": ["Sonntag: 20:00 - 21:00 Uhr"],
                "note": "Suppenausgabe an der Westseite des Hauptbahnhofs.",
            }
        ]


def normalize_offer_display_fields(offer: dict[str, Any]) -> None:
    for key in (
        "name",
        "organization",
        "source_title",
        "category",
        "subcategory",
        "short_description",
        "card_summary",
        "address",
        "location",
        "opening_times",
        "einsatzzeiten",
        "target_group",
        "requirements",
        "cost",
        "services_provided",
        "languages",
        "notes",
        "aliases",
        "retrieval_keywords",
        "facts",
        "map_points",
    ):
        if key in offer:
            offer[key] = normalize_visible_value(offer[key], key)

    for evidence_item in offer.get("source_evidence", []):
        if "evidence_text" in evidence_item:
            evidence_item["evidence_text"] = normalize_visible_value(evidence_item["evidence_text"], "evidence_text")
    for evidence_items in offer.get("field_evidence", {}).values():
        for evidence_item in evidence_items:
            if "evidence_text" in evidence_item:
                evidence_item["evidence_text"] = normalize_visible_value(evidence_item["evidence_text"], "evidence_text")


def normalize_visible_value(value: Any, key: str = "") -> Any:
    if isinstance(value, str):
        if key in URL_LIKE_KEYS or looks_like_url_or_email(value):
            return restore_encoding(value)
        return display_text(value)
    if isinstance(value, list):
        return [normalize_visible_value(item, key) for item in value]
    if isinstance(value, dict):
        return {item_key: normalize_visible_value(item_value, item_key) for item_key, item_value in value.items()}
    return value


def first(fields: dict[str, list[str]], key: str) -> str | None:
    values = fields.get(key_text(key), [])
    return values[0] if values else None


def split_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return unique(display_text(item) for item in value.split(",") if item.strip())


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


def looks_like_time_hint(value: str) -> bool:
    normalized = normalize_key(value)
    return any(term in normalized for term in ("standzeit", "einsatz", "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag", "taeglich"))


def evidence(field_name: str, value: str | None, source_hash: str | None) -> dict[str, str | None]:
    return {
        "field_name": field_name,
        "source_url": ANNOTATION_SOURCE,
        "evidence_text": value or "",
        "checked_at": CHECKED_AT,
        "source_hash": source_hash,
    }


def set_evidence(offer: dict[str, Any], items: list[dict[str, str | None]]) -> None:
    names = {item["field_name"] for item in items}
    offer["source_evidence"] = [item for item in offer.get("source_evidence", []) if item.get("field_name") not in names]
    offer["source_evidence"].extend(items)
    field_evidence = offer.setdefault("field_evidence", {})
    for item in items:
        field_evidence[item["field_name"]] = [item]


def unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        cleaned = display_text(value)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", key_text(value).casefold()).strip()


def normalize_address(value: str) -> str:
    value = display_text(value).replace(";", ",")
    if re.search(r"\b0\d{4}\b", value) and "Leipzig" not in value:
        value = f"{value} Leipzig"
    return value


def display_text(value: str) -> str:
    value = restore_encoding(value)
    if looks_like_url_or_email(value):
        return value
    for src, dst in GERMAN_DISPLAY_REPLACEMENTS:
        value = value.replace(src, dst)
    value = value.replace(" EUR", " €")
    value = value.replace("EUR", "€")
    return re.sub(r"\s+", " ", value).strip()


def restore_encoding(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    replacements = {
        "â€“": "–",
        "â€”": "—",
        "â‚¬": "€",
        "â€ž": "„",
        "â€œ": "“",
        "â€": "”",
        "Â»": "»",
        "Â«": "«",
        "Ã¤": "ä",
        "Ã¶": "ö",
        "Ã¼": "ü",
        "Ã„": "Ä",
        "Ã–": "Ö",
        "Ãœ": "Ü",
        "ÃŸ": "ß",
        "Ã©": "é",
        "Ã¨": "è",
        "Ã¡": "á",
        "Ã ": "à",
        "Ã³": "ó",
        "Ã²": "ò",
        "Ãº": "ú",
        "Ã¹": "ù",
        "\u00a0": " ",
        "\u2011": "-",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = value.replace("HilfebusSZL", "Hilfebus - SZL")
    value = value.replace("Team KonsumSZL", "Team Konsum - SZL")
    value = value.replace("Team WohnenSZL", "Team Wohnen - SZL")
    return re.sub(r"\s+", " ", value).strip()


def looks_like_url_or_email(value: str) -> bool:
    return bool(re.match(r"^(?:https?://|mailto:)", value, flags=re.IGNORECASE)) or "@" in value and " " not in value


def key_text(value: str) -> str:
    value = display_text(value)
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
        "é": "e",
        "è": "e",
        "á": "a",
        "à": "a",
        "ó": "o",
        "ò": "o",
        "ú": "u",
        "ù": "u",
        "–": "-",
        "—": "-",
        "€": "EUR",
        "„": '"',
        "“": '"',
        "”": '"',
        "»": '"',
        "«": '"',
        "\u00a0": " ",
        "\u2011": "-",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip()


if __name__ == "__main__":
    main()
