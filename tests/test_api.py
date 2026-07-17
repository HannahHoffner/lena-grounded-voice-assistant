from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import Category, ChatTurn, Language
from app.offer_roles import sleep_roles
from app.providers.llm import BlabladorProvider, ProviderAnswer, ProviderError, ProviderRoute
from app.speech import SpeechSynthesizer, SpeechTranscriber


ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "canonical" / "offers.json"


def settings(provider: str = "template", *, max_chars: int = 50000) -> Settings:
    return Settings(
        app_root=ROOT,
        kb_path=KB_PATH,
        rewrite_provider=provider,
        blablador_base_url="https://example.invalid/v1" if provider == "blablador" else None,
        blablador_api_key="test-token" if provider == "blablador" else None,
        blablador_model="test-model" if provider == "blablador" else None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=max_chars,
        speech_transcription_base_url="https://example.invalid/v1" if provider == "blablador" else None,
        speech_transcription_api_key="test-token" if provider == "blablador" else None,
        speech_transcription_model="whisper-large-v3" if provider == "blablador" else None,
        speech_synthesis_base_url="https://example.invalid/v1" if provider == "blablador" else None,
        speech_synthesis_api_key="test-token" if provider == "blablador" else None,
        speech_synthesis_model="gpt-4o-mini-tts" if provider == "blablador" else None,
        interaction_logging_enabled=False,
    )


def test_health_and_frontend_work() -> None:
    client = TestClient(create_app(settings()))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["kb_loaded"] is True
    assert health.json()["offer_count"] == 30
    assert health.json()["active_provider"] == "template"
    assert health.json()["speech"]["server_transcription_available"] is False
    assert health.json()["speech"]["server_synthesis_available"] is True
    assert client.get("/").status_code == 200


def test_speech_config_reports_server_speech_availability() -> None:
    template_client = TestClient(create_app(settings()))
    blablador_client = TestClient(create_app(settings("blablador")))

    template_config = template_client.get("/api/speech/config").json()
    blablador_config = blablador_client.get("/api/speech/config").json()

    assert template_config["server_transcription_available"] is False
    assert template_config["server_synthesis_available"] is True
    assert blablador_config["server_transcription_available"] is True
    assert blablador_config["server_synthesis_available"] is True


def test_speech_transcription_endpoint_uses_configured_transcriber(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))

    async def transcribe(self: SpeechTranscriber, audio: bytes, *, content_type: str, language: Language) -> str:
        assert audio == b"fake-audio"
        assert content_type == "audio/webm"
        assert language == Language.DE
        return "Ich brauche Essen"

    monkeypatch.setattr(SpeechTranscriber, "transcribe", transcribe)
    response = TestClient(app).post(
        "/api/speech/transcribe?language=de",
        content=b"fake-audio",
        headers={"Content-Type": "audio/webm"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Ich brauche Essen"}


def test_speech_synthesis_endpoint_uses_configured_synthesizer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))

    async def synthesize(self: SpeechSynthesizer, text: str, *, language: Language) -> bytes:
        assert text == "Ich beantworte Fragen."
        assert language == Language.DE
        return b"fake-mp3"

    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize)
    response = TestClient(app).post(
        "/api/speech/synthesize",
        json={"text": "Ich beantworte Fragen.", "language": "de"},
    )

    assert response.status_code == 200
    assert response.content == b"fake-mp3"
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_existing_lena_environment_names_are_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import load_settings

    monkeypatch.delenv("REWRITE_PROVIDER", raising=False)
    monkeypatch.delenv("BLABLADOR_BASE_URL", raising=False)
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    monkeypatch.delenv("BLABLADOR_MODEL", raising=False)
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "blablador")
    monkeypatch.setenv("LENA_LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LENA_LLM_API_KEY", "test-token")
    monkeypatch.setenv("LENA_LLM_MODEL", "test-model")

    loaded = load_settings()

    assert loaded.rewrite_provider == "blablador"
    assert loaded.blablador_configured is True


