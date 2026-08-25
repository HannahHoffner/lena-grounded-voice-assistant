"""Integrationspruefungen des strukturierten WP4-Dialogpfads."""

from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime, timedelta
import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.interpreter import AcuteRiskStatus, Need, QueryInterpretation, RequestedService, ScopeStatus
from app.main import create_app
from app.providers.llm import InterpreterError
from app.dialogue import load_dialogue_resource


ROOT = Path(__file__).resolve().parents[1]


def interpretation(
    need: Need,
    *,
    facts: dict[str, object] | None = None,
    scope: ScopeStatus = ScopeStatus.IN_SCOPE,
    risk: AcuteRiskStatus = AcuteRiskStatus.NOT_DETECTED,
    services: list[RequestedService] | None = None,
) -> QueryInterpretation:
    explicit = {
        "age": None,
        "age_group": "unknown",
        "gender": "unknown",
        "drug_use": "unknown",
        "no_social_benefit_entitlement": "unknown",
        "district": None,
        "requested_day": None,
        "requested_time": None,
    }
    explicit.update(facts or {})
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
            "need": need.value,
            "explicit_service_requests": [value.value for value in services or []],
            "scope_status": scope.value,
            "input_language": "de",
            "explicit_facts": explicit,
            "uncertain_hints": [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": risk.value,
        }
    )


class DialogueProvider:
    def __init__(self, responses: list[QueryInterpretation]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    async def interpret_query(self, **kwargs) -> QueryInterpretation:
        self.calls.append(kwargs)
        return self.responses.pop(0)

    def context_fits(self, offers) -> bool:
        return False


class FailingDialogueProvider(DialogueProvider):
    async def interpret_query(self, **kwargs) -> QueryInterpretation:
        self.calls.append(kwargs)
        raise InterpreterError("interpreter_timeout")


def client_with(tmp_path, responses: list[QueryInterpretation]) -> tuple[TestClient, DialogueProvider]:
    settings = Settings(
        app_root=ROOT,
        runtime_dir=tmp_path / "runtime",
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=False,
    )
    app = create_app(settings)
    provider = DialogueProvider(responses)
    app.state.service.blablador = provider
    return TestClient(app), provider


def open_sleep(client: TestClient) -> dict[str, object]:
    response = client.post("/api/query", json={"query": "Ich brauche einen Schlafplatz.", "language": "de"})
    assert response.status_code == 200
    body = response.json()
    assert [card["id"] for card in body["cards"]] == ["7"]
    assert body["clarification"]["type"] == "sleep_target_group"
    assert {choice["value"] for choice in body["clarification"]["choices"]} == {
        "under_18",
        "female",
    }
    return body


def send_choices(client: TestClient, opened: dict[str, object], values: list[str], *, language: str = "de"):
    return client.post(
        "/api/query",
        json={
            "query": "",
            "language": language,
            "session_id": opened["session_id"],
            "dialog_id": opened["clarification"]["dialog_id"],
            "choice_values": values,
        },
    )


def test_general_sleep_opens_ruecke_and_multifact_choices(tmp_path) -> None:
    client, provider = client_with(tmp_path, [interpretation(Need.SLEEP)])
    body = open_sleep(client)

    assert "freie" in body["answer"].casefold()
    assert body["clarification"]["multiple_facts_allowed"] is False
    assert provider.calls[0]["dialog_context"] is None


def test_sleep_button_female_preserves_unknown_age_and_opens_age_clarification(tmp_path) -> None:
    client, provider = client_with(tmp_path, [interpretation(Need.SLEEP)])
    opened = open_sleep(client)
    response = send_choices(client, opened, ["female"])

    assert response.status_code == 200
    body = response.json()
    assert body["clarification"]["type"] == "sleep_age"
    assert body["question"] == "Ich bin eine Frau"
    assert {card["id"] for card in body["cards"]} == {"7", "8"}
    assert "female" not in body["question"].casefold()
    assert len(provider.calls) == 1


def test_female_without_age_gets_one_short_age_followup_and_conditional_scharni(tmp_path) -> None:
    client, _ = client_with(
        tmp_path,
        [interpretation(Need.SLEEP), interpretation(Need.SLEEP, facts={"gender": "female"})],
    )
    opened = open_sleep(client)
    body = client.post(
        "/api/query",
        json={"query": "Ich bin eine Frau.", "session_id": opened["session_id"]},
    ).json()

    assert body["clarification"]["type"] == "sleep_age"
    assert body["clarification"]["choices"] == []
    assert {card["id"] for card in body["cards"]} == {"7", "8"}
    assert body["map_data"] is None or "8" not in {item["id"] for item in body["map_data"]["destinations"]}


def test_initial_explicit_female_fact_skips_redundant_target_group_question(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP, facts={"gender": "female"})])
    body = client.post(
        "/api/query",
        json={"query": "Ich bin eine Frau und brauche einen Schlafplatz.", "language": "de"},
    ).json()

    assert body["clarification"]["type"] == "sleep_age"
    assert body["clarification"]["choices"] == []
    assert {card["id"] for card in body["cards"]} == {"7", "8"}


