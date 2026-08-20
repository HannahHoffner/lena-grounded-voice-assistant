"""Vertrags- und Integrationsprüfungen der deterministischen WP9A-Safety-Policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application_texts import APPLICATION_COPY_VERSION, application_text, load_application_texts
from app.config import Settings
from app.dialogue import DIALOG_CONTRACT_VERSION
from app.interpreter import AcuteRiskStatus, Need, QueryInterpretation, ScopeStatus
from app.main import create_app
from app.models import Language
from app.policy_facts import EMERGENCY_POLICY
from app.providers.llm import InterpreterError
from app.safety import (
    SAFETY_POLICY_VERSION,
    SAFETY_PREFLIGHT_VERSION,
    SafetyTextKind,
    load_safety_scenarios,
    preflight_detects_immediate_danger,
    safety_text,
)
from app.service import _general_help_contact


ROOT = Path(__file__).resolve().parents[1]


def settings(tmp_path: Path, *, interaction_logging: bool = False) -> Settings:
    return Settings(
        app_root=ROOT,
        runtime_dir=tmp_path / "runtime",
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=interaction_logging,
        interaction_log_path=tmp_path / "interactions.jsonl",
    )


def interpretation(
    risk: AcuteRiskStatus,
    *,
    need: Need = Need.SLEEP,
    scope: ScopeStatus = ScopeStatus.IN_SCOPE,
) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
            "need": need.value,
            "explicit_service_requests": ["overnight_stay"] if need == Need.SLEEP else [],
            "scope_status": scope.value,
            "input_language": "de",
            "explicit_facts": {
                "age": None,
                "age_group": "unknown",
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


class QueueProvider:
    def __init__(self, responses: list[QueryInterpretation | Exception]) -> None:
        self.responses = responses
        self.interpreter_calls = 0
        self.selector_calls = 0
        self.formulator_calls = 0

    async def interpret_query(self, **_kwargs) -> QueryInterpretation:
        self.interpreter_calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def select_candidates(self, **_kwargs):
        self.selector_calls += 1
        raise AssertionError("selector must not run in a safety path")

    async def formulate_answer(self, **_kwargs):
        self.formulator_calls += 1
        raise AssertionError("formulator must not run in a safety path")

    def context_fits(self, _evidence) -> bool:
        return False


def post(client: TestClient, query: str, language: Language = Language.DE, **extra):
    return client.post(
        "/api/query",
        json={"query": query, "language": language.value, **extra},
    )


def assert_safety_stop(body: dict[str, object], language: Language, kind: SafetyTextKind) -> None:
    assert body["answer"] == safety_text(language, kind)
    assert body["answer_type"] in {"acute_risk", "technical_fallback"}
    assert body["cards"] == []
    assert body["card_ids"] == []
    assert body["map_marker_ids"] == []
    assert body["map_data"] is None
    assert body["clarification"] is None
    assert body["answer"].count("112") == 1


def assert_technical_hilfebus_stop(body: dict[str, object], app, language: Language) -> None:
    """Wie assert_safety_stop, aber für den Interpreter-Ausfall mit Hilfebus-Kontakt.

    Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5) enthält
    der reine 112-Text zusätzlich den deterministischen Hilfebus-Kontakt, sobald
    die Wissensbasis ihn liefert -- siehe `_technical_safety_fallback()` in
    `app/service.py` und `docs/safety-and-error-policy.md`.
    """
    offer = _general_help_contact(app.state.kb.offers)
    assert offer is not None, "Testfixtur ohne Hilfebus-Kontakt in der Wissensbasis"
    phone = ", ".join(offer.phone_numbers) or "—"
    times = "; ".join(offer.opening_hours_raw or offer.standzeiten_raw) or "—"
    expected_answer = safety_text(language, SafetyTextKind.TECHNICAL_HILFEBUS, phone=phone, times=times)
    assert body["answer"] == expected_answer
    assert body["answer_type"] == "technical_fallback"
    assert [card["id"] for card in body["cards"]] == [offer.id]
    assert body["card_ids"] == [offer.id]
    assert body["clarification"] is None
    assert body["answer"].count("112") == 1


def test_policy_fact_is_single_versioned_112_with_official_references() -> None:
    assert EMERGENCY_POLICY.policy_version == "1"
    assert EMERGENCY_POLICY.emergency_number == "112"
    assert EMERGENCY_POLICY.source_urls == (
        "https://www.bbk.bund.de/DE/Warnung-Vorsorge/Vorsorge/Gesundheit-und-Hygiene/Erste-Hilfe-und-Notruf/erste-hilfe-und-notruf_node.html",
        "https://digital-strategy.ec.europa.eu/en/policies/112",
    )


def test_versioned_synthetic_catalog_covers_all_languages_and_required_groups() -> None:
    catalog = load_safety_scenarios()
    assert catalog.synthetic_data_only is True
    assert len(catalog.scenarios) == 19
    assert {item.scenario_group for item in catalog.scenarios} == {"detected", "uncertain", "not_detected"}
    assert all(set(item.synthetic_inputs) == set(Language) for item in catalog.scenarios)


def test_narrow_preflight_detects_catalogue_immediate_cases_without_provider(tmp_path) -> None:
    """Ein Preflight-Treffer öffnet den bestätigenden Safety-Dialog, kein Sofort-Stopp.

    Der enge Preflight läuft vor jedem Interpreteraufruf; ein Treffer kann nicht
    zwischen einer echten Akutformulierung und einem exakt wortgleichen Zitat
    unterscheiden. Ein sofortiger 112-Stopp ohne Rückfragemöglichkeit wäre daher
    zu weitgehend; stattdessen wird dieselbe bestätigende Rückfrage wie bei einem
    vom Interpreter gemeldeten unsicheren Risiko gestellt.
    """
    catalog = load_safety_scenarios()
    app = create_app(settings(tmp_path))
    provider = QueueProvider([])
    app.state.service.blablador = provider
    client = TestClient(app)

    for scenario in catalog.scenarios:
        for language, query in scenario.synthetic_inputs.items():
            hit = preflight_detects_immediate_danger(query)
            if scenario.scenario_group == "detected":
                assert hit, (scenario.scenario_id, language)
                body = post(client, query, language).json()
                assert body["answer_type"] == "acute_risk_clarification"
                assert body["cards"] == [] and body["map_data"] is None
                assert body["clarification"]["type"] == "acute_risk_confirmation"
                assert "112" not in body["answer"]
            else:
                assert not hit, (scenario.scenario_id, language)
    assert provider.interpreter_calls == 0


def test_catalogue_uncertain_and_nonacute_control_paths_cover_five_languages(tmp_path: Path) -> None:
    catalog = load_safety_scenarios()
    uncertain = [item for item in catalog.scenarios if item.scenario_group == "uncertain"]
    nonacute = [item for item in catalog.scenarios if item.scenario_group == "not_detected"]

    uncertain_app = create_app(settings(tmp_path / "uncertain"))
    uncertain_provider = QueueProvider(
        [interpretation(AcuteRiskStatus.UNCERTAIN) for _ in range(len(uncertain) * len(Language))]
    )
    uncertain_app.state.service.blablador = uncertain_provider
    uncertain_client = TestClient(uncertain_app)
    for scenario in uncertain:
        for language, query in scenario.synthetic_inputs.items():
            body = post(uncertain_client, query, language).json()
            assert body["answer_type"] == scenario.expected_policy_path
            assert body["clarification"]["type"] == "acute_risk_confirmation"
            assert body["cards"] == [] and body["map_data"] is None

    nonacute_app = create_app(settings(tmp_path / "nonacute"))
    nonacute_provider = QueueProvider(
        [
            interpretation(
                AcuteRiskStatus.NOT_DETECTED,
                need=Need.UNKNOWN,
                scope=ScopeStatus.OUT_OF_SCOPE,
            )
            for _ in range(len(nonacute) * len(Language))
        ]
    )
    nonacute_app.state.service.blablador = nonacute_provider
    nonacute_client = TestClient(nonacute_app)
    for scenario in nonacute:
        for language, query in scenario.synthetic_inputs.items():
            body = post(nonacute_client, query, language).json()
            assert body["answer_type"] == "out_of_scope"
            assert body["clarification"] is None
            assert body["cards"] == [] and body["map_data"] is None
            assert "112" not in body["answer"]


@pytest.mark.parametrize("language", list(Language))
def test_interpreter_detected_wins_over_scope_and_returns_no_results(
    tmp_path: Path,
    language: Language,
) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([
        interpretation(AcuteRiskStatus.DETECTED, need=Need.UNKNOWN, scope=ScopeStatus.OUT_OF_SCOPE)
    ])
    app.state.service.blablador = provider
    body = post(TestClient(app), "ambiguous synthetic input", language).json()

    assert_safety_stop(body, language, SafetyTextKind.DETECTED)
    assert provider.interpreter_calls == 1
    assert provider.selector_calls == provider.formulator_calls == 0


def test_uncertain_opens_single_structured_safety_dialog_without_results(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([interpretation(AcuteRiskStatus.UNCERTAIN)])
    app.state.service.blablador = provider
    body = post(TestClient(app), "synthetic uncertain statement").json()

    assert body["answer_type"] == "acute_risk_clarification"
    assert body["cards"] == [] and body["map_data"] is None
    assert body["clarification"]["type"] == "acute_risk_confirmation"
    assert {choice["value"] for choice in body["clarification"]["choices"]} == {
        "immediate_danger_yes",
        "immediate_danger_no",
        "immediate_danger_unsure",
    }
    assert provider.selector_calls == provider.formulator_calls == 0


@pytest.mark.parametrize(
    ("choice", "kind"),
    [
        ("immediate_danger_yes", SafetyTextKind.DETECTED),
        ("immediate_danger_unsure", SafetyTextKind.UNCERTAIN),
    ],
)
def test_safety_dialog_yes_and_unsure_stop_without_another_provider_call(
    tmp_path: Path,
    choice: str,
    kind: SafetyTextKind,
) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([interpretation(AcuteRiskStatus.UNCERTAIN)])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain statement").json()
    body = post(
        client,
        "",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
        choice_values=[choice],
    ).json()

    assert_safety_stop(body, Language.DE, kind)
    assert provider.interpreter_calls == 1


def test_safety_dialog_no_resumes_structured_need_without_risk_fact(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([interpretation(AcuteRiskStatus.UNCERTAIN)])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain sleep request").json()
    body = post(
        client,
        "",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
        choice_values=["immediate_danger_no"],
    ).json()

    assert body["answer_type"] == "clarification"
    assert body["clarification"]["type"] == "sleep_target_group"
    assert [card["id"] for card in body["cards"]] == ["7"]
    assert provider.interpreter_calls == 1


def _preflight_trigger_query(language: Language = Language.DE) -> str:
    catalog = load_safety_scenarios()
    scenario = next(item for item in catalog.scenarios if item.scenario_id == "immediate_self_harm")
    return scenario.synthetic_inputs[language]


@pytest.mark.parametrize(
    ("choice", "kind"),
    [
        ("immediate_danger_yes", SafetyTextKind.DETECTED),
        ("immediate_danger_unsure", SafetyTextKind.UNCERTAIN),
    ],
)
def test_preflight_triggered_dialog_yes_and_unsure_stop_without_provider_call(
    tmp_path: Path,
    choice: str,
    kind: SafetyTextKind,
) -> None:
    """Der Preflight ruft keinen Provider auf; Bestätigung oder Unsicherheit stoppen konservativ."""
    app = create_app(settings(tmp_path))
    provider = QueueProvider([])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, _preflight_trigger_query()).json()
    assert opened["answer_type"] == "acute_risk_clarification"
    body = post(
        client,
        "",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
        choice_values=[choice],
    ).json()

    assert_safety_stop(body, Language.DE, kind)
    assert provider.interpreter_calls == 0


def test_preflight_triggered_dialog_no_opens_general_need_clarification_without_provider_call(
    tmp_path: Path,
) -> None:
    """Ohne echte Interpretation ist kein Bedarf bekannt; die Verneinung fragt ihn allgemein nach."""
    app = create_app(settings(tmp_path))
    provider = QueueProvider([])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, _preflight_trigger_query()).json()
    body = post(
        client,
        "",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
        choice_values=["immediate_danger_no"],
    ).json()

    assert body["answer_type"] == "clarification"
    assert body["clarification"]["type"] == "general_need"
    assert body["cards"] == []
    assert provider.interpreter_calls == 0


def test_preflight_triggered_dialog_explicit_free_text_no_resumes_via_fresh_interpretation(
    tmp_path: Path,
) -> None:
    """Eine exakte Freitextverneinung löst den Dialog auf; der reale Bedarf kommt aus der Neuinterpretation."""
    app = create_app(settings(tmp_path))
    provider = QueueProvider([interpretation(AcuteRiskStatus.NOT_DETECTED, need=Need.SLEEP)])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, _preflight_trigger_query()).json()
    body = post(
        client,
        "Nein.",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
    ).json()

    assert body["answer_type"] == "clarification"
    assert body["clarification"]["type"] == "sleep_target_group"
    assert provider.interpreter_calls == 1


def test_free_text_denial_needs_both_validated_model_status_and_explicit_words(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider(
        [
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.NOT_DETECTED),
        ]
    )
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain sleep request").json()
    resumed = post(client, "Nein", session_id=opened["session_id"]).json()
    assert resumed["clarification"]["type"] == "sleep_target_group"

    second_app = create_app(settings(tmp_path / "model_only"))
    second_provider = QueueProvider(
        [
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.NOT_DETECTED, need=Need.TOILET),
        ]
    )
    second_app.state.service.blablador = second_provider
    second_client = TestClient(second_app)
    second_opened = post(second_client, "synthetic uncertain sleep request").json()
    not_cleared = post(second_client, "Wo ist eine Toilette?", session_id=second_opened["session_id"]).json()
    assert not_cleared["clarification"]["type"] == "acute_risk_confirmation"
    assert not_cleared["cards"] == []


def test_topic_change_does_not_clear_open_safety_dialog(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider(
        [
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.UNCERTAIN, need=Need.TOILET),
        ]
    )
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain sleep request").json()
    body = post(client, "Wo ist eine Toilette?", session_id=opened["session_id"]).json()

    assert body["answer_type"] == "acute_risk_clarification"
    assert body["cards"] == [] and body["map_data"] is None
    assert body["clarification"]["type"] == "acute_risk_confirmation"


def test_language_change_and_speech_text_preserve_open_safety_dialog(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider(
        [
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.UNCERTAIN),
        ]
    )
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain statement", Language.DE).json()
    continued = post(
        client,
        "răspuns neclar",
        Language.RO,
        session_id=opened["session_id"],
        input_mode="speech",
    ).json()
    assert continued["language"] == "ro"
    assert continued["clarification"]["type"] == "acute_risk_confirmation"
    assert continued["clarification"]["prompt"] == application_text(
        Language.RO,
        "dialogue.prompts.acute_risk_confirmation",
    )


def test_safety_dialog_rejects_manipulated_choice_and_fingerprint_change(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([interpretation(AcuteRiskStatus.UNCERTAIN)])
    app.state.service.blablador = provider
    client = TestClient(app)
    opened = post(client, "synthetic uncertain statement").json()
    invalid = post(
        client,
        "",
        session_id=opened["session_id"],
        dialog_id=opened["clarification"]["dialog_id"],
        choice_values=["female"],
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "dialog_response_invalid"

    replaced = app.state.service.sessions.resolve(
        opened["session_id"],
        Language.DE,
        "different-safe-fingerprint-0000000000000000",
    )
    assert replaced.dialog is None
    assert replaced.turns == []


def test_second_unresolved_safety_answer_ends_conservatively(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider(
        [
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.UNCERTAIN),
            interpretation(AcuteRiskStatus.UNCERTAIN),
        ]
    )
    app.state.service.blablador = provider
    client = TestClient(app)
    first = post(client, "synthetic uncertain statement").json()
    retry = post(client, "unverständlich", session_id=first["session_id"]).json()
    assert retry["clarification"]["type"] == "acute_risk_confirmation"
    final = post(client, "weiterhin unverständlich", session_id=retry["session_id"]).json()
    assert_safety_stop(final, Language.DE, SafetyTextKind.UNCERTAIN)


@pytest.mark.parametrize(
    "error",
    [
        InterpreterError("interpreter_timeout"),
        InterpreterError("interpreter_http_error"),
        InterpreterError("interpreter_invalid_json"),
        InterpreterError("interpreter_schema_error"),
        InterpreterError("interpreter_contract_violation"),
    ],
)
def test_interpreter_failures_are_closed_with_conditional_112(
    tmp_path: Path,
    error: InterpreterError,
) -> None:
    app = create_app(settings(tmp_path))
    provider = QueueProvider([error])
    app.state.service.blablador = provider
    body = post(TestClient(app), "synthetic normal request").json()

    assert_technical_hilfebus_stop(body, app, Language.DE)
    assert body["status"] == "error"
    assert provider.selector_calls == provider.formulator_calls == 0


def test_unavailable_interpreter_is_fail_closed_and_not_lexically_routed(tmp_path: Path) -> None:
    app = create_app(settings(tmp_path))
    body = post(TestClient(app), "Ich brauche Essen.").json()
    assert_technical_hilfebus_stop(body, app, Language.DE)


def test_safety_session_and_interaction_log_redact_danger_text(tmp_path: Path) -> None:
    dangerous = "synthetic detailed danger text that must not persist"
    app = create_app(settings(tmp_path, interaction_logging=True))
    provider = QueueProvider([interpretation(AcuteRiskStatus.UNCERTAIN)])
    app.state.service.blablador = provider
    body = post(TestClient(app), dangerous).json()

    session_text = (tmp_path / "runtime" / "sessions.json").read_text(encoding="utf-8")
    log_text = (tmp_path / "interactions.jsonl").read_text(encoding="utf-8")
    record = json.loads(log_text)
    assert dangerous not in session_text
    assert dangerous not in log_text
    assert record["user_query"] == "[redacted_safety_input]"
    assert record["acute_risk_status"] == "uncertain"
    assert record["safety_path"] == "uncertain_dialog"
    assert body["history"][-1]["question"] == application_text(Language.DE, "safety.redacted_input")


def test_health_reports_redacted_safety_contract_and_honest_language_status(tmp_path: Path) -> None:
    health = TestClient(create_app(settings(tmp_path))).get("/api/health").json()
    resource = load_application_texts()
    assert health["safety_policy_version"] == SAFETY_POLICY_VERSION
    assert health["safety_preflight_version"] == SAFETY_PREFLIGHT_VERSION
    assert health["safety_dialogue_contract_version"] == DIALOG_CONTRACT_VERSION
    assert health["safety_text_resource_version"] == APPLICATION_COPY_VERSION
    assert health["technical_fallback_includes_emergency_guidance"] is True
    assert health["supported_safety_languages"] == [item.value for item in Language]
    assert health["safety_translation_status_by_language"] == {
        language.value: resource.languages[language].linguistic_review_status.value
        for language in Language
    }