def test_template_query_returns_isolated_cards() -> None:
    client = TestClient(create_app(settings()))
    response = client.post("/api/query", json={"query": "", "language": "de", "category": "medical"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "template"
    assert body["cards"]
    assert body["cards"][0]["name"].startswith("UVO")
    assert "Taubestr." in body["cards"][0]["address"]


def test_overnight_verb_query_is_not_rejected_as_out_of_scope() -> None:
    client = TestClient(create_app(settings()))
    body = client.post(
        "/api/query", json={"query": "Wo kann ich übernachten?", "language": "de", "category": None}
    ).json()

    assert body["status"] == "ok"
    assert body["cards"]
    assert any("Übernachtung" in card["name"] or "Notschlafstelle" in card["name"] for card in body["cards"])


def test_self_description_and_out_of_scope_are_deterministic() -> None:
    client = TestClient(create_app(settings()))

    self_response = client.post("/api/query", json={"query": "Who are you?", "language": "en", "category": None}).json()
    outside = client.post("/api/query", json={"query": "How do telescopes work?", "language": "en", "category": None}).json()

    assert self_response["status"] == "ok"
    assert self_response["provider"] == "template"
    assert self_response["cards"] == []
    assert self_response["answer"].startswith("I am LENA")
    assert outside["status"] == "no_results"
    assert outside["answer"].startswith("I can’t help")


def test_vague_help_request_asks_for_a_category() -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "I need help", "language": "en", "category": None}).json()

    assert body["status"] == "no_results"
    assert body["session_id"]
    assert body["question"] == "I need help"
    assert body["cards"]
    assert "Hilfebus" in body["cards"][0]["name"]
    assert body["map_data"]["origin"]["label"] == "Leipzig Hauptbahnhof"
    assert body["map_data"]["destinations"]
    assert body["answer"].startswith("What kind of help")


def test_session_follow_up_keeps_chat_history() -> None:
    client = TestClient(create_app(settings()))
    first = client.post("/api/query", json={"query": "Ich brauche Hilfe", "language": "de"}).json()
    second = client.post(
        "/api/query",
        json={"query": "Essen", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["session_id"] == first["session_id"]
    assert len(second["history"]) == 2
    assert second["history"][0]["question"] == "Ich brauche Hilfe"
    assert second["history"][1]["question"] == "Essen"
    assert second["status"] == "ok"


def test_tuesday_food_names_schwanenteich_stand_time() -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "Wo bekomme ich Dienstag Essen?", "language": "de"}).json()

    card_ids = {card["id"] for card in body["cards"]}
    assert body["status"] == "ok"
    assert "14" in card_ids
    assert "Schwanenteich" in body["answer"]
    assert "17:00" in body["answer"]
    assert "keine Essensausgabe" in body["answer"]


def test_wednesday_food_does_not_use_tuesday_office_food_offer() -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "Wo bekomme ich Mittwoch Essen?", "language": "de"}).json()
    card_text = json.dumps(body["cards"], ensure_ascii=False)

    assert body["status"] == "ok"
    assert "14" not in {card["id"] for card in body["cards"]}
    assert "Schwanenteich" not in body["answer"]
    assert "Nürnberger Str. 37" not in card_text


def test_sunday_food_names_hilfebus_soup_stand_time() -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "Wo bekomme ich Sonntag Essen?", "language": "de"}).json()

    assert body["status"] == "ok"
    assert body["cards"][0]["id"] == "21"
    assert "Hilfebus" in body["answer"]
    assert "sonntags 20:00-21:00" in body["answer"]
    assert "Hauptbahnhof" in body["answer"]
    destinations = body["map_data"]["destinations"]
    assert any("Westseite" in destination["address"] for destination in destinations)
    assert all("Demmeringstr. 32" not in destination["address"] for destination in destinations)


def test_wednesday_medical_names_mobile_medibus_places() -> None:
    client = TestClient(create_app(settings()))
    body = client.post(
        "/api/query",
        json={"query": "Wo bekomme ich Mittwoch medizinische Hilfe?", "language": "de"},
    ).json()

    assert body["status"] == "ok"
    assert body["cards"][0]["id"] == "25"
    assert "Medibus" in body["answer"]
    assert "Mittwoch Hauptbahnhof" in body["answer"]


@pytest.mark.parametrize("language", ["de", "en", "pl", "ro", "ru"])
def test_template_answer_uses_selected_language(language: str) -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "", "language": language, "category": "food"}).json()

    assert body["status"] == "ok"
    assert body["language"] == language
    assert body["answer"]