@pytest.mark.parametrize(
    ("age", "gender", "expected_first", "forbidden"),
    [(24, "female", "8", None), (17, "female", "vkkj_notschlafstelle", "8"), (27, "female", "8", None), (31, "male", "7", None)],
)
def test_sleep_free_text_resolution_matrix(tmp_path, age, gender, expected_first, forbidden) -> None:
    client, provider = client_with(
        tmp_path,
        [interpretation(Need.SLEEP), interpretation(Need.SLEEP, facts={"age": age, "gender": gender})],
    )
    opened = open_sleep(client)
    response = client.post(
        "/api/query",
        json={"query": f"Ich bin {age}.", "language": "de", "session_id": opened["session_id"]},
    )

    assert response.status_code == 200
    body = response.json()
    ids = [card["id"] for card in body["cards"]]
    assert ids[0] == expected_first
    if forbidden:
        assert forbidden not in ids
    if age == 17:
        assert "vkkj_notschlafstelle" in body["map_marker_ids"]
        assert "vkkj_jugendnotdienst" in body["map_marker_ids"]
    assert provider.calls[1]["dialog_context"].dialog_type == "sleep_target_group"
    assert provider.calls[1]["conversation_history"] == []


def test_speech_followup_uses_same_interpreter_path_and_keeps_language_change(tmp_path) -> None:
    client, provider = client_with(
        tmp_path,
        [interpretation(Need.SLEEP), interpretation(Need.SLEEP, facts={"gender": "female"})],
    )
    opened = open_sleep(client)
    response = client.post(
        "/api/query",
        json={
            "query": "Sunt femeie.",
            "language": "ro",
            "input_mode": "speech",
            "session_id": opened["session_id"],
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["session_id"] == opened["session_id"]
    assert body["clarification"]["type"] == "sleep_age"
    assert provider.calls[1]["language"].value == "ro"


def test_speech_age_and_free_text_both_neither_and_correction_are_explicit(tmp_path) -> None:
    client, _ = client_with(
        tmp_path,
        [interpretation(Need.SLEEP), interpretation(Need.SLEEP, facts={"age": 24})],
    )
    opened = open_sleep(client)
    spoken = client.post(
        "/api/query",
        json={"query": "24", "input_mode": "speech", "session_id": opened["session_id"]},
    ).json()
    assert spoken["cards"][0]["id"] == "7"

    for text, facts, expected in (
        ("Ich bin unter 18", {"age_group": "under_18"}, "vkkj_jugendnotdienst"),
        ("Ich bin mindestens 18", {"age_group": "adult"}, "7"),
        ("Nein, ich bin 27", {"age": 27}, "7"),
    ):
        local, _ = client_with(tmp_path / text.replace(" ", "_"), [interpretation(Need.SLEEP), interpretation(Need.SLEEP, facts=facts)])
        current = open_sleep(local)
        resolved = local.post("/api/query", json={"query": text, "session_id": current["session_id"]}).json()
        assert resolved["cards"][0]["id"] == expected


def test_schoppi_dialog_resolves_sleep_and_day_support_without_drug_inference(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.UNKNOWN), interpretation(Need.UNKNOWN)])
    sleep_open = client.post("/api/query", json={"query": "Wo ist Schoppi?", "language": "de"}).json()
    assert sleep_open["clarification"]["type"] == "organization_need"
    sleep = send_choices(client, sleep_open, ["sleep"]).json()
    assert [card["id"] for card in sleep["cards"]] == ["6"]

    day_open = client.post("/api/query", json={"query": "Wo ist A1?", "language": "de"}).json()
    day = send_choices(client, day_open, ["day_support"]).json()
    assert [card["id"] for card in day["cards"]] == ["11"]


