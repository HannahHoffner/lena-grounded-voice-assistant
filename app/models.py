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
    language: str
    source_url: str
    last_updated: str
    tags: list[str] = Field(default_factory=list)
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
    retrieved_page_ids: list[str] = Field(default_factory=list)
    answer_text: str
    status: str
    weak_match: bool = False
    kb_version: str | None = None
    rewrite_provider: str | None = None
    rewrite_model: str | None = None
    stt_provider: str | None = None
    tts_provider: str | None = None


class SourceDefinition(BaseModel):
    source_id: str
    title: str
    url: str
    language: str
    tags: list[str] = Field(default_factory=list)
    category: str = "general"
    publisher: str | None = None
    format: Literal["auto", "html", "pdf"] = "auto"


class PublishedDataset(BaseModel):
    manifest: Manifest
    pages: list[PageMetadata]
    aliases: dict[str, list[str]]
    page_chunks: list[dict]