def test_blablador_failure_falls_back_without_exposing_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))

    async def fail(_: dict) -> dict:
        raise ProviderError("secret provider detail")

    assert app.state.service.blablador is not None
    monkeypatch.setattr(app.state.service.blablador, "_post", fail)
    body = TestClient(app).post(
        "/api/query", json={"query": "Where can I get food?", "language": "en", "category": None}
    ).json()

    assert body["status"] == "ok"
    assert body["provider"] == "template"
    assert "secret" not in body["answer"]
    assert body["cards"]


def test_provider_rejects_unknown_card_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]

    async def response(_: dict) -> dict:
        content = json.dumps({"answer": "A short grounded answer.", "card_ids": ["invented-offer"]})
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(ProviderError):
        import asyncio
        asyncio.run(provider.answer(query="help", language=Language.EN, category=Category.ADVICE, offers=[offer]))


def test_provider_treats_null_content_as_safe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]

    async def response(_: dict) -> dict:
        return {"choices": [{"message": {"content": None}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(ProviderError):
        import asyncio
        asyncio.run(provider.answer(query="help", language=Language.EN, category=Category.ADVICE, offers=[offer]))


def test_provider_rejects_unsupported_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]

    async def response(_: dict) -> dict:
        content = json.dumps({"answer": "Call 99999999.", "card_ids": [offer.id]})
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(ProviderError):
        import asyncio
        asyncio.run(provider.answer(query="help", language=Language.EN, category=Category.ADVICE, offers=[offer]))


def test_provider_accepts_source_time_with_different_range_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = next(item for item in app.state.kb.offers if "Care Bags" in item.name)

    async def response(_: dict) -> dict:
        content = json.dumps(
            {"answer": "Distribution is from 16:00 to 19:00.", "card_ids": [offer.id]}
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    result = asyncio.run(
        provider.answer(query="food", language=Language.EN, category=Category.FOOD, offers=[offer])
    )

    assert result.card_ids == [offer.id]


def test_provider_accepts_no_card_ids_for_unsuitable_context(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = next(item for item in app.state.kb.offers if item.source_index == 7)

    async def response(_: dict) -> dict:
        content = json.dumps(
            {
                "answer": "LENA hat in diesen Daten keinen passenden Schlafplatz fuer Minderjaehrige.",
                "card_ids": [],
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    result = asyncio.run(
        provider.answer(
            query="Ich bin erst 12.",
            language=Language.DE,
            category=Category.SLEEP,
            offers=[offer],
            conversation_history=[
                ChatTurn(question="Wo kann ich schlafen?", answer="Du kannst in der Rueckmarsdorfer Strasse schlafen.")
            ],
        )
    )

    assert result.card_ids == []


def test_two_stage_pipeline_routes_all_offers_then_formulates_from_selected_records() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        def context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            offers = kwargs["offers"]
            captured["route_count"] = len(offers)
            captured["route_history"] = kwargs["conversation_history"]
            selected = next(offer for offer in offers if offer.source_index == 9)
            return ProviderRoute(
                intent=Category.ADVICE,
                offer_ids=[selected.id],
                needs_clarification=False,
                out_of_scope=False,
            )

        async def answer(self, **kwargs) -> ProviderAnswer:
            offers = kwargs["offers"]
            captured["answer_count"] = len(offers)
            captured["question"] = kwargs["query"]
            captured["routing_context"] = kwargs["routing_context"]
            captured["answer_history"] = kwargs["conversation_history"]
            return ProviderAnswer(answer="I found a suitable service.", card_ids=[offers[0].id])

    app.state.service.blablador = FakeProvider()

    body = TestClient(app).post(
        "/api/query", json={"query": "A detailed but indirect Leipzig support question", "language": "en", "category": None}
    ).json()

    assert body["provider"] == "blablador"
    assert captured["route_count"] == 30
    assert captured["answer_count"] == 1
    assert captured["question"] == "A detailed but indirect Leipzig support question"
    assert captured["routing_context"] == {"intent": "advice", "source": "llm_router"}
    assert captured["route_history"] == []
    assert captured["answer_history"] == []


def test_llm_follow_up_receives_previous_session_turns_and_can_return_no_cards() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        def context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            captured["route_history"] = kwargs["conversation_history"]
            roles = sleep_roles(kwargs["offers"])
            return ProviderRoute(
                intent=Category.SLEEP,
                offer_ids=[roles["ruecke"][0].id, roles["women"][0].id],
                needs_clarification=False,
                out_of_scope=False,
            )

        async def answer(self, **kwargs) -> ProviderAnswer:
            captured["answer_history"] = kwargs["conversation_history"]
            if kwargs["query"] == "Ich bin erst 12.":
                return ProviderAnswer(
                    answer="LENA hat in diesen Daten keinen passenden Schlafplatz fuer Minderjaehrige.",
                    card_ids=[],
                )
            return ProviderAnswer(answer="Du kannst in der Rueckmarsdorfer Strasse schlafen.", card_ids=[kwargs["offers"][0].id])

    app.state.service.blablador = FakeProvider()
    client = TestClient(app)
    first = client.post("/api/query", json={"query": "Wo kann ich schlafen?", "language": "de"}).json()
    second = client.post(
        "/api/query",
        json={"query": "Ich bin erst 12.", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["provider"] == "blablador"
    assert second["cards"] == []
    assert len(captured["route_history"]) == 1
    assert captured["route_history"][0].question == "Wo kann ich schlafen?"
    assert len(captured["answer_history"]) == 1
    assert captured["answer_history"][0].question == "Wo kann ich schlafen?"
    assert captured["answer_history"][0].answer


def test_answer_prompt_uses_informal_language_and_forbids_visible_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = next(item for item in app.state.kb.offers if item.source_index == 10)
    captured: dict[str, object] = {}

    async def response(payload: dict) -> dict:
        captured["payload"] = payload
        content = json.dumps({"answer": "Du kannst dort Mittagessen bekommen.", "card_ids": [offer.id]})
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    asyncio.run(
        provider.answer(
            query="Ich hab Hunger",
            language=Language.DE,
            category=Category.FOOD,
            offers=[offer],
            conversation_history=[ChatTurn(question="Ich brauche Hilfe", answer="Welche Hilfe brauchst du?")],
        )
    )

    system_prompt = captured["payload"]["messages"][0]["content"]
    user_prompt = json.loads(captured["payload"]["messages"][1]["content"])
    assert "Never use formal German Sie/Ihnen" in system_prompt
    assert "Never mention internal record IDs" in system_prompt
    assert "labels like 'ID 7'" in system_prompt
    assert "CONVERSATION_CONTEXT" in system_prompt
    assert user_prompt["CONVERSATION_CONTEXT"][0]["user"] == "Ich brauche Hilfe"


def test_sleep_router_enforces_ruecke_and_target_group_options() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        def context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            role_map = sleep_roles(kwargs["offers"])
            return ProviderRoute(
                intent=Category.SLEEP,
                offer_ids=[role_map["men"][-1].id],
                needs_clarification=False,
                out_of_scope=False,
            )

        async def answer(self, **kwargs) -> ProviderAnswer:
            offers = kwargs["offers"]
            captured["ids"] = [offer.id for offer in offers]
            return ProviderAnswer(
                answer="Wende dich zuerst an die Rückmarsdorfer Straße. Danach gibt es passende Orte nach Zielgruppe.",
                card_ids=[offer.id for offer in offers],
            )

    app.state.service.blablador = FakeProvider()
    body = TestClient(app).post(
        "/api/query", json={"query": "Wo kann ich übernachten?", "language": "de", "category": None}
    ).json()

    assert body["provider"] == "blablador"
    roles = sleep_roles(app.state.kb.offers)
    expected = [roles["ruecke"][0].id, roles["women"][0].id, roles["drug"][0].id]
    assert captured["ids"][:3] == expected
    assert [card["id"] for card in body["cards"][:3]] == expected


def test_router_rejects_unknown_offer_id(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador

    async def response(_: dict) -> dict:
        content = json.dumps(
            {
                "intent": "sleep",
                "offer_ids": ["invented-offer"],
                "needs_clarification": False,
                "out_of_scope": False,
                "acute_risk_detected": False,
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(ProviderError):
        import asyncio
        asyncio.run(
            provider.route(
                query="sleep",
                language=Language.EN,
                category=None,
                offers=app.state.kb.offers,
            )
        )


def test_router_prompt_contains_question_index_and_sleep_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    ruecke = sleep_roles(app.state.kb.offers)["ruecke"][0]
    captured: dict[str, object] = {}

    async def response(payload: dict) -> dict:
        captured["payload"] = payload
        content = json.dumps(
            {
                "intent": "sleep",
                "offer_ids": [ruecke.id],
                "needs_clarification": False,
                "out_of_scope": False,
                "acute_risk_detected": False,
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    route = asyncio.run(
        provider.route(
            query="Wo kann ich übernachten?",
            language=Language.DE,
            category=None,
            offers=app.state.kb.offers,
            conversation_history=[ChatTurn(question="Ich brauche Hilfe", answer="Welche Hilfe brauchst du?")],
        )
    )
    payload = captured["payload"]
    user_prompt = json.loads(payload["messages"][1]["content"])

    assert route.intent == Category.SLEEP
    assert route.acute_risk_detected is False
    assert "acute_risk_detected" in payload["messages"][0]["content"]
    assert user_prompt["question"] == "Wo kann ich übernachten?"
    assert user_prompt["CONVERSATION_CONTEXT"][0]["user"] == "Ich brauche Hilfe"
    assert len(user_prompt["OFFER_INDEX"]) == 30
    assert user_prompt["SLEEP_ROUTING_POLICY"]["general_sleep_first"] == ruecke.id


def test_explicit_womens_sleep_route_removes_male_only_ruecke_card() -> None:
    app = create_app(settings())

    class FakeProvider:
        def index_context_fits(self, offers) -> bool:
            return True

        def context_fits(self, offers) -> bool:
            return True

        async def route(self, **kwargs) -> ProviderRoute:
            roles = sleep_roles(kwargs["offers"])
            return ProviderRoute(
                intent=Category.SLEEP,
                offer_ids=[roles["ruecke"][0].id, roles["women"][0].id, roles["drug"][0].id],
                needs_clarification=False,
                out_of_scope=False,
            )

        async def answer(self, **kwargs) -> ProviderAnswer:
            offers = kwargs["offers"]
            return ProviderAnswer(answer="Für Frauen gibt es passende Übernachtungsangebote.", card_ids=[o.id for o in offers])

    app.state.service.blablador = FakeProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Ich suche einen Schlafplatz für Frauen", "language": "de", "category": None},
    ).json()

    role_map = sleep_roles(app.state.kb.offers)
    ids = [card["id"] for card in body["cards"]]
    assert ids[0] == role_map["women"][0].id
    assert role_map["ruecke"][0].id not in ids


def test_full_context_size_guard_disables_llm_router() -> None:
    app = create_app(settings("blablador", max_chars=100))

    assert app.state.service.full_context_available is False
    health = TestClient(app).get("/api/health").json()
    assert health["llm_router_available"] is False
    assert health["full_context_fallback_available"] is False


def test_frontend_contains_required_languages_and_no_internal_source_term() -> None:
    frontend = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    frontend += (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    for language in ("Deutsch", "English", "Polski", "Română", "Русский"):
        assert language in frontend
    for category in ("Food", "Sleep", "Medical help", "Advice"):
        assert category in frontend
    for interaction_text in ("Speak question", "I answer questions about help in Leipzig", "voiceReady"):
        assert interaction_text in frontend
    assert "SESSION_TIMEOUT_MS = 3 * 60 * 1000" in frontend
    assert "MediaRecorder" in frontend
    assert "/api/speech/transcribe" in frontend
    assert "/api/speech/synthesize" in frontend
    assert "speechSynthesis" not in frontend
    assert "submit-icon" in frontend
    assert "submitQuery(transcript)" not in frontend
    assert "replayAnswerButton" in frontend
    assert "textForSpeech" in frontend
    assert "germanTime" in frontend
    assert "englishTime" in frontend
    assert "Wissensbasis" not in frontend
    assert "knowledge base" not in frontend.casefold()


def test_english_cards_are_loaded_from_stored_translations() -> None:
    client = TestClient(create_app(settings()))
    body = client.post("/api/query", json={"query": "", "language": "en", "category": "sleep"}).json()
    card_text = json.dumps(body["cards"], ensure_ascii=False)

    assert body["status"] == "ok"
    assert "Grundversorgung" not in card_text
    assert "Social counseling" in card_text or "Basic supplies" in card_text
    assert "Scharnhorststr. 27, 04275 Leipzig" in card_text
