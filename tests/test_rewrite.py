from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from app.kb import KnowledgeBase
from app.models import KnowledgeAnswer, Language
from app.providers.rewrite import OllamaRewriteProvider


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_ollama_provider_uses_retrieved_pages_only(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict) -> _FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            return _FakeResponse(
                {
                    "message": {
                        "content": json_module.dumps(
                            {
                                "answer_text": "Die Leipziger Oase ist montags bis freitags von 08:00 bis 16:00 Uhr geöffnet.",
                                "status": "ok",
                                "retrieved_page_ids": ["leipziger-oase"],
                            }
                        )
                    }
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
        system_prompt_path=Path(__file__).resolve().parents[1] / "data" / "prompts" / "system_prompt.md",
    )

    answer = asyncio.run(provider.answer("oeffnungszeiten oase", Language.DE, kb))

    prompt = captured["payload"]["messages"][1]["content"]  # type: ignore[index]
    assert "PAGE_ID: leipziger-oase" in prompt
    assert "PAGE_ID: drk-kurse" not in prompt
    assert answer.retrieved_page_ids[0] == "leipziger-oase"


def test_ollama_provider_prefers_dominant_top_hit_context(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict) -> _FakeResponse:
            captured["payload"] = json
            return _FakeResponse(
                {
                    "message": {
                        "content": json_module.dumps(
                            {
                                "answer_text": "Die Tafel Leipzig hat mehrere Ausgabestellen.",
                                "status": "ok",
                                "retrieved_page_ids": ["tafel-leipzig"],
                            }
                        )
                    }
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
        system_prompt_path=Path(__file__).resolve().parents[1] / "data" / "prompts" / "system_prompt.md",
    )

    asyncio.run(provider.answer("wo kann ich etwas essen", Language.DE, kb))

    prompt = captured["payload"]["messages"][1]["content"]  # type: ignore[index]
    assert "PAGE_ID: tafel-leipzig" in prompt
    assert "PAGE_ID: heilsarmee-begegnungszentrum" not in prompt


def test_ollama_provider_normalizes_inconsistent_model_status(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict) -> _FakeResponse:
            return _FakeResponse(
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "answer_text": "Die Tafel Leipzig hat mehrere Ausgabestellen.",
                                "status": "clarification_needed",
                            }
                        )
                    }
                }
            )

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
    )

    answer = asyncio.run(provider.answer("wo kann ich etwas essen", Language.DE, kb))

    assert isinstance(answer, KnowledgeAnswer)
    assert answer.status == "ok"
    assert answer.clarification_needed is False
    assert "Tafel Leipzig" in answer.answer_text


def test_ollama_provider_bypasses_llm_for_crisis_queries(monkeypatch) -> None:
    class _FailingAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("Ollama client should not be created for crisis queries")

    monkeypatch.setattr(httpx, "AsyncClient", _FailingAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
    )

    answer = asyncio.run(provider.answer("I want to kill myself", Language.EN, kb))

    assert answer.status == "crisis"
    assert answer.crisis_mode is True
    assert "112" in answer.answer_text


def test_ollama_provider_falls_back_when_model_invents_sensitive_detail(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict) -> _FakeResponse:
            return _FakeResponse(
                {
                    "message": {
                        "content": json_module.dumps(
                            {
                                "answer_text": "Leipziger Oase ist in der Marsstrasse 99, 04000 Leipzig.",
                                "status": "ok",
                                "retrieved_page_ids": ["leipziger-oase"],
                            }
                        )
                    }
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
        system_prompt_path=Path(__file__).resolve().parents[1] / "data" / "prompts" / "system_prompt.md",
    )

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_answer_source == "validator_fallback"
    assert provider.last_validation_error is not None
    assert "Marsstrasse" not in answer.answer_text
    assert "04000" not in answer.answer_text
    assert "Leipziger Oase" in answer.answer_text
    assert "Nuernberger Strasse 31" in answer.answer_text or "NÃ¼rnberger StraÃŸe 31" in answer.answer_text


def test_ollama_provider_records_prompt_and_evidence_hashes(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict) -> _FakeResponse:
            return _FakeResponse(
                {
                    "message": {
                        "content": json_module.dumps(
                            {
                                "answer_text": "Leipziger Oase ist in Nuernberger Strasse 31, 04103 Leipzig.",
                                "status": "ok",
                                "retrieved_page_ids": ["leipziger-oase"],
                            }
                        )
                    }
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
        system_prompt_path=Path(__file__).resolve().parents[1] / "data" / "prompts" / "system_prompt.md",
    )

    asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_prompt_hash
    assert provider.last_system_prompt_hash
    assert provider.last_user_prompt_hash
    assert "PAGE_ID: leipziger-oase" in provider.last_evidence_context
