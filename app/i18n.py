"""Validiert, migriert und verwendet gespeicherte Angebotsübersetzungen."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .config import Settings
from .card_texts import localize_card_text
from .kb_loader import KnowledgeBase
from .models import Language, OfferCard, OfferRecord
from .spoken_text import offer_spoken_text
from .translation_tokens import PROTECTED_TOKEN_RE, protected_token_inventory
from .translation_contract import (
    FactualIntegrityStatus,
    LinguisticReviewStatus,
    OfferTranslationEntry,
    TranslationFields,
    TranslationRecord,
    TranslationRuntimePolicy,
    TranslationStore,
)


TARGET_LANGUAGES = (Language.EN, Language.PL, Language.RO, Language.RU)
INTERNAL_ID_RE = re.compile(r"\b(?:offer|source|wfs)[ _-]?id\b", re.IGNORECASE)
CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")


@dataclass(frozen=True)
class TranslationContext:
    source_version: str
    source_dataset_hash: str
    curation_catalog_hash: str
    curation_version: str


@dataclass(frozen=True)
class TranslationCatalog:
    store: TranslationStore
    checked_at: str
    integrity_errors: tuple[str, ...] = ()
    migrated_from_schema: str | None = None


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def translation_context(kb: KnowledgeBase) -> TranslationContext:
    curation = kb.metadata.get("curation") if isinstance(kb.metadata.get("curation"), dict) else {}
    return TranslationContext(
        source_version=str(curation.get("approved_source_release_id") or kb.release_id or "source-version-unknown"),
        source_dataset_hash=kb.source_hash,
        curation_catalog_hash=str(curation.get("catalog_content_hash") or ""),
        curation_version=str(curation.get("catalog_version") or "curation-version-unknown"),
    )


def source_translation_hash(offer: OfferRecord) -> str:
    return _sha256(
        {
            "short_description": offer.short_description,
            "services": offer.services,
            "opening_hours_raw": offer.opening_hours_raw,
            "notes": offer.notes,
        }
    )


def operational_facts_hash(offer: OfferRecord) -> str:
    return _sha256(
        {
            "display_name": offer.display_name or offer.name,
            "organization_aliases": offer.organization_aliases,
            "offer_aliases": offer.offer_aliases,
            "district": offer.district,
            "address": offer.address,
            "phone_numbers": offer.phone_numbers,
            "emails": offer.emails,
            "website": offer.website,
            "standzeiten_raw": offer.standzeiten_raw,
        }
    )


def offer_translation_hash(offer: OfferRecord) -> str:
    """Kompatibilitätsname für den Hash der tatsächlich übersetzbaren Felder."""
    return source_translation_hash(offer)


def translation_version(fields: TranslationFields, context: TranslationContext, offer: OfferRecord) -> str:
    return _sha256(
        {
            "fields": fields.model_dump(mode="json"),
            "offer_id": offer.id,
            "source_translation_hash": source_translation_hash(offer),
            "operational_facts_hash": operational_facts_hash(offer),
            "curation_catalog_hash": context.curation_catalog_hash,
        }
    )


def translation_store_path(settings: Settings) -> Path:
    external = (settings.data_dir or settings.app_root / "data") / "i18n" / "offer_translations.json"
    bootstrap = (settings.bootstrap_data_dir or settings.app_root / "data") / "i18n" / "offer_translations.json"
    return external if external.is_file() else bootstrap


def translation_store_write_path(settings: Settings) -> Path:
    return (settings.data_dir or settings.app_root / "data") / "i18n" / "offer_translations.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Ersetzt eine JSON-Datei atomar; ein Fehlschlag lässt den Altstand intakt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def empty_store(*, source_dataset_hash: str | None = None) -> TranslationStore:
    return TranslationStore(
        generated_at=datetime.now(UTC),
        source_dataset_hash=source_dataset_hash,
        languages=list(TARGET_LANGUAGES),
        entries={},
    )


def validate_translation_fields(
    offer: OfferRecord,
    fields: TranslationFields,
    language: Language | None = None,
) -> tuple[str, ...]:
    errors: list[str] = []
    if len(fields.services) != len(offer.services):
        errors.append("services_length_mismatch")
    if len(fields.opening_hours_raw) != len(offer.opening_hours_raw):
        errors.append("opening_hours_raw_length_mismatch")
    if len(fields.notes) != len(offer.notes):
        errors.append("notes_length_mismatch")
    source_values = [offer.short_description, *offer.services, *offer.opening_hours_raw, *offer.notes]
    translated_values = [fields.short_description, *fields.services, *fields.opening_hours_raw, *fields.notes]
    translated_text = " ".join(translated_values)
    if INTERNAL_ID_RE.search(" ".join(translated_values)):
        errors.append("internal_id_visible")
    if language == Language.RU and not CYRILLIC_RE.search(translated_text):
        errors.append("target_script_mismatch")
    if language in {Language.EN, Language.PL, Language.RO} and CYRILLIC_RE.search(translated_text):
        errors.append("target_script_mismatch")
    for index, (source, translated) in enumerate(zip(source_values, translated_values, strict=False)):
        if PROTECTED_TOKEN_RE.findall(source) != PROTECTED_TOKEN_RE.findall(translated):
            errors.append(f"protected_token_mismatch:{index}")
        for token in protected_token_inventory(offer):
            if token in source and translated.count(token) != source.count(token):
                errors.append(f"proper_name_mismatch:{index}")
                break
    return tuple(dict.fromkeys(errors))


def _legacy_status(value: object, *, stale: bool) -> LinguisticReviewStatus:
    if stale:
        return LinguisticReviewStatus.STALE
    status = str(value or "machine")
    if status in {"rejected", "unusable"}:
        return LinguisticReviewStatus.REVIEW_PENDING
    if status in {"reviewed", "review_needed"}:
        return LinguisticReviewStatus.REVIEW_PENDING
    if status in {"needs_translation", "needs_update"}:
        return LinguisticReviewStatus.STALE
    return LinguisticReviewStatus.MACHINE


def migrate_legacy_store(
    payload: dict[str, Any],
    offers: list[OfferRecord],
    context: TranslationContext,
) -> TranslationStore:
    """Migriert Schema 1 im Speicher ohne menschliche Freigaben zu erfinden."""
    by_id = {offer.id: offer for offer in offers}
    migrated = empty_store(source_dataset_hash=context.source_dataset_hash)
    entries = payload.get("entries")
    if entries is not None and not isinstance(entries, dict):
        raise ValueError("legacy translation entries must be a mapping")
    for offer_id, raw_entry in (entries or {}).items():
        if not isinstance(raw_entry, dict):
            continue
        raw_translations = raw_entry.get("translations")
        if raw_translations is not None and not isinstance(raw_translations, dict):
            raise ValueError("legacy translations must be a mapping")
        offer = by_id.get(str(offer_id))
        translations: dict[Language, TranslationRecord] = {}
        for language in TARGET_LANGUAGES:
            raw_fields = (raw_translations or {}).get(language.value)
            if not isinstance(raw_fields, dict):
                continue
            try:
                fields = TranslationFields(
                    short_description=raw_fields.get("short_description"),
                    services=raw_fields.get("services"),
                )
            except ValidationError:
                continue
            if offer is None:
                legacy_hash = str(raw_entry.get("source_hash") or "")
                stable_hash = legacy_hash if re.fullmatch(r"[a-f0-9]{64}", legacy_hash) else _sha256(fields.model_dump(mode="json"))
                translations[language] = TranslationRecord(
                    target_language=language,
                    fields=fields,
                    linguistic_review_status=LinguisticReviewStatus.STALE,
                    factual_integrity_status=FactualIntegrityStatus.STALE,
                    source_version="legacy-unversioned",
                    source_translation_hash=stable_hash,
                    operational_facts_hash=stable_hash,
                    curation_catalog_hash=context.curation_catalog_hash,
                    curation_version=context.curation_version,
                    translation_prompt_version="legacy-unversioned",
                    provider=str(raw_entry.get("provider") or "not_recorded"),
                    model_identifier=str(raw_entry.get("model") or "not_recorded"),
                    created_at=raw_entry.get("translated_at") or payload.get("generated_at") or now_utc(),
                    translation_version=_sha256({"legacy_fields": fields.model_dump(mode="json"), "offer_id": offer_id}),
                )
                continue
            errors = validate_translation_fields(offer, fields)
            stale = bool(raw_entry.get("stale")) or raw_entry.get("source_hash") != offer.source_hash
            status = _legacy_status(raw_entry.get("review_status"), stale=stale)
            integrity = FactualIntegrityStatus.INVALID if errors else (
                FactualIntegrityStatus.STALE if stale else FactualIntegrityStatus.VALID
            )
            translations[language] = TranslationRecord(
                target_language=language,
                fields=fields,
                linguistic_review_status=status,
                factual_integrity_status=integrity,
                source_version=context.source_version,
                source_translation_hash=source_translation_hash(offer),
                operational_facts_hash=operational_facts_hash(offer),
                curation_catalog_hash=context.curation_catalog_hash,
                curation_version=context.curation_version,
                translation_prompt_version="legacy-unversioned",
                provider=str(raw_entry.get("provider") or "not_recorded"),
                model_identifier=str(raw_entry.get("model") or "not_recorded"),
                created_at=raw_entry.get("translated_at") or payload.get("generated_at") or now_utc(),
                translation_version=translation_version(fields, context, offer),
            )
        migrated.entries[str(offer_id)] = OfferTranslationEntry(
            offer_id=str(offer_id),
            source_name=offer.name if offer else str(raw_entry.get("source_name") or f"archived-{offer_id}"),
            active=offer is not None,
            translations=translations,
        )
    return migrated


def migrate_schema_two_store(
    payload: dict[str, Any],
    offers: list[OfferRecord],
    context: TranslationContext,
) -> TranslationStore:
    """Migriert Schema 2 (ohne opening_hours_raw/notes) auf Schema 3.

    Die beiden neuen Felder wurden für bestehende Datensätze nie übersetzt;
    die Migration erfindet daher keine Übersetzung, sondern setzt sie leer
    und markiert jeden migrierten Datensatz als stale, damit er erst nach
    echter Neuerzeugung wieder als nutzbar gilt.
    """
    by_id = {offer.id: offer for offer in offers}
    migrated = empty_store(source_dataset_hash=context.source_dataset_hash)
    entries = payload.get("entries")
    if entries is not None and not isinstance(entries, dict):
        raise ValueError("legacy translation entries must be a mapping")
    for offer_id, raw_entry in (entries or {}).items():
        if not isinstance(raw_entry, dict):
            continue
        raw_translations = raw_entry.get("translations")
        if raw_translations is not None and not isinstance(raw_translations, dict):
            raise ValueError("legacy translations must be a mapping")
        offer = by_id.get(str(offer_id))
        translations: dict[Language, TranslationRecord] = {}
        for language in TARGET_LANGUAGES:
            raw_record = (raw_translations or {}).get(language.value)
            if not isinstance(raw_record, dict):
                continue
            raw_fields = raw_record.get("fields")
            if not isinstance(raw_fields, dict):
                continue
            try:
                fields = TranslationFields(
                    short_description=raw_fields.get("short_description"),
                    services=raw_fields.get("services") or [],
                    opening_hours_raw=[],
                    notes=[],
                )
            except ValidationError:
                continue
            provider = str(raw_record.get("provider") or "not_recorded")
            model_identifier = str(raw_record.get("model_identifier") or "not_recorded")
            created_at = raw_record.get("created_at") or payload.get("generated_at") or now_utc()
            if offer is None:
                stable_hash = _sha256(fields.model_dump(mode="json"))
                translations[language] = TranslationRecord(
                    target_language=language,
                    fields=fields,
                    linguistic_review_status=LinguisticReviewStatus.STALE,
                    factual_integrity_status=FactualIntegrityStatus.STALE,
                    source_version=str(raw_record.get("source_version") or "legacy-unversioned"),
                    source_translation_hash=stable_hash,
                    operational_facts_hash=stable_hash,
                    curation_catalog_hash=context.curation_catalog_hash,
                    curation_version=context.curation_version,
                    translation_prompt_version=str(
                        raw_record.get("translation_prompt_version") or "legacy-unversioned"
                    ),
                    provider=provider,
                    model_identifier=model_identifier,
                    created_at=created_at,
                    translation_version=_sha256({"legacy_fields": fields.model_dump(mode="json"), "offer_id": offer_id}),
                )
                continue
            translations[language] = TranslationRecord(
                target_language=language,
                fields=fields,
                linguistic_review_status=LinguisticReviewStatus.STALE,
                factual_integrity_status=FactualIntegrityStatus.STALE,
                source_version=context.source_version,
                source_translation_hash=source_translation_hash(offer),
                operational_facts_hash=operational_facts_hash(offer),
                curation_catalog_hash=context.curation_catalog_hash,
                curation_version=context.curation_version,
                translation_prompt_version=str(
                    raw_record.get("translation_prompt_version") or "legacy-unversioned"
                ),
                provider=provider,
                model_identifier=model_identifier,
                created_at=created_at,
                translation_version=translation_version(fields, context, offer),
            )
        migrated.entries[str(offer_id)] = OfferTranslationEntry(
            offer_id=str(offer_id),
            source_name=offer.name if offer else str(raw_entry.get("source_name") or f"archived-{offer_id}"),
            active=offer is not None,
            translations=translations,
        )
    return migrated


def _validate_current_record(
    record: TranslationRecord,
    offer: OfferRecord,
    context: TranslationContext,
) -> tuple[str, ...]:
    errors = list(validate_translation_fields(offer, record.fields, record.target_language))
    expected = {
        "source_version": context.source_version,
        "source_translation_hash": source_translation_hash(offer),
        "operational_facts_hash": operational_facts_hash(offer),
        "curation_catalog_hash": context.curation_catalog_hash,
        "curation_version": context.curation_version,
        "translation_version": translation_version(record.fields, context, offer),
    }
    for field, value in expected.items():
        if getattr(record, field) != value:
            errors.append(f"identity_mismatch:{field}")
    return tuple(errors)


def load_translation_catalog(
    settings: Settings,
    kb: KnowledgeBase,
    *,
    path: Path | None = None,
) -> TranslationCatalog:
    checked_at = now_utc()
    payload = read_json(path or translation_store_path(settings))
    context = translation_context(kb)
    migrated_from: str | None = None
    errors: list[str] = []
    try:
        stored_schema_version = str(payload.get("schema_version"))
        if stored_schema_version == "1":
            store = migrate_legacy_store(payload, kb.offers, context)
            migrated_from = "1"
        elif stored_schema_version == "2":
            store = migrate_schema_two_store(payload, kb.offers, context)
            migrated_from = "2"
        else:
            store = TranslationStore.model_validate(payload)
    except ValueError:
        return TranslationCatalog(
            store=empty_store(source_dataset_hash=kb.source_hash),
            checked_at=checked_at,
            integrity_errors=("translation_store_invalid",),
        )

    active_ids = {offer.id for offer in kb.offers}
    by_id = kb.by_id()
    for offer_id, entry in store.entries.items():
        entry.active = offer_id in active_ids
        offer = by_id.get(offer_id)
        if offer is None:
            continue
        for language, record in entry.translations.items():
            record_errors = _validate_current_record(record, offer, context)
            if record_errors:
                errors.extend(f"{offer_id}:{language.value}:{item}" for item in record_errors)
                record.factual_integrity_status = (
                    FactualIntegrityStatus.STALE
                    if all(item.startswith("identity_mismatch") for item in record_errors)
                    else FactualIntegrityStatus.INVALID
                )
    return TranslationCatalog(store=store, checked_at=checked_at, integrity_errors=tuple(errors), migrated_from_schema=migrated_from)


def _base_card(offer: OfferRecord) -> OfferCard:
    return OfferCard(
        id=offer.id,
        name=offer.display_name or offer.name,
        short_description=offer.short_description,
        services=offer.services,
        address=offer.address,
        phone_numbers=offer.phone_numbers,
        opening_hours_raw=offer.opening_hours_raw,
        standzeiten_raw=offer.standzeiten_raw,
        notes=offer.notes,
    )


def _record_is_usable(record: TranslationRecord, policy: TranslationRuntimePolicy) -> bool:
    if record.factual_integrity_status != FactualIntegrityStatus.VALID:
        return False
    if record.linguistic_review_status in {LinguisticReviewStatus.REJECTED, LinguisticReviewStatus.STALE}:
        return False
    if policy == TranslationRuntimePolicy.REVIEWED_ONLY:
        return record.linguistic_review_status == LinguisticReviewStatus.REVIEWED
    if policy == TranslationRuntimePolicy.REVIEWED_OR_MACHINE:
        return record.linguistic_review_status in {
            LinguisticReviewStatus.MACHINE,
            LinguisticReviewStatus.REVIEW_PENDING,
            LinguisticReviewStatus.REVIEWED,
        }
    return False


def localize_offer_card(
    offer: OfferRecord,
    language: Language,
    catalog: TranslationCatalog,
    policy: TranslationRuntimePolicy,
) -> OfferCard:
    """Localize stored prose and closed operational annotations for display.

    Names/addresses and source facts remain unchanged; only phone annotations
    and stand prose use the versioned application-copy projection.
    """
    card = _base_card(offer)
    update: dict[str, object] = {}
    if language != Language.DE and policy != TranslationRuntimePolicy.SOURCE_LANGUAGE_FALLBACK:
        entry = catalog.store.entries.get(offer.id)
        record = entry.translations.get(language) if entry and entry.active else None
        if (
            record is not None
            and _record_is_usable(record, policy)
            and not validate_translation_fields(offer, record.fields, language)
        ):
            update = {
                "short_description": record.fields.short_description,
                "services": record.fields.services,
                "opening_hours_raw": record.fields.opening_hours_raw,
                "notes": record.fields.notes,
            }
    update["phone_numbers"] = [localize_card_text(value, language, policy) for value in card.phone_numbers]
    update["standzeiten_raw"] = [localize_card_text(value, language, policy) for value in card.standzeiten_raw]
    # Single point where spoken_text is built, from whichever fields (source or
    # translated) actually ended up on the card -- keeps card, tile and the TTS
    # allow-list (app/spoken_text.py) from ever disagreeing.
    update["spoken_text"] = offer_spoken_text(
        offer,
        language,
        short_description=update.get("short_description", card.short_description),
        services=update.get("services", card.services),
        opening_hours_raw=update.get("opening_hours_raw", card.opening_hours_raw),
        notes=update.get("notes", card.notes),
        phone_numbers=update["phone_numbers"],
        standzeiten_raw=update["standzeiten_raw"],
    )
    return card.model_copy(update=update)
def analyze_translation_catalog(catalog: TranslationCatalog, kb: KnowledgeBase) -> dict[str, object]:
    context = translation_context(kb)
    counts: dict[str, dict[str, int]] = {}
    by_id = kb.by_id()
    for language in TARGET_LANGUAGES:
        language_counts = {status.value: 0 for status in LinguisticReviewStatus}
        language_counts.update({"missing": 0, "integrity_error": 0})
        for offer in kb.offers:
            entry = catalog.store.entries.get(offer.id)
            record = entry.translations.get(language) if entry else None
            if record is None:
                language_counts["missing"] += 1
                continue
            record_errors = _validate_current_record(record, by_id[offer.id], context)
            if record_errors or record.factual_integrity_status != FactualIntegrityStatus.VALID:
                language_counts["integrity_error"] += 1
            effective_status = (
                LinguisticReviewStatus.STALE
                if any(item.startswith("identity_mismatch") for item in record_errors)
                else record.linguistic_review_status
            )
            language_counts[effective_status.value] += 1
        counts[language.value] = language_counts
    return {
        "store_schema_version": catalog.store.schema_version,
        "active_runtime_policy": None,
        "languages": counts,
        "last_successful_local_integrity_check": (
            catalog.checked_at if not catalog.integrity_errors else None
        ),
        "integrity_error_count": len(catalog.integrity_errors),
        "migrated_from_schema": catalog.migrated_from_schema,
    }


def translation_summary(catalog: TranslationCatalog, kb: KnowledgeBase, policy: TranslationRuntimePolicy) -> dict[str, object]:
    summary = analyze_translation_catalog(catalog, kb)
    summary["active_runtime_policy"] = policy.value
    summary["runtime_quality_status"] = (
        "source_language_only"
        if policy == TranslationRuntimePolicy.SOURCE_LANGUAGE_FALLBACK
        else "reviewed_only_incomplete"
        if policy == TranslationRuntimePolicy.REVIEWED_ONLY
        else "machine_translations_allowed_not_human_reviewed"
    )
    return summary


def clone_store(store: TranslationStore) -> TranslationStore:
    """Liefert eine tiefe Kopie für vollständig schreibfreie Dry-Runs."""
    return TranslationStore.model_validate(deepcopy(store.model_dump(mode="python")))