def test_schoppi_with_explicit_sleep_need_skips_redundant_need_question(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP, services=[RequestedService.OVERNIGHT_STAY])])
    body = client.post(
        "/api/query",
        json={"query": "Ich möchte bei Schoppi schlafen.", "language": "de"},
    ).json()

    assert [card["id"] for card in body["cards"]] == ["6"]
    assert body["clarification"] is None


def test_kuebel_requires_place_and_gruenau_never_guesses_another_team(tmp_path) -> None:
    client, _ = client_with(
        tmp_path,
        [interpretation(Need.ADVICE), interpretation(Need.ADVICE, facts={"district": "Grünau"})],
    )
    opened = client.post("/api/query", json={"query": "Ich suche Kübel", "language": "de"}).json()
    assert opened["clarification"]["type"] == "organization_district"
    resolved = client.post(
        "/api/query",
        json={"query": "in Grünau", "language": "de", "session_id": opened["session_id"]},
    ).json()
    assert {card["id"] for card in resolved["cards"]}.issubset({"19.2", "21"})
    assert "19.1" not in {card["id"] for card in resolved["cards"]}
    assert "19.3" not in {card["id"] for card in resolved["cards"]}


def test_general_help_choice_and_unresolved_answer_falls_back_to_curated_hilfebus(tmp_path) -> None:
    client, _ = client_with(
        tmp_path,
        [interpretation(Need.GENERAL_HELP), interpretation(Need.GENERAL_HELP), interpretation(Need.GENERAL_HELP)],
    )
    opened = client.post("/api/query", json={"query": "Ich brauche Hilfe", "language": "de"}).json()
    assert opened["clarification"]["type"] == "general_need"
    food = send_choices(client, opened, ["food"]).json()
    assert food["cards"]
    assert food["clarification"] is None

    unclear = client.post("/api/query", json={"query": "Hilfe", "language": "de"}).json()
    fallback = client.post(
        "/api/query",
        json={"query": "weiß nicht", "language": "de", "session_id": unclear["session_id"]},
    ).json()
    assert [card["id"] for card in fallback["cards"]] == ["21"]
    assert "Hilfebus" in fallback["answer"]
    assert "täglich 18:00" in fallback["answer"]
    assert "23:00" in fallback["answer"]
    assert fallback["cards"][0]["address"] is None
    assert fallback["map_data"] is None


def test_unknown_need_choice_and_unresolved_answer_falls_back_to_curated_hilfebus(tmp_path) -> None:
    """AP10: ein unklares/unverständliches need=unknown erhält dieselbe
    Ein-Frage-Klärung und Hilfebus-Eskalation wie need=general_help, statt in
    der generischen No-Results-Antwort ohne Rückfrage zu enden."""
    client, _ = client_with(
        tmp_path,
        [interpretation(Need.UNKNOWN), interpretation(Need.UNKNOWN), interpretation(Need.UNKNOWN)],
    )
    opened = client.post("/api/query", json={"query": "@@@ ???", "language": "de"}).json()
    assert opened["clarification"]["type"] == "general_need"
    food = send_choices(client, opened, ["food"]).json()
    assert food["cards"]
    assert food["clarification"] is None

    unclear = client.post("/api/query", json={"query": "???", "language": "de"}).json()
    fallback = client.post(
        "/api/query",
        json={"query": "weiß nicht", "language": "de", "session_id": unclear["session_id"]},
    ).json()
    assert [card["id"] for card in fallback["cards"]] == ["21"]
    assert "Hilfebus" in fallback["answer"]


