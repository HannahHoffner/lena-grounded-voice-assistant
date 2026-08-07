from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import Language
from app.sessions import SessionStore


def test_session_resolves_to_new_session_after_three_minutes(
    tmp_path,
    monkeypatch,
) -> None:
    current = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    def fake_now() -> datetime:
        return current

    monkeypatch.setattr("app.sessions.utc_now", fake_now)
    store = SessionStore(tmp_path / "sessions.json")

    first = store.resolve(None, Language.DE)
    same = store.resolve(first.session_id, Language.DE)

    assert same.session_id == first.session_id

    current += timedelta(seconds=179)
    still_same = store.resolve(first.session_id, Language.DE)

    assert still_same.session_id == first.session_id

    current += timedelta(seconds=2)
    fresh = store.resolve(first.session_id, Language.DE)

    assert fresh.session_id != first.session_id
    assert fresh.turns == []


def test_session_timeout_default_is_three_minutes(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")

    assert store.timeout_seconds == 180
