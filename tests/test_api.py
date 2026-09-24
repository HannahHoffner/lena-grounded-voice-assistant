from __future__ import annotations

import json
import asyncio
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.candidate_contract import CandidateRole
from app.formulation import (
    AnswerType,
    ClaimType,
    FactType,
    FORMULATOR_PROMPT_VERSION,
    FORMULATOR_SYSTEM_PROMPT,
    FormulatorError,
    GroundingDiagnosticCode,
    build_formulator_evidence,
)
from app.i18n import localize_offer_card
from app.interpreter import (
    INTERPRETER_PROMPT_VERSION,
    AcuteRiskStatus,
    Need,
    QueryInterpretation,
    RequestedService,
    ScopeStatus,
)
from app.llm_selection import SELECTOR_PROMPT_VERSION, CandidateSelectionResponse
from app.main import create_app
from app.models import ChatTurn, Language
from app.providers.llm import BlabladorProvider, InterpreterError, ProviderAnswer, ProviderError
from app.spatial import LEIPZIG_HBF, distance_from_hbf
from app.speech import SpeechSynthesizer, SpeechTranscriber


ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "data" / "canonical" / "offers.json"


@pytest.mark.parametrize("envelope", [None, [], "unexpected", 7])
def test_invalid_llm_envelope_uses_controlled_interpreter_error(monkeypatch, envelope) -> None:
    provider = BlabladorProvider(settings("blablador"))
    async def fake_post(payload):
        return envelope
    monkeypatch.setattr(provider, "_post", fake_post)
    with pytest.raises(InterpreterError, match="interpreter_invalid_json"):
        asyncio.run(provider.interpret_query(query="Hilfe", language=Language.DE, category=None, aliases=[]))


@pytest.mark.parametrize("provider", ["edge", "openai"])
@pytest.mark.parametrize("language", list(Language))
def test_tts_api_reaches_adapter_with_session_bound_text(monkeypatch, provider, language) -> None:
    import edge_tts
    import httpx
    from app.speech import EDGE_VOICES, normalize_tts_text

    captured = {}
    audio = b"synthetic-audio"
    class Edge:
        def __init__(self, **kwargs): captured.update(kwargs)
        async def stream(self):
            yield {"type": "WordBoundary", "text": "ignored"}
            yield {"type": "audio", "data": audio}
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return httpx.Response(200, content=audio, request=httpx.Request("POST", url))
    monkeypatch.setattr(edge_tts, "Communicate", Edge)
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    app = create_app(replace(
        settings("blablador"), speech_synthesis_provider=provider, speech_synthesis_response_format="wav",
    ))
    session = app.state.service.sessions.create(language, app.state.kb.runtime_kb_fingerprint)
    app.state.service.sessions.add_turn(session, question="Test", answer="Antwort", speakable_texts=["112"])
    client = TestClient(app)
    response = client.post("/api/speech/synthesize", json={
        "text": "112", "language": language.value, "session_id": session.session_id,
    })
    assert response.status_code == 200
    assert response.content == audio
    expected_format = "mp3" if provider == "edge" else "wav"
    assert client.get("/api/speech/config").json()["synthesis_format"] == expected_format
    assert response.headers["content-type"] == ("audio/mpeg" if provider == "edge" else "audio/wav")
    if provider == "edge":
        assert captured["text"] == normalize_tts_text("112", language)
        assert captured["voice"] == EDGE_VOICES[language]
    else:
        assert captured["url"].endswith("/audio/speech")
        assert captured["headers"]["Authorization"] == "Bearer test-token"
        assert captured["json"]["input"] == normalize_tts_text("112", language)
        assert captured["json"]["response_format"] == "wav"


def _interpretation(
    need: Need = Need.UNKNOWN,
    *,
    scope: ScopeStatus = ScopeStatus.IN_SCOPE,
    risk: AcuteRiskStatus = AcuteRiskStatus.NOT_DETECTED,
    facts: dict[str, object] | None = None,
    services: list[RequestedService] | None = None,
) -> QueryInterpretation:
    explicit_facts = {
        "age": None,
        "gender": "unknown",
        "drug_use": "unknown",
        "no_social_benefit_entitlement": "unknown",
        "district": None,
        "requested_day": None,
        "requested_time": None,
    }
    explicit_facts.update(facts or {})
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
            "need": need.value,
            "explicit_service_requests": [item.value for item in services or []],
            "scope_status": scope.value,
            "input_language": "de",
            "explicit_facts": explicit_facts,
            "uncertain_hints": [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": risk.value,
        }
    )


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


