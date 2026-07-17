"""Atomare, begrenzte Session-Persistenz für den lokalen Einzelprozessbetrieb."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .models import ChatTurn, Language


LOGGER = logging.getLogger(__name__)
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _lock_for(path: Path) -> threading.RLock:
    """Teilt einen Lock zwischen allen Stores derselben Datei im Prozess."""
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.RLock())


class ConversationSession(BaseModel):
    """Kompakter Gesprächszustand ohne vollständige Provider-Prompthistorie."""

    session_id: str
    language: Language
    created_at: datetime
    last_activity_at: datetime
    turns: list[ChatTurn] = Field(default_factory=list)
    pending_clarification: bool = False


@dataclass(slots=True)
class _LoadResult:
    sessions: dict[str, ConversationSession]
    writable: bool = True
    changed: bool = False


@dataclass(slots=True)
class SessionStore:
    """Persistiert begrenzte Sessions fehlertolerant in einer lokalen JSON-Datei.

    Der Lock schützt den vollständigen Lese-Ändere-Schreibe-Zyklus zwischen
    Store-Instanzen innerhalb eines Prozesses. Mehrere Serverprozesse benötigen
    weiterhin einen extern koordinierten Speicher.
    """

    path: Path
    timeout_seconds: int = 180
    max_turns: int = 8
    max_sessions: int = 500
    _lock: threading.RLock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.max_turns <= 0 or self.max_sessions <= 0:
            raise ValueError("Sessiongrenzen müssen positive Ganzzahlen sein")
        self._lock = _lock_for(self.path)

    def resolve(self, session_id: str | None, language: Language) -> ConversationSession:
        """Liefert eine aktive Session oder legt bei Ablauf/Sprachwechsel eine neue an."""
        with self._lock:
            now = utc_now()
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            existing = loaded.sessions.get(session_id) if session_id else None
            if existing and existing.language == language:
                if loaded.changed and loaded.writable:
                    self._write_all_unlocked(loaded.sessions)
                return existing

            session = self._new_session(language, now)
            loaded.sessions[session.session_id] = session
            self._enforce_capacity_unlocked(loaded, protected_id=session.session_id)
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return session

    def create(self, language: Language) -> ConversationSession:
        """Erzeugt eine neue Session; ein Persistenzfehler blockiert sie nicht."""
        return self.resolve(None, language)

    def get(self, session_id: str | None) -> ConversationSession | None:
        """Lädt eine aktive Session und bereinigt dabei abgelaufene Datensätze."""
        if not session_id:
            return None
        with self._lock:
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, utc_now())
            if loaded.changed and loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return loaded.sessions.get(session_id)

    def save(self, session: ConversationSession) -> ConversationSession:
        """Speichert eine Session atomar und liefert sie auch bei Schreibfehlern zurück."""
        with self._lock:
            now = utc_now()
            updated = session.model_copy(deep=True)
            updated.last_activity_at = now
            updated.turns = updated.turns[-self.max_turns :]
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            loaded.sessions[updated.session_id] = updated
            self._enforce_capacity_unlocked(loaded, protected_id=updated.session_id)
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return updated

    def add_turn(
        self,
        session: ConversationSession,
        *,
        question: str,
        answer: str,
        pending_clarification: bool,
    ) -> ConversationSession:
        """Fügt einen Turn ohne Lost Update unter dem gemeinsamen Dateilock hinzu."""
        with self._lock:
            now = utc_now()
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            current = loaded.sessions.get(session.session_id)
            if current is None or current.language != session.language:
                current = session.model_copy(deep=True)
            else:
                current = current.model_copy(deep=True)
            current.turns.append(ChatTurn(question=question, answer=answer))
            current.turns = current.turns[-self.max_turns :]
            current.pending_clarification = pending_clarification
            current.last_activity_at = now
            loaded.sessions[current.session_id] = current
            self._enforce_capacity_unlocked(loaded, protected_id=current.session_id)
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return current

    @staticmethod
    def _new_session(language: Language, now: datetime) -> ConversationSession:
        return ConversationSession(
            session_id=uuid.uuid4().hex,
            language=language,
            created_at=now,
            last_activity_at=now,
        )

    def _load_all_unlocked(self) -> _LoadResult:
        if not self.path.is_file():
            return _LoadResult({})
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            LOGGER.warning("session.corrupt_file.detected", extra={"error_type": type(exc).__name__})
            return _LoadResult({}, writable=self._quarantine_unlocked())
        except OSError as exc:
            LOGGER.warning("session.load.failed", extra={"error_type": type(exc).__name__})
            return _LoadResult({}, writable=False)
        if not isinstance(payload, dict):
            LOGGER.warning("session.corrupt_file.detected", extra={"error_type": "InvalidRootType"})
            return _LoadResult({}, writable=self._quarantine_unlocked())

        sessions: dict[str, ConversationSession] = {}
        invalid_count = 0
        for session_id, value in payload.items():
            try:
                parsed = ConversationSession.model_validate(value)
                if parsed.session_id != session_id:
                    raise ValueError("Session-ID stimmt nicht mit dem Schlüssel überein")
                sessions[session_id] = parsed
            except (ValidationError, TypeError, ValueError):
                invalid_count += 1
        if invalid_count:
            LOGGER.warning("session.validation.failed", extra={"invalid_count": invalid_count})
        return _LoadResult(sessions, changed=bool(invalid_count))

    def _cleanup_unlocked(self, loaded: _LoadResult, now: datetime) -> None:
        threshold = timedelta(seconds=self.timeout_seconds)
        expired = [
            session_id
            for session_id, session in loaded.sessions.items()
            if now - session.last_activity_at > threshold
        ]
        for session_id in expired:
            del loaded.sessions[session_id]
        if expired:
            loaded.changed = True
            LOGGER.info("session.cleanup.completed", extra={"removed_count": len(expired)})
        self._enforce_capacity_unlocked(loaded)

    def _enforce_capacity_unlocked(
        self,
        loaded: _LoadResult,
        *,
        protected_id: str | None = None,
    ) -> None:
        excess = len(loaded.sessions) - self.max_sessions
        if excess <= 0:
            return
        ordered = sorted(
            loaded.sessions.values(),
            key=lambda item: (item.last_activity_at, item.created_at, item.session_id),
        )
        removable = [item for item in ordered if item.session_id != protected_id]
        for session in removable[:excess]:
            del loaded.sessions[session.session_id]
        loaded.changed = True
        LOGGER.info("session.capacity.enforced", extra={"removed_count": excess})

    def _quarantine_unlocked(self) -> bool:
        recovery = self.path.with_name(
            f"sessions.corrupt.{utc_now():%Y%m%dT%H%M%S}.{uuid.uuid4().hex}.json"
        )
        try:
            os.replace(self.path, recovery)
        except OSError as exc:
            LOGGER.error("session.load.failed", extra={"error_type": type(exc).__name__})
            return False
        return True

    def _write_all_unlocked(self, sessions: dict[str, ConversationSession]) -> bool:
        started = time.perf_counter()
        temp_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                key: ConversationSession.model_validate(value).model_dump(mode="json")
                for key, value in sessions.items()
            }
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
            temp_path = None
        except (OSError, TypeError, ValueError, ValidationError) as exc:
            LOGGER.error("session.write.failed", extra={"error_type": type(exc).__name__})
            return False
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.warning("session.temp_cleanup.failed")
        LOGGER.info(
            "session.write.completed",
            extra={
                "session_count": len(sessions),
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return True
