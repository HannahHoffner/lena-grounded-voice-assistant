from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Language(StrEnum):
    DE = "de"
    EN = "en"
    PL = "pl"
    RO = "ro"
    RU = "ru"


class PageMetadata(BaseModel):
    page_id: str
    title: str
    category: str = "general"
    service_type: str = "general"
    language: str
    source_url: str
    last_updated: str
    publisher: str | None = None
    address: str | None = None
    opening_hours: list[str] = Field(default_factory=list)
    description: str = ""
    target_groups: list[str] = Field(default_factory=list)
    gender_access: str | None = None
    walk_in: bool | None = None
    requires_registration: bool | None = None
    languages: list[str] = Field(default_factory=list)
    phone: str | None = None
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    review_status: Literal["published", "needs_review"] = "published"
    validation_issues: list[str] = Field(default_factory=list)
    source_snapshot_path: str | None = None
    source_content_hash: str | None = None
    source_last_seen: str | None = None
    source_updated_at: str | None = None
    summary: str
    file_path: str


class Manifest(BaseModel):
    kb_version: str
    generated_at: datetime
    source_count: int
    page_count: int


class TranscribeResponse(BaseModel):
    transcript: str
    provider: str
    status: Literal["ok", "error"]
    detail: str | None = None


class QueryRequest(BaseModel):
    transcript: str
    language: Language
    session_id: str | None = None


class SessionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ENDED = "ended"
    RESET = "reset"


class SessionEvent(StrEnum):
    STARTED = "started"
    CONTINUED = "continued"
    EXPIRED_RESET = "expired_reset"
    ENDED_RESET = "ended_reset"
    CONTEXT_RESET = "context_reset"
    LANGUAGE_RESET = "language_reset"


class RetrievedPage(BaseModel):
    page_id: str
    title: str
    score: float


class QueryAnswerResponse(BaseModel):
    answer_text: str
    status: Literal["ok", "weak_match", "unknown", "clarification_needed"]
    weak_match: bool = False
    clarification_needed: bool = False
    clarification_question: str | None = None
    retrieved_page_ids: list[str] = Field(default_factory=list)
    provider: str
    model: str | None = None
    session_id: str
    session_status: SessionStatus = SessionStatus.ACTIVE
    session_event: SessionEvent = SessionEvent.STARTED
    session_message: str | None = None


class KnowledgeAnswer(BaseModel):
    answer_text: str
    status: Literal["ok", "weak_match", "unknown", "clarification_needed"]
    weak_match: bool = False
    clarification_needed: bool = False
    clarification_question: str | None = None
    retrieved_page_ids: list[str] = Field(default_factory=list)


class SynthesizeRequest(BaseModel):
    text: str
    language: Language


class SynthesizeResponse(BaseModel):
    status: Literal["ok", "unavailable", "error"]
    provider: str
    audio_url: str | None = None
    detail: str | None = None


class TranscriptEvent(BaseModel):
    timestamp: datetime
    session_id: str
    language: Language
    transcript: str
    resolved_transcript: str | None = None
    retrieved_page_ids: list[str] = Field(default_factory=list)
    answer_text: str
    status: str
    weak_match: bool = False
    kb_version: str | None = None
    rewrite_provider: str | None = None
    rewrite_model: str | None = None
    stt_provider: str | None = None
    tts_provider: str | None = None
    follow_up_mode: Literal["none", "referential", "alternative", "topic_shift", "fresh_topic"] = "none"
    session_status: SessionStatus = SessionStatus.ACTIVE
    session_event: SessionEvent = SessionEvent.CONTINUED


class SourceDefinition(BaseModel):
    source_id: str
    title: str
    url: str
    language: str
    tags: list[str] = Field(default_factory=list)
    category: str = "general"
    service_type: str = "general"
    publisher: str | None = None
    target_groups: list[str] = Field(default_factory=list)
    gender_access: str | None = None
    languages: list[str] = Field(default_factory=list)
    entity_mode: Literal["single", "location_list", "service_catalog"] = "single"
    format: Literal["auto", "html", "pdf"] = "auto"


class PublishedDataset(BaseModel):
    manifest: Manifest
    pages: list[PageMetadata]
    aliases: dict[str, list[str]]


class ConversationContext(BaseModel):
    session_id: str
    resolved_transcript: str
    history_summary: str | None = None
    preferred_page_ids: list[str] = Field(default_factory=list)
    excluded_page_ids: list[str] = Field(default_factory=list)
    follow_up_mode: Literal["none", "referential", "alternative", "topic_shift", "fresh_topic"] = "none"


class SessionTurn(BaseModel):
    timestamp: datetime
    language: Language
    transcript: str
    resolved_transcript: str | None = None
    answer_text: str
    answer_status: str
    retrieved_page_ids: list[str] = Field(default_factory=list)
    primary_page_ids: list[str] = Field(default_factory=list)
    topic_categories: list[str] = Field(default_factory=list)
    topic_service_types: list[str] = Field(default_factory=list)
    follow_up_mode: Literal["none", "referential", "alternative", "topic_shift", "fresh_topic"] = "none"


class ConversationSession(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime
    last_activity_at: datetime
    selected_language: Language
    recent_turns: list[SessionTurn] = Field(default_factory=list)
    ended_reason: str | None = None
    last_session_event: SessionEvent = SessionEvent.STARTED
    last_session_message: str | None = None


class SessionEndRequest(BaseModel):
    session_id: str


class SessionEndResponse(BaseModel):
    status: Literal["ok"]
    session_id: str
    session_status: SessionStatus = SessionStatus.ENDED
    session_event: SessionEvent = SessionEvent.ENDED_RESET
    session_message: str | None = None