class _InterpreterOnlyProvider:
    async def interpret_query(self, **kwargs) -> QueryInterpretation:
        query = kwargs["query"].casefold()
        category = kwargs.get("category")
        if category is not None:
            need = Need(category.value)
            return _interpretation(need)
        if "who are you" in query:
            return _interpretation(Need.UNKNOWN)
        if "telescope" in query:
            return _interpretation(Need.UNKNOWN, scope=ScopeStatus.OUT_OF_SCOPE)
        if "übernacht" in query or "schlaf" in query:
            return _interpretation(Need.SLEEP)
        if "help" in query or "hilfe" in query:
            return _interpretation(Need.GENERAL_HELP)
        return _interpretation(Need.UNKNOWN)

    def context_fits(self, _evidence) -> bool:
        return False


def _template_client_with_interpreter() -> TestClient:
    app = create_app(settings())
    app.state.service.blablador = _InterpreterOnlyProvider()
    return TestClient(app)


def _evidence_for(
    app,
    offer,
    *,
    query: str = "help",
    language: Language = Language.EN,
    answer_type: AnswerType = AnswerType.GROUNDED_RESULT,
    role: CandidateRole = CandidateRole.DIRECT_SERVICE,
):
    return build_formulator_evidence(
        query=query,
        language=language,
        answer_type=answer_type,
        need=Need.ADVICE,
        offers=[offer],
        roles={offer.id: role},
        mandatory_ids={offer.id},
    )


def _fact(evidence, fact_type: FactType):
    return next(fact for fact in evidence.selected_offers[0].facts if fact.fact_type == fact_type)


def _formulator_json(
    evidence,
    *,
    text: str,
    fact_types: tuple[FactType, ...] = (FactType.DISPLAY_NAME,),
    claim_type: ClaimType = ClaimType.ACTION,
    card_ids: list[str] | None = None,
) -> str:
    offer = evidence.selected_offers[0]
    fact_ids = [_fact(evidence, fact_type).fact_id for fact_type in fact_types]
    return json.dumps(
        {
            "contract_version": "2",
            "language": evidence.requested_language.value,
            "sentences": [
                {
                    "text": text,
                    "claim_type": claim_type.value,
                    "offer_id": offer.offer_id,
                    "fact_ids": fact_ids,
                    "policy_ids": [],
                }
            ],
            "card_ids": card_ids if card_ids is not None else [offer.offer_id],
        }
    )


def _seed_tts_session(app, *, answer: str, language: Language = Language.DE) -> str:
    service = app.state.service
    session = service.sessions.resolve(None, language, service.kb.runtime_kb_fingerprint or "")
    session = service.sessions.add_turn(session, question="test", answer=answer)
    return session.session_id


