from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models import ChatTurn, Language
from app.sessions import ConversationSession, SessionStore
from app.dialogue import DialogRequestError, DialogType, new_dialog
from app.interpreter import Gender, Need


def test_session_resolves_to_new_session_after_three_minutes(
    tmp_path,
    monkeypatch,
) -> None:
    current = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    def fake_now() -> datetime:
        return current

    monkeypatch.setattr("app.sessions.utc_now", fake_now)
    store = SessionStore(tmp_path / "sessions.json")

    first = store.resolve(None, Language.DE, "kb-v1")
    same = store.resolve(first.session_id, Language.DE, "kb-v1")

    assert same.session_id == first.session_id

    current += timedelta(seconds=179)
    still_same = store.resolve(first.session_id, Language.DE, "kb-v1")

    assert still_same.session_id == first.session_id

    current += timedelta(seconds=2)
    fresh = store.resolve(first.session_id, Language.DE, "kb-v1")

    assert fresh.session_id != first.session_id
    assert fresh.turns == []


def test_session_timeout_default_is_three_minutes(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")

    assert store.timeout_seconds == 180


def test_session_keeps_history_only_for_the_same_runtime_fingerprint(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    first = store.create(Language.DE, "same-source-and-curation")
    first = store.add_turn(
        first,
        question="Wo kann ich schlafen?",
        answer="Aktuelle Antwort",
    )

    same = SessionStore(store.path).resolve(
        first.session_id,
        Language.DE,
        "same-source-and-curation",
    )
    changed_curation = store.resolve(first.session_id, Language.DE, "same-source-new-curation")

    assert [turn.answer for turn in same.turns] == ["Aktuelle Antwort"]
    assert changed_curation.session_id != first.session_id
    assert changed_curation.turns == []


def test_legacy_and_changed_release_sessions_cannot_reuse_stale_offer_text(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    legacy = ConversationSession(
        session_id="legacy",
        language=Language.DE,
        created_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
        turns=[
            ChatTurn(
                question="Scharni",
                answer="Alte Adresse und Sozialamt-Angebote 1 bis 4",
            )
        ],
    )
    store.save(legacy)

    migrated = store.resolve("legacy", Language.DE, "current-fingerprint")
    changed_release = store.resolve(
        migrated.session_id,
        Language.DE,
        "new-source-release-fingerprint",
    )

    assert migrated.session_id != "legacy"
    assert migrated.turns == []
    assert changed_release.session_id != migrated.session_id
    assert changed_release.turns == []


def test_language_change_preserves_session_when_runtime_fingerprint_is_unchanged(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    german = store.create(Language.DE, "kb-v1")
    german = store.add_turn(
        german,
        question="Neues Thema",
        answer="Antwort",
    )

    english = store.resolve(german.session_id, Language.EN, "kb-v1")

    assert english.session_id == german.session_id
    assert english.language == Language.EN
    assert [turn.answer for turn in english.turns] == ["Antwort"]


def test_open_dialog_persists_across_restart_and_language_change(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    session = store.create(Language.DE, "fingerprint-current")
    dialog = new_dialog(
        DialogType.SLEEP_TARGET_GROUP,
        need=Need.SLEEP,
        fingerprint="fingerprint-current",
        session_timeout_seconds=180,
    )
    store.set_dialog(session, dialog)

    restored = SessionStore(store.path).resolve(session.session_id, Language.RO, "fingerprint-current")

    assert restored.session_id == session.session_id
    assert restored.language == Language.RO
    assert restored.dialog is not None
    assert restored.dialog.dialog_id == dialog.dialog_id


def test_fingerprint_change_discards_dialog_and_structured_facts(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    session = store.create(Language.DE, "fingerprint-old-1")
    dialog = new_dialog(
        DialogType.SLEEP_TARGET_GROUP,
        need=Need.SLEEP,
        fingerprint="fingerprint-old-1",
        session_timeout_seconds=180,
    )
    dialog.known_explicit_facts.gender = Gender.FEMALE
    store.set_dialog(session, dialog)

    changed = store.resolve(session.session_id, Language.DE, "fingerprint-new-1")

    assert changed.session_id != session.session_id
    assert changed.dialog is None
    assert changed.turns == []


def test_dialog_claim_is_single_use_even_across_store_instances(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    session = store.create(Language.DE, "fingerprint-current")
    dialog = new_dialog(
        DialogType.SLEEP_TARGET_GROUP,
        need=Need.SLEEP,
        fingerprint="fingerprint-current",
        session_timeout_seconds=180,
    )
    session = store.set_dialog(session, dialog)
    first, claimed = store.claim_dialog(session, dialog_id=dialog.dialog_id, choice_values=["under_18"])

    assert claimed.status.value == "processing"
    with pytest.raises(DialogRequestError):
        SessionStore(store.path).claim_dialog(first, dialog_id=dialog.dialog_id, choice_values=["under_18"])
