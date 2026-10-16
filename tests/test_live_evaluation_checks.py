"""Geschlossene E2E-Prüfungen und explizite Grenzen ohne Provideraufrufe."""

import pytest

from app.live_evaluation import (
    EvaluationComponent,
    EvaluationStage,
    LiveScenario,
    ScenarioExpectation,
    load_live_scenario_catalog,
)
from app.live_evaluation_runner import _evaluate_e2e
from app.models import (
    Language,
    MapData,
    MapDestination,
    MapOrigin,
    OfferCard,
    QueryResponse,
)


def _scenario(*, required=None, allowed=None, forbidden=None) -> LiveScenario:
    return LiveScenario(
        scenario_id="t_explicit_checks",
        component=EvaluationComponent.END_TO_END,
        language="de",
        synthetic_inputs=["Synthetischer Prüftext"],
        expectation=ScenarioExpectation(
            required=required or {}, allowed=allowed or {}, forbidden=forbidden or [],
        ),
    )


def _response() -> QueryResponse:
    return QueryResponse(
        answer="Synthetische Antwort.", language=Language.DE,
        provider="template", status="ok",
    )


@pytest.mark.parametrize("expected,valid", [("de", True), ("ro", False)])
def test_requested_language_checks_response_metadata(expected: str, valid: bool) -> None:
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"requested_language": expected}), _response(),
    )
    assert checks["requested_language"] is valid
    assert mismatches == ([] if valid else ["requested_language"])
    assert unverified == []


def test_need_is_unverified_without_final_need_metadata() -> None:
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"need": "food"}), _response(),
    )
    assert checks["need"] is None
    assert mismatches == []
    assert unverified == ["need"]


@pytest.mark.parametrize("surface", ["card_ids", "cards", "map_marker_ids", "map_data", "source_ids", "spoken_result_ids"])
def test_forbidden_numeric_id_is_checked_on_every_output_surface(surface: str) -> None:
    response = _response()
    if surface == "cards":
        response.cards = [OfferCard(id="1", name="Test", short_description="Test")]
    elif surface == "map_data":
        response.map_data = MapData(
            origin=MapOrigin(id="origin", label="Test", address="Test", latitude=51.3, longitude=12.3),
            destinations=[MapDestination(id="1", label="Test", address="Test", latitude=51.3, longitude=12.3)],
        )
    elif surface == "source_ids":
        response.interaction.source_ids = ["1"]
    else:
        setattr(response, surface, ["1"])
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"forbidden_results_absent": True}, forbidden=["1"]), response,
    )
    assert checks["forbidden_ids_absent"] is False
    assert checks["forbidden_results_absent"] is False
    assert set(mismatches) == {"forbidden_ids_absent", "forbidden_results_absent"}
    assert unverified == []


def test_absent_numeric_id_is_verified_but_symbolic_ban_is_not_guessed() -> None:
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"forbidden_results_absent": True}, forbidden=["1", "invented_offer"]),
        _response(),
    )
    assert checks["forbidden_ids_absent"] is True
    assert checks["forbidden_results_absent"] is None
    assert checks["forbidden:invented_offer"] is None
    assert set(unverified) == {"forbidden_results_absent", "forbidden:invented_offer"}
    assert mismatches == []


def test_known_violation_is_not_hidden_by_an_unverified_ban() -> None:
    response = _response()
    response.card_ids = ["1"]
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"forbidden_results_absent": True}, forbidden=["1", "invented_offer"]), response,
    )
    assert checks["forbidden_results_absent"] is False
    assert "forbidden_results_absent" in mismatches
    assert "forbidden:invented_offer" in unverified


@pytest.mark.parametrize("forbidden,expected", [(["1"], True), ([], None)])
def test_result_absence_requires_an_explicit_operationalized_ban(forbidden, expected) -> None:
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"forbidden_results_absent": True}, forbidden=forbidden), _response(),
    )
    assert checks["forbidden_results_absent"] is expected
    assert mismatches == []
    assert ("forbidden_results_absent" in unverified) == (expected is None)


def test_unknown_required_and_allowed_conditions_remain_visible() -> None:
    checks, mismatches, _critical, unverified = _evaluate_e2e(
        _scenario(required={"future_check": True}, allowed={"additional_results": ["7"]}),
        _response(),
    )
    assert checks == {"future_check": None, "allowed:additional_results": None}
    assert set(unverified) == set(checks)
    assert mismatches == []


def test_required_catalog_keys_never_silently_disappear() -> None:
    catalog = load_live_scenario_catalog()
    for scenario in catalog.scenarios_for(EvaluationStage.END_TO_END):
        checks, _mismatches, _critical, unverified = _evaluate_e2e(scenario, _response())
        assert set(scenario.expectation.required) <= set(checks), scenario.scenario_id
        assert all(
            key in checks or f"allowed:{key}" in checks
            for key in scenario.expectation.allowed
        ), scenario.scenario_id
        assert set(unverified) == {key for key, value in checks.items() if value is None}