def test_health_and_frontend_work() -> None:
    client = TestClient(create_app(settings()))

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["kb_loaded"] is True
    assert health.json()["offer_count"] == 28
    assert health.json()["official_offer_source"]["status"] == "verified"
    assert health.json()["official_offer_source"]["record_count"] == 2
    assert health.json()["active_provider"] == "template"
    assert health.json()["llm_selector_available"] is False
    assert health.json()["selector_contract_version"] == "1"
    assert health.json()["selector_prompt_version"] == SELECTOR_PROMPT_VERSION
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
    answer = "Ich beantworte Fragen."
    session_id = _seed_tts_session(app, answer=answer)

    async def synthesize(self: SpeechSynthesizer, text: str, *, language: Language) -> bytes:
        assert text == answer
        assert language == Language.DE
        return b"fake-mp3"

    monkeypatch.setattr(SpeechSynthesizer, "synthesize", synthesize)
    response = TestClient(app).post(
        "/api/speech/synthesize",
        json={"text": answer, "language": "de", "session_id": session_id},
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
    client = _template_client_with_interpreter()
    response = client.post("/api/query", json={"query": "", "language": "de", "category": "medical"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "template"
    assert body["cards"]
    assert {card["id"] for card in body["cards"]} == {"10", "24", "25"}


def test_overnight_verb_query_is_not_rejected_as_out_of_scope() -> None:
    client = _template_client_with_interpreter()
    body = client.post(
        "/api/query", json={"query": "Wo kann ich übernachten?", "language": "de", "category": None}
    ).json()

    assert body["status"] == "ok"
    assert body["cards"]
    assert body["cards"][0]["id"] == "7"
    assert {card["id"] for card in body["cards"]} <= {"7", "21"}


def test_self_description_and_out_of_scope_are_deterministic() -> None:
    client = _template_client_with_interpreter()

    self_response = client.post("/api/query", json={"query": "Who are you?", "language": "en", "category": None}).json()
    outside = client.post("/api/query", json={"query": "How do telescopes work?", "language": "en", "category": None}).json()

    assert self_response["status"] == "ok"
    assert self_response["provider"] == "template"
    assert self_response["cards"] == []
    assert self_response["answer"].startswith("I am LENA")
    assert outside["status"] == "no_results"
    assert outside["cards"] == []


def test_vague_help_request_asks_for_a_category() -> None:
    client = _template_client_with_interpreter()
    body = client.post("/api/query", json={"query": "I need help", "language": "en", "category": None}).json()

    assert body["status"] == "no_results"
    assert body["session_id"]
    assert body["question"] == "I need help"
    assert body["cards"] == []
    assert body["clarification"]["type"] == "general_need"
    assert body["map_data"] is None
    assert body["answer"] == "What help do you need?"


def test_session_follow_up_keeps_chat_history() -> None:
    client = _template_client_with_interpreter()
    first = client.post("/api/query", json={"query": "Ich brauche Hilfe", "language": "de"}).json()
    second = client.post(
        "/api/query",
        json={
            "query": "",
            "language": "de",
            "session_id": first["session_id"],
            "dialog_id": first["clarification"]["dialog_id"],
            "choice_values": ["food"],
        },
    ).json()

    assert second["session_id"] == first["session_id"]
    assert len(second["history"]) == 2
    assert second["history"][0]["question"] == "Ich brauche Hilfe"
    assert second["history"][1]["question"] == "Essen und Grundversorgung"
    assert second["status"] == "ok"


def test_tuesday_food_names_schwanenteich_stand_time() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class TuesdayProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(
                Need.FOOD,
                facts={"age": 30, "requested_day": "tuesday"},
                services=[RequestedService.FOOD],
            )

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            candidate_ids = {item.offer_id for item in kwargs["decision"].selectable_candidates}
            captured["selector_ids"] = candidate_ids
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[offer_id for offer_id in ("22", "14") if offer_id in candidate_ids],
            )

        def context_fits(self, evidence) -> bool:
            return True

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            captured["evidence_ids"] = [offer.offer_id for offer in evidence.selected_offers]
            return ProviderAnswer(
                answer=(
                    "Bei Bahnhofsmission Leipzig bekommst du belegte Brötchen. "
                    "Bei Diakonie Leipzig gibt es dienstags am Schwanenteich Brötchen oder Suppe."
                ),
                card_ids=[offer.offer_id for offer in evidence.selected_offers],
                sentence_count=2,
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = TuesdayProvider()
    client = TestClient(app)
    body = client.post("/api/query", json={"query": "Wo bekomme ich Dienstag Essen?", "language": "de"}).json()

    card_ids = {card["id"] for card in body["cards"]}
    assert body["status"] == "ok"
    assert {"14", "22"} <= captured["selector_ids"]
    assert captured["evidence_ids"] == ["22", "14"]
    assert "Bahnhofsmission Leipzig" in body["answer"]
    assert "Schwanenteich" in body["answer"]
    assert "Nutze" not in body["answer"]
    assert "14" in card_ids
    assert "22" in card_ids
    card = next(card for card in body["cards"] if card["id"] == "14")
    assert "Schwanenteich" in json.dumps(card, ensure_ascii=False)
    assert "17:00" in json.dumps(card, ensure_ascii=False)
    assert len(body["spoken_result_ids"]) <= 3
    assert len(body["card_ids"]) <= 3
    assert body["map_marker_ids"] == [item["id"] for item in body["map_data"]["destinations"]]
    assert "14:schwanenteich" in body["map_marker_ids"]


def test_wednesday_food_does_not_use_tuesday_office_food_offer() -> None:
    app = create_app(settings())

    class WednesdayProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(
                Need.FOOD,
                facts={"requested_day": "wednesday"},
                services=[RequestedService.FOOD],
            )

        def context_fits(self, offers) -> bool:
            return False

    app.state.service.blablador = WednesdayProvider()
    client = TestClient(app)
    body = client.post("/api/query", json={"query": "Wo bekomme ich Mittwoch Essen?", "language": "de"}).json()
    card_text = json.dumps(body["cards"], ensure_ascii=False)

    assert body["status"] == "ok"
    assert "14" not in {card["id"] for card in body["cards"]}
    assert "14:schwanenteich" not in body["map_marker_ids"]
    assert "Schwanenteich" not in body["answer"]
    assert "Nürnberger Str. 37" not in card_text


def test_sunday_food_names_hilfebus_soup_stand_time() -> None:
    app = create_app(settings())

    class SundayProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(
                Need.FOOD,
                facts={"requested_day": "sunday"},
                services=[RequestedService.FOOD],
            )

        def context_fits(self, offers) -> bool:
            return False

    app.state.service.blablador = SundayProvider()
    client = TestClient(app)
    body = client.post("/api/query", json={"query": "Wo bekomme ich Sonntag Essen?", "language": "de"}).json()

    assert body["status"] == "ok"
    assert body["cards"][0]["id"] == "21"
    assert "Hilfebus" in body["cards"][0]["name"]
    assert "20:00" in json.dumps(body["cards"][0], ensure_ascii=False)
    destinations = body["map_data"]["destinations"]
    assert any("Westseite" in destination["address"] for destination in destinations)
    assert all("Demmeringstr. 32" not in destination["address"] for destination in destinations)
    assert body["map_marker_ids"] == [destination["id"] for destination in destinations]


def test_wednesday_medical_names_mobile_medibus_places() -> None:
    app = create_app(settings())

    class WednesdayProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.MEDICAL, facts={"requested_day": "wednesday"})

        def context_fits(self, offers) -> bool:
            return False

    app.state.service.blablador = WednesdayProvider()
    client = TestClient(app)
    body = client.post(
        "/api/query",
        json={"query": "Wo bekomme ich Mittwoch medizinische Hilfe?", "language": "de"},
    ).json()

    assert body["status"] == "ok"
    assert body["cards"][0]["id"] == "25"
    assert "Hauptbahnhof" in json.dumps(body["cards"][0], ensure_ascii=False)


@pytest.mark.parametrize("language", ["de", "en", "pl", "ro", "ru"])
def test_template_answer_uses_selected_language(language: str) -> None:
    client = _template_client_with_interpreter()
    # Eingefroren auf Montag 10:00, da das Angebot mit "food"-Kategorie nur
    # Montag-Freitag tagsüber geöffnet hat; ohne feste Uhr hängt der Testerfolg
    # von der realen Tageszeit ab (WP9C).
    client.app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    body = client.post("/api/query", json={"query": "", "language": language, "category": "food"}).json()

    assert body["status"] == "ok"
    assert body["language"] == language
    assert body["answer"]


def test_custom_hbf_settings_are_used_for_spatial_ordering_and_map_origin() -> None:
    custom_latitude, custom_longitude = 51.28, 12.62
    app = create_app(replace(settings(), hbf_latitude=custom_latitude, hbf_longitude=custom_longitude))
    app.state.service.blablador = _InterpreterOnlyProvider()
    client = TestClient(app)
    # Eingefroren auf Montag 10:00 (WP9C), da die Food-Selektion ein
    # geöffnetes Angebot voraussetzt.
    client.app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))

    body = client.post("/api/query", json={"query": "", "language": "de", "category": "food"}).json()

    assert body["status"] == "ok"
    map_data = body["map_data"]
    assert map_data is not None
    assert map_data["origin"]["latitude"] == custom_latitude
    assert map_data["origin"]["longitude"] == custom_longitude
    assert (map_data["origin"]["latitude"], map_data["origin"]["longitude"]) != (
        LEIPZIG_HBF.latitude,
        LEIPZIG_HBF.longitude,
    )
    destination = map_data["destinations"][0]
    custom_origin = app.state.service.hbf_origin
    assert destination["distance_meters"] == distance_from_hbf(
        destination["latitude"], destination["longitude"], origin=custom_origin
    )
    assert destination["distance_meters"] != distance_from_hbf(
        destination["latitude"], destination["longitude"]
    )


