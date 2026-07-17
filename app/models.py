"""Pydantic-Vertragsmodelle für Wissensbasis, API, Karten und LLM-Antworten."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator


MAX_QUERY_CHARS = 10_000
MAX_TTS_CHARS = 20_000


class Language(str, Enum):
    DE = "de"
    EN = "en"
    PL = "pl"
    RO = "ro"
    RU = "ru"


class Category(str, Enum):
    FOOD = "food"
    SLEEP = "sleep"
    MEDICAL = "medical"
    ADVICE = "advice"


class OfferRecord(BaseModel):
    """Normalisierter, fachlicher Datensatz eines WFS-Hilfsangebots."""
    id: str
    source_index: int
    source_title: str
    name: str
    source_category: str
    short_description: str
    district: str | None = None
    address: str | None = None
    header_address: str | None = None
    services: list[str] = Field(default_factory=list)
    opening_hours_raw: list[str] = Field(default_factory=list)
    standzeiten_raw: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    website: str | None = None
    notes: list[str] = Field(default_factory=list)
    raw_fields: dict[str, list[str]] = Field(default_factory=dict)
    raw_text: str
    geometry: dict[str, object] | None = None
    source_feature_id: str | None = None
    source_updated_at: str | None = None
    source_hash: str | None = None
    raw_properties: dict[str, object] = Field(default_factory=dict)


class OfferCard(BaseModel):
    id: str
    name: str
    short_description: str
    services: list[str] = Field(default_factory=list)
    address: str | None = None
    phone_numbers: list[str] = Field(default_factory=list)
    opening_hours_raw: list[str] = Field(default_factory=list)
    standzeiten_raw: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ChatTurn(BaseModel):
    question: str
    answer: str


class MapOrigin(BaseModel):
    id: str
    label: str
    address: str
    latitude: float
    longitude: float


class MapDestination(BaseModel):
    id: str
    label: str
    address: str
    latitude: float
    longitude: float
    distance_meters: int | None = None
    description: str | None = None
    phone_numbers: list[str] = Field(default_factory=list)
    opening_hours: list[str] = Field(default_factory=list)


class MapData(BaseModel):
    origin: MapOrigin
    destinations: list[MapDestination] = Field(default_factory=list)
    selected_destination_id: str | None = None


class QueryRequest(BaseModel):
    """Validierte Anfrage des Frontends an den zentralen Query-Endpunkt."""
    query: str = Field(default="", max_length=MAX_QUERY_CHARS)
    language: Language = Language.DE
    category: Category | None = None
    session_id: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def clean_query(self) -> "QueryRequest":
        self.query = " ".join(self.query.split())
        return self


class SpeechSynthesisRequest(BaseModel):
    """Validierter Text- und Sprachvertrag für die Sprachsynthese."""

    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)
    language: Language = Language.DE

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class QueryResponse(BaseModel):
    """Öffentliche Antwort mit Text, Karten, Session- und Kartendaten."""
    answer: str
    cards: list[OfferCard] = Field(default_factory=list)
    language: Language
    provider: Literal["template", "blablador"]
    status: Literal["ok", "no_results", "error"]
    session_id: str | None = None
    question: str = ""
    history: list[ChatTurn] = Field(default_factory=list)
    map_data: MapData | None = None


class LLMAnswer(BaseModel):
    answer: str
    card_ids: list[str] = Field(default_factory=list, max_length=4)


class LLMRoute(BaseModel):
    """Strikt validiertes Ergebnis der ersten, nur routenden LLM-Stufe."""
    intent: Literal["food", "sleep", "medical", "advice", "unknown"]
    offer_ids: list[str] = Field(default_factory=list, max_length=6)
    needs_clarification: bool = False
    out_of_scope: bool = False
    acute_risk_detected: StrictBool
