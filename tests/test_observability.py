"""Integrationstests für technische Events und das lokale Interaktionsprotokoll."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.application_texts import application_text
from app.interpreter import AcuteRiskStatus, Need, QueryInterpretation, ScopeStatus
from app.interactions import InteractionRecord, InteractionWriter
from app.llm_selection import CandidateSelectionResponse, SelectorError
from app.main import create_app
from app.models import Language
from app.providers.llm import InterpreterError, ProviderAnswer
from app.sessions import SessionStore
from app.speech import SpeechSynthesisError, SpeechSynthesizer, SpeechTranscriber, SpeechTranscriptionError
from app.safety import SafetyTextKind, safety_text


ROOT = Path(__file__).resolve().parents[1]


def _interpretation(
    need: Need = Need.UNKNOWN,
    *,
    scope: ScopeStatus = ScopeStatus.IN_SCOPE,
    risk: AcuteRiskStatus = AcuteRiskStatus.NOT_DETECTED,
) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
            "contract_version": "3",
            "need": need.value,
            "explicit_service_requests": [],
            "scope_status": scope.value,
            "input_language": "de",
            "explicit_facts": {
                "age": None,
                "gender": "unknown",
                "drug_use": "unknown",
                "no_social_benefit_entitlement": "unknown",
                "district": None,
                "requested_day": None,
                "requested_time": None,
            },
            "uncertain_hints": [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": risk.value,
        }
    )


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    settings = Settings(
        app_root=tmp_path,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        wfs_auto_sync=False,
        interaction_logging_enabled=True,
        interaction_log_path=tmp_path / "runtime" / "logs" / "interactions.jsonl",
    )
    return replace(settings, **overrides)


def _records(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_unavailable_interpreter_writes_minimal_redacted_safety_interaction(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    response = TestClient(create_app(settings)).post(
        "/api/query",
        json={"query": "Wo bekomme ich Essen?", "language": "de"},
    )

    assert response.status_code == 200
    record = _records(settings.interaction_log_path)[0]  # type: ignore[arg-type]
    assert record["user_query"] == "[redacted_safety_input]"
    assert record["assistant_answer"] == response.json()["answer"]
    assert record["language"] == "de"
    assert record["input_mode"] == "text"
    assert record["route"] == "interpreter_error"
    assert record["source_ids"] == []
    assert record["candidate_result_count"] == 0
    assert record["acute_risk_detected"] is False
    assert record["fallback_used"] is True
    assert record["safety_path"] == "interpreter_failure"
    assert record["safety_fallback_used"] is True
    assert record["schema_version"] == 11
    assert record["selector_used"] is False
    assert record["selector_bypass_reason"] == "interpreter_unavailable"
    assert record["selector_eligible_count"] >= record["selector_final_count"]
    assert record["selector_error_code"] is None
    assert record["candidate_selection_status"] is None
    assert record["formulator_used"] is False
    assert record["formulator_fallback_used"] is False
    assert record["formulator_error_code"] is None
    assert record["llm_budget_status"] == "within_budget"
    assert record["data_release_id"].startswith("curation-")
    assert record["software_version"]
    assert record["timestamp"].endswith("Z")
    assert len(_records(settings.interaction_log_path)) == 1  # type: ignore[arg-type]


def test_speech_mode_stores_processed_transcription_without_request_metadata(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    secret = "api-key-must-not-appear"
    response = TestClient(create_app(settings)).post(
        "/api/query",
        headers={"Authorization": f"Bearer {secret}", "Cookie": "sid=private"},
        json={
            "query": "  Wo   bekomme ich Essen?  ",
            "language": "de",
            "input_mode": "speech",
            "system_prompt": "must-not-appear",
            "provider_response": "must-not-appear",
        },
    )

    assert response.status_code == 200
    raw = settings.interaction_log_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
    record = json.loads(raw)
    assert record["input_mode"] == "speech"
    assert record["user_query"] == "[redacted_safety_input]"
    assert secret not in raw
    assert "sid=private" not in raw
    assert "system_prompt" not in raw
    assert "provider_response" not in raw


def test_llm_formulator_path_stores_visible_answer_and_sources(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    # Eingefroren auf Montag 10:00, da die Food-Selektion ein geöffnetes
    # Angebot voraussetzt; ohne feste Uhr hängt der Testerfolg von der realen
    # Tageszeit ab (WP9C).
    app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))

    class FormulatorProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.FOOD)

        def context_fits(self, evidence) -> bool:
            return True

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[0].offer_id],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            return ProviderAnswer(
                "Final sichtbare Formulatorantwort.",
                [evidence.selected_offers[0].offer_id],
                sentence_count=1,
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FormulatorProvider()
    response = TestClient(app).post("/api/query", json={"query": "Wo gibt es Essen?"})
    record = _records(app.state.interaction_writer.path)[0]

    assert response.json()["answer"] == "Final sichtbare Formulatorantwort."
    assert record["assistant_answer"] == response.json()["answer"]
    assert record["route"] == "llm_formulation"
    assert record["source_ids"]
    assert record["selector_used"] is True
    assert record["selection_source"] == "llm_selector"
    assert record["selector_final_count"] == 1
    assert record["answer_type"] == "grounded_result"
    assert record["formulator_used"] is True
    assert record["formulator_fallback_used"] is False
    assert record["formulator_error_code"] is None
    assert record["formulator_sentence_count"] == 1
    assert record["formulator_offer_count"] == 1
    assert record["formulator_language"] == "de"
    assert record["llm_budget_status"] == "within_budget"
    assert "candidates" not in record
    assert "prompt" not in record
    assert "evidence" not in record
    assert "fact_ids" not in record


def test_provider_failure_stores_controlled_fallback_and_logs_event(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))
    sensitive_query = "Wo bekomme ich private fallback Mahlzeiten?"

    class FailedProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            raise InterpreterError("interpreter_http_error")

        def context_fits(self, offers) -> bool:
            return False

    app.state.service.blablador = FailedProvider()
    with caplog.at_level(logging.INFO):
        response = TestClient(app).post("/api/query", json={"query": sensitive_query})
    record = _records(app.state.interaction_writer.path)[0]
    app_logs = "\n".join(item.getMessage() for item in caplog.records if item.name.startswith("app."))

    assert response.status_code == 200
    assert record["assistant_answer"] == response.json()["answer"]
    assert record["fallback_used"] is True
    assert record["route"] == "interpreter_error"
    assert record["interpreter_error_code"] == "interpreter_http_error"
    assert record["selector_bypass_reason"] == "interpreter_unavailable"
    assert record["source_ids"] == []
    assert "query.interpreter.failed" in app_logs
    assert "query.fallback.used" in app_logs
    assert "request.completed" in app_logs
    assert sensitive_query not in app_logs
    assert response.json()["answer"] not in app_logs


def test_selector_failure_logging_is_redacted_and_skips_formulator(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))

    class FailedSelectorProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.MEDICAL)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            raise SelectorError("selector_invalid_id")

        def context_fits(self, offers) -> bool:
            return True

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            raise AssertionError("same provider must be skipped after selector failure")

    app.state.service.blablador = FailedSelectorProvider()
    response = TestClient(app).post("/api/query", json={"query": "medizinische Hilfe"})
    record = _records(app.state.interaction_writer.path)[0]
    raw = app.state.interaction_writer.path.read_text(encoding="utf-8")

    assert response.json()["provider"] == "template"
    assert record["selection_source"] == "deterministic_selector_fallback"
    assert record["selector_fallback_used"] is True
    assert record["selector_error_code"] == "selector_invalid_id"
    assert "candidates" not in record
    assert "prompt" not in raw


def test_acute_risk_stores_only_controlled_visible_answer(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))

    class RiskProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(risk=AcuteRiskStatus.DETECTED)

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            raise AssertionError("Formulator must not run")

    app.state.service.blablador = RiskProvider()
    response = TestClient(app).post(
        "/api/query",
        json={"query": "Ich bin jetzt akut in Gefahr.", "language": "de"},
    )
    record = _records(app.state.interaction_writer.path)[0]

    assert response.json()["answer"] == safety_text(Language.DE, SafetyTextKind.DETECTED)
    assert record["assistant_answer"] == safety_text(Language.DE, SafetyTextKind.DETECTED)
    assert record["acute_risk_detected"] is True
    assert record["route"] == "acute_risk"
    assert record["source_ids"] == []
    assert record["candidate_result_count"] == 0


def test_no_results_path_stores_final_response(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    response = TestClient(app).post("/api/query", json={"query": "Quantenphysik"})
    record = _records(app.state.interaction_writer.path)[0]

    assert record["assistant_answer"] == response.json()["answer"]
    assert record["route"] == "interpreter_error"
    assert record["source_ids"] == []


def test_disabled_interaction_logging_creates_no_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path, interaction_logging_enabled=False)
    response = TestClient(create_app(settings)).post("/api/query", json={"query": "Essen"})

    assert response.status_code == 200
    assert not settings.interaction_log_path.exists()  # type: ignore[union-attr]


def test_write_failure_is_redacted_and_does_not_change_response(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("block", encoding="utf-8")
    settings = _settings(tmp_path, interaction_log_path=blocking_file / "interactions.jsonl")
    query = "sensitive write failure question"

    with caplog.at_level(logging.ERROR):
        response = TestClient(create_app(settings)).post("/api/query", json={"query": query})

    assert response.status_code == 200
    assert "interaction.write.failed" in caplog.text
    assert query not in caplog.text
    assert response.json()["answer"] not in caplog.text


def test_parallel_writes_keep_one_valid_json_record_per_line(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "interactions.jsonl"
    writer = InteractionWriter(path, enabled=True)

    def write(index: int) -> bool:
        return writer.write(
            InteractionRecord(
                session_id=f"session-{index}",
                language=Language.DE,
                input_mode="text",
                user_query=f"query-{index}",
                assistant_answer=f"answer-{index}",
                route="test",
            )
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert all(executor.map(write, range(40)))

    records = _records(path)
    assert len(records) == 40
    assert {record["session_id"] for record in records} == {f"session-{index}" for index in range(40)}


def test_stt_and_tts_success_and_failure_events_are_visible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings(tmp_path))

    async def transcribe_ok(self, audio: bytes, *, content_type: str, language: Language) -> str:
        return "Transkription"

    async def synthesize_ok(self, text: str, *, language: Language) -> bytes:
        return b"audio"

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe_ok)
    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize_ok)
    service = app.state.service
    session = service.sessions.resolve(None, Language.DE, service.kb.runtime_kb_fingerprint or "")
    session = service.sessions.add_turn(session, question="test", answer="Antwort")
    with caplog.at_level(logging.INFO):
        client = TestClient(app)
        assert client.post(
            "/api/speech/transcribe?language=de",
            content=b"audio",
            headers={"Content-Type": "audio/webm"},
        ).status_code == 200
        assert client.post(
            "/api/speech/synthesize",
            json={"text": "Antwort", "language": "de", "session_id": session.session_id},
        ).status_code == 200
    assert "stt.completed" in caplog.text
    assert "tts.completed" in caplog.text

    async def transcribe_failed(*args, **kwargs) -> str:
        raise SpeechTranscriptionError("secret provider response")

    async def synthesize_failed(*args, **kwargs) -> bytes:
        raise SpeechSynthesisError("secret provider response")

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe_failed)
    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize_failed)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert client.post(
            "/api/speech/transcribe?language=de",
            content=b"audio",
            headers={"Content-Type": "audio/webm"},
        ).status_code == 503
        assert client.post(
            "/api/speech/synthesize",
            json={"text": "Antwort", "language": "de", "session_id": session.session_id},
        ).status_code == 503
    assert "stt.failed" in caplog.text
    assert "tts.failed" in caplog.text
    assert "secret provider response" not in caplog.text


def test_session_read_and_write_failures_are_redacted(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    invalid_json = tmp_path / "sessions.json"
    invalid_json.write_text("private-session-content", encoding="utf-8")
    store = SessionStore(invalid_json)
    with caplog.at_level(logging.WARNING):
        assert store.get("session-id") is None
    assert "session.corrupt_file.detected" in caplog.text
    assert "private-session-content" not in caplog.text

    unwritable_target = tmp_path / "session-directory"
    unwritable_target.mkdir()
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        session = SessionStore(unwritable_target).create(Language.DE, "kb-v1")
    assert session.session_id
    assert "session.write.failed" in caplog.text


def test_frontend_marks_recognized_and_transcribed_queries_as_speech() -> None:
    source = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'input_mode: state.queryInputMode' in source
    assert source.count('state.queryInputMode = "speech";') == 2
    assert 'state.queryInputMode = "text";' in source