def test_blablador_failure_falls_back_without_exposing_error(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    calls = 0

    async def fail(_: dict) -> dict:
        nonlocal calls
        calls += 1
        raise ProviderError("secret provider detail")

    assert app.state.service.blablador is not None
    monkeypatch.setattr(app.state.service.blablador, "_post", fail)
    body = TestClient(app).post(
        "/api/query", json={"query": "Where can I get food?", "language": "en", "category": None}
    ).json()

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises, sofern die Wissensbasis ihn
    # liefert.
    offer = next(offer for offer in app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    assert body["status"] == "error"
    assert body["provider"] == "template"
    assert "secret" not in body["answer"]
    assert [card["id"] for card in body["cards"]] == [offer.id]
    assert body["cards"][0]["address"] is None
    assert body["map_data"] is None
    assert calls == 1  # Interpreterfehler darf keinen Formulatoraufruf auslösen.


def test_provider_rejects_unknown_card_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]

    evidence = _evidence_for(app, offer)

    async def response(_: dict) -> dict:
        content = _formulator_json(evidence, text=f"Contact {offer.display_name or offer.name}.", card_ids=["999"])
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(FormulatorError, match="formulator_invalid_card"):
        import asyncio
        asyncio.run(provider.formulate_answer(evidence=evidence))


def test_provider_treats_null_content_as_safe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]
    evidence = _evidence_for(app, offer)

    async def response(_: dict) -> dict:
        return {"choices": [{"message": {"content": None}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(FormulatorError, match="formulator_invalid_json"):
        import asyncio
        asyncio.run(provider.formulate_answer(evidence=evidence))


def test_provider_rejects_unsupported_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = app.state.kb.offers[0]
    evidence = _evidence_for(app, offer)

    async def response(_: dict) -> dict:
        content = _formulator_json(evidence, text="Call 99999999.")
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        import asyncio
        asyncio.run(provider.formulate_answer(evidence=evidence))


def test_provider_accepts_source_time_with_different_range_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    # Angebot 16 (TiMMi ToHelp - Projekt "Care Bags") zeigt seit dem
    # Organisations-display_name-Fallback (Untersuchung zu unbemerkten
    # Fallbacks, Folgefix) den kuratierten Kurznamen "TiMMi ToHelp" statt des
    # vollen Quellnamens; per ID statt per Namensteilstring auswählen.
    offer = next(item for item in app.state.kb.offers if item.id == "16")
    evidence = _evidence_for(app, offer, query="food")
    time_fact = next(
        fact for fact in evidence.selected_offers[0].facts
        if fact.fact_type in {FactType.OPENING_TIME, FactType.STAND_TIME, FactType.NOTE}
        and "16:00" in fact.value
        and "19:00" in fact.value
    )

    async def response(_: dict) -> dict:
        content = json.dumps({
            "contract_version": "2",
            "language": "en",
            "sentences": [{
                "text": "Distribution is from 16:00 to 19:00.",
                "claim_type": "action",
                "offer_id": offer.id,
                "fact_ids": [time_fact.fact_id],
                "policy_ids": [],
            }],
            "card_ids": [offer.id],
        })
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    result = asyncio.run(
        provider.formulate_answer(evidence=evidence)
    )

    assert result.card_ids == [offer.id]


def test_provider_accepts_no_card_ids_for_unsuitable_context(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    evidence = build_formulator_evidence(
        query="Ich bin erst 12.",
        language=Language.DE,
        answer_type=AnswerType.NO_VERIFIED_RESULT,
        need=Need.SLEEP,
        offers=[],
        roles={},
    )
    no_result_policy = next(policy for policy in evidence.binding_policies if policy.policy_id.value == "no_verified_result")

    async def response(_: dict) -> dict:
        content = json.dumps({
            "contract_version": "2",
            "language": "de",
            "sentences": [{
                "text": "LENA hat in den freigegebenen Daten kein passendes Angebot gefunden.",
                "claim_type": "no_result",
                "offer_id": None,
                "fact_ids": [],
                "policy_ids": [no_result_policy.policy_id.value],
            }],
            "card_ids": [],
        })
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    result = asyncio.run(
        provider.formulate_answer(evidence=evidence)
    )

    assert result.card_ids == []


def test_interpreter_then_candidate_selector_formulates_from_curated_records() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def context_fits(self, offers) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            captured["aliases"] = kwargs["aliases"]
            captured["interpreter_history"] = kwargs["conversation_history"]
            assert "offers" not in kwargs
            return _interpretation(Need.ADVICE)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[-1].offer_id],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            captured["evidence"] = evidence
            captured["answer_count"] = len(evidence.selected_offers)
            captured["answer_ids"] = [offer.offer_id for offer in evidence.selected_offers]
            captured["question"] = evidence.current_query
            return ProviderAnswer(
                answer="I found a suitable service.",
                card_ids=[evidence.selected_offers[0].offer_id],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FakeProvider()

    body = TestClient(app).post(
        "/api/query", json={"query": "A detailed but indirect Leipzig support question", "language": "en", "category": None}
    ).json()

    assert body["provider"] == "blablador"
    assert captured["aliases"]
    assert all(not hasattr(alias, "offer_ids") for alias in captured["aliases"])
    assert captured["answer_count"] <= 4
    assert captured["question"] == "A detailed but indirect Leipzig support question"
    evidence = captured["evidence"]
    assert evidence.evidence_version == "4"
    assert evidence.prompt_version == FORMULATOR_PROMPT_VERSION
    assert all(item.candidate_role in {"direct_service", "referral_contact"} for item in evidence.selected_offers)
    assert [item.offer_id for item in evidence.selected_offers] == captured["answer_ids"]
    assert captured["interpreter_history"] == []


def test_map_destinations_not_cited_in_the_answer_are_still_localized() -> None:
    """`map_data.destinations` is intentionally uncapped and wider than the

    (<=4) offers the answer actually cites in `response.cards` -- a user
    reported that tiles for offers *not* mentioned in the answer kept showing
    raw German content in a non-German session, because the localization
    patch in `QueryService.query()` used to only cover `response.cards`.
    """
    app = create_app(settings())

    class FakeProvider:
        def context_fits(self, offers) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.ADVICE)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            # Only cite one candidate -- the others remain in map_data.destinations
            # (built from the full candidate list) without ever appearing in cards.
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[-1].offer_id],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            return ProviderAnswer(
                answer="Found it.",
                card_ids=[evidence.selected_offers[0].offer_id],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FakeProvider()

    body = TestClient(app).post(
        "/api/query", json={"query": "A detailed but indirect Leipzig support question", "language": "en", "category": None}
    ).json()

    cited_ids = {card["id"] for card in body["cards"]}
    destinations = body["map_data"]["destinations"]
    assert len(destinations) > len(cited_ids), "test needs at least one uncited destination to be meaningful"

    # Jedes nicht zitierte Ziel muss korrekt lokalisiert sein; dass sich die
    # Lokalisierung ueberhaupt vom deutschen Original unterscheidet, muss aber
    # nur bei mindestens einem gelten -- einzelne kurze Bezeichnungen (z. B.
    # "Hilfebus") bleiben in der maschinellen EN-Uebersetzung legitim
    # unveraendert, weil es keine idiomatische Entsprechung gibt.
    kb_by_id = app.state.service.kb.by_id()
    any_distinct = False
    for destination in destinations:
        if destination["id"] in cited_ids:
            continue
        offer = kb_by_id[destination["id"]]
        expected = localize_offer_card(
            offer, Language.EN, app.state.service.translation_catalog, app.state.service.translation_policy
        )
        assert destination["description"] == expected.short_description
        any_distinct = any_distinct or destination["description"] != offer.short_description
    assert any_distinct, "test needs at least one uncited destination with a distinct EN translation to be meaningful"


def test_formulator_retries_once_after_grounding_failure_then_succeeds() -> None:
    """A single bad sample (contract violation, ungrounded claim, ...) must not
    fall back to the static template if a second attempt would have cited its
    facts correctly -- see FORMULATOR_MAX_ATTEMPTS in app/service.py.
    """
    app = create_app(settings())
    attempts: list[int] = []

    class FlakyProvider:
        def context_fits(self, offers) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.ADVICE)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[0].offer_id],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                raise FormulatorError("formulator_ungrounded_claim")
            evidence = kwargs["evidence"]
            return ProviderAnswer(
                answer="Found it on the second try.",
                card_ids=[evidence.selected_offers[0].offer_id],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FlakyProvider()

    body = TestClient(app).post(
        "/api/query", json={"query": "A detailed but indirect Leipzig support question", "language": "en", "category": None}
    ).json()

    assert attempts == [1, 2]
    assert body["provider"] == "blablador"
    assert body["answer"] == "Found it on the second try."


@pytest.mark.parametrize("diagnostic", [
    GroundingDiagnosticCode.TARGET_FACT_MISSING,
    GroundingDiagnosticCode.PHONE_NOT_EXACT,
    GroundingDiagnosticCode.REFERRAL_ROLE_MISMATCH,
])
def test_formulator_falls_back_to_template_after_repeated_grounding_failures(diagnostic) -> None:
    """The retry is bounded -- a persistently non-compliant model must still
    fall back to the safe template rather than retry indefinitely.
    """
    app = create_app(settings())
    attempts: list[int] = []

    class AlwaysFlakyProvider:
        def context_fits(self, offers) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.ADVICE)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="selected",
                selected_ids=[kwargs["decision"].selectable_candidates[0].offer_id],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            attempts.append(len(attempts) + 1)
            if len(attempts) == 1:
                assert "retry_diagnostic" not in kwargs
            else:
                assert kwargs["retry_diagnostic"] == diagnostic
            raise FormulatorError("formulator_ungrounded_claim", diagnostic_code=diagnostic)

    app.state.service.blablador = AlwaysFlakyProvider()

    body = TestClient(app).post(
        "/api/query", json={"query": "A detailed but indirect Leipzig support question", "language": "en", "category": None}
    ).json()

    assert attempts == [1, 2]
    assert body["provider"] == "template"


def test_structured_dialog_follow_up_excludes_natural_language_session_turns() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def context_fits(self, evidence) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            captured["interpreter_history"] = kwargs["conversation_history"]
            facts = {"age": 12} if kwargs["query"] == "Ich bin erst 12." else None
            return _interpretation(Need.SLEEP, facts=facts)

        async def select_candidates(self, **kwargs) -> CandidateSelectionResponse:
            return CandidateSelectionResponse(
                contract_version="1",
                selection_status="no_selection",
                selected_ids=[],
            )

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            captured["formulator_query"] = evidence.current_query
            return ProviderAnswer(
                answer="Wende dich an den Jugendnotdienst.",
                card_ids=[item.offer_id for item in evidence.selected_offers],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FakeProvider()
    client = TestClient(app)
    first = client.post("/api/query", json={"query": "Wo kann ich schlafen?", "language": "de"}).json()
    assert first["clarification"]["type"] == "sleep_target_group"
    second = client.post(
        "/api/query",
        json={"query": "Ich bin erst 12.", "language": "de", "session_id": first["session_id"]},
    ).json()

    assert second["provider"] == "blablador"
    assert [card["id"] for card in second["cards"]] == ["vkkj_jugendnotdienst", "21"]
    hilfebus = next(card for card in second["cards"] if card["id"] == "21")
    curated_hilfebus = app.state.service.kb.by_id()["21"]
    assert hilfebus["name"] == "Hilfebus"
    assert hilfebus["phone_numbers"] == curated_hilfebus.phone_numbers
    assert hilfebus["phone_numbers"]
    assert hilfebus["opening_hours_raw"] == curated_hilfebus.opening_hours_raw
    assert hilfebus["address"] is None
    assert not any(marker_id.startswith("21:") for marker_id in second["map_marker_ids"])
    assert captured["interpreter_history"] == []
    assert captured["formulator_query"] == "Ich bin erst 12."


def test_answer_prompt_uses_informal_language_and_forbids_visible_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    offer = next(item for item in app.state.kb.offers if item.source_index == 10)
    evidence = _evidence_for(app, offer, query="Ich hab Hunger", language=Language.DE)
    name_fact = _fact(evidence, FactType.DISPLAY_NAME)
    captured: dict[str, object] = {}

    async def response(payload: dict) -> dict:
        captured["payload"] = payload
        content = _formulator_json(evidence, text=f"Geh zu {name_fact.value}.")
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    asyncio.run(
        provider.formulate_answer(evidence=evidence)
    )

    system_prompt = captured["payload"]["messages"][0]["content"]
    user_prompt = json.loads(captured["payload"]["messages"][1]["content"])
    assert system_prompt == FORMULATOR_SYSTEM_PROMPT
    assert "simple informal language" in system_prompt
    assert "expose internal IDs" in system_prompt
    assert user_prompt["current_query"] == "Ich hab Hunger"
    assert "recent_user_messages" not in user_prompt


def test_candidate_selector_limits_general_sleep_to_referral_contacts() -> None:
    app = create_app(settings())
    captured: dict[str, object] = {}

    class FakeProvider:
        def context_fits(self, evidence) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.SLEEP)

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            captured["ids"] = [offer.offer_id for offer in evidence.selected_offers]
            return ProviderAnswer(
                answer="Wende dich zuerst an die Rückmarsdorfer Straße. Danach gibt es passende Orte nach Zielgruppe.",
                card_ids=captured["ids"],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FakeProvider()
    body = TestClient(app).post(
        "/api/query", json={"query": "Wo kann ich übernachten?", "language": "de", "category": None}
    ).json()

    assert body["provider"] == "template"
    assert [card["id"] for card in body["cards"]] == ["7"]
    assert body["clarification"]["type"] == "sleep_target_group"
    assert "ids" not in captured


def test_interpreter_rejects_model_output_with_offer_id(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador

    async def response(_: dict) -> dict:
        content = json.dumps(
            {
                **_interpretation(Need.SLEEP).model_dump(mode="json"),
                "offer_id": "invented-offer",
            }
        )
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    with pytest.raises(InterpreterError, match="interpreter_contract_violation"):
        import asyncio
        asyncio.run(
            provider.interpret_query(
                query="sleep",
                language=Language.EN,
                category=None,
                aliases=app.state.service.interpreter_aliases,
            )
        )


def test_interpreter_prompt_has_versions_context_and_no_offer_index(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings("blablador"))
    provider: BlabladorProvider = app.state.service.blablador
    captured: dict[str, object] = {}

    async def response(payload: dict) -> dict:
        captured["payload"] = payload
        content = _interpretation(Need.SLEEP).model_dump_json()
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(provider, "_post", response)
    import asyncio
    interpretation = asyncio.run(
        provider.interpret_query(
            query="Wo kann ich übernachten?",
            language=Language.DE,
            category=None,
            aliases=app.state.service.interpreter_aliases,
            conversation_history=[ChatTurn(question="Ich brauche Hilfe", answer="Welche Hilfe brauchst du?")],
        )
    )
    payload = captured["payload"]
    user_prompt = json.loads(payload["messages"][1]["content"])

    assert interpretation.need == Need.SLEEP
    assert interpretation.acute_risk_status == AcuteRiskStatus.NOT_DETECTED
    assert "acute_risk_status" in payload["messages"][0]["content"]
    assert user_prompt["contract_version"] == "4"
    assert user_prompt["prompt_version"] == INTERPRETER_PROMPT_VERSION
    assert user_prompt["current_query"] == "Wo kann ich übernachten?"
    assert user_prompt["recent_user_messages"] == ["Ich brauche Hilfe"]
    assert "OFFER_INDEX" not in user_prompt
    assert "SLEEP_ROUTING_POLICY" not in user_prompt
    assert "offer_ids" not in json.dumps(user_prompt)


def test_explicit_womens_sleep_selects_only_verified_scharni_offer() -> None:
    app = create_app(settings())

    class FakeProvider:
        def context_fits(self, evidence) -> bool:
            return True

        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.SLEEP, facts={"age": 30, "gender": "female"})

        async def formulate_answer(self, **kwargs) -> ProviderAnswer:
            evidence = kwargs["evidence"]
            return ProviderAnswer(
                answer="Für Frauen gibt es ein passendes Übernachtungsangebot.",
                card_ids=[offer.offer_id for offer in evidence.selected_offers],
                answer_type=evidence.answer_type,
            )

    app.state.service.blablador = FakeProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Ich suche einen Schlafplatz für Frauen", "language": "de", "category": None},
    ).json()

    ids = [card["id"] for card in body["cards"]]
    assert ids == ["8"]
    assert body["map_marker_ids"] == ["8"]
    assert body["map_data"]["destinations"][0]["address"] == "Georg-Schumann-Str. 268, 04159 Leipzig"


def test_sleeping_bag_only_corrects_sleep_classification_and_prioritizes_hilfebus() -> None:
    app = create_app(settings())

    class ContradictoryProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.SLEEP, services=[RequestedService.CLOTHING])

        def context_fits(self, _evidence) -> bool:
            return False

    app.state.service.blablador = ContradictoryProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Wo bekomme ich einen Schlafsack?", "language": "de"},
    ).json()

    assert body["clarification"] is None
    assert body["cards"][0]["id"] == "21"
    assert "Schlafsäcke" in " ".join(body["cards"][0]["services"])
    assert "8" not in [card["id"] for card in body["cards"]]
    assert not any(marker_id.startswith("21") for marker_id in body["map_marker_ids"])


