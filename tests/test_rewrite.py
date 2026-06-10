from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.kb import KnowledgeBase
from app.maps import MapBuilder
from app.config import load_settings
from app.models import KnowledgeAnswer, Language
from app.providers.rewrite import OpenAICompatibleRewriteProvider, OllamaRewriteProvider, _clean_answer_text, create_rewrite_provider
from app.temporal import build_temporal_context


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(self.status_code, json=self._payload)
            raise httpx.HTTPStatusError("mock status error", request=httpx.Request("POST", "http://test"), response=response)
        return None

    def json(self) -> dict:
        return self._payload


def _write_test_kb(tmp_path: Path, pages: list[dict], markdown: dict[str, str] | None = None) -> KnowledgeBase:
    published = tmp_path / "published"
    index = published / "index"
    pages_root = published / "pages"
    index.mkdir(parents=True)
    pages_root.mkdir(parents=True)
    (index / "manifest.json").write_text(
        json.dumps(
            {
                "kb_version": "test",
                "generated_at": "2026-06-07T00:00:00+00:00",
                "source_count": 1,
                "page_count": len(pages),
            }
        ),
        encoding="utf-8",
    )
    normalized_pages = []
    aliases: dict[str, list[str]] = {}
    for page in pages:
        item = {
            "page_id": page["page_id"],
            "title": page["title"],
            "language": "de",
            "source_url": "https://example.test/source",
            "last_updated": "2026-06-07",
            "summary": page.get("summary", page.get("description", page["title"])),
            "file_path": f"{page['page_id']}.md",
            "category": page.get("category", "water"),
            "service_type": page.get("service_type", "general"),
            "description": page.get("description", ""),
            "address": page.get("address"),
            "latitude": page.get("latitude"),
            "longitude": page.get("longitude"),
            "geo_status": page.get("geo_status"),
            "tags": page.get("tags", []),
            "aliases": page.get("aliases", []),
        }
        normalized_pages.append(item)
        for alias in item["aliases"] + [item["title"]]:
            aliases.setdefault(alias, []).append(item["page_id"])
        (pages_root / item["file_path"]).write_text((markdown or {}).get(item["page_id"], item["summary"]), encoding="utf-8")
    (index / "pages.json").write_text(json.dumps(normalized_pages), encoding="utf-8")
    (index / "aliases.json").write_text(json.dumps(aliases), encoding="utf-8")
    return KnowledgeBase(published)


def test_clean_answer_text_does_not_truncate_long_user_answer() -> None:
    text = (
        "Für Frauen gibt es das AWW Übernachtungshaus für wohnungslose Frauen in Leipzig. "
        "Die Adresse ist Scharnhorststraße 27, 04275 Leipzig. "
        "Die Telefonnummer ist 0341 5852413. "
        "Geöffnet ist Montag bis Freitag von 16 Uhr bis 8 Uhr. "
        "Samstags, sonntags und an Feiertagen ist es ganztägig geöffnet. "
        "Dies ist eine Notunterkunft für Frauen."
    )

    cleaned = _clean_answer_text(text)

    assert cleaned == text
    assert not cleaned.endswith("...")


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


@pytest.mark.parametrize(
    ("transcript", "language"),
    [
        ("Ich will mir etwas antun.", Language.DE),
        ("Ich will jemanden verletzen.", Language.DE),
        ("Jemand greift mich am Bahnhof an.", Language.DE),
        ("Ich habe eine Ueberdosis genommen.", Language.DE),
        ("Die Person ist bewusstlos und hat eine schwere Verletzung.", Language.DE),
        ("I want to hurt myself.", Language.EN),
        ("I will hurt someone.", Language.EN),
        ("Someone is attacking me at the station.", Language.EN),
        ("I cannot breathe and have chest pain.", Language.EN),
    ],
)
def test_template_provider_detects_crisis_patterns(transcript: str, language: Language) -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer(transcript, language, kb))

    assert answer.status == "crisis"
    assert answer.crisis_mode is True
    assert "112" in answer.answer_text
    assert "110" in answer.answer_text


