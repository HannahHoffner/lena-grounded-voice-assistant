from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from ..models import Language


V2Category = Literal[
    "food",
    "sleep",
    "medical",
    "general_advice",
    "addiction",
    "hygiene",
    "emergency_system",
    "other_source_listed",
]
ReviewStatus = Literal["draft", "needs_review", "reviewed", "published"]
Urgency = Literal["now", "today", "tonight", "soon", "general", "unknown"]


class V2Coordinates(BaseModel):
    latitude: float
    longitude: float


class V2MapPoint(BaseModel):
    point_id: str
    label: str
    address: str
    latitude: float
    longitude: float
    opening_hours: list[str] = Field(default_factory=list)
    note: str | None = None


class V2Evidence(BaseModel):
    field_name: str
    source_url: str
    evidence_text: str = Field(min_length=1)
    checked_at: str
    source_hash: str | None = None


class V2Offer(BaseModel):
    offer_id: str
    name: str
    organization: str
    category: V2Category
    subcategory: str | None = None
    short_description: str
    card_summary: str | None = None
    retrieval_keywords: list[str] = Field(default_factory=list)
    facts: dict[str, str | list[str] | None] = Field(default_factory=dict)
    source_url: str
    source_title: str
    source_evidence: list[V2Evidence] = Field(default_factory=list)
    last_checked: str
    address: str | None = None
    location: str | None = None
    coordinates: V2Coordinates | None = None
    opening_times: list[str] = Field(default_factory=list)
    einsatzzeiten: list[str] = Field(default_factory=list)
    phone: str | None = None
    phone_reachable_when: str | None = None
    email: str | None = None
    fax: str | None = None
    contact_people: list[str] = Field(default_factory=list)
    website: str | None = None
    target_group: list[str] = Field(default_factory=list)
    requirements: str | None = None
    restrictions: str | None = None
    cost: str | None = None
    services_provided: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    notes: str | None = None
    review_status: ReviewStatus = "draft"
    reviewer: str | None = None
    reviewed_at: str | None = None
    source_hash: str | None = None
    snapshot_path: str | None = None
    detail_source_urls: list[str] = Field(default_factory=list)
    map_points: list[V2MapPoint] = Field(default_factory=list)
    field_evidence: dict[str, list[V2Evidence]] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reviewed_offers_need_evidence(self) -> "V2Offer":
        if self.review_status in {"reviewed", "published"}:
            required = {"name", "category", "short_description", "source_url"}
            evidence_fields = {item.field_name for item in self.source_evidence}
            field_evidence_fields = set(self.field_evidence)
            missing = sorted(required - evidence_fields - field_evidence_fields)
            if missing:
                raise ValueError(f"reviewed v2 offer lacks evidence for: {', '.join(missing)}")
            if not self.reviewer or not self.reviewed_at:
                raise ValueError("reviewed v2 offer needs reviewer and reviewed_at")
        return self

    @property
    def all_times(self) -> list[str]:
        return [*self.opening_times, *self.einsatzzeiten]

    @property
    def is_user_offer(self) -> bool:
        return self.category != "emergency_system"


class V2Dataset(BaseModel):
    version: str
    generated_at: datetime
    source_policy: str
    authoritative_source_url: str
    source_hash: str | None = None
    offers: list[V2Offer]


class V2Intent(BaseModel):
    selected_language: Language
    user_input: str
    primary_need: V2Category | Literal["unknown"] = "unknown"
    secondary_needs: list[V2Category] = Field(default_factory=list)
    urgency: Urgency = "unknown"
    time_reference: str | None = None
    follow_up_context: str | None = None
    clarification_needed: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
