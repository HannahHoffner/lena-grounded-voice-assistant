"""Pydantic-Vertragsmodelle für Wissensbasis, API, Karten und LLM-Antworten."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


MAX_QUERY_CHARS = 10_000
MAX_TTS_CHARS = 20_000
ChoiceValue = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,31}$")]


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
    TOILET = "toilet"


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
    curation_hash: str | None = None
    raw_properties: dict[str, object] = Field(default_factory=dict)
    organization_id: str | None = None
    location_id: str | None = None
    offer_type: str | None = None
    display_name: str | None = None
    organization_aliases: list[str] = Field(default_factory=list)
    offer_aliases: list[str] = Field(default_factory=list)
    search_phrases: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    place_type: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    target_groups: list[str] = Field(default_factory=list)
    minimum_age: int | None = None
    maximum_age: int | None = None
    eligible_genders: list[str] = Field(default_factory=list)
    requires_explicit_drug_use: bool = False
    referral_needs: list[str] = Field(default_factory=list)
    priority_rules: list[str] = Field(default_factory=list)
    service_schedules: dict[str, str] = Field(default_factory=dict)
    access_rules: list[str] = Field(default_factory=list)
    curation_decision_ids: list[str] = Field(default_factory=list)
    source_reference_ids: list[str] = Field(default_factory=list)
    review_status: str | None = None
    coordinates_status: str | None = None


class OfferCard(BaseModel):
    record_type: Literal["social_offer"] = "social_offer"
    id: str
    name: str
    short_description: str
    services: list[str] = Field(default_factory=list)
    address: str | None = None
    phone_numbers: list[str] = Field(default_factory=list)
    opening_hours_raw: list[str] = Field(default_factory=list)
    standzeiten_raw: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    # Server-built readout of exactly this card's fields, in the response
    # language. The "listen to this offer" button sends this text back to
    # /api/speech/synthesize verbatim -- the endpoint only speaks text it
    # already vouched for (see QueryService._register_speakable_text), so the
    # client never gets to have arbitrary text synthesized.
    spoken_text: str = ""


class PublicToiletCard(BaseModel):
    """Positive, source-grounded card projection for a public toilet."""

    record_type: Literal["public_toilet"] = "public_toilet"
    id: str = Field(pattern=r"^toilet:[0-9]{4}$")
    name: str
    operator_name: str
    district: str
    opening_hours_raw: list[str] = Field(default_factory=list)
    facilities: list[str] = Field(default_factory=list)
    fee_status: Literal["free", "paid", "unknown"]
    fee_cents: int | None = None
    fee_raw: str
    service_phone: str | None = None
    distance_meters: int = Field(ge=0)
    source_attribution: Literal["Stadt Leipzig"] = "Stadt Leipzig"
    spoken_text: str = ""


class DrinkingFountainCard(BaseModel):
    """Source-grounded card projection of an approved fixed fountain."""

    record_type: Literal["drinking_fountain"] = "drinking_fountain"
    id: str = Field(pattern=r"^drinking_fountain:[a-z0-9][a-z0-9-]{0,79}$")
    name: str
    location_description: str | None = None
    address: str | None = None
    cost_status: Literal["free", "unknown"]
    potable_water_status: Literal["verified", "unknown"]
    operation_status: Literal["unknown", "inactive"]
    seasonal_status: Literal["april_to_october", "unknown"]
    season_start: Literal["april"] | None = None
    season_end: Literal["october"] | None = None
    distance_meters: int = Field(ge=0)
    source_attribution: Literal["Leipziger Wasserwerke"] = "Leipziger Wasserwerke"
    spoken_text: str = ""


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
    services: list[str] = Field(default_factory=list)
    standzeiten_raw: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    record_type: Literal["social_offer", "public_toilet", "drinking_fountain"] = "social_offer"
    # See OfferCard.spoken_text.
    spoken_text: str = ""
    fee_raw: str | None = None
    facilities: list[str] = Field(default_factory=list)
    cost_status: Literal["free", "unknown"] | None = None
    potable_water_status: Literal["verified", "unknown"] | None = None
    seasonal_status: Literal["april_to_october", "unknown"] | None = None
    source_attribution: str | None = None


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
    input_mode: Literal["text", "speech"] = "text"
    dialog_id: str | None = Field(default=None, min_length=16, max_length=64)
    choice_values: list[ChoiceValue] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def clean_query(self) -> "QueryRequest":
        self.query = " ".join(self.query.split())
        if len(self.choice_values) != len(set(self.choice_values)):
            raise ValueError("choice_values must be unique")
        if self.choice_values and (not self.dialog_id or not self.session_id):
            raise ValueError("dialog and session IDs are required for choices")
        if self.choice_values and (self.query or self.category is not None):
            raise ValueError("choices cannot be combined with query text or category")
        if self.dialog_id and not self.choice_values and not self.query:
            raise ValueError("dialog response must contain text or choices")
        return self


class SpeechSynthesisRequest(BaseModel):
    """Validierter Text- und Sprachvertrag für die Sprachsynthese."""

    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)
    language: Language = Language.DE
    session_id: str = Field(min_length=16, max_length=80)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class QueryInteraction(BaseModel):
    """Interne Laufzeitmetadaten für das lokale Interaktionsprotokoll."""

    route: str = "unknown"
    source_ids: list[str] = Field(default_factory=list)
    candidate_result_count: int = Field(default=0, ge=0)
    acute_risk_detected: bool = False
    acute_risk_status: Literal["not_assessed", "not_detected", "detected", "uncertain"] = "not_assessed"
    safety_path: str = "none"
    safety_dialogue_used: bool = False
    safety_dialogue_result: str | None = None
    safety_fallback_used: bool = False
    safety_response_language: Language | None = None
    fallback_used: bool = False
    interpreter_error_code: str | None = Field(default=None, max_length=60)
    data_release_id: str | None = None
    candidate_selection_status: str | None = None
    dialog_type: str | None = None
    dialog_attempt_count: int | None = Field(default=None, ge=0, le=2)
    dialog_result_status: str | None = None
    selector_used: bool = False
    selection_source: str | None = None
    selector_bypass_reason: str | None = None
    selector_eligible_count: int = Field(default=0, ge=0, le=64)
    selector_final_count: int = Field(default=0, ge=0, le=4)
    selector_fallback_used: bool = False
    selector_error_code: str | None = None
    answer_type: str | None = None
    formulator_used: bool = False
    formulator_fallback_used: bool = False
    formulator_error_code: str | None = None
    formulator_sentence_count: int = Field(default=0, ge=0, le=3)
    formulator_offer_count: int = Field(default=0, ge=0, le=4)
    formulator_language: Language | None = None
    llm_budget_status: str = "within_budget"
    infrastructure_source: str | None = None
    infrastructure_result_count: int = Field(default=0, ge=0, le=500)
    infrastructure_spoken_count: int = Field(default=0, ge=0, le=3)
    infrastructure_card_count: int = Field(default=0, ge=0, le=3)
    infrastructure_marker_count: int = Field(default=0, ge=0, le=500)
    infrastructure_distance_ranking_used: bool = False
    infrastructure_district_ranking_used: bool = False
    infrastructure_error_code: str | None = None
    infrastructure_distance_class: str | None = None


class ClarificationChoice(BaseModel):
    """Lokalisierte Darstellung eines stabilen technischen Dialogwerts."""

    model_config = ConfigDict(extra="forbid")
    value: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(min_length=1, max_length=120)


class ClarificationBlock(BaseModel):
    """Oeffentlicher, angebotsfreier Vertrag einer offenen Rueckfrage."""

    model_config = ConfigDict(extra="forbid")
    dialog_id: str = Field(min_length=16, max_length=64)
    type: str = Field(min_length=1, max_length=40)
    prompt: str = Field(min_length=1, max_length=300)
    allow_free_text: bool
    allow_speech: bool
    multiple_facts_allowed: bool
    submit_label: str = Field(min_length=1, max_length=80)
    choices: list[ClarificationChoice] = Field(default_factory=list, max_length=6)
    # Prompt und Auswahlmoeglichkeiten als ein zusammenhaengender, vorlesbarer
    # Text (live gemeldet: die Kaesten selbst wurden nie vorgelesen, nur der
    # Prompt). Muss serverseitig in `speakable_texts` derselben Runde stehen,
    # siehe QueryService.query() -- sonst lehnt /api/speech/synthesize ihn ab.
    spoken_text: str = Field(min_length=1, max_length=1200)


class QueryResponse(BaseModel):
    """Öffentliche Antwort mit Text, Karten, Session- und Kartendaten."""
    answer: str
    cards: list[OfferCard | PublicToiletCard | DrinkingFountainCard] = Field(default_factory=list)
    language: Language
    provider: Literal["template", "blablador"]
    status: Literal["ok", "no_results", "error"]
    answer_type: str = "grounded_result"
    session_id: str | None = None
    question: str = ""
    history: list[ChatTurn] = Field(default_factory=list)
    map_data: MapData | None = None
    clarification: ClarificationBlock | None = None
    spoken_result_ids: list[str] = Field(default_factory=list, max_length=4)
    card_ids: list[str] = Field(default_factory=list, max_length=4)
    map_marker_ids: list[str] = Field(default_factory=list, max_length=500)
    interaction: QueryInteraction = Field(default_factory=QueryInteraction, exclude=True)
