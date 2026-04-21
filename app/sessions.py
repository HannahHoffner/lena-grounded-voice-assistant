from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .kb import KnowledgeBase
from .models import (
    ConversationContext,
    ConversationSession,
    Language,
    QueryAnswerResponse,
    QueryRequest,
    SessionEvent,
    SessionStatus,
    SessionTurn,
)
from .retrieval import RetrievalEngine, normalize_text, query_tokens_for_search, tokenize


REFERENTIAL_TERMS = (
    " it ",
    " there ",
    " that place",
    " this place",
    " es ",
    " dort",
    " da ",
    "diese stelle",
    "dieser ort",
    "diesen ort",
    "diese anlaufstelle",
)
ALTERNATIVE_TERMS = ("another", "other", "different", "else", "another place", "andere", "weiteres", "alternative")
TOPIC_SHIFT_PREFIXES = ("und ", "and ", "what about ", "was ist mit ", "und fuer ", "und für ", "fuer ", "für ")
ATTRIBUTE_FOLLOWUP_TOKENS = {
    "adresse",
    "address",
    "appointment",
    "anmeldung",
    "email",
    "kontakt",
    "oeffnungszeiten",
    "offen",
    "open",
    "sonntag",
    "sonntags",
    "sunday",
    "termin",
    "uhrzeit",
    "wann",
    "where",
    "wie",
    "wo",
}
TARGET_GROUP_FOLLOWUP_TOKENS = {"frau", "frauen", "familien", "families", "maenner", "mann", "men", "women"}
TOPIC_TOKENS = {
    "beratung",
    "clothing",
    "dusche",
    "duschen",
    "essen",
    "food",
    "frau",
    "frauen",
    "kleidung",
    "medical",
    "medizin",
    "shower",
    "shelter",
    "unterkunft",
    "women",
}
RELATED_TOPIC_TOKENS = {
    "food": {"housing", "hygiene", "social"},
    "housing": {"food", "hygiene", "social"},
    "hygiene": {"housing", "food", "social"},
    "social": {"housing", "food", "hygiene"},
}
SELF_CONTAINED_QUERY_SCORE = 0.35


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class SessionResolution:
    session: ConversationSession
    context: ConversationContext
    session_event: SessionEvent
    session_message: str | None


