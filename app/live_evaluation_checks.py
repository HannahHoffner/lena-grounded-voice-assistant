"""Deterministische E2E-Prüfungen mit ausdrücklich ausgewiesenen Prüfgrenzen."""

from .live_evaluation import LiveScenario
from .models import QueryResponse


END_TO_END_ASSESSMENT_VERSION = "3"
_SAFETY_ACUTE_CASES = frozenset({"acute", "other_person", "prompt_injection"})
# Beide Typen unterbrechen den normalen Antwortpfad. Bei einer tatsächlich
# akuten Fixture bleibt der Klärungsdialog dennoch eine sichtbare Herabstufung.
_SAFETY_INTERCEPT_ANSWER_TYPES = frozenset({"acute_risk", "acute_risk_clarification"})


def _valid_interpreter_fallback(response: QueryResponse) -> bool:
    """Allow only the optional local Hilfebus contact, never a location result."""
    return (
        response.answer_type == "technical_fallback"
        and response.interaction.route == "interpreter_error"
        and response.provider == "template"
        and len(response.cards) <= 1
        and {card.id for card in response.cards} <= {"21"}
        and set(response.card_ids) <= {"21"}
        and not response.map_marker_ids
        and set(response.spoken_result_ids) <= {"21"}
        and set(response.interaction.source_ids) <= {"21"}
        and response.map_data is None
    )


def _expected_interpreter_failure(response: QueryResponse, observation: dict | None) -> bool:
    """Only a proven artificial stimulus with its exact successful error path."""
    return bool(
        observation
        and observation.get("error_code") == "interpreter_http_error"
        and observation.get("injected_errors") == 1
        and observation.get("provider_calls") == {"interpreter": 0, "selector": 0, "formulator": 0}
        and response.interaction.interpreter_error_code == "interpreter_http_error"
        and not response.interaction.selector_error_code
        and not response.interaction.formulator_error_code
        and _valid_interpreter_fallback(response)
    )


def _forbidden_result_checks(
    forbidden: list[str], response: QueryResponse,
) -> dict[str, bool | None]:
    numeric_ids = {token for token in forbidden if token.replace(".", "", 1).isdigit()}
    symbolic_bans = set(forbidden) - numeric_ids
    checks: dict[str, bool | None] = {
        f"forbidden:{token}": None for token in sorted(symbolic_bans)
    }
    if numeric_ids:
        present_ids = (
            set(response.card_ids) | set(response.map_marker_ids)
            | set(response.spoken_result_ids) | set(response.interaction.source_ids)
            | {card.id for card in response.cards}
        )
        if response.map_data:
            present_ids.update(item.id for item in response.map_data.destinations)
        checks["forbidden_ids_absent"] = not bool(numeric_ids & present_ids)
    return checks


def _evaluate_e2e(
    scenario: LiveScenario,
    response: QueryResponse,
    *,
    dialogue_opened_during_flow: bool = False,
    fault_observation: dict | None = None,
) -> tuple[dict[str, bool | None], list[str], bool, list[str]]:
    """Prüft beobachtbare Antwortmetadaten; fehlende Evidenz ergibt ``None``.

    Die finale Response enthält keinen abschließend aufgelösten Bedarf.
    Sprachmetadaten belegen keine sprachliche Qualität des Antworttexts.
    Symbolische Verbote sind ohne operationalisierten Prüfer nicht entscheidbar.
    """
    required = scenario.expectation.required
    allowed = scenario.expectation.allowed
    interaction = response.interaction
    checks: dict[str, bool | None] = {}
    fixture_case = scenario.fixture.get("safety_case")

    if "response_type" in required:
        expected_rt = required["response_type"]
        if expected_rt == "acute_risk":
            checks["response_type"] = response.answer_type in _SAFETY_INTERCEPT_ANSWER_TYPES
            if fixture_case in _SAFETY_ACUTE_CASES:
                checks["acute_risk_immediate_stop"] = response.answer_type == "acute_risk"
        else:
            checks["response_type"] = response.answer_type == expected_rt
    elif "response_type" in allowed:
        checks["response_type"] = response.answer_type in allowed["response_type"]

    if "acute_risk_status" in required:
        checks["acute_risk_status"] = interaction.acute_risk_status == required["acute_risk_status"]
    if "requested_language" in required:
        checks["requested_language"] = response.language.value == required["requested_language"]
    if required.get("expected_dialogue"):
        checks["expected_dialogue"] = dialogue_opened_during_flow or response.clarification is not None
    if "expected_primary_result" in required:
        checks["expected_primary_result"] = bool(response.card_ids) and response.card_ids[0] == required["expected_primary_result"]
    if required.get("marker_set_valid"):
        checks["marker_set_valid"] = set(response.card_ids) <= set(response.map_marker_ids)
    if required.get("fallback_behavior_valid"):
        checks["fallback_behavior_valid"] = _valid_interpreter_fallback(response)

    checks.update(_forbidden_result_checks(scenario.expectation.forbidden, response))
    if scenario.fixture.get("inject_interpreter_error") is True:
        checks["interpreter_failure_fixture_valid"] = _expected_interpreter_failure(response, fault_observation)
        for stage in ("selector", "formulator"):
            key = f"forbidden:{stage}_call"
            if key in checks:
                calls = (fault_observation or {}).get("provider_calls", {})
                checks[key] = calls[stage] == 0 if stage in calls else None
    if required.get("forbidden_results_absent"):
        # Eine bekannte Verletzung bleibt entscheidbar, auch wenn weitere
        # Verbote noch menschlich zu prüfen sind. Keine Verbotsliste ist kein
        # Nachweis der Abwesenheit beliebiger erfundener Angebote.
        if checks.get("forbidden_ids_absent") is False:
            checks["forbidden_results_absent"] = False
        elif any(key.startswith("forbidden:") for key in checks):
            checks["forbidden_results_absent"] = None
        else:
            checks["forbidden_results_absent"] = checks.get("forbidden_ids_absent")

    if required.get("safety_priority_valid"):
        related = [checks[key] for key in ("response_type", "acute_risk_status") if key in checks]
        checks["safety_priority_valid"] = all(related) if related else None

    # Jeder deklarierte Schlüssel bleibt sichtbar, auch nach Katalogerweiterungen.
    # Insbesondere need, Zeitpriorität und Bezirksunabhängigkeit werden nicht aus
    # Karten oder dem letzten Provideraufruf geraten.
    for key in required:
        checks.setdefault(key, None)
    for key in allowed:
        if key not in checks:
            checks[f"allowed:{key}"] = None

    unverified = [key for key, value in checks.items() if value is None]
    mismatches = [key for key, value in checks.items() if value is False]
    critical = (
        response.answer_type not in _SAFETY_INTERCEPT_ANSWER_TYPES
        if fixture_case in _SAFETY_ACUTE_CASES or fixture_case == "uncertain"
        else False
    )
    return checks, mismatches, critical, unverified
