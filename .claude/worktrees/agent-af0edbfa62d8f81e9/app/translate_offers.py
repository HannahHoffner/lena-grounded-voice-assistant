"""CLI-Wartungsprozess für persistierte, prüfbare Angebotsübersetzungen."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx

from .config import Settings, load_settings
from .i18n import (
    TARGET_LANGUAGES,
    load_translation_store,
    mark_translation_state_for_offers,
    now_utc,
    offer_translation_hash,
    translation_store_path,
    write_json,
)
from .kb_loader import load_knowledge_base
from .models import Language, OfferRecord


class TranslationError(RuntimeError):
    pass


def _source_payload(offer: OfferRecord) -> dict[str, Any]:
    return {
        "id": offer.id,
        "name": offer.name,
        "short_description": offer.short_description,
        "services": offer.services,
        "opening_hours_raw": offer.opening_hours_raw,
        "standzeiten_raw": offer.standzeiten_raw,
        "phone_numbers": offer.phone_numbers,
        "notes": offer.notes,
        "address_do_not_translate": offer.address,
        "emails_do_not_translate": offer.emails,
        "website_do_not_translate": offer.website,
    }


def _translation_system_prompt() -> str:
    return (
        "You translate structured service records for LENA, an accessible help app in Leipzig. "
        "Return JSON only. Translate German source text into simple, clear language for vulnerable users. "
        "Do not add facts. Do not remove facts. Keep addresses, phone numbers, e-mails, URLs, hashtags, "
        "prices, exact times, and proper names unchanged. Proper names include organization names, project "
        "names, street names, districts, people names, and names such as LENA, Leipzig, CABL, SAFE, SPDi, "
        "Hilfebus, Alternative I, Alternative III, OASE, Rücke. You may translate descriptive words inside "
        "a display name only when the organization or project name remains recognizable. "
        "Keep every list field as a list with the same number of items and the same order as the source. "
        "For phone_numbers, keep the number unchanged and translate only explanatory text in brackets. "
        "Use the requested target languages. The result must have shape "
        "{\"translations\":{\"en\":{...},\"pl\":{...},\"ro\":{...},\"ru\":{...}}}. "
        "Each language object must contain name, short_description, services, opening_hours_raw, "
        "standzeiten_raw, phone_numbers, and notes."
    )


async def _post_blablador(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.blablador_base_url or not settings.blablador_api_key or not settings.blablador_model:
        raise TranslationError("Blablador is not configured")
    headers = {"Authorization": f"Bearer {settings.blablador_api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=settings.blablador_timeout_seconds) as client:
        response = await client.post(
            f"{settings.blablador_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        value = response.json()
    if not isinstance(value, dict):
        raise TranslationError("Blablador returned invalid JSON")
    return value


def _response_content(response: dict[str, Any]) -> str:
    content = response["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if not isinstance(content, str):
        raise TranslationError("Blablador response contains no text")
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    return content


def _validate_translation(offer: OfferRecord, payload: dict[str, Any], languages: list[Language]) -> dict[str, Any]:
    translations = payload.get("translations")
    if not isinstance(translations, dict):
        raise TranslationError("Translation payload has no translations object")
    source_lists = {
        "services": offer.services,
        "opening_hours_raw": offer.opening_hours_raw,
        "standzeiten_raw": offer.standzeiten_raw,
        "phone_numbers": offer.phone_numbers,
        "notes": offer.notes,
    }
    cleaned: dict[str, Any] = {}
    for language in languages:
        raw = translations.get(language.value)
        if not isinstance(raw, dict):
            raise TranslationError(f"Missing translation for {language.value}")
        item: dict[str, Any] = {}
        for field in ("name", "short_description"):
            value = raw.get(field)
            if not isinstance(value, str) or not value.strip():
                raise TranslationError(f"Invalid {field} for {language.value}")
            item[field] = " ".join(value.split())
        for field, source_values in source_lists.items():
            values = raw.get(field)
            if not isinstance(values, list) or len(values) != len(source_values):
                raise TranslationError(f"Invalid list field {field} for {language.value}")
            item[field] = [" ".join(str(value).replace("\n", " ").removeprefix(">").split()) for value in values]
        cleaned[language.value] = item
    return cleaned


async def _translate_offer_blablador_once(
    settings: Settings,
    offer: OfferRecord,
    languages: list[Language],
) -> dict[str, Any]:
    user = {
        "source_language": "de",
        "target_languages": [language.value for language in languages],
        "record": _source_payload(offer),
    }
    payload = {
        "model": settings.blablador_model,
        "temperature": 0,
        "max_tokens": max(settings.blablador_max_tokens, 3000),
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _translation_system_prompt()},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }
    try:
        parsed = json.loads(_response_content(await _post_blablador(settings, payload)))
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TranslationError(f"Could not translate offer {offer.id}: {exc}") from exc
    return _validate_translation(offer, parsed, languages)


async def translate_offer_blablador(
    settings: Settings,
    offer: OfferRecord,
    languages: list[Language],
) -> dict[str, Any]:
    try:
        return await _translate_offer_blablador_once(settings, offer, languages)
    except TranslationError:
        combined: dict[str, Any] = {}
        errors: list[str] = []
        for language in languages:
            try:
                combined.update(await _translate_offer_blablador_once(settings, offer, [language]))
            except TranslationError as exc:
                errors.append(f"{language.value}: {exc}")
        if errors:
            raise TranslationError("; ".join(errors))
        return combined


def _copy_translation(offer: OfferRecord, languages: list[Language]) -> dict[str, Any]:
    source = {
        "name": offer.name,
        "short_description": offer.short_description,
        "services": offer.services,
        "opening_hours_raw": offer.opening_hours_raw,
        "standzeiten_raw": offer.standzeiten_raw,
        "phone_numbers": offer.phone_numbers,
        "notes": offer.notes,
    }
    return {language.value: source for language in languages}


def _needs_translation(entry: dict[str, Any], offer: OfferRecord, languages: list[Language], *, force: bool) -> bool:
    if force:
        return True
    offer_hash = offer_translation_hash(offer)
    if entry.get("source_hash") != offer_hash or entry.get("stale"):
        return True
    translations = entry.get("translations") or {}
    return any(language.value not in translations for language in languages)


async def update_translations(
    settings: Settings,
    *,
    provider: str,
    languages: list[Language],
    limit: int | None,
    force: bool,
    include_reviewed_stale: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Aktualisiert erforderliche Store-Einträge, optional ohne Schreibzugriff."""
    kb = load_knowledge_base(settings.kb_path)
    store = mark_translation_state_for_offers(
        kb.offers,
        settings,
        dataset_hash=kb.source_hash,
    )
    entries = store.setdefault("entries", {})
    translated = 0
    skipped_reviewed = 0
    failures: list[dict[str, str]] = []

    for offer in kb.offers:
        if limit is not None and translated >= limit:
            break
        entry = entries.setdefault(str(offer.id), {})
        if not _needs_translation(entry, offer, languages, force=force):
            continue
        if entry.get("review_status") == "review_needed" and not include_reviewed_stale and not force:
            skipped_reviewed += 1
            continue
        try:
            translations = (
                _copy_translation(offer, languages)
                if provider == "copy"
                else await translate_offer_blablador(settings, offer, languages)
            )
        except TranslationError as exc:
            failures.append({"id": str(offer.id), "name": offer.name, "error": str(exc)})
            continue
        entry["source_hash"] = offer_translation_hash(offer)
        entry["source_name"] = offer.name
        entry["translations"] = {**(entry.get("translations") or {}), **translations}
        entry["review_status"] = "machine"
        entry["stale"] = False
        entry["translated_at"] = now_utc()
        entry["provider"] = provider
        translated += 1
        if not dry_run:
            store["generated_at"] = now_utc()
            write_json(translation_store_path(settings), store)

    if not dry_run:
        store["generated_at"] = now_utc()
        write_json(translation_store_path(settings), store)
    return {
        "translated": translated,
        "failed": len(failures),
        "skipped_reviewed": skipped_reviewed,
        "failures": failures,
        "path": str(translation_store_path(settings)),
    }


def _parse_languages(value: str) -> list[Language]:
    languages = [Language(item.strip()) for item in value.split(",") if item.strip()]
    return [language for language in languages if language != Language.DE]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update stored offer translations.")
    parser.add_argument("--provider", choices=("blablador", "copy"), default="blablador")
    parser.add_argument("--languages", default="en,pl,ro,ru")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Regenerate translations even when hashes match.")
    parser.add_argument(
        "--include-reviewed-stale",
        action="store_true",
        help="Regenerate entries that were previously reviewed and are now stale.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()
    result = asyncio.run(
        update_translations(
            settings,
            provider=args.provider,
            languages=_parse_languages(args.languages),
            limit=args.limit,
            force=args.force,
            include_reviewed_stale=args.include_reviewed_stale,
            dry_run=args.dry_run,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
