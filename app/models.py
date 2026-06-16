from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator


class Language(StrEnum):
    DE = "de"
    EN = "en"
    PL = "pl"
    RO = "ro"
    RU = "ru"


class PageMetadata(BaseModel):
    entity_id: str | None = None
    page_id: str
    entity_kind: str = "service_location"
    status: Literal["active", "temporarily_changed", "deprecated", "removed", "merged", "stale"] = "active"
    parent_entity_id: str | None = None
    organization: str | None = None
    title: str
    canonical_title: str | None = None
    category: str = "general"
    service_type: str = "general"
    language: str
    source_url: str
    source_urls: list[str] = Field(default_factory=list)
    source_document_refs: list[str] = Field(default_factory=list)
    last_updated: str
    last_verified: str | None = None
    publisher: str | None = None
    address: str | None = None
    normalized_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geo_status: Literal["ready", "approximate", "missing_address", "failed", "filtered_out"] | None = None
    geo_source: Literal["manual", "build_geocoder", "source_embedded"] | None = None
    geo_confidence: float | None = None
    geo_precision: Literal["exact", "approximate"] | None = None
    district: str | None = None
    opening_hours: list[str] = Field(default_factory=list)
    opening_hours_normalized: list[dict[str, Any]] = Field(default_factory=list)
    description: str = ""
    target_groups: list[str] = Field(default_factory=list)
    eligibility: str | None = None
    gender_access: str | None = None
    walk_in: bool | None = None
    requires_registration: bool | None = None
    appointment_required: bool | None = None
    languages: list[str] = Field(default_factory=list)
    phone: str | None = None
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    confidence: float | None = None
    source_trust_tier: int | None = None
    conflict_fields: list[str] = Field(default_factory=list)
    stale: bool = False
    superseded_by: str | None = None
    merged_into: str | None = None
    entity_signature: str | None = None
    review_status: Literal["published", "needs_review"] = "published"
    validation_issues: list[str] = Field(default_factory=list)
    source_snapshot_path: str | None = None
    source_content_hash: str | None = None
    source_last_seen: str | None = None
    source_updated_at: str | None = None
    summary: str
    file_path: str

    @model_validator(mode="after")
    def _apply_defaults(self) -> PageMetadata:
        if self.entity_id is None:
            self.entity_id = self.page_id
        if self.canonical_title is None:
            self.canonical_title = self.title
        if self.organization is None:
            self.organization = self.publisher
        if not self.source_urls:
            self.source_urls = [self.source_url]
        if self.last_verified is None:
            self.last_verified = self.source_last_seen or self.last_updated
        if self.appointment_required is None:
            self.appointment_required = self.requires_registration
        if self.stale and self.status == "active":
            self.status = "stale"
        if self.normalized_address is None and self.address:
            normalized = str(self.address).casefold().strip()
            self.normalized_address = " ".join(normalized.split()) or None
        return self


class Manifest(BaseModel):
    kb_version: str
    generated_at: datetime
    source_count: int
    page_count: int
    document_count: int = 0
    entity_count: int = 0
    canonical_db: str | None = None
    index_artifacts: list[str] = Field(default_factory=list)


class TranscribeResponse(BaseModel):
    transcript: str
    provider: str
    status: Literal["ok", "error"]
    detail: str | None = None


class QueryRequest(BaseModel):
    transcript: str
    language: Language
    session_id: str | None = None


class SymbolSubstep(BaseModel):
    id: str
    label: str
    icon: str


class SymbolCategory(BaseModel):
    id: str
    label: str
    icon: str
    priority: int
    group: Literal["primary", "secondary"] = "primary"
    result_mode: Literal["cards-map", "cards", "static"] = "cards-map"
    substeps: list[SymbolSubstep] = Field(default_factory=list)


class SymbolConfigResponse(BaseModel):
    language: Language
    categories: list[SymbolCategory]


class SymbolActionRequest(BaseModel):
    category_id: str
    language: Language
    substep_id: str | None = None
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


class TemporalContext(BaseModel):
    now_iso: str
    date_iso: str
    weekday_index: int
    weekday_en: str
    weekday_de: str
    is_weekend: bool
    month: int
    season: Literal["winter", "spring", "summer", "autumn"]
    season_hints: list[str] = Field(default_factory=list)


AnswerStatus = Literal["ok", "weak_match", "unknown", "clarification_needed", "self_description", "out_of_scope", "crisis"]


class MapOrigin(BaseModel):
    id: str
    label: str
    address: str
    latitude: float
    longitude: float


class MapDestination(BaseModel):
    id: str
    page_id: str
    label: str
    organization_label: str | None = None
    service_type: str
    address: str
    latitude: float
    longitude: float
    distance_meters: int | None = None
    description: str | None = None
    opening_hours: list[str] = Field(default_factory=list)


class MapData(BaseModel):
    origin: MapOrigin
    destinations: list[MapDestination] = Field(default_factory=list)
    selected_destination_id: str | None = None


class QueryAnswerResponse(BaseModel):
    answer_text: str
    status: AnswerStatus
    weak_match: bool = False
    clarification_needed: bool = False
    clarification_question: str | None = None
    out_of_scope: bool = False
    self_description: bool = False
    crisis_mode: bool = False
    retrieved_page_ids: list[str] = Field(default_factory=list)
    map_data: MapData | None = None
    provider: str
    model: str | None = None
    session_id: str
    session_status: SessionStatus = SessionStatus.ACTIVE
    session_event: SessionEvent = SessionEvent.STARTED
    session_message: str | None = None
    temporal_context: TemporalContext | None = None
    sources: list[str] = Field(default_factory=list)
    last_checked: str | None = None
    answer_evidence: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    cards: list["SymbolResultCard"] = Field(default_factory=list)
    follow_up_options: list[dict[str, str]] = Field(default_factory=list)


