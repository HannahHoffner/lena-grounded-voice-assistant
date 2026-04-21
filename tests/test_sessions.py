from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.kb import KnowledgeBase
from app.models import Language, QueryAnswerResponse, QueryRequest, SessionEvent
from app.sessions import SessionManager, SessionStore


def _manager(tmp_path) -> tuple[SessionManager, KnowledgeBase]:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    store = SessionStore(tmp_path / "sessions.json")
    return SessionManager(store, kb, timeout_seconds=300), kb


def _response(session_id: str, page_ids: list[str], answer_text: str = "Test answer") -> QueryAnswerResponse:
    return QueryAnswerResponse(
        answer_text=answer_text,
        status="ok",
        retrieved_page_ids=page_ids,
        provider="template",
        model=None,
        session_id=session_id,
    )


def test_session_follow_up_keeps_same_entity_context(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    started_at = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Wo kann ich duschen?", language=Language.DE)
    first = manager.prepare_request(first_payload, now=started_at)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["leipziger-oase"]), first.context, now=started_at)

    second_payload = QueryRequest(transcript="Wie ist die Adresse?", language=Language.DE, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=started_at + timedelta(seconds=30))

    assert second.session.session_id == first.session.session_id
    assert second.session_event == SessionEvent.CONTINUED
    assert second.context.follow_up_mode == "referential"
    assert second.context.preferred_page_ids == ["leipziger-oase"]


def test_session_alternative_request_excludes_previous_place(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Wo kann ich duschen?", language=Language.DE)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(
        first.session,
        first_payload,
        _response(first.session.session_id, ["leipziger-oase", "wohnungsnotfallhilfe-pdf-leipziger-oase-katalog"]),
        first.context,
        now=now,
    )

    second_payload = QueryRequest(transcript="Gibt es noch einen anderen Ort?", language=Language.DE, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=20))

    assert second.context.follow_up_mode == "alternative"
    assert "leipziger-oase" in second.context.excluded_page_ids


def test_session_topic_shift_keeps_session_but_drops_entity_bias(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Wo kann ich duschen?", language=Language.DE)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["leipziger-oase"]), first.context, now=now)

    second_payload = QueryRequest(transcript="Und was ist mit Essen?", language=Language.DE, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=40))

    assert second.session.session_id == first.session.session_id
    assert second.context.follow_up_mode == "topic_shift"
    assert second.context.preferred_page_ids == []


def test_session_timeout_starts_new_session(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Where can I get food?", language=Language.EN)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["tafel-leipzig-markkleeberg"]), first.context, now=now)

    second_payload = QueryRequest(transcript="Is it open today?", language=Language.EN, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=301))

    assert second.session_event == SessionEvent.EXPIRED_RESET
    assert second.session.session_id != first.session.session_id


def test_language_change_starts_new_session(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Where can I get food?", language=Language.EN)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["tafel-leipzig-markkleeberg"]), first.context, now=now)

    second_payload = QueryRequest(transcript="Wo kann ich duschen?", language=Language.DE, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=30))

    assert second.session_event == SessionEvent.LANGUAGE_RESET
    assert second.session.session_id != first.session.session_id


def test_unrelated_low_signal_query_resets_context(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="Wo kann ich duschen?", language=Language.DE)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["leipziger-oase"]), first.context, now=now)

    second_payload = QueryRequest(transcript="astronomy telescope orbit", language=Language.DE, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=30))

    assert second.session_event == SessionEvent.CONTEXT_RESET
    assert second.session.session_id != first.session.session_id


def test_appointment_follow_up_keeps_same_entity_context(tmp_path) -> None:
    manager, _ = _manager(tmp_path)
    now = datetime(2026, 4, 21, 10, 0, tzinfo=UTC)
    first_payload = QueryRequest(transcript="What is CABL?", language=Language.EN)
    first = manager.prepare_request(first_payload, now=now)
    manager.record_turn(first.session, first_payload, _response(first.session.session_id, ["cabl-uvo"]), first.context, now=now)

    second_payload = QueryRequest(transcript="Do I need an appointment?", language=Language.EN, session_id=first.session.session_id)
    second = manager.prepare_request(second_payload, now=now + timedelta(seconds=20))

    assert second.session_event == SessionEvent.CONTINUED
    assert second.session.session_id == first.session.session_id
    assert second.context.follow_up_mode == "referential"
    assert second.context.preferred_page_ids == ["cabl-uvo"]