def test_unclear_scope_with_unknown_need_also_opens_general_clarification(tmp_path) -> None:
    """Der neue Auslöser greift unabhängig davon, ob der Interpreter need=unknown
    mit scope_status=in_scope oder scope_status=unclear meldet."""
    client, _ = client_with(tmp_path, [interpretation(Need.UNKNOWN, scope=ScopeStatus.UNCLEAR)])
    opened = client.post("/api/query", json={"query": "@@@ ???", "language": "de"}).json()
    assert opened["clarification"]["type"] == "general_need"


def test_unintelligible_sleep_answer_ends_dialog_with_hilfebus_instead_of_loop(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP), interpretation(Need.SLEEP)])
    opened = open_sleep(client)
    fallback = client.post(
        "/api/query",
        json={"query": "hm?", "language": "de", "session_id": opened["session_id"]},
    ).json()

    assert fallback["clarification"] is None
    assert [card["id"] for card in fallback["cards"]] == ["21"]


def test_topic_change_safety_scope_and_interpreter_failure_close_or_preserve_correctly(tmp_path) -> None:
    responses = [
        interpretation(Need.SLEEP),
        interpretation(Need.TOILET),
        interpretation(Need.SLEEP),
        interpretation(Need.UNKNOWN, risk=AcuteRiskStatus.DETECTED),
        interpretation(Need.SLEEP),
        interpretation(Need.UNKNOWN, scope=ScopeStatus.OUT_OF_SCOPE),
    ]
    client, _ = client_with(tmp_path, responses)
    first = open_sleep(client)
    toilet = client.post("/api/query", json={"query": "Wo ist eine Toilette?", "session_id": first["session_id"]}).json()
    assert toilet["clarification"] is None

    risk_open = open_sleep(client)
    risk = client.post("/api/query", json={"query": "Ich bin jetzt akut in Gefahr", "session_id": risk_open["session_id"]}).json()
    assert risk["cards"] == [] and risk["clarification"] is None and "112" in risk["answer"]

    scope_open = open_sleep(client)
    scope = client.post("/api/query", json={"query": "Wie ist das Wetter?", "session_id": scope_open["session_id"]}).json()
    assert scope["cards"] == [] and scope["clarification"] is None


def test_dialog_id_choice_and_replay_validation_is_redacted(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP)])
    opened = open_sleep(client)
    invalid = send_choices(client, opened, ["manipulated"])
    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "dialog_response_invalid"
    assert "female" not in invalid.text

    accepted = send_choices(client, opened, ["under_18"])
    assert accepted.status_code == 200
    replay = send_choices(client, opened, ["under_18"])
    assert replay.status_code == 409