class SymbolResultCard(BaseModel):
    page_id: str
    title: str
    category: str
    service_type: str
    address: str | None = None
    location: str | None = None
    opening_hours: list[str] = Field(default_factory=list)
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    description: str | None = None
    card_summary: str | None = None
    action: str
    target_groups: list[str] = Field(default_factory=list)
    requirements: str | None = None
    services_provided: list[str] = Field(default_factory=list)
    notes: str | None = None
    last_updated: str | None = None
    has_map_location: bool = False


class SymbolActionResponse(BaseModel):
    answer_text: str
    status: AnswerStatus
    category_id: str
    substep_id: str | None = None
    cards: list[SymbolResultCard] = Field(default_factory=list)
    retrieved_page_ids: list[str] = Field(default_factory=list)
    map_data: MapData | None = None
    static_response: bool = False
    no_map_reason: str | None = None
    provider: Literal["symbol"] = "symbol"
    model: None = None
    session_id: str
    session_status: SessionStatus = SessionStatus.ACTIVE
    session_event: SessionEvent = SessionEvent.STARTED
    session_message: str | None = None
    temporal_context: TemporalContext | None = None
    sources: list[str] = Field(default_factory=list)
    last_checked: str | None = None
    answer_evidence: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    follow_up_options: list[dict[str, str]] = Field(default_factory=list)


class KnowledgeAnswer(BaseModel):
    answer_text: str
    status: AnswerStatus
    weak_match: bool = False
    clarification_needed: bool = False
    clarification_question: str | None = None
    out_of_scope: bool = False
    self_description: bool = False
    crisis_mode: bool = False
    retrieved_page_ids: list[str] = Field(default_factory=list)
    map_data: MapData | None = None
    sources: list[str] = Field(default_factory=list)
    last_checked: str | None = None
    answer_evidence: list[dict[str, Any]] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    follow_up_options: list[dict[str, str]] = Field(default_factory=list)


class LLMKnowledgeAnswer(BaseModel):
    answer_text: str
    status: AnswerStatus
    weak_match: bool = False
    clarification_needed: bool = False
    clarification_question: str | None = None
    out_of_scope: bool = False
    self_description: bool = False
    crisis_mode: bool = False
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
    status: AnswerStatus
    weak_match: bool = False
    out_of_scope: bool = False
    self_description: bool = False
    crisis_mode: bool = False
    kb_version: str | None = None
    rewrite_provider: str | None = None
    rewrite_model: str | None = None
    stt_provider: str | None = None
    tts_provider: str | None = None
    follow_up_mode: Literal["none", "referential", "alternative", "topic_shift", "fresh_topic"] = "none"
    session_status: SessionStatus = SessionStatus.ACTIVE
    session_event: SessionEvent = SessionEvent.CONTINUED
    temporal_context: TemporalContext | None = None


class SourceDefinition(BaseModel):
    source_id: str
    title: str
    url: str = Field(validation_alias=AliasChoices("url", "seed_url"))
    language: str
    source_type: Literal["html", "pdf", "mixed", "manual"] = "html"
    trust_tier: int = 2
    allowed_domains: list[str] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    crawl_depth: int = 0
    follow_pdf_links: bool = False
    entity_expectation: str | None = None
    schedule_class: Literal["daily", "weekly", "monthly", "manual"] = "weekly"
    priority: int = 100
    manual_files: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str = "general"
    service_type: str = "general"
    publisher: str | None = None
    target_groups: list[str] = Field(default_factory=list)
    gender_access: str | None = None
    languages: list[str] = Field(default_factory=list)
    entity_mode: Literal["single", "location_list", "service_catalog"] = "single"
    format: Literal["auto", "html", "pdf"] = "auto"
    fetch_frequency: Literal["daily", "weekly", "monthly", "manual"] | None = None
    owner: str | None = None
    reliability_level: Literal["official", "trusted_partner", "secondary", "manual"] | None = None
    last_checked_at: str | None = None
    last_changed_at: str | None = None
    current_hash: str | None = None
    source_status: Literal["active", "failed", "stale", "retired", "needs_review"] = "active"
    notes: str | None = None


class PublishedDataset(BaseModel):
    manifest: Manifest
    pages: list[PageMetadata]
    aliases: dict[str, list[str]]
    field_indexes: dict[str, dict[str, list[str]]] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    session_id: str
    resolved_transcript: str
    history_summary: str | None = None
    preferred_page_ids: list[str] = Field(default_factory=list)
    excluded_page_ids: list[str] = Field(default_factory=list)
    follow_up_mode: Literal["none", "referential", "alternative", "topic_shift", "fresh_topic"] = "none"
    last_intent: str | None = None
    last_topic: str | None = None
    last_place_page_id: str | None = None
    clarification_state: str | None = None


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
    last_intent: str | None = None
    last_topic: str | None = None
    last_place_page_id: str | None = None
    last_service_category: str | None = None
    last_retrieved_page_ids: list[str] = Field(default_factory=list)
    last_answer_summary: str | None = None
    clarification_state: str | None = None
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