def test_crisis_does_not_call_openai_compatible_provider(monkeypatch) -> None:
    class _FailingAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("external LLM client should not be created for crisis queries")

    monkeypatch.setattr(httpx, "AsyncClient", _FailingAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")

    answer = asyncio.run(provider.answer("Ich bringe mich um.", Language.DE, kb))

    assert answer.status == "crisis"
    assert provider.last_answer_source == "guardrail"


def test_template_fallbacks_do_not_expose_internal_terms() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    unknown = asyncio.run(provider.answer("qwertz asdf yxv", Language.DE, kb))
    out_of_scope = asyncio.run(provider.answer("Was ist die Hauptstadt von Frankreich?", Language.DE, kb))

    assert unknown.status == "unknown"
    assert out_of_scope.status == "out_of_scope"
    for answer in (unknown, out_of_scope):
        lowered = answer.answer_text.casefold()
        assert "wissensbasis" not in lowered
        assert "knowledge base" not in lowered
        assert "retrieval" not in lowered
        assert "provider" not in lowered


def test_water_query_with_only_generic_app_page_returns_plain_limitation(tmp_path: Path) -> None:
    kb = _write_test_kb(
        tmp_path,
        [
            {
                "page_id": "trinkwasser-app",
                "title": "Leipziger Trinkwasserbrunnen",
                "category": "water",
                "service_type": "food_distribution",
                "summary": "Laden Sie die App herunter. Die App zeigt den kuerzesten Weg zum Trinkwasserbrunnen.",
                "aliases": ["trinkwasser", "trinkwasserbrunnen", "wasser"],
                "tags": ["wasser", "trinkwasser"],
            }
        ],
    )
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("Wo finde ich Trinkwasser?", Language.DE, kb))

    assert answer.status == "unknown"
    assert "keinen sicheren konkreten Trinkwasser-Standort" in answer.answer_text
    assert "App" not in answer.answer_text
    assert "Website" not in answer.answer_text
    assert "Google Maps" not in answer.answer_text
    assert "online suchen" not in answer.answer_text


def test_water_query_lists_concrete_locations_and_map_targets(tmp_path: Path) -> None:
    kb = _write_test_kb(
        tmp_path,
        [
            {
                "page_id": "trinkwasser-app",
                "title": "Leipziger Trinkwasserbrunnen",
                "category": "water",
                "service_type": "food_distribution",
                "summary": "Die App zeigt den kuerzesten Weg.",
                "aliases": ["trinkwasser", "trinkwasserbrunnen", "wasser"],
                "tags": ["wasser", "trinkwasser"],
            },
            {
                "page_id": "wasser-augustusplatz",
                "title": "Trinkwasserbrunnen Augustusplatz",
                "category": "water",
                "service_type": "food_distribution",
                "address": "Augustusplatz, 04109 Leipzig",
                "latitude": 51.3397,
                "longitude": 12.3819,
                "geo_status": "ready",
                "aliases": ["trinkwasser", "trinkwasserbrunnen", "wasser", "augustusplatz"],
                "tags": ["wasser", "trinkwasser"],
            },
            {
                "page_id": "wasser-markt",
                "title": "Trinkwasserbrunnen Markt",
                "category": "water",
                "service_type": "food_distribution",
                "address": "Markt, 04109 Leipzig",
                "latitude": 51.3402,
                "longitude": 12.3758,
                "geo_status": "ready",
                "aliases": ["trinkwasser", "trinkwasserbrunnen", "wasser", "markt"],
                "tags": ["wasser", "trinkwasser"],
            },
        ],
    )
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("Wo finde ich Trinkwasser?", Language.DE, kb))
    map_data = MapBuilder(load_settings()).build_for_answer(answer, kb)

    assert answer.status == "ok"
    assert "Trinkwasserbrunnen Augustusplatz" in answer.answer_text
    assert "Trinkwasserbrunnen Markt" in answer.answer_text
    assert "Leipziger Trinkwasserbrunnen" not in answer.answer_text
    assert "App" not in answer.answer_text
    assert answer.retrieved_page_ids[:2] == ["wasser-augustusplatz", "wasser-markt"]
    assert map_data is not None
    assert {item.page_id for item in map_data.destinations} == {"wasser-augustusplatz", "wasser-markt"}


def test_english_water_query_uses_plain_limitation_without_redirect(tmp_path: Path) -> None:
    kb = _write_test_kb(
        tmp_path,
        [
            {
                "page_id": "water-app",
                "title": "Leipzig drinking water fountains",
                "category": "water",
                "service_type": "food_distribution",
                "summary": "Download the app. The app will show the nearest water fountain.",
                "aliases": ["water", "drinking water", "water fountain"],
                "tags": ["water", "drinking"],
            }
        ],
    )
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("Where can I get drinking water?", Language.EN, kb))

    assert answer.status == "unknown"
    assert "safe concrete drinking-water location" in answer.answer_text
    assert "download the app" not in answer.answer_text.casefold()
    assert "check the website" not in answer.answer_text.casefold()
    assert "search online" not in answer.answer_text.casefold()