class SessionStore:
    def __init__(self, path: Path, max_turns: int = 6) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_turns = max_turns

    def get(self, session_id: str) -> ConversationSession | None:
        return self._load_all().get(session_id)

    def save(self, session: ConversationSession) -> ConversationSession:
        data = self._load_all()
        trimmed = session.model_copy(
            update={
                "recent_turns": session.recent_turns[-self.max_turns :],
            }
        )
        data[trimmed.session_id] = trimmed
        self._dump_all(data)
        return trimmed

    def create(self, language: Language, event: SessionEvent, message: str | None = None, *, now: datetime | None = None) -> ConversationSession:
        timestamp = now or utc_now()
        session = ConversationSession(
            session_id=uuid.uuid4().hex,
            status=SessionStatus.ACTIVE,
            created_at=timestamp,
            last_activity_at=timestamp,
            selected_language=language,
            last_session_event=event,
            last_session_message=message,
        )
        return self.save(session)

    def mark(self, session: ConversationSession, status: SessionStatus, event: SessionEvent, message: str | None = None, *, now: datetime | None = None) -> ConversationSession:
        timestamp = now or utc_now()
        updated = session.model_copy(
            update={
                "status": status,
                "last_activity_at": timestamp,
                "ended_reason": message,
                "last_session_event": event,
                "last_session_message": message,
            }
        )
        return self.save(updated)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def _load_all(self) -> dict[str, ConversationSession]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        sessions: dict[str, ConversationSession] = {}
        for session_id, raw in payload.items():
            try:
                session = ConversationSession.model_validate(raw)
            except Exception:
                continue
            sessions[session_id] = session
        return sessions

    def _dump_all(self, sessions: dict[str, ConversationSession]) -> None:
        payload = {session_id: session.model_dump(mode="json") for session_id, session in sessions.items()}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SessionManager:
    def __init__(self, store: SessionStore, kb: KnowledgeBase, timeout_seconds: int = 300) -> None:
        self.store = store
        self.kb = kb
        self.timeout = timedelta(seconds=timeout_seconds)
        self.retrieval = RetrievalEngine(kb)

    def prepare_request(self, payload: QueryRequest, now: datetime | None = None) -> SessionResolution:
        timestamp = now or utc_now()
        previous = self.store.get(payload.session_id) if payload.session_id else None
        query = payload.transcript.strip()
        if not previous:
            session = self.store.create(payload.language, SessionEvent.STARTED, _session_message(SessionEvent.STARTED), now=timestamp)
            return SessionResolution(
                session=session,
                context=ConversationContext(session_id=session.session_id, resolved_transcript=query),
                session_event=SessionEvent.STARTED,
                session_message=_session_message(SessionEvent.STARTED),
            )

        if previous.status != SessionStatus.ACTIVE:
            event = SessionEvent.ENDED_RESET if previous.status == SessionStatus.ENDED else SessionEvent.EXPIRED_RESET
            if previous.status == SessionStatus.RESET:
                event = SessionEvent.CONTEXT_RESET
            session = self.store.create(payload.language, event, _session_message(event), now=timestamp)
            return SessionResolution(
                session=session,
                context=ConversationContext(session_id=session.session_id, resolved_transcript=query),
                session_event=event,
                session_message=_session_message(event),
            )

        if payload.language != previous.selected_language:
            self.store.mark(previous, SessionStatus.RESET, SessionEvent.LANGUAGE_RESET, _session_message(SessionEvent.LANGUAGE_RESET), now=timestamp)
            session = self.store.create(payload.language, SessionEvent.LANGUAGE_RESET, _session_message(SessionEvent.LANGUAGE_RESET), now=timestamp)
            return SessionResolution(
                session=session,
                context=ConversationContext(session_id=session.session_id, resolved_transcript=query),
                session_event=SessionEvent.LANGUAGE_RESET,
                session_message=_session_message(SessionEvent.LANGUAGE_RESET),
            )

        if timestamp - previous.last_activity_at > self.timeout:
            self.store.mark(previous, SessionStatus.EXPIRED, SessionEvent.EXPIRED_RESET, _session_message(SessionEvent.EXPIRED_RESET), now=timestamp)
            session = self.store.create(payload.language, SessionEvent.EXPIRED_RESET, _session_message(SessionEvent.EXPIRED_RESET), now=timestamp)
            return SessionResolution(
                session=session,
                context=ConversationContext(session_id=session.session_id, resolved_transcript=query),
                session_event=SessionEvent.EXPIRED_RESET,
                session_message=_session_message(SessionEvent.EXPIRED_RESET),
            )

        context, event = self._build_context(previous, payload)
        if event == SessionEvent.CONTEXT_RESET:
            self.store.mark(previous, SessionStatus.RESET, SessionEvent.CONTEXT_RESET, _session_message(SessionEvent.CONTEXT_RESET), now=timestamp)
            session = self.store.create(payload.language, SessionEvent.CONTEXT_RESET, _session_message(SessionEvent.CONTEXT_RESET), now=timestamp)
            return SessionResolution(
                session=session,
                context=ConversationContext(session_id=session.session_id, resolved_transcript=query),
                session_event=SessionEvent.CONTEXT_RESET,
                session_message=_session_message(SessionEvent.CONTEXT_RESET),
            )

        active = previous.model_copy(
            update={
                "last_activity_at": timestamp,
                "last_session_event": event,
                "last_session_message": _session_message(event) if event != SessionEvent.CONTINUED else None,
            }
        )
        active = self.store.save(active)
        return SessionResolution(
            session=active,
            context=context,
            session_event=event,
            session_message=_session_message(event) if event != SessionEvent.CONTINUED else None,
        )

    def end_session(self, session_id: str, now: datetime | None = None) -> ConversationSession | None:
        session = self.store.get(session_id)
        if not session:
            return None
        return self.store.mark(session, SessionStatus.ENDED, SessionEvent.ENDED_RESET, _session_message(SessionEvent.ENDED_RESET), now=now)

    def record_turn(
        self,
        session: ConversationSession,
        payload: QueryRequest,
        response: QueryAnswerResponse,
        context: ConversationContext,
        now: datetime | None = None,
    ) -> ConversationSession:
        timestamp = now or utc_now()
        pages = [_get_page(self.kb, page_id) for page_id in response.retrieved_page_ids[:3]]
        pages = [page for page in pages if page is not None]
        turn = SessionTurn(
            timestamp=timestamp,
            language=payload.language,
            transcript=payload.transcript,
            resolved_transcript=context.resolved_transcript,
            answer_text=response.answer_text,
            answer_status=response.status,
            retrieved_page_ids=response.retrieved_page_ids[:5],
            primary_page_ids=_primary_page_ids(response.retrieved_page_ids[:5], self.kb),
            topic_categories=sorted({page.category for page in pages if page.category}),
            topic_service_types=sorted({page.service_type for page in pages if page.service_type}),
            follow_up_mode=context.follow_up_mode,
        )
        updated = session.model_copy(
            update={
                "status": SessionStatus.ACTIVE,
                "last_activity_at": timestamp,
                "selected_language": payload.language,
                "recent_turns": [*session.recent_turns, turn][-self.store.max_turns :],
            }
        )
        return self.store.save(updated)

    def _build_context(self, session: ConversationSession, payload: QueryRequest) -> tuple[ConversationContext, SessionEvent]:
        query = payload.transcript.strip()
        context = ConversationContext(session_id=session.session_id, resolved_transcript=query)
        if not session.recent_turns:
            return context, SessionEvent.CONTINUED

        last_turn = session.recent_turns[-1]
        focus_turn = _focus_turn(session.recent_turns)
        topic_turn = _topic_turn(session.recent_turns)
        focus_page_ids = focus_turn.primary_page_ids[:2] if focus_turn else []
        topic_turns = _context_turns(topic_turn, focus_turn, last_turn)
        normalized = f" {normalize_text(query)} "
        raw_tokens = set(tokenize(query))
        tokens = set(query_tokens_for_search(query, payload.language))
        raw_results = self.retrieval.retrieve(query, payload.language, limit=4)
        raw_top_score = raw_results[0].score if raw_results else 0.0
        referential = _is_referential_followup(normalized)
        alternative = _is_alternative_followup(normalized)
        attribute_only = _is_attribute_followup(raw_tokens or tokens)
        topic_shift = _is_topic_shift_followup(normalized, raw_tokens or tokens)
        shared_anchor = _has_anchor_overlap(query, last_turn, self.kb)
        same_topic = _has_topic_overlap(tokens, last_turn)

        if alternative and focus_page_ids:
            context.follow_up_mode = "alternative"
            context.excluded_page_ids = _family_related_page_ids(focus_page_ids[:1], self.kb)
            context.history_summary = _history_summary(topic_turns, self.kb)
            context.resolved_transcript = " ".join(filter(None, [query, topic_turn.transcript if topic_turn else "", _page_titles(focus_page_ids[:1], self.kb)])).strip()
            return context, SessionEvent.CONTINUED

        if (referential or attribute_only or shared_anchor) and focus_page_ids:
            context.follow_up_mode = "referential"
            context.preferred_page_ids = focus_page_ids[:1]
            context.history_summary = _history_summary(topic_turns, self.kb)
            context.resolved_transcript = " ".join(filter(None, [query, _page_titles(focus_page_ids[:1], self.kb), topic_turn.transcript if topic_turn else ""])).strip()
            return context, SessionEvent.CONTINUED

        if topic_shift or same_topic:
            context.follow_up_mode = "topic_shift"
            context.history_summary = _history_summary(topic_turns or session.recent_turns[-2:], self.kb)
            return context, SessionEvent.CONTINUED

        if referential or attribute_only:
            context.follow_up_mode = "referential"
            context.history_summary = _history_summary(topic_turns, self.kb)
            return context, SessionEvent.CONTINUED

        if raw_top_score >= SELF_CONTAINED_QUERY_SCORE and len(tokens) >= 2:
            return context, SessionEvent.CONTEXT_RESET

        return context, SessionEvent.CONTEXT_RESET


