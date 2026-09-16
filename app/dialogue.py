"""Versionierter, begrenzter Dialogzustand und paketierte Dialogtexte."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .application_texts import (
    APPLICATION_COPY_VERSION,
    application_text,
    load_application_texts,
)
from .interpreter import AgeGroup, Gender, Need, RequestedService, ThreeWayStatus
from .models import ClarificationBlock, ClarificationChoice, Language


DIALOG_CONTRACT_VERSION = "2"
DIALOG_COPY_VERSION = APPLICATION_COPY_VERSION


class DialogueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DialogType(str, Enum):
    SLEEP_TARGET_GROUP = "sleep_target_group"
    SLEEP_AGE = "sleep_age"
    ORGANIZATION_NEED = "organization_need"
    ORGANIZATION_DISTRICT = "organization_district"
    GENERAL_NEED = "general_need"
    ACUTE_RISK_CONFIRMATION = "acute_risk_confirmation"


class DialogStatus(str, Enum):
    AWAITING_ANSWER = "awaiting_answer"
    PROCESSING = "processing"
    CLOSED = "closed"
    ABANDONED = "abandoned"


class KnownExplicitFacts(DialogueModel):
    age: int | None = Field(default=None, ge=0, le=120)
    age_group: AgeGroup = AgeGroup.UNKNOWN
    gender: Gender = Gender.UNKNOWN
    drug_use: ThreeWayStatus = ThreeWayStatus.UNKNOWN
    no_social_benefit_entitlement: ThreeWayStatus = ThreeWayStatus.UNKNOWN
    district: str | None = Field(default=None, max_length=80)


class DialogChoice(DialogueModel):
    value: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")


class DialogState(DialogueModel):
    dialog_version: Literal[DIALOG_CONTRACT_VERSION] = DIALOG_CONTRACT_VERSION
    dialog_id: str = Field(min_length=16, max_length=64)
    dialog_type: DialogType
    status: DialogStatus = DialogStatus.AWAITING_ANSWER
    originating_need: Need
    originating_services: list[RequestedService] = Field(default_factory=list, max_length=4)
    knowledge_base_fingerprint: str = Field(min_length=16, max_length=128)
    known_explicit_facts: KnownExplicitFacts = Field(default_factory=KnownExplicitFacts)
    requested_fields: list[str] = Field(default_factory=list, max_length=4)
    attempt_count: int = Field(default=0, ge=0, le=2)
    max_attempts: int = Field(ge=1, le=2)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    choices: list[DialogChoice] = Field(default_factory=list, max_length=6)
    allow_multiple_choices: bool = False
    alias: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_state(self) -> "DialogState":
        values = [choice.value for choice in self.choices]
        if len(values) != len(set(values)):
            raise ValueError("dialog choices must be unique")
        if self.expires_at <= self.created_at:
            raise ValueError("dialog expiry must follow creation")
        if self.attempt_count > self.max_attempts:
            raise ValueError("dialog attempt limit exceeded")
        return self


class DialogRequestError(RuntimeError):
    """Redigierter Fehler fuer ungueltige oder nicht mehr offene Dialoge."""

    def __init__(self, code: str = "dialog_invalid") -> None:
        super().__init__(code)
        self.code = code


def load_dialogue_resource():
    """Kompatibilitätszugriff auf die gemeinsame Anwendungsressource."""
    return load_application_texts()


def new_dialog(
    dialog_type: DialogType,
    *,
    need: Need,
    fingerprint: str,
    session_timeout_seconds: int,
    facts: KnownExplicitFacts | None = None,
    services: list[RequestedService] | None = None,
    alias: str | None = None,
    now: datetime | None = None,
    attempt_count: int = 1,
) -> DialogState:
    current = now or datetime.now(UTC)
    definitions = {
        DialogType.SLEEP_TARGET_GROUP: (
            ["age_group", "gender"],
            ["under_18", "female"],
            False,
            2,
        ),
        DialogType.SLEEP_AGE: (["age"], [], False, 2),
        DialogType.ORGANIZATION_NEED: (["need"], ["sleep", "day_support"], False, 1),
        DialogType.ORGANIZATION_DISTRICT: (["district"], [], False, 1),
        DialogType.GENERAL_NEED: (["need"], ["food", "drinking_water", "sleep", "medical", "advice", "toilet"], False, 1),
        DialogType.ACUTE_RISK_CONFIRMATION: (
            ["acute_risk_status"],
            ["immediate_danger_yes", "immediate_danger_no", "immediate_danger_unsure"],
            False,
            2,
        ),
    }
    requested, choices, multiple, maximum = definitions[dialog_type]
    return DialogState(
        dialog_id=uuid.uuid4().hex,
        dialog_type=dialog_type,
        originating_need=need,
        originating_services=list(services or []),
        knowledge_base_fingerprint=fingerprint,
        known_explicit_facts=facts or KnownExplicitFacts(),
        requested_fields=requested,
        attempt_count=attempt_count,
        max_attempts=maximum,
        created_at=current,
        updated_at=current,
        expires_at=current + timedelta(seconds=session_timeout_seconds),
        choices=[DialogChoice(value=value) for value in choices],
        allow_multiple_choices=multiple,
        alias=alias,
    )


def clarification_block(dialog: DialogState, language: Language) -> ClarificationBlock:
    prompt = application_text(language, f"dialogue.prompts.{dialog.dialog_type.value}")
    choices = [
        ClarificationChoice(
            value=choice.value,
            label=application_text(language, f"dialogue.choices.{choice.value}"),
        )
        for choice in dialog.choices
    ]
    # Ein Satz je Auswahlmoeglichkeit, nach dem Prompt -- die Kaesten sind sonst
    # rein visuell und fuer eine sprachgefuehrte Nutzung nicht erreichbar.
    spoken_text = " ".join([prompt, *(f"{choice.label}." for choice in choices)])
    return ClarificationBlock(
        dialog_id=dialog.dialog_id,
        type=dialog.dialog_type.value,
        prompt=prompt,
        allow_free_text=True,
        allow_speech=True,
        multiple_facts_allowed=dialog.allow_multiple_choices,
        submit_label=application_text(language, "dialogue.submit_label"),
        choices=choices,
        spoken_text=spoken_text,
    )


def visible_choice_text(dialog: DialogState, values: list[str], language: Language) -> str:
    return ", ".join(application_text(language, f"dialogue.choices.{value}") for value in values)


def dialogue_text(
    language: Language,
    section: Literal["prompts", "answers"],
    key: str,
    **values: str,
) -> str:
    return application_text(language, f"dialogue.{section}.{key}", **values)


def public_dialogue_copy(language: Language) -> dict[str, object]:
    """Liefert ausschliesslich UI-Texte, keine Freigabedaten oder Angebotswerte."""
    texts = load_application_texts().languages[language].texts
    return {
        "copy_version": DIALOG_COPY_VERSION,
        "prompts": {key.rsplit(".", 1)[-1]: value for key, value in texts.items() if key.startswith("dialogue.prompts.")},
        "choices": {key.rsplit(".", 1)[-1]: value for key, value in texts.items() if key.startswith("dialogue.choices.")},
        "submit_label": application_text(language, "dialogue.submit_label"),
    }