def test_interpreter_timeout_closes_open_dialog_and_fails_closed_without_results(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP)])
    opened = open_sleep(client)
    failing = FailingDialogueProvider([])
    client.app.state.service.blablador = failing

    response = client.post(
        "/api/query",
        json={"query": "unverständlich", "session_id": opened["session_id"]},
    )
    body = response.json()

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises, sofern die Wissensbasis ihn
    # liefert; der offene Fachdialog selbst bleibt trotzdem geschlossen, ohne
    # dass Dialogfakten übernommen werden.
    offer = next(offer for offer in client.app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    assert response.status_code == 200
    assert body["status"] == "error"
    assert body["clarification"] is None
    assert [card["id"] for card in body["cards"]] == [offer.id]
    assert body["map_data"] is None
    assert body["answer_type"] == "technical_fallback"
    assert "112" in body["answer"]
    assert "Hilfebus" in body["answer"]


def test_expired_foreign_and_missing_session_dialog_answers_are_rejected(tmp_path) -> None:
    client, _ = client_with(tmp_path, [interpretation(Need.SLEEP), interpretation(Need.SLEEP)])
    first = open_sleep(client)
    second = open_sleep(client)

    foreign = client.post(
        "/api/query",
        json={
            "session_id": second["session_id"],
            "dialog_id": first["clarification"]["dialog_id"],
            "choice_values": ["under_18"],
        },
    )
    assert foreign.status_code == 409
    missing = client.post(
        "/api/query",
        json={"dialog_id": first["clarification"]["dialog_id"], "choice_values": ["under_18"]},
    )
    assert missing.status_code == 422

    service = client.app.state.service
    session = service.sessions.get(first["session_id"])
    assert session and session.dialog
    session.dialog.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    service.sessions.save(session)
    expired = send_choices(client, first, ["under_18"])
    assert expired.status_code == 409


def test_dialog_copy_has_five_languages_and_explicit_review_status_in_health(tmp_path) -> None:
    client, _ = client_with(tmp_path, [])
    for language in ("de", "en", "pl", "ro", "ru"):
        copy = client.get(f"/api/dialogue/copy?language={language}").json()
        assert copy["copy_version"] == "7"
        assert copy["prompts"]["general_need"]
    summary = client.get("/api/health").json()["application_texts"]
    assert summary["languages"]["de"]["review_pending"] > 0
    for language in ("en", "pl", "ro", "ru"):
        assert summary["languages"][language]["machine"] > 0
    assert all(item["reviewed"] == 0 for item in summary["languages"].values())


@pytest.mark.parametrize(
    ("language", "expected_labels"),
    [
        ("de", ["Ich bin unter 18", "Ich bin eine Frau"]),
        ("en", ["I am under 18", "I am a woman"]),
        ("pl", ["Mam mniej niż 18 lat", "Jestem kobietą"]),
        ("ro", ["Am sub 18 ani", "Sunt femeie"]),
        ("ru", ["Мне меньше 18 лет", "Я женщина"]),
    ],
)
def test_sleep_dialog_exposes_only_minor_and_female_choices_in_all_languages(
    tmp_path, language: str, expected_labels: list[str]
) -> None:
    client, _ = client_with(tmp_path / language, [interpretation(Need.SLEEP)])
    response = client.post(
        "/api/query",
        json={"query": "synthetic sleep request", "language": language},
    )

    assert response.status_code == 200
    choices = response.json()["clarification"]["choices"]
    assert [choice["value"] for choice in choices] == ["under_18", "female"]
    assert [choice["label"] for choice in choices] == expected_labels


@pytest.mark.parametrize(
    ("content", "code"),
    [(None, "application_text_resource_missing"), ("{}", "application_text_resource_invalid")],
)
def test_missing_or_invalid_dialogue_resource_has_redacted_error(tmp_path, monkeypatch, content, code) -> None:
    root = tmp_path / "bootstrap"
    if content is not None:
        path = root / "i18n" / "application_texts.json"
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")
    from app.application_texts import load_application_texts

    load_application_texts.cache_clear()
    monkeypatch.setattr("app.application_texts.packaged_bootstrap_data_root", lambda: root)
    try:
        with pytest.raises(RuntimeError, match=code):
            load_dialogue_resource()
    finally:
        load_application_texts.cache_clear()


def test_sensitive_button_value_is_not_written_to_interaction_log(tmp_path) -> None:
    log_path = tmp_path / "runtime" / "interactions.jsonl"
    settings = Settings(
        app_root=ROOT,
        runtime_dir=tmp_path / "runtime",
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_log_path=log_path,
        interaction_logging_enabled=True,
    )
    app = create_app(settings)
    app.state.service.blablador = DialogueProvider([interpretation(Need.SLEEP)])
    client = TestClient(app)
    opened = open_sleep(client)
    send_choices(client, opened, ["under_18"])

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    choice_record = records[-1]
    assert choice_record["user_query"] == ""
    assert choice_record["dialog_type"] == "sleep_target_group"
    assert choice_record["dialog_attempt_count"] == 1
    assert "under_18" not in json.dumps(choice_record, ensure_ascii=False)