def test_location_validator_replaces_forbidden_llm_redirect(tmp_path: Path, monkeypatch) -> None:
    kb = _write_test_kb(
        tmp_path,
        [
            {
                "page_id": "wasser-markt",
                "title": "Trinkwasserbrunnen Markt",
                "category": "water",
                "service_type": "food_distribution",
                "address": "Markt, 04109 Leipzig",
                "latitude": 51.3402,
                "longitude": 12.3758,
                "geo_status": "ready",
                "aliases": ["trinkwasser", "trinkwasserbrunnen", "wasser"],
                "tags": ["wasser", "trinkwasser"],
            }
        ],
    )

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
                                "answer_text": "Bitte laden Sie die App herunter. Die App zeigt den kuerzesten Weg.",
                                "status": "ok",
                            }
                        )
                    }
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    provider = OllamaRewriteProvider(
        base_url="http://127.0.0.1:11434",
        model="translategemma:4b",
    )
    calls = {"count": 0}

    def location_required_after_generation(transcript: str, language: Language) -> bool:
        calls["count"] += 1
        return calls["count"] >= 2

    monkeypatch.setattr("app.providers.rewrite._is_location_required_query", location_required_after_generation)

    answer = asyncio.run(provider.answer("Trinkwasser Markt", Language.DE, kb))

    assert answer.status == "ok"
    assert "Trinkwasserbrunnen Markt" in answer.answer_text
    assert "App" not in answer.answer_text
    assert provider.last_answer_source == "validator_fallback"


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


def test_create_rewrite_provider_initializes_blablador() -> None:
    provider = create_rewrite_provider(
        "blablador",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
        llm_api_key="token",
        llm_model="alias-large",
    )

    assert provider.name == "blablador"
    assert provider.model_name == "alias-large"
    assert provider.uses_llm is True


def test_openai_provider_falls_back_without_api_key() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(
        base_url="https://example.test/v1",
        api_key=None,
        model="alias-large",
    )

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_answer_source == "template_fallback"
    assert provider.last_provider_error == "missing_api_key"
    assert answer.status == "ok"
    assert "Leipziger Oase" in answer.answer_text


def test_openai_provider_uses_retrieved_pages_only(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json_module.dumps(
                                    {
                                        "answer_text": "Leipziger Oase ist in Nuernberger Strasse 31, 04103 Leipzig.",
                                        "status": "ok",
                                    }
                                )
                            }
                        }
                    ]
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(
        base_url="https://api.example.test/v1/",
        api_key="secret-token-for-test",
        model="alias-large",
    )

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    prompt = captured["payload"]["messages"][1]["content"]  # type: ignore[index]
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert "PAGE_ID: leipziger-oase" in prompt
    assert "PAGE_ID: drk-kurse" not in prompt
    assert captured["headers"] == {"Authorization": "Bearer secret-token-for-test"}
    assert answer.retrieved_page_ids[0] == "leipziger-oase"
    assert provider.last_answer_source == "llm"


def test_openai_provider_uses_template_guard_for_sleep_location(monkeypatch) -> None:
    class _FailingAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("LLM client should not be created for sleep-location guard")

    monkeypatch.setattr(httpx, "AsyncClient", _FailingAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(
        base_url="https://api.example.test/v1/",
        api_key="secret-token-for-test",
        model="alias-large",
    )

    answer = asyncio.run(provider.answer("wo kann ein Mann übernachten", Language.DE, kb))

    assert answer.status == "ok"
    assert provider.last_answer_source == "template_detail_guard"
    assert answer.retrieved_page_ids[0] == "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner"
    assert "Rückmarsdorfer Straße 5–7" in answer.answer_text
    assert "psychisch kranker" not in answer.answer_text


def test_openai_provider_falls_back_on_timeout(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_answer_source == "template_fallback"
    assert provider.last_provider_error == "timeout"
    assert "Leipziger Oase" in answer.answer_text


def test_openai_provider_falls_back_on_http_429_and_403(monkeypatch) -> None:
    statuses = [429, 403]

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            return _FakeResponse({"error": "nope"}, status_code=statuses.pop(0))

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")

    answer_429 = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))
    assert provider.last_provider_error == "http_429"
    assert "Leipziger Oase" in answer_429.answer_text

    answer_403 = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))
    assert provider.last_provider_error == "http_403"
    assert "Leipziger Oase" in answer_403.answer_text


