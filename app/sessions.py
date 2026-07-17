"""Dateibasierte, zeitlich begrenzte Gesprächssitzungen für Folgefragen."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field

from .models import ChatTurn, Language


LOGGER = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConversationSession(BaseModel):
    """Kompakter Gesprächszustand ohne vollständige Provider-Prompthistorie."""
    session_id: str
    language: Language
    created_at: datetime
    last_activity_at: datetime
    turns: list[ChatTurn] = Field(default_factory=list)
    pending_clarification: bool = False


@dataclass(slots=True)
class SessionStore:
    """Persistiert eine begrenzte Zahl von Turns in einer lokalen JSON-Datei.

    Die Implementierung ist für den lokalen Einzelprozessbetrieb gedacht und
    bietet keine Sperren für konkurrierende Schreibzugriffe mehrerer Prozesse.
    """
    path: Path
    timeout_seconds: int = 180
    max_turns: int = 8

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def resolve(self, session_id: str | None, language: Language) -> ConversationSession:
        """Liefert eine gültige Session oder beginnt bei Ablauf/Sprachwechsel neu."""
        existing = self.get(session_id) if session_id else None
        now = utc_now()
        if (
            not existing
            or existing.language != language
            or now - existing.last_activity_at > timedelta(seconds=self.timeout_seconds)
        ):
            return self.create(language)
        return existing

    def create(self, language: Language) -> ConversationSession:
        now = utc_now()
        session = ConversationSession(
            session_id=uuid.uuid4().hex,
            language=language,
            created_at=now,
            last_activity_at=now,
        )
        return self.save(session)

    def get(self, session_id: str | None) -> ConversationSession | None:
        if not session_id:
            return None
        return self._load_all().get(session_id)

    def save(self, session: ConversationSession) -> ConversationSession:
        session.last_activity_at = utc_now()
        session.turns = session.turns[-self.max_turns :]
        sessions = self._load_all()
        sessions[session.session_id] = session
        self._dump_all(sessions)
        return session

    def add_turn(
        self,
        session: ConversationSession,
        *,
        question: str,
        answer: str,
        pending_clarification: bool,
    ) -> ConversationSession:
        session.turns.append(ChatTurn(question=question, answer=answer))
        session.pending_clarification = pending_clarification
        return self.save(session)

    def _load_all(self) -> dict[str, ConversationSession]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("session.read.failed", extra={"error_type": type(exc).__name__})
            return {}
        sessions: dict[str, ConversationSession] = {}
        if not isinstance(payload, dict):
            return sessions
        for session_id, value in payload.items():
            try:
                sessions[session_id] = ConversationSession.model_validate(value)
            except Exception as exc:
                LOGGER.warning("session.read.failed", extra={"error_type": type(exc).__name__})
                continue
        return sessions

    def _dump_all(self, sessions: dict[str, ConversationSession]) -> None:
        try:
            self.path.write_text(
                json.dumps(
                    {key: value.model_dump(mode="json") for key, value in sessions.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            LOGGER.error("session.write.failed", extra={"error_type": type(exc).__name__})
            raise