def _session_message(event: SessionEvent) -> str | None:
    messages = {
        SessionEvent.STARTED: "New conversation started.",
        SessionEvent.EXPIRED_RESET: "Conversation expired after five minutes. A new conversation started.",
        SessionEvent.ENDED_RESET: "Conversation ended.",
        SessionEvent.CONTEXT_RESET: "A new conversation started because the previous context no longer fit.",
        SessionEvent.LANGUAGE_RESET: "A new conversation started because the language changed.",
    }
    return messages.get(event)


def _is_referential_followup(normalized_transcript: str) -> bool:
    return any(term in normalized_transcript for term in REFERENTIAL_TERMS)


def _is_alternative_followup(normalized_transcript: str) -> bool:
    return any(term in normalized_transcript for term in ALTERNATIVE_TERMS)


def _is_attribute_followup(tokens: set[str]) -> bool:
    return bool(tokens) and (tokens <= ATTRIBUTE_FOLLOWUP_TOKENS or (tokens & ATTRIBUTE_FOLLOWUP_TOKENS and len(tokens) <= 4 and not tokens & TOPIC_TOKENS))


def _is_topic_shift_followup(normalized_transcript: str, tokens: set[str]) -> bool:
    trimmed = normalized_transcript.strip()
    if any(trimmed.startswith(prefix) for prefix in TOPIC_SHIFT_PREFIXES):
        return True
    if tokens and tokens <= TARGET_GROUP_FOLLOWUP_TOKENS:
        return True
    if len(tokens) <= 4 and tokens & TARGET_GROUP_FOLLOWUP_TOKENS:
        return True
    return False


