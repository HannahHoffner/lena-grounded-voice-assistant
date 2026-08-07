"""Verwaltet persistierte Kartenübersetzungen und manuelle Fachkraft-Overrides."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .models import Language, OfferCard, OfferRecord


TRANSLATED_FIELDS = (
    "name",
    "short_description",
    "services",
    "opening_hours_raw",
    "standzeiten_raw",
    "phone_numbers",
    "notes",
)
TARGET_LANGUAGES = (Language.EN, Language.PL, Language.RO, Language.RU)


def translation_store_path(settings: Settings) -> Path:
    return settings.app_root / "data" / "i18n" / "offer_translations.json"


def manual_overrides_path(settings: Settings) -> Path:
    return settings.app_root / "data" / "i18n" / "manual_overrides.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def offer_translation_hash(offer: OfferRecord) -> str:
    if offer.source_hash:
        return offer.source_hash
    payload = {
        "name": offer.name,
        "short_description": offer.short_description,
        "services": offer.services,
        "opening_hours_raw": offer.opening_hours_raw,
        "standzeiten_raw": offer.standzeiten_raw,
        "phone_numbers": offer.phone_numbers,
        "emails": offer.emails,
        "website": offer.website,
        "notes": offer.notes,
        "address": offer.address,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def empty_store() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": now_utc(),
        "description": (
            "Stored offer translations for LENA. Machine translations are generated only "
            "for new or changed WFS records and can be adjusted through manual_overrides.json."
        ),
        "languages": [language.value for language in TARGET_LANGUAGES],
        "entries": {},
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_translation_store(settings: Settings) -> dict[str, Any]:
    payload = read_json(translation_store_path(settings))
    if not payload:
        return empty_store()
    payload.setdefault("schema_version", 1)
    payload.setdefault("languages", [language.value for language in TARGET_LANGUAGES])
    payload.setdefault("entries", {})
    return payload


def load_manual_overrides(settings: Settings) -> dict[str, Any]:
    payload = read_json(manual_overrides_path(settings))
    payload.setdefault("schema_version", 1)
    payload.setdefault("entries", {})
    return payload


def _base_card(offer: OfferRecord) -> OfferCard:
    return OfferCard(
        id=offer.id,
        name=offer.name,
        short_description=offer.short_description,
        services=offer.services,
        address=offer.address,
        phone_numbers=offer.phone_numbers,
        opening_hours_raw=offer.opening_hours_raw,
        standzeiten_raw=offer.standzeiten_raw,
        notes=offer.notes,
    )


def _apply_translation(card: OfferCard, translation: dict[str, Any] | None) -> OfferCard:
    if not isinstance(translation, dict):
        return card
    update = card.model_dump(mode="json")
    for field in TRANSLATED_FIELDS:
        if field in translation:
            update[field] = translation[field]
    update["id"] = card.id
    update["address"] = card.address
    return OfferCard.model_validate(update)


def localize_offer_card(
    offer: OfferRecord,
    language: Language,
    store: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> OfferCard:
    """Erzeugt eine lokalisierte Karte mit manuellen Overrides als letzter Stufe."""
    card = _base_card(offer)
    offer_hash = offer_translation_hash(offer)
    entry = ((store or {}).get("entries") or {}).get(str(offer.id), {})
    if language != Language.DE and entry.get("source_hash") == offer_hash:
        card = _apply_translation(card, (entry.get("translations") or {}).get(language.value))

    override_entry = ((overrides or {}).get("entries") or {}).get(str(offer.id), {})
    override_translation = (override_entry.get("translations") or {}).get(language.value)
    card = _apply_translation(card, override_translation)
    return card


def mark_translation_state_for_offers(
    offers: list[OfferRecord],
    settings: Settings,
    *,
    dataset_hash: str | None = None,
) -> dict[str, Any]:
    """Markiert Übersetzungen anhand stabiler Angebots-Hashes als aktuell/veraltet."""
    store = load_translation_store(settings)
    entries = store.setdefault("entries", {})
    current_ids = {str(offer.id) for offer in offers}
    changed = False

    for offer in offers:
        offer_id = str(offer.id)
        offer_hash = offer_translation_hash(offer)
        if offer_id not in entries:
            entries[offer_id] = {
                "source_hash": offer_hash,
                "source_name": offer.name,
                "review_status": "needs_translation",
                "translations": {},
            }
            changed = True
        entry = entries[offer_id]
        if entry.get("source_hash") != offer_hash:
            previous_status = str(entry.get("review_status") or "machine")
            entry["previous_source_hash"] = entry.get("source_hash")
            entry["source_hash"] = offer_hash
            entry["source_name"] = offer.name
            entry["stale"] = True
            entry["review_status"] = "review_needed" if previous_status == "reviewed" else "needs_update"
            changed = True
        entry.setdefault("translations", {})
        entry.setdefault("source_name", offer.name)

    for offer_id, entry in entries.items():
        active = offer_id in current_ids
        if entry.get("active", True) != active:
            entry["active"] = active
            if not active:
                entry["archived_at"] = now_utc()
            changed = True

    store["generated_at"] = now_utc()
    if dataset_hash:
        store["source_dataset_hash"] = dataset_hash
    if changed or not translation_store_path(settings).is_file():
        write_json(translation_store_path(settings), store)
    return store


def translation_summary(store: dict[str, Any], offers: list[OfferRecord]) -> dict[str, int]:
    entries = store.get("entries") or {}
    summary = {"ok": 0, "missing": 0, "stale": 0, "review_needed": 0}
    for offer in offers:
        entry = entries.get(str(offer.id), {})
        offer_hash = offer_translation_hash(offer)
        translations = entry.get("translations") or {}
        missing = [language.value for language in TARGET_LANGUAGES if language.value not in translations]
        if entry.get("source_hash") != offer_hash or entry.get("stale"):
            summary["stale"] += 1
        elif missing:
            summary["missing"] += 1
        elif entry.get("review_status") == "review_needed":
            summary["review_needed"] += 1
        else:
            summary["ok"] += 1
    return summary
