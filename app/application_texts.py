"""Lädt die gemeinsame, versionierte Textquelle für Backend und Frontend."""

from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from .models import Language
from .policy_facts import EMERGENCY_NUMBER
from .resources import packaged_bootstrap_data_root
from .translation_contract import LinguisticReviewStatus, ReviewRole


APPLICATION_TEXT_SCHEMA_VERSION = "2"
APPLICATION_COPY_VERSION = "8"
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
SAFETY_TEXT_RESOURCE_IDS = {
    "safety.detected",
    "safety.uncertain",
    "safety.technical",
    "safety.technical_hilfebus",
}


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LanguageTextInventory(ResourceModel):
    source_language: Literal["de"]
    target_language: Language
    version: Literal[APPLICATION_COPY_VERSION]
    linguistic_review_status: LinguisticReviewStatus
    source_origin: Literal["author_formulated", "machine_drafted"]
    reviewed_by_role: ReviewRole | None = None
    reviewed_at: datetime | None = None
    texts: dict[str, str]

    @model_validator(mode="after")
    def validate_review_metadata(self) -> "LanguageTextInventory":
        reviewed = self.linguistic_review_status == LinguisticReviewStatus.REVIEWED
        if reviewed and not (self.reviewed_by_role and self.reviewed_at):
            raise ValueError("reviewed application copy requires role and timestamp")
        if not reviewed and (self.reviewed_by_role is not None or self.reviewed_at is not None):
            raise ValueError("unreviewed application copy must not carry review approval metadata")
        if any(not value.strip() or len(value) > 1_200 for value in self.texts.values()):
            raise ValueError("application text is empty or too long")
        return self


class ApplicationTextResource(ResourceModel):
    schema_version: Literal[APPLICATION_TEXT_SCHEMA_VERSION]
    copy_version: Literal[APPLICATION_COPY_VERSION]
    languages: dict[Language, LanguageTextInventory]

    @model_validator(mode="after")
    def validate_inventory(self) -> "ApplicationTextResource":
        if set(self.languages) != set(Language):
            raise ValueError("application text resource must contain every supported language")
        inventories = list(self.languages.values())
        expected_ids = set(inventories[0].texts)
        if any(set(item.texts) != expected_ids for item in inventories):
            raise ValueError("application text ids differ between languages")
        source = self.languages[Language.DE].texts
        for language, item in self.languages.items():
            if item.target_language != language:
                raise ValueError("application text language key mismatch")
            for resource_id, text in item.texts.items():
                if PLACEHOLDER_RE.findall(text) != PLACEHOLDER_RE.findall(source[resource_id]):
                    raise ValueError(f"placeholder mismatch for {resource_id}:{language.value}")
            for resource_id in SAFETY_TEXT_RESOURCE_IDS:
                if item.texts.get(resource_id, "").count("{emergency_number}") != 1:
                    raise ValueError(f"safety text must contain one emergency-number token: {language.value}")
        return self


@lru_cache(maxsize=1)
def load_application_texts() -> ApplicationTextResource:
    path = packaged_bootstrap_data_root() / "i18n" / "application_texts.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ApplicationTextResource.model_validate(payload)
    except OSError as exc:
        raise RuntimeError("application_text_resource_missing") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError("application_text_resource_invalid") from exc


def application_text(language: Language, resource_id: str, **values: str) -> str:
    try:
        template = load_application_texts().languages[language].texts[resource_id]
    except KeyError as exc:
        raise RuntimeError("application_text_missing") from exc
    safe_values = {"emergency_number": EMERGENCY_NUMBER, **values}
    expected = set(PLACEHOLDER_RE.findall(template))
    if expected != set(safe_values) & expected:
        raise RuntimeError("application_text_values_missing")
    return template.format(**safe_values)


def public_application_copy(language: Language) -> dict[str, object]:
    """Liefert UI-Texte und Dialoglabels ohne interne Review- oder Fachwerte."""
    inventory = load_application_texts().languages[language]
    ui = {key.removeprefix("ui."): value for key, value in inventory.texts.items() if key.startswith("ui.")}
    return {"copy_version": APPLICATION_COPY_VERSION, "language": language.value, "texts": ui}


def application_text_summary() -> dict[str, object]:
    resource = load_application_texts()
    languages: dict[str, dict[str, int]] = {}
    areas: dict[str, dict[str, dict[str, int]]] = {
        area: {} for area in ("ui", "dialogue", "fallback", "safety")
    }
    for language, inventory in resource.languages.items():
        counts = {status.value: 0 for status in LinguisticReviewStatus}
        counts.update({"missing": 0})
        counts[inventory.linguistic_review_status.value] = len(inventory.texts)
        languages[language.value] = counts
        for area in areas:
            area_counts = {status.value: 0 for status in LinguisticReviewStatus}
            area_counts.update({"missing": 0})
            area_counts[inventory.linguistic_review_status.value] = sum(
                resource_id.startswith(f"{area}.") for resource_id in inventory.texts
            )
            areas[area][language.value] = area_counts
    return {
        "copy_version": resource.copy_version,
        "languages": languages,
        "areas": areas,
        "resource_count_per_language": len(resource.languages[Language.DE].texts),
    }