def _has_anchor_overlap(query: str, last_turn: SessionTurn, kb: KnowledgeBase) -> bool:
    query_tokens = set(query_tokens_for_search(query, last_turn.language))
    if not query_tokens or not last_turn.primary_page_ids:
        return False
    anchor_tokens: set[str] = set()
    for page_id in last_turn.primary_page_ids[:2]:
        page = _get_page(kb, page_id)
        if not page:
            continue
        anchor_tokens.update(tokenize(" ".join([page.title, page.address or "", " ".join(page.aliases)])))
    return bool(query_tokens & anchor_tokens)


def _has_topic_overlap(query_tokens: set[str], last_turn: SessionTurn) -> bool:
    if not query_tokens:
        return False
    turn_topics = set(last_turn.topic_categories) | set(last_turn.topic_service_types)
    if query_tokens & turn_topics:
        return True
    for topic in turn_topics:
        if query_tokens & RELATED_TOPIC_TOKENS.get(topic, set()):
            return True
    return False


def _history_summary(turns: list[SessionTurn], kb: KnowledgeBase) -> str:
    lines: list[str] = []
    for turn in turns:
        page_titles = _page_titles(turn.primary_page_ids[:2], kb)
        line = f"Previous request: {turn.transcript}"
        if page_titles:
            line += f"\nPrevious pages: {page_titles}"
        lines.append(line)
    return "\n".join(lines).strip()


def _focus_turn(turns: list[SessionTurn]) -> SessionTurn | None:
    for turn in reversed(turns):
        if turn.primary_page_ids:
            return turn
    return None


def _topic_turn(turns: list[SessionTurn]) -> SessionTurn | None:
    for turn in reversed(turns):
        if turn.follow_up_mode not in {"referential", "alternative"}:
            return turn
    return _focus_turn(turns)


def _context_turns(*turns: SessionTurn | None) -> list[SessionTurn]:
    unique_turns: list[SessionTurn] = []
    seen: set[tuple[datetime, str]] = set()
    for turn in turns:
        if not turn:
            continue
        key = (turn.timestamp, turn.transcript)
        if key in seen:
            continue
        seen.add(key)
        unique_turns.append(turn)
    return unique_turns


def _page_titles(page_ids: list[str], kb: KnowledgeBase) -> str:
    titles: list[str] = []
    for page_id in page_ids:
        page = _get_page(kb, page_id)
        if page:
            titles.append(page.title)
    return ", ".join(titles)


def _family_related_page_ids(page_ids: list[str], kb: KnowledgeBase) -> list[str]:
    if not page_ids:
        return []
    first_id = page_ids[0]
    first_page = _get_page(kb, first_id)
    if not first_page:
        return page_ids[:1]
    family = first_page.title.split(" - ", 1)[0].strip()
    related: list[str] = []
    for candidate in kb.dataset.pages:
        if candidate.title.split(" - ", 1)[0].strip() == family and candidate.page_id not in related:
            related.append(candidate.page_id)
    return related or page_ids[:1]


def _primary_page_ids(page_ids: list[str], kb: KnowledgeBase) -> list[str]:
    primary: list[str] = []
    families: set[str] = set()
    for page_id in page_ids:
        page = _get_page(kb, page_id)
        if not page:
            continue
        family = page.title.split(" - ", 1)[0].strip()
        if family in families and page.service_type == "service_catalog":
            continue
        families.add(family)
        primary.append(page_id)
    return primary[:3]


def _get_page(kb: KnowledgeBase, page_id: str):
    try:
        return kb.get_page(page_id)
    except KeyError:
        return None
