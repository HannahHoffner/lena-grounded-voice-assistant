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

from .dialogue import DialogRequestError, DialogState, DialogStatus
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
    dialog: DialogState | None = None
    runtime_kb_fingerprint: str | None = None
    # Server-built spoken_text values for the cards/destinations of the most
    # recent turn only (not part of the displayed history). This is the
    # allow-list /api/speech/synthesize checks against for per-card "listen"
    # requests, alongside turns[-1].answer for the main answer replay -- see
    # main.py::synthesize_speech. Old sessions loaded without this field
    # default to empty, which just means per-card TTS is unavailable for them
    # until their next turn.
    speakable_texts: list[str] = Field(default_factory=list)


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
    # Infrastructure routes (toilets/fountains) can report up to 500 map
    # markers per query; without a cap, speakable_texts would write that many
    # full sentences into the session store on every such turn. Bounded the
    # same way turns/sessions already are, not left to grow with the result set.
    max_speakable_texts: int = 40
    _lock: threading.RLock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.timeout_seconds <= 0
            or self.max_turns <= 0
            or self.max_sessions <= 0
            or self.max_speakable_texts <= 0
        ):
            raise ValueError("Sessiongrenzen müssen positive Ganzzahlen sein")
        self._lock = _lock_for(self.path)

    def resolve(
        self,
        session_id: str | None,
        language: Language,
        runtime_kb_fingerprint: str,
    ) -> ConversationSession:
        """Erhaelt Sprachwechsel, verwirft aber jeden fremden Wissensstand."""
        with self._lock:
            now = utc_now()
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            existing = loaded.sessions.get(session_id) if session_id else None
            if (
                existing
                and existing.runtime_kb_fingerprint == runtime_kb_fingerprint
            ):
                if existing.language != language:
                    existing = existing.model_copy(deep=True)
                    existing.language = language
                    existing.last_activity_at = now
                    loaded.sessions[existing.session_id] = existing
                    loaded.changed = True
                if existing.dialog and existing.dialog.expires_at <= now:
                    existing = existing.model_copy(deep=True)
                    existing.dialog = None
                    loaded.sessions[existing.session_id] = existing
                    loaded.changed = True
                if loaded.changed and loaded.writable:
                    self._write_all_unlocked(loaded.sessions)
                return existing

            if existing:
                loaded.sessions.pop(existing.session_id, None)
            session = self._new_session(language, now, runtime_kb_fingerprint)
            loaded.sessions[session.session_id] = session
            self._enforce_capacity_unlocked(loaded, protected_id=session.session_id)
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return session

    def create(self, language: Language, runtime_kb_fingerprint: str) -> ConversationSession:
        """Erzeugt eine neue Session; ein Persistenzfehler blockiert sie nicht."""
        return self.resolve(None, language, runtime_kb_fingerprint)

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
        speakable_texts: list[str] | None = None,
    ) -> ConversationSession:
        """Fügt einen Turn ohne Lost Update unter dem gemeinsamen Dateilock hinzu."""
        with self._lock:
            now = utc_now()
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            current = loaded.sessions.get(session.session_id)
            if (
                current is None
                or current.language != session.language
                or current.runtime_kb_fingerprint != session.runtime_kb_fingerprint
            ):
                current = session.model_copy(deep=True)
            else:
                current = current.model_copy(deep=True)
            current.turns.append(ChatTurn(question=question, answer=answer))
            current.turns = current.turns[-self.max_turns :]
            current.speakable_texts = list(speakable_texts or [])[: self.max_speakable_texts]
            current.last_activity_at = now
            loaded.sessions[current.session_id] = current
            self._enforce_capacity_unlocked(loaded, protected_id=current.session_id)
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return current

    def set_dialog(self, session: ConversationSession, dialog: DialogState | None) -> ConversationSession:
        """Ersetzt den einzigen Dialogzustand atomar in der aktuellen Session."""
        with self._lock:
            now = utc_now()
            loaded = self._load_all_unlocked()
            self._cleanup_unlocked(loaded, now)
            current = loaded.sessions.get(session.session_id)
            current = (current or session).model_copy(deep=True)
            if dialog and dialog.knowledge_base_fingerprint != current.runtime_kb_fingerprint:
                raise DialogRequestError("dialog_fingerprint_mismatch")
            current.dialog = dialog.model_copy(deep=True) if dialog else None
            current.last_activity_at = now
            loaded.sessions[current.session_id] = current
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return current

    def claim_dialog(
        self,
        session: ConversationSession,
        *,
        dialog_id: str,
        choice_values: list[str] | None = None,
    ) -> tuple[ConversationSession, DialogState]:
        """Beansprucht genau eine offene Antwort und verhindert Doppelverarbeitung."""
        with self._lock:
            current, loaded, now = self._current_unlocked(session)
            dialog = current.dialog
            if (
                not dialog
                or dialog.dialog_id != dialog_id
                or dialog.status != DialogStatus.AWAITING_ANSWER
                or dialog.expires_at <= now
                or dialog.knowledge_base_fingerprint != current.runtime_kb_fingerprint
            ):
                raise DialogRequestError()
            values = list(choice_values or [])
            allowed = {choice.value for choice in dialog.choices}
            if values and (not set(values).issubset(allowed) or (len(values) > 1 and not dialog.allow_multiple_choices)):
                raise DialogRequestError()
            dialog = dialog.model_copy(deep=True)
            dialog.status = DialogStatus.PROCESSING
            dialog.updated_at = now
            current.dialog = dialog
            current.last_activity_at = now
            loaded.sessions[current.session_id] = current
            if loaded.writable:
                self._write_all_unlocked(loaded.sessions)
            return current, dialog

    def _current_unlocked(
        self,
        session: ConversationSession,
    ) -> tuple[ConversationSession, _LoadResult, datetime]:
        now = utc_now()
        loaded = self._load_all_unlocked()
        self._cleanup_unlocked(loaded, now)
        current = loaded.sessions.get(session.session_id)
        if current is None or current.runtime_kb_fingerprint != session.runtime_kb_fingerprint:
            raise DialogRequestError("dialog_session_invalid")
        return current.model_copy(deep=True), loaded, now

    @staticmethod
    def _new_session(
        language: Language,
        now: datetime,
        runtime_kb_fingerprint: str,
    ) -> ConversationSession:
        return ConversationSession(
            session_id=uuid.uuid4().hex,
            language=language,
            created_at=now,
            last_activity_at=now,
            runtime_kb_fingerprint=runtime_kb_fingerprint,
        )

    def _load_all_unlocked(self) -> _LoadResult:
        if not self.path.is_file():
            return _LoadResult({})
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
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
                # TTL und Kapazitätsordnung vergleichen absolute Zeitpunkte.
                # Ein beschädigter Einzelrecord darf die übrigen nicht blockieren.
                timestamps = [parsed.created_at, parsed.last_activity_at]
                if parsed.dialog:
                    timestamps.extend([
                        parsed.dialog.created_at, parsed.dialog.updated_at, parsed.dialog.expires_at,
                    ])
                if any(stamp.utcoffset() is None for stamp in timestamps):
                    raise ValueError("Sessionzeitstempel benötigen eine Zeitzone")
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
