from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Language
from app.sessions import ConversationSession, SessionStore


ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "canonical" / "offers.json"


def _session(session_id: str, activity: datetime) -> ConversationSession:
    return ConversationSession(
        session_id=session_id,
        language=Language.DE,
        created_at=activity,
        last_activity_at=activity,
    )


def _write_sessions(path: Path, sessions: list[ConversationSession]) -> None:
    path.write_text(
        json.dumps(
            {item.session_id: item.model_dump(mode="json") for item in sessions},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_atomic_replace_preserves_previous_file_and_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "sessions.json"
    store = SessionStore(path)
    session = store.create(Language.DE)
    previous = path.read_bytes()

    def fail_replace(source, destination) -> None:
        assert Path(source).parent == path.parent
        assert Path(destination) == path
        raise OSError("simulated replace failure")

    monkeypatch.setattr("app.sessions.os.replace", fail_replace)
    updated = store.add_turn(
        session,
        question="sensitive question",
        answer="sensitive answer",
        pending_clarification=False,
    )

    assert len(updated.turns) == 1
    assert path.read_bytes() == previous
    assert list(tmp_path.glob(".sessions.json.*.tmp")) == []


def test_parallel_store_instances_do_not_lose_sessions_or_turns(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    stores = [SessionStore(path, max_turns=50, max_sessions=100) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        created = list(pool.map(lambda store: store.create(Language.DE), stores))

    base = created[0]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda pair: pair[1].add_turn(
                    base,
                    question=f"question-{pair[0]}",
                    answer=f"answer-{pair[0]}",
                    pending_clarification=False,
                ),
                enumerate(stores),
            )
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    persisted = SessionStore(path, max_turns=50, max_sessions=100).get(base.session_id)
    assert len(payload) == 8
    assert persisted is not None
    assert {turn.question for turn in persisted.turns} == {f"question-{index}" for index in range(8)}


def test_lock_is_released_after_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sessions.json"
    store = SessionStore(path)
    real_replace = __import__("app.sessions", fromlist=["os"]).os.replace
    calls = 0

    def fail_once(source, destination) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated")
        real_replace(source, destination)

    monkeypatch.setattr("app.sessions.os.replace", fail_once)
    first = store.create(Language.DE)
    second = store.create(Language.DE)

    assert first.session_id != second.session_id
    assert store.get(second.session_id) is not None


def test_ttl_boundary_and_capacity_are_persisted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    path = tmp_path / "sessions.json"
    _write_sessions(
        path,
        [
            _session("expired", now - timedelta(seconds=181)),
            _session("boundary", now - timedelta(seconds=180)),
            _session("older-active", now - timedelta(seconds=20)),
            _session("newer-active", now - timedelta(seconds=10)),
        ],
    )
    monkeypatch.setattr("app.sessions.utc_now", lambda: now)

    store = SessionStore(path, timeout_seconds=180, max_sessions=2)
    assert store.get("boundary") is None

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"older-active", "newer-active"}


def test_exact_ttl_boundary_remains_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    path = tmp_path / "sessions.json"
    _write_sessions(path, [_session("boundary", now - timedelta(seconds=180))])
    monkeypatch.setattr("app.sessions.utc_now", lambda: now)

    assert SessionStore(path, timeout_seconds=180).get("boundary") is not None


@pytest.mark.parametrize("content", ["not-json", "[]"])
def test_corrupt_file_is_quarantined_without_logging_content(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    content: str,
) -> None:
    path = tmp_path / "sessions.json"
    path.write_text(content, encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        session = SessionStore(path).create(Language.DE)

    assert SessionStore(path).get(session.session_id) is not None
    recovery = list(tmp_path.glob("sessions.corrupt.*.json"))
    assert len(recovery) == 1
    assert recovery[0].read_text(encoding="utf-8") == content
    assert content not in caplog.text
    assert "session.corrupt_file.detected" in caplog.text


def test_invalid_record_is_removed_while_valid_record_survives(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "sessions.json"
    valid = _session("valid", datetime.now(UTC))
    payload = {"valid": valid.model_dump(mode="json"), "invalid": {"secret": "private"}}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        loaded = SessionStore(path).get("valid")

    assert loaded is not None
    assert set(json.loads(path.read_text(encoding="utf-8"))) == {"valid"}
    assert "session.validation.failed" in caplog.text
    assert "private" not in caplog.text


def test_failed_quarantine_keeps_corrupt_file_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "sessions.json"
    path.write_text("corrupt-sensitive-content", encoding="utf-8")

    monkeypatch.setattr("app.sessions.os.replace", lambda *_: (_ for _ in ()).throw(OSError("blocked")))
    session = SessionStore(path).create(Language.DE)

    assert session.session_id
    assert path.read_text(encoding="utf-8") == "corrupt-sensitive-content"
    assert list(tmp_path.glob("sessions.corrupt.*.json")) == []


def test_session_cleanup_does_not_touch_interaction_log(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    session_path = runtime / "sessions.json"
    interaction_path = runtime / "logs" / "interactions.jsonl"
    interaction_path.parent.mkdir()
    interaction_path.write_text('{"sentinel":"research-record"}\n', encoding="utf-8")
    _write_sessions(session_path, [_session("expired", now - timedelta(seconds=181))])
    monkeypatch.setattr("app.sessions.utc_now", lambda: now)

    assert SessionStore(session_path).get("expired") is None
    assert interaction_path.read_text(encoding="utf-8") == '{"sentinel":"research-record"}\n'


def test_session_write_failure_does_not_block_api_or_interaction_record(tmp_path: Path) -> None:
    settings = Settings(
        app_root=tmp_path,
        kb_path=KB_PATH,
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_log_path=tmp_path / "runtime" / "logs" / "interactions.jsonl",
    )
    app = create_app(settings)
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("file blocks directory creation", encoding="utf-8")
    app.state.service.sessions.path = blocked_parent / "sessions.json"

    response = TestClient(app).post("/api/query", json={"query": "Wo gibt es Essen?"})

    assert response.status_code == 200
    record_path = settings.interaction_log_path
    assert record_path is not None
    records = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["session_id"] == response.json()["session_id"]
    assert records[0]["assistant_answer"] == response.json()["answer"]


def test_session_limits_require_positive_integers(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SessionStore(tmp_path / "sessions.json", timeout_seconds=0)
    with pytest.raises(ValueError):
        Settings(
            app_root=tmp_path,
            kb_path=KB_PATH,
            rewrite_provider="template",
            blablador_base_url=None,
            blablador_api_key=None,
            blablador_model=None,
            blablador_timeout_seconds=1,
            blablador_max_context_chars=50_000,
            session_max_entries=0,
        )