def test_openai_provider_falls_back_on_invalid_json(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            return _FakeResponse({"choices": [{"message": {"content": "not json"}}]})

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_answer_source == "template_fallback"
    assert provider.last_provider_error == "invalid_json"
    assert "Leipziger Oase" in answer.answer_text


def test_openai_provider_falls_back_on_schema_mismatch(monkeypatch) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            return _FakeResponse({"choices": [{"message": {"content": json_module.dumps({"status": "ok"})}}]})

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")

    answer = asyncio.run(provider.answer("wo ist leipziger oase", Language.DE, kb))

    assert provider.last_answer_source == "template_fallback"
    assert provider.last_provider_error == "schema_mismatch"
    assert "Leipziger Oase" in answer.answer_text


def test_template_english_answer_does_not_copy_german_description() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("What is Bahnhofsmission Leipzig?", Language.EN, kb))

    assert answer.status in {"ok", "weak_match"}
    assert "Bahnhofsmission Leipzig" in answer.answer_text
    assert "Hilfe, Betreuung, Begegnung" not in answer.answer_text
    assert "Vermittlung am Bahnhof" not in answer.answer_text
    assert "This is a station support service" in answer.answer_text


def test_template_german_answer_may_use_german_description() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("Bahnhofsmission Leipzig", Language.DE, kb))

    assert answer.status == "ok"
    assert "Hilfe, Betreuung" in answer.answer_text


def test_template_today_unknown_hours_does_not_claim_open_today() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )
    temporal_context = build_temporal_context(datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc))

    answer = asyncio.run(provider.answer("Hat die Tafel Lindenau heute offen?", Language.DE, kb, temporal_context=temporal_context))

    assert "Für heute" in answer.answer_text
    assert "keine sicheren Öffnungszeiten" in answer.answer_text
    assert "stehen diese Öffnungszeiten" not in answer.answer_text


def test_template_generic_sleep_query_asks_target_group() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("wo kann ich übernachten", Language.DE, kb))

    assert answer.status == "clarification_needed"
    assert answer.clarification_needed is True
    assert "Männer" in answer.answer_text
    assert "Frauen" in answer.answer_text
    assert "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner" in answer.retrieved_page_ids


def test_template_mens_sleep_query_prefers_general_mens_shelter() -> None:
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = create_rewrite_provider(
        "template",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="local-model",
        ollama_timeout_seconds=5,
        minimum_match_threshold=0.08,
        weak_match_threshold=0.18,
        clarification_gap_threshold=0.03,
    )

    answer = asyncio.run(provider.answer("wo kann ein Mann übernachten", Language.DE, kb))

    assert answer.status == "ok"
    assert answer.retrieved_page_ids[0] == "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner"
    assert "Rückmarsdorfer Straße 5–7" in answer.answer_text
    assert "psychisch kranker" not in answer.answer_text


def test_openai_provider_prompt_includes_temporal_context_and_requested_language(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
            captured["payload"] = json
            return _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json_module.dumps(
                                    {
                                        "answer_text": "Leipziger Oase is at Nuernberger Strasse 31, 04103 Leipzig.",
                                        "status": "ok",
                                    }
                                )
                            }
                        }
                    ]
                }
            )

    json_module = json
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    kb = KnowledgeBase(Path(__file__).resolve().parents[1] / "data" / "published")
    provider = OpenAICompatibleRewriteProvider(base_url="https://api.example.test/v1", api_key="token")
    temporal_context = build_temporal_context(datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc))

    asyncio.run(provider.answer("Where is Leipziger Oase?", Language.EN, kb, temporal_context=temporal_context))

    prompt = captured["payload"]["messages"][1]["content"]  # type: ignore[index]
    assert "Temporal context computed by backend" in prompt
    assert "date_iso: 2026-06-06" in prompt
    assert "weekday: Saturday / Samstag" in prompt
    assert "Answer fully in English" in prompt
    assert "Translate German service descriptions into English" in prompt
    assert "Use simple language" in prompt
    assert "Forbidden answer_text words include" in prompt
    assert "Wissensbasis" in prompt
    assert "knowledge base" in prompt
