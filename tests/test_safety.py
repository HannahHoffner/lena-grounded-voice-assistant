from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.interpreter import AcuteRiskStatus, Need, QueryInterpretation, ScopeStatus
from app.main import create_app
from app.models import Language
from app.providers.llm import BlabladorProvider, InterpreterError, ProviderAnswer
from app.application_texts import application_text
from app.safety import SafetyTextKind, safety_text
from app.speech import EMERGENCY_NUMBER_SPEECH, SpeechSynthesizer, normalize_tts_text


ROOT = Path(__file__).resolve().parents[1]


def _interpretation(
    need: Need = Need.UNKNOWN,
    *,
    scope: ScopeStatus = ScopeStatus.IN_SCOPE,
    risk: AcuteRiskStatus = AcuteRiskStatus.NOT_DETECTED,
) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
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


def _settings(provider: str = "template") -> Settings:
    return Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider=provider,
        blablador_base_url="https://example.invalid/v1" if provider == "blablador" else None,
        blablador_api_key="test-token" if provider == "blablador" else None,
        blablador_model="test-model" if provider == "blablador" else None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50000,
        interaction_logging_enabled=False,
    )


@pytest.mark.parametrize(
    ("language", "query"),
    [
        (Language.DE, "Ich will mich jetzt umbringen."),
        (Language.EN, "I am going to attack someone right now."),
        (Language.PL, "Mam teraz poważne problemy z oddychaniem."),
        (Language.RO, "Vreau să mă rănesc acum."),
        (Language.RU, "Я сейчас причиню кому-то вред."),
    ],
)
def test_acute_risk_signal_interrupts_query_before_answer_and_retrieval(
    language: Language,
    query: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prüft den vom Interpreter signalisierten Fall isoliert vom separat getesteten Preflight.

    Einige der hier verwendeten realistischen Formulierungen treffen auch den
    engen Preflight-Regex und würden dort bereits direkt stoppen. Der Preflight
    wird deshalb für diesen Test deaktiviert und separat in
    test_safety_policy.py geprüft.
    """
    monkeypatch.setattr("app.service.preflight_detects_immediate_danger", lambda _query: False)
    app = create_app(_settings())

    class RiskProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            assert kwargs["query"] == query
            return _interpretation(risk=AcuteRiskStatus.DETECTED)

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            raise AssertionError("Der Formulator darf bei Akutgefahr nicht laufen")

    app.state.service.blablador = RiskProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": query, "language": language.value},
    ).json()

    assert body["answer"] == safety_text(language, SafetyTextKind.DETECTED)
    assert body["provider"] == "template"
    assert body["status"] == "no_results"
    assert body["cards"] == []
    assert body["map_data"] is None
    assert "112" in body["answer"]


def test_provider_validates_true_acute_risk_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(_settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador

    async def response(_: dict) -> dict:
        content = json.dumps(
            _interpretation(risk=AcuteRiskStatus.DETECTED).model_dump(mode="json")
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    interpretation = asyncio.run(
        provider.interpret_query(
            query="I am in immediate danger.",
            language=Language.EN,
            category=None,
            aliases=app.state.service.interpreter_aliases,
        )
    )

    assert interpretation.acute_risk_status == AcuteRiskStatus.DETECTED


@pytest.mark.parametrize(
    "query",
    [
        "Wo bekomme ich heute etwas zu essen?",
        "Diese Prüfung bringt mich um.",
        "Im Geschichtsunterricht sprachen wir über einen Angriff von 1813.",
        "Vor vielen Jahren hatte ich einen medizinischen Notfall, jetzt geht es mir gut.",
    ],
)
def test_false_risk_signal_keeps_normal_llm_path(query: str) -> None:
    app = create_app(_settings())
    # Fest verankerte Werktags-Uhrzeit, damit die Kandidatenauswahl unabhängig
    # von der tatsächlichen Uhrzeit des Testlaufs ein offenes Essensangebot
    # findet (Standzeiten-/Öffnungszeitenprüfung ist sonst reale Uhrzeit-
    # abhängig und macht den Test sonst unabhängig von dieser Änderung flaky).
    app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    called = {"answer": 0}

    class NormalProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.FOOD)

        def context_fits(self, evidence) -> bool:
            return True

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            called["answer"] += 1
            evidence = kwargs["evidence"]
            return ProviderAnswer(
                "Die normale kontrollierte Testantwort.",
                [evidence.selected_offers[0].offer_id],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = NormalProvider()
    body = TestClient(app).post("/api/query", json={"query": query, "language": "de"}).json()

    assert called["answer"] == 1
    assert body["provider"] == "blablador"
    assert body["answer"] == "Die normale kontrollierte Testantwort."
    assert "112" not in body["answer"]


@pytest.mark.parametrize("invalid_value", [None, "true", 1])
def test_interpreter_rejects_missing_or_invalid_risk_signal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    invalid_value: object,
) -> None:
    app = create_app(_settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    sensitive_query = "vertrauliche Krisenaussage"

    async def response(_: dict) -> dict:
        route = _interpretation(scope=ScopeStatus.OUT_OF_SCOPE).model_dump(mode="json")
        route.pop("acute_risk_status")
        if invalid_value is not None:
            route["acute_risk_status"] = invalid_value
        return {"choices": [{"message": {"content": json.dumps(route)}}]}

    monkeypatch.setattr(provider, "_post", response)
    with caplog.at_level(logging.WARNING), pytest.raises(InterpreterError):
        asyncio.run(
            provider.interpret_query(
                query=sensitive_query,
                language=Language.DE,
                category=None,
                aliases=app.state.service.interpreter_aliases,
            )
        )

    assert "query.interpreter.schema_invalid" in caplog.text
    assert sensitive_query not in caplog.text


def test_interpreter_rejects_unparseable_response_without_logging_query(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    sensitive_query = "private acute statement"

    async def response(_: dict) -> dict:
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(provider, "_post", response)
    with caplog.at_level(logging.WARNING), pytest.raises(InterpreterError):
        asyncio.run(
            provider.interpret_query(
                query=sensitive_query,
                language=Language.EN,
                category=None,
                aliases=app.state.service.interpreter_aliases,
            )
        )

    assert sensitive_query not in caplog.text


def test_llm_failure_uses_conditional_safety_fallback_without_inventing_detected_risk() -> None:
    app = create_app(_settings())

    class FailedProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            raise InterpreterError("interpreter_http_error")

    app.state.service.blablador = FailedProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "A completely unrelated question", "language": "en"},
    ).json()

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises; der bedingte 112-Hinweis
    # bleibt Teil des Texts.
    offer = next(offer for offer in app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    phone = ", ".join(offer.phone_numbers) or "—"
    times = "; ".join(offer.opening_hours_raw or offer.standzeiten_raw) or "—"
    assert body["provider"] == "template"
    from app.hilfebus import contact_hint
    assert body["answer"] == safety_text(Language.EN, SafetyTextKind.TECHNICAL) + " " + contact_hint(offer, Language.EN)
    assert body["answer"].count("112") == 1
    assert body["answer_type"] == "technical_fallback"
    assert [card["id"] for card in body["cards"]] == [offer.id]


def test_missing_localized_safety_text_uses_controlled_german_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(_settings())

    class RiskProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(risk=AcuteRiskStatus.DETECTED)

    real_application_text = application_text

    def missing_polish(language: Language, resource_id: str, **values: str) -> str:
        if language == Language.PL and resource_id == "safety.detected":
            raise RuntimeError("application_text_missing")
        return real_application_text(language, resource_id, **values)

    monkeypatch.setattr("app.safety.application_text", missing_polish)
    app.state.service.blablador = RiskProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Pilne zagrożenie", "language": "pl"},
    ).json()

    assert body["answer"] == safety_text(Language.DE, SafetyTextKind.DETECTED)
    assert "112" in body["answer"]


@pytest.mark.parametrize("language", list(Language))
def test_tts_normalizes_112_before_existing_synthesis_provider(
    monkeypatch: pytest.MonkeyPatch,
    language: Language,
) -> None:
    synthesizer = SpeechSynthesizer(replace(_settings(), speech_synthesis_provider="edge"))
    captured: dict[str, str] = {}

    async def synthesize_edge(self, text: str, *, language: Language) -> bytes:
        captured["text"] = text
        return b"audio"

    monkeypatch.setattr(SpeechSynthesizer, "_synthesize_edge", synthesize_edge)
    result = asyncio.run(synthesizer.synthesize("Bitte 112 anrufen.", language=language))

    assert result == b"audio"
    assert captured["text"] == f"Bitte {EMERGENCY_NUMBER_SPEECH[language]} anrufen."
    assert "112" not in normalize_tts_text(safety_text(language, SafetyTextKind.DETECTED), language)
