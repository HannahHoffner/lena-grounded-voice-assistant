from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Category, Language
from app.providers.llm import BlabladorProvider, ProviderAnswer, ProviderError, ProviderRoute
from app.service import ACUTE_RISK_RESPONSE
from app.speech import EMERGENCY_NUMBER_SPEECH, SpeechSynthesizer, normalize_tts_text


ROOT = Path(__file__).resolve().parents[1]


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
) -> None:
    app = create_app(_settings())

    class RiskProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            assert kwargs["query"] == query
            return ProviderRoute(None, [], False, False, acute_risk_detected=True)

        async def answer(self, **kwargs) -> ProviderAnswer:
            raise AssertionError("Der Formulator darf bei Akutgefahr nicht laufen")

    app.state.service.blablador = RiskProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": query, "language": language.value},
    ).json()

    assert body["answer"] == ACUTE_RISK_RESPONSE[language]
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
            {
                "intent": "unknown",
                "offer_ids": [],
                "needs_clarification": False,
                "out_of_scope": False,
                "acute_risk_detected": True,
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    route = asyncio.run(
        provider.route(
            query="I am in immediate danger.",
            language=Language.EN,
            category=None,
            offers=app.state.kb.offers,
        )
    )

    assert route.acute_risk_detected is True
    assert route.offer_ids == []
    assert route.intent is None


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
    called = {"answer": 0}

    class NormalProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            return ProviderRoute(Category.FOOD, [kwargs["offers"][0].id], False, False)

        async def answer(self, **kwargs) -> ProviderAnswer:
            called["answer"] += 1
            return ProviderAnswer("Die normale kontrollierte Testantwort.", [kwargs["offers"][0].id])

    app.state.service.blablador = NormalProvider()
    body = TestClient(app).post("/api/query", json={"query": query, "language": "de"}).json()

    assert called["answer"] == 1
    assert body["provider"] == "blablador"
    assert body["answer"] == "Die normale kontrollierte Testantwort."
    assert "112" not in body["answer"]


@pytest.mark.parametrize("invalid_value", [None, "true", 1])
def test_router_rejects_missing_or_non_boolean_risk_signal(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    invalid_value: object,
) -> None:
    app = create_app(_settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    sensitive_query = "vertrauliche Krisenaussage"

    async def response(_: dict) -> dict:
        route = {
            "intent": "unknown",
            "offer_ids": [],
            "needs_clarification": False,
            "out_of_scope": True,
        }
        if invalid_value is not None:
            route["acute_risk_detected"] = invalid_value
        return {"choices": [{"message": {"content": json.dumps(route)}}]}

    monkeypatch.setattr(provider, "_post", response)
    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError):
        asyncio.run(
            provider.route(
                query=sensitive_query,
                language=Language.DE,
                category=None,
                offers=app.state.kb.offers,
            )
        )

    assert "llm_route_response_invalid" in caplog.text
    assert sensitive_query not in caplog.text


def test_router_rejects_unparseable_response_without_logging_query(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(_settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    sensitive_query = "private acute statement"

    async def response(_: dict) -> dict:
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(provider, "_post", response)
    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError):
        asyncio.run(
            provider.route(
                query=sensitive_query,
                language=Language.EN,
                category=None,
                offers=app.state.kb.offers,
            )
        )

    assert "llm_route_response_invalid" in caplog.text
    assert sensitive_query not in caplog.text


def test_llm_failure_keeps_existing_fallback_without_inventing_risk() -> None:
    app = create_app(_settings())

    class FailedProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            raise ProviderError("test failure")

    app.state.service.blablador = FailedProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "A completely unrelated question", "language": "en"},
    ).json()

    assert body["provider"] == "template"
    assert "112" not in body["answer"]


def test_missing_localized_safety_text_uses_controlled_german_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(_settings())

    class RiskProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            return ProviderRoute(None, [], False, False, acute_risk_detected=True)

    monkeypatch.delitem(ACUTE_RISK_RESPONSE, Language.PL)
    app.state.service.blablador = RiskProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Pilne zagrożenie", "language": "pl"},
    ).json()

    assert body["answer"] == ACUTE_RISK_RESPONSE[Language.DE]
    assert "112" in body["answer"]


@pytest.mark.parametrize("language", list(Language))
def test_tts_normalizes_112_before_existing_synthesis_provider(
    monkeypatch: pytest.MonkeyPatch,
    language: Language,
) -> None:
    synthesizer = SpeechSynthesizer(_settings())
    captured: dict[str, str] = {}

    async def synthesize_edge(self, text: str, *, language: Language) -> bytes:
        captured["text"] = text
        return b"audio"

    monkeypatch.setattr(SpeechSynthesizer, "_synthesize_edge", synthesize_edge)
    result = asyncio.run(synthesizer.synthesize("Bitte 112 anrufen.", language=language))

    assert result == b"audio"
    assert captured["text"] == f"Bitte {EMERGENCY_NUMBER_SPEECH[language]} anrufen."
    assert "112" not in normalize_tts_text(ACUTE_RISK_RESPONSE[language], language)
