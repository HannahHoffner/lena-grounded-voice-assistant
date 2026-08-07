"""Lokale, append-basierte Protokollierung vollständiger Interaktionen."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .models import Language
from .version import software_version


LOGGER = logging.getLogger(__name__)


class InteractionRecord(BaseModel):
    """Validierter Datensatz einer vollständig sichtbaren Nutzerinteraktion."""

    schema_version: Literal[11] = 11
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None
    language: Language
    input_mode: Literal["text", "speech"]
    user_query: str
    assistant_answer: str
    route: str
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
    selector_eligible_count: int = Field(default=0, ge=0, le=26)
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
    software_version: str = Field(default_factory=software_version)


class InteractionWriter:
    """Schreibt pro Interaktion genau eine UTF-8-JSON-Zeile.

    Die Sperre schützt parallele Threads innerhalb eines Prozesses. Schreibfehler
    werden redigiert protokolliert und bewusst nicht an den Query-Pfad
    weitergegeben.
    """

    def __init__(self, path: Path, *, enabled: bool) -> None:
        self.path = path
        self.enabled = enabled
        self._lock = threading.Lock()

    def write(self, record: InteractionRecord) -> bool:
        """Persistiert einen Datensatz und meldet Erfolg ohne Inhalte zu loggen."""
        if not self.enabled:
            return False
        line = json.dumps(record.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(line + "\n")
                    handle.flush()
        except OSError as exc:
            LOGGER.error("interaction.write.failed", extra={"error_type": type(exc).__name__})
            return False
        return True