def test_combined_sleep_place_and_clothing_request_remains_sleep_routing() -> None:
    app = create_app(settings())

    class CombinedProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(
                Need.SLEEP,
                facts={"age": 30, "gender": "female"},
                services=[RequestedService.OVERNIGHT_STAY, RequestedService.CLOTHING],
            )

        def context_fits(self, _evidence) -> bool:
            return False

    app.state.service.blablador = CombinedProvider()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Ich brauche einen Schlafplatz und warme Kleidung.", "language": "de"},
    ).json()

    assert body["clarification"] is None
    assert body["cards"][0]["id"] == "8"
    assert body["map_marker_ids"] == ["8"]


def test_context_size_guard_is_applied_per_evidence_package() -> None:
    app = create_app(settings("blablador", max_chars=100))

    assert app.state.service.interpreter_available is True
    assert app.state.service.formulator_context_available is True
    health = TestClient(app).get("/api/health").json()
    assert "llm_router_available" not in health
    assert health["llm_interpreter_available"] is True
    assert health["llm_formulator_available"] is True

    offer = app.state.kb.offers[0]
    evidence = _evidence_for(app, offer, query="Eine ausreichend lange Frage nach Essen in Leipzig")
    assert app.state.service.blablador.context_fits(evidence) is False


def test_frontend_contains_required_languages_and_no_internal_source_term() -> None:
    frontend = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    frontend += (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    resources = json.loads(
        (ROOT / "app" / "resources" / "bootstrap" / "i18n" / "application_texts.json").read_text(encoding="utf-8")
    )
    english = resources["languages"]["en"]["texts"]

    for language in ("Deutsch", "English", "Polski", "Română", "Русский"):
        assert language in frontend
    for category in ("Food", "Sleep", "Medical help", "Advice"):
        assert category in english.values()
    assert english["ui.micLabel"] == "Speak question"
    assert english["ui.mainIntro"].startswith("I answer questions about help in Leipzig")
    assert "ui.voiceReady" in english
    assert "/api/i18n/copy" in frontend
    assert "SESSION_TIMEOUT_MS = 3 * 60 * 1000" in frontend
    assert "MediaRecorder" in frontend
    assert "/api/speech/transcribe" in frontend
    assert "/api/speech/synthesize" in frontend
    assert "speechSynthesis" not in frontend
    assert "submit-icon" in frontend
    assert "submitQuery(transcript)" not in frontend
    assert "replayAnswerButton" in frontend
    assert "textForSpeech" not in frontend
    assert "germanTime" not in frontend
    assert "englishTime" not in frontend
    assert "session_id: state.sessionId" in frontend
    assert "state.lastAnswer = text().error" not in frontend
    assert "speakText(text().speechIntro)" not in frontend
    assert "Wissensbasis" not in frontend
    assert "knowledge base" not in frontend.casefold()


def test_english_cards_are_loaded_from_stored_translations() -> None:
    app = create_app(settings())

    class WomenProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            return _interpretation(Need.SLEEP, facts={"age": 30, "gender": "female"})

        def context_fits(self, offers) -> bool:
            return False

    app.state.service.blablador = WomenProvider()
    client = TestClient(app)
    body = client.post(
        "/api/query",
        json={"query": "I need a place for a woman to sleep", "language": "en"},
    ).json()
    card_text = json.dumps(body["cards"], ensure_ascii=False)

    assert body["status"] == "ok"
    assert "Scharni" in card_text
    assert "Scharnhorststr. 27, 04275 Leipzig" not in card_text
    assert "Georg-Schumann-Str. 268, 04159 Leipzig" in card_text
