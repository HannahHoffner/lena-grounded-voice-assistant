"""Kanonische Erkennung und requestlokale Maskierung operativer Tokens."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import OfferRecord
from .translation_contract import TranslationFields


PROTECTED_TOKEN_RE = re.compile(
    r"https?://[^\s<>]+|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"(?<!\w)(?:\+\d{1,3}[\s/-]?)?(?:\(?\d{2,5}\)?[\s/-])(?:\d[\d\s/-]{3,}\d)|"
    r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b|"
    r"\b\d{1,2}\.\d{1,2}\.(?:\d{2,4})?\b|"
    r"(?<!\w)\d+(?:[.,]\d+)?(?:\s?(?:€|Euro))?|"
    r"[€$£]",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"__LENA_P\d{4}__")
PLACEHOLDER_FRAGMENT_RE = re.compile(r"_*LENA(?:[_-][A-Z0-9]+)+_*", re.IGNORECASE)


class TranslationPlaceholderError(RuntimeError):
    """Redigierter Platzhalterfehler ohne Texte oder operative Fakten."""


@dataclass(frozen=True)
class ProtectedOccurrence:
    placeholder: str
    token: str
    field_path: str


@dataclass(frozen=True)
class MaskedTranslation:
    fields: TranslationFields
    occurrences: tuple[ProtectedOccurrence, ...]


def protected_token_inventory(offer: OfferRecord) -> tuple[str, ...]:
    """Liefert das eine operative Klartextinventar für Prüfung und Maskierung."""
    proper_names = [
        offer.display_name or offer.name,
        offer.name,
        *offer.organization_aliases,
        *offer.offer_aliases,
        *(value for value in (offer.district, offer.address, offer.website) if value),
        *offer.phone_numbers,
        *offer.emails,
    ]
    return tuple(dict.fromkeys(value.strip() for value in proper_names if value and value.strip()))


def protected_tokens_in_text(offer: OfferRecord, text: str) -> tuple[tuple[int, int, str], ...]:
    """Ermittelt überlappungsfrei die längsten kanonisch geschützten Spannen."""
    candidates = [(match.start(), match.end(), match.group(0)) for match in PROTECTED_TOKEN_RE.finditer(text)]
    for token in protected_token_inventory(offer):
        start = 0
        while (index := text.find(token, start)) >= 0:
            candidates.append((index, index + len(token), token))
            start = index + len(token)
    selected: list[tuple[int, int, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(candidate[0] < end and candidate[1] > begin for begin, end, _ in selected):
            continue
        selected.append(candidate)
    return tuple(sorted(selected))


def _mask_text(
    offer: OfferRecord,
    text: str,
    field_path: str,
    offset: int,
) -> tuple[str, list[ProtectedOccurrence]]:
    occurrences: list[ProtectedOccurrence] = []
    parts: list[str] = []
    cursor = 0
    for index, (start, end, token) in enumerate(protected_tokens_in_text(offer, text), start=offset):
        placeholder = f"__LENA_P{index:04d}__"
        parts.extend((text[cursor:start], placeholder))
        occurrences.append(ProtectedOccurrence(placeholder, token, field_path))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), occurrences


_LIST_FIELDS = ("services", "opening_hours_raw", "notes")


def mask_translation_fields(offer: OfferRecord) -> MaskedTranslation:
    """Maskiert jedes Tokenvorkommen mit einem eigenen deterministischen Marker."""
    all_source_text = [
        offer.short_description,
        *offer.services,
        *offer.opening_hours_raw,
        *offer.notes,
    ]
    if PLACEHOLDER_FRAGMENT_RE.search("\n".join(all_source_text)):
        raise TranslationPlaceholderError("translation_token_restore_failed")
    occurrences: list[ProtectedOccurrence] = []
    short_description, additions = _mask_text(offer, offer.short_description, "short_description", 0)
    occurrences.extend(additions)
    masked_lists: dict[str, list[str]] = {}
    for field_name in _LIST_FIELDS:
        masked_items: list[str] = []
        for index, item in enumerate(getattr(offer, field_name)):
            masked, additions = _mask_text(offer, item, f"{field_name}[{index}]", len(occurrences))
            masked_items.append(masked)
            occurrences.extend(additions)
        masked_lists[field_name] = masked_items
    return MaskedTranslation(
        fields=TranslationFields(short_description=short_description, **masked_lists),
        occurrences=tuple(occurrences),
    )


def _field_values(fields: TranslationFields) -> dict[str, str]:
    values = {"short_description": fields.short_description}
    for field_name in _LIST_FIELDS:
        values.update(
            {f"{field_name}[{index}]": value for index, value in enumerate(getattr(fields, field_name))}
        )
    return values


def restore_translation_fields(masked: MaskedTranslation, translated: TranslationFields) -> TranslationFields:
    """Prüft Marker vollständig und stellt Tokens exakt im Ursprungsfeld wieder her."""
    if any(
        len(getattr(translated, field_name)) != len(getattr(masked.fields, field_name))
        for field_name in _LIST_FIELDS
    ):
        raise TranslationPlaceholderError("translation_token_restore_failed")
    values = _field_values(translated)
    combined = "\n".join(values.values())
    expected = {item.placeholder: item for item in masked.occurrences}
    exact_found = PLACEHOLDER_RE.findall(combined)
    if any(placeholder not in expected for placeholder in exact_found):
        raise TranslationPlaceholderError("translation_placeholder_unknown")
    without_exact_placeholders = PLACEHOLDER_RE.sub("", combined)
    if PLACEHOLDER_FRAGMENT_RE.search(without_exact_placeholders):
        raise TranslationPlaceholderError("translation_placeholder_modified")
    for placeholder, occurrence in expected.items():
        count = combined.count(placeholder)
        if count > 1:
            raise TranslationPlaceholderError("translation_placeholder_duplicate")
        if count == 0:
            raise TranslationPlaceholderError("translation_placeholder_missing")
        if placeholder not in values[occurrence.field_path]:
            raise TranslationPlaceholderError("translation_placeholder_modified")
    restored = dict(values)
    for occurrence in masked.occurrences:
        restored[occurrence.field_path] = restored[occurrence.field_path].replace(
            occurrence.placeholder,
            occurrence.token,
            1,
        )
    if PLACEHOLDER_FRAGMENT_RE.search("\n".join(restored.values())):
        raise TranslationPlaceholderError("translation_token_restore_failed")
    return TranslationFields(
        short_description=restored["short_description"],
        **{
            field_name: [
                restored[f"{field_name}[{index}]"]
                for index in range(len(getattr(translated, field_name)))
            ]
            for field_name in _LIST_FIELDS
        },
    )
