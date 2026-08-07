"""Lokale Vertragstests für den operativen Übersetzungs-Platzhalterschutz."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.config import load_settings
from app.kb_loader import load_active_knowledge_base
from app.translation_contract import TranslationFields
from app.translation_tokens import (
    TranslationPlaceholderError,
    mask_translation_fields,
    restore_translation_fields,
)


def _offer(tmp_path, *, short_description: str, services: list[str]):
    settings = replace(
        load_settings(),
        data_dir=tmp_path / "data",
        runtime_dir=tmp_path / "runtime",
        interaction_logging_enabled=False,
    )
    source = load_active_knowledge_base(settings).by_id()["23"]
    return source.model_copy(update={"short_description": short_description, "services": services})


def _replace(fields: TranslationFields, old: str, new: str) -> TranslationFields:
    return TranslationFields(
        short_description=fields.short_description.replace(old, new),
        services=[value.replace(old, new) for value in fields.services],
        opening_hours_raw=[value.replace(old, new) for value in fields.opening_hours_raw],
        notes=[value.replace(old, new) for value in fields.notes],
    )


def test_mask_and_restore_protects_all_required_token_classes(tmp_path) -> None:
    short = (
        "Rücke und Scharni nennen Mobile, Kübel und Helene. "
        "Kontakt: 0341 123456, team@example.org, https://example.org/hilfe."
    )
    services = [
        "Die Nutzung kostet 0,50 Euro oder 2,00 € (heute 12:30).",
        "Treff am 03.08.2026 in der Georg-Schumann-Str. 268, 04159 Leipzig.",
        "Rücke-Rücke\nScharni.",
    ]
    offer = _offer(tmp_path, short_description=short, services=services)
    offer = offer.model_copy(
        update={
            "display_name": "Helene",
            "organization_aliases": ["Rücke", "Mobile", "Kübel"],
            "offer_aliases": ["Scharni"],
            "address": "Georg-Schumann-Str. 268, 04159 Leipzig",
            "phone_numbers": ["0341 123456"],
            "emails": ["team@example.org"],
            "website": "https://example.org/hilfe",
        }
    )

    masked = mask_translation_fields(offer)
    serialized = "\n".join([masked.fields.short_description, *masked.fields.services])
    for token in (
        "0,50 Euro",
        "2,00 €",
        "0341 123456",
        "12:30",
        "03.08.2026",
        "team@example.org",
        "https://example.org/hilfe",
        "Rücke",
        "Scharni",
        "Mobile",
        "Kübel",
        "Helene",
        "Georg-Schumann-Str. 268, 04159 Leipzig",
    ):
        assert token not in serialized
    assert len({item.placeholder for item in masked.occurrences}) == len(masked.occurrences)
    assert all("23" not in item.placeholder for item in masked.occurrences)

    restored = restore_translation_fields(masked, masked.fields)
    assert restored == TranslationFields(
        short_description=short,
        services=services,
        opening_hours_raw=offer.opening_hours_raw,
        notes=offer.notes,
    )


def test_same_token_gets_one_placeholder_per_occurrence(tmp_path) -> None:
    offer = _offer(
        tmp_path,
        short_description="Rücke am Anfang, Rücke am Ende Rücke",
        services=["(Rücke), Rücke-Rücke."],
    ).model_copy(update={"display_name": "Rücke", "offer_aliases": ["Rücke"]})
    masked = mask_translation_fields(offer)
    ruecke = [item for item in masked.occurrences if item.token == "Rücke"]
    assert len(ruecke) == 6
    assert len({item.placeholder for item in ruecke}) == 6
    assert restore_translation_fields(masked, masked.fields).short_description == offer.short_description
    assert restore_translation_fields(masked, masked.fields).services == offer.services


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        (lambda fields, token: _replace(fields, token, ""), "translation_placeholder_missing"),
        (
            lambda fields, token: _replace(fields, token, "__LENA_PX000__"),
            "translation_placeholder_modified",
        ),
        (
            lambda fields, token: _replace(fields, token, token + token),
            "translation_placeholder_duplicate",
        ),
        (
            lambda fields, token: TranslationFields(
                short_description=fields.short_description + " __LENA_P9999__",
                services=fields.services,
                opening_hours_raw=fields.opening_hours_raw,
                notes=fields.notes,
            ),
            "translation_placeholder_unknown",
        ),
    ],
)
def test_restore_rejects_invalid_placeholder_inventory(tmp_path, mutation, error_code) -> None:
    offer = _offer(tmp_path, short_description="Preis 0,50 Euro.", services=["Kontakt Rücke."]).model_copy(
        update={"display_name": "Rücke"}
    )
    masked = mask_translation_fields(offer)
    changed = mutation(masked.fields, masked.occurrences[0].placeholder)
    with pytest.raises(TranslationPlaceholderError, match=error_code):
        restore_translation_fields(masked, changed)


def test_restore_rejects_placeholder_moved_between_service_fields(tmp_path) -> None:
    offer = _offer(tmp_path, short_description="Ohne Token", services=["Preis 0,50 Euro", "Zeit 12:30"])
    masked = mask_translation_fields(offer)
    first = masked.occurrences[0].placeholder
    second = masked.occurrences[1].placeholder
    moved = TranslationFields(
        short_description=masked.fields.short_description,
        services=[
            masked.fields.services[0].replace(first, second),
            masked.fields.services[1].replace(second, first),
        ],
        opening_hours_raw=masked.fields.opening_hours_raw,
        notes=masked.fields.notes,
    )
    with pytest.raises(TranslationPlaceholderError, match="translation_placeholder_modified"):
        restore_translation_fields(masked, moved)


def test_restore_rejects_changed_service_length(tmp_path) -> None:
    offer = _offer(tmp_path, short_description="Preis 0,50 Euro", services=["Rücke", "12:30"])
    masked = mask_translation_fields(offer)
    shortened = TranslationFields(short_description=masked.fields.short_description, services=masked.fields.services[:1])
    with pytest.raises(TranslationPlaceholderError, match="translation_token_restore_failed"):
        restore_translation_fields(masked, shortened)


def test_mask_rejects_reserved_placeholder_collision_in_source(tmp_path) -> None:
    offer = _offer(tmp_path, short_description="Text __LENA_Q0000__", services=[])
    with pytest.raises(TranslationPlaceholderError, match="translation_token_restore_failed"):
        mask_translation_fields(offer)


@pytest.mark.parametrize("language", ["en", "pl", "ro", "ru"])
def test_masking_contract_is_target_language_independent(tmp_path, language) -> None:
    offer = _offer(tmp_path, short_description="Rücke kostet 0,50 Euro", services=["Telefon 0341 123456"])
    masked = mask_translation_fields(offer)
    assert language
    assert restore_translation_fields(masked, masked.fields) == TranslationFields(
        short_description=offer.short_description,
        services=offer.services,
        opening_hours_raw=offer.opening_hours_raw,
        notes=offer.notes,
    )
