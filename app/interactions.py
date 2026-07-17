"""Lokale, append-basierte Protokollierung vollständiger Interaktionen."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .models import Language


LOGGER = logging.getLogger(__name__)


def software_version() -> str:
    """Liefert die installierte Paketversion ohne zusätzliche Laufzeitabfrage."""
    try:
        return version("lena-code3")
    except PackageNotFoundError:
        return "0.1.0"


class InteractionRecord(BaseModel):
    """Validierter Datensatz einer vollständig sichtbaren Nutzerinteraktion."""

    schema_version: Literal[1] = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None
    language: Language
    input_mode: Literal["text", "speech"]
    user_query: str
    assistant_answer: str
    route: str
    source_ids: list[str] = Field(default_factory=list)
    retrieval_result_count: int = Field(default=0, ge=0)
    acute_risk_detected: bool = False
    fallback_used: bool = False
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
