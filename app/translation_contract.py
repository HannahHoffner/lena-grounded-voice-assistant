"""Strikte Verträge für gespeicherte Übersetzungen und Sprachreviews."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Language


TRANSLATION_STORE_VERSION = "3"
TRANSLATION_PROMPT_VERSION = "4"
TRANSLATION_REVIEW_PACKAGE_VERSION = "1"
TRANSLATABLE_FIELDS = ("short_description", "services", "opening_hours_raw", "notes")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinguisticReviewStatus(str, Enum):
    MACHINE = "machine"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
    REJECTED = "rejected"
    STALE = "stale"


class FactualIntegrityStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"


class TranslationRuntimePolicy(str, Enum):
    REVIEWED_ONLY = "reviewed_only"
    REVIEWED_OR_MACHINE = "reviewed_or_machine"
    SOURCE_LANGUAGE_FALLBACK = "source_language_fallback"


class ReviewRole(str, Enum):
    AUTHOR = "author_review"
    NATIVE_SPEAKER = "native_speaker_review"
    PROFESSIONAL_TRANSLATION = "professional_translation_review"
    DOMAIN_EXPERT = "domain_expert_review"


class TranslationFields(StrictModel):
    short_description: str = Field(min_length=1, max_length=2_000)
    services: list[str] = Field(default_factory=list, max_length=50)
    opening_hours_raw: list[str] = Field(default_factory=list, max_length=20)
    notes: list[str] = Field(default_factory=list, max_length=30)


class TranslationRecord(StrictModel):
    target_language: Language
    fields: TranslationFields
    linguistic_review_status: LinguisticReviewStatus
    factual_integrity_status: FactualIntegrityStatus
    source_version: str = Field(min_length=1, max_length=160)
    source_translation_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    operational_facts_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    curation_catalog_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    curation_version: str = Field(min_length=1, max_length=160)
    translation_prompt_version: str = Field(min_length=1, max_length=80)
    provider: str = Field(min_length=1, max_length=120)
    model_identifier: str = Field(min_length=1, max_length=160)
    created_at: datetime
    translation_version: str = Field(min_length=1, max_length=160)
    reviewed_by_role: ReviewRole | None = None
    reviewed_at: datetime | None = None
    review_scope: str | None = Field(default=None, min_length=1, max_length=500)
    review_comment: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def validate_review_evidence(self) -> "TranslationRecord":
        evidence = (self.reviewed_by_role, self.reviewed_at, self.review_scope)
        if self.linguistic_review_status in {
            LinguisticReviewStatus.REVIEWED,
            LinguisticReviewStatus.REJECTED,
        } and any(value is None for value in evidence):
            raise ValueError("reviewed and rejected translations require complete human review metadata")
        if self.linguistic_review_status not in {
            LinguisticReviewStatus.REVIEWED,
            LinguisticReviewStatus.REJECTED,
        } and any(value is not None for value in evidence):
            raise ValueError("unreviewed translations must not carry human review approval metadata")
        if self.target_language == Language.DE:
            raise ValueError("stored offer translations must not target the source language")
        return self


class OfferTranslationEntry(StrictModel):
    offer_id: str = Field(min_length=1, max_length=80)
    source_name: str = Field(min_length=1, max_length=500)
    active: bool = True
    translations: dict[Language, TranslationRecord] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_language_keys(self) -> "OfferTranslationEntry":
        if any(language != record.target_language for language, record in self.translations.items()):
            raise ValueError("translation language key does not match record")
        return self


class TranslationStore(StrictModel):
    schema_version: Literal[TRANSLATION_STORE_VERSION] = TRANSLATION_STORE_VERSION
    generated_at: datetime
    source_dataset_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    languages: list[Language]
    entries: dict[str, OfferTranslationEntry] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_inventory(self) -> "TranslationStore":
        expected = {Language.EN, Language.PL, Language.RO, Language.RU}
        if set(self.languages) != expected:
            raise ValueError("translation store language inventory is incomplete")
        if any(key != entry.offer_id for key, entry in self.entries.items()):
            raise ValueError("translation entry key does not match offer id")
        return self


class ReviewPackageItem(StrictModel):
    offer_id: str
    target_language: Language
    source_version: str
    source_translation_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    curation_catalog_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    translation_version: str
    source_short_description: str
    source_services: list[str]
    source_opening_hours_raw: list[str]
    source_notes: list[str]
    translated_short_description: str
    translated_services: list[str]
    translated_opening_hours_raw: list[str]
    translated_notes: list[str]
    visible_operational_facts: dict[str, str | list[str] | None]
    current_status: LinguisticReviewStatus
    review_decision: Literal["", "reviewed", "rejected"] = ""
    reviewer_role: ReviewRole | None = None
    reviewed_at: datetime | None = None
    review_scope: str | None = None
    review_comment: str | None = Field(default=None, max_length=1_000)


class TranslationReviewPackage(StrictModel):
    package_version: Literal[TRANSLATION_REVIEW_PACKAGE_VERSION] = TRANSLATION_REVIEW_PACKAGE_VERSION
    exported_at: datetime
    items: list[ReviewPackageItem]
