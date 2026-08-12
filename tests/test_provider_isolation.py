"""Regression tests for provider-free tests and explicit live-smoke consent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

import app.config as config
import app.multilingual_review as multilingual_review
from app.config import Settings
from app.live_evaluation import EvaluationStage, load_live_scenario_catalog, require_live_authorization
from app.providers.llm import BlabladorProvider


ROOT = Path(__file__).resolve().parents[1]


def _provider_settings(tmp_path: Path, *, formulator_model: str | None = None) -> Settings:
    return Settings(
        app_root=tmp_path,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="blablador",
        blablador_base_url="https://provider.example/v1",
        blablador_api_key="test-token",
        blablador_model="test-model",
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        blablador_formulator_model=formulator_model,
        wfs_auto_sync=False,
        toilet_auto_sync=False,
        interaction_logging_enabled=False,
    )


def test_pytest_does_not_load_checkout_env_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".env").write_text(
        "REWRITE_PROVIDER=blablador\nBLABLADOR_API_KEY=must-not-load\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "checkout_root", lambda: tmp_path)

    settings = config.load_settings()

    assert __import__("os").environ["LENA_ENV_FILE_MODE"] == "disabled"
    assert settings.rewrite_provider == "template"
    assert settings.blablador_api_key is None
    assert settings.blablador_configured is False


def test_explicit_test_settings_can_initialize_provider_without_transport(
    tmp_path: Path,
) -> None:
    provider = BlabladorProvider(_provider_settings(tmp_path))

    assert provider.name == "blablador"
    assert provider.model == "test-model"


def test_provider_captures_last_confirmed_model_per_stage(tmp_path: Path) -> None:
    """Die vom Provider in der Antwort zurückgemeldete Modellkennung (Antwortfeld
    ``model``) wird je Stufe erfasst, unabhängig von der gesendeten Alias-Anfrage.
    Siehe docs/live-provider-evaluation.md und Abschnitt 6.7 der Thesis: Erst diese
    Erfassung macht die vom Provider bestätigte Modellkennung überhaupt auswertbar.
    """
    provider = BlabladorProvider(_provider_settings(tmp_path))
    assert provider.last_confirmed_models == {"interpreter": None, "selector": None, "formulator": None}

    async def fake_post(_: dict) -> dict:
        return {"model": "alias-fast-2026-08-01", "choices": [{"message": {"content": "{}"}}]}

    provider._post = fake_post  # type: ignore[method-assign]
    asyncio.run(
        provider._request_with_timeout({"model": "alias-fast"}, timeout_seconds=1, stage="interpreter")
    )

    assert provider.last_confirmed_models == {
        "interpreter": "alias-fast-2026-08-01",
        "selector": None,
        "formulator": None,
    }


def test_unmocked_http_transport_fails_immediately(tmp_path: Path) -> None:
    provider = BlabladorProvider(_provider_settings(tmp_path))

    with pytest.raises(AssertionError, match="external_network_call_blocked"):
        asyncio.run(provider._post({"model": "test-model"}))


def _live_arguments(*, confirm: bool = False) -> list[str]:
    arguments = [
        "multilingual_review", "live-smoke", "--stage", "interpreter",
        "--expected-model", "test-model",
        "--expected-provider-domain", "provider.example",
        "--max-requests", "15", "--max-provider-calls", "15",
        "--max-interpreter-calls", "15", "--max-selector-calls", "0",
        "--max-formulator-calls", "0", "--max-total-runtime-seconds", "300",
        "--max-failures", "3",
    ]
    return [*arguments, "--confirm-live"] if confirm else arguments


@pytest.mark.parametrize(
    ("arguments", "allow_env", "expected"),
    [
        (_live_arguments(), True, "confirmation"),
        (_live_arguments(confirm=True), False, "environment"),
    ],
)
def test_live_smoke_aborts_before_settings_without_both_consents(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
    allow_env: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(sys, "argv", arguments)
    if allow_env:
        monkeypatch.setenv("LENA_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setattr(
        multilingual_review,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings_must_not_load")),
    )

    with pytest.raises(SystemExit, match=expected):
        multilingual_review.main()


def test_live_smoke_accepts_only_exact_true_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limits = load_live_scenario_catalog().plan(EvaluationStage.INTERPRETER).live_limits
    with pytest.raises(SystemExit, match="environment"):
        require_live_authorization(
            confirm_live=True,
            stage=EvaluationStage.INTERPRETER,
            limits=limits,
            environ={"LENA_ALLOW_LIVE_SMOKE": "yes"},
        )

    require_live_authorization(
        confirm_live=True,
        stage=EvaluationStage.INTERPRETER,
        limits=limits,
        environ={"LENA_ALLOW_LIVE_SMOKE": "TRUE"},
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["multilingual_review", "live-smoke", "--stage", "unknown", "--confirm-live"],
        ["multilingual_review", "live-smoke", "--stage", "interpreter", "--confirm-live"],
    ],
)
def test_unknown_stage_or_missing_limits_abort_during_parsing_before_settings(
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setenv("LENA_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setattr(
        multilingual_review,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings_must_not_load")),
    )

    with pytest.raises(SystemExit):
        multilingual_review.main()


def test_live_dry_run_never_loads_settings_or_initializes_provider(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["multilingual_review", "live-dry-run", "--stage", "all"])
    monkeypatch.setattr(
        multilingual_review,
        "load_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings_must_not_load")),
    )

    multilingual_review.main()

    output = __import__("json").loads(capsys.readouterr().out)
    assert output["status"] == "prepared_not_executed"
    assert output["live_provider_calls_authorized"] is False


def test_live_smoke_rejects_changed_model_before_runner_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _live_arguments(confirm=True)
    arguments[arguments.index("test-model")] = "different-model"
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setenv("LENA_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setattr(multilingual_review, "load_settings", lambda: _provider_settings(tmp_path))
    monkeypatch.setattr(
        multilingual_review,
        "run_interpreter_live_gate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner_must_not_start")),
    )

    with pytest.raises(SystemExit, match="model_identifier_mismatch"):
        multilingual_review.main()


def test_live_smoke_rejects_when_only_one_stage_model_diverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regressionstest für den WP9B-Reviewbefund: Ein abweichender Stufen-Override

    (hier Formulator) muss das Gate auch dann stoppen, wenn der gemeinsame
    Basiswert unverändert bleibt. Der frühere Abgleich ausschließlich über
    ``settings.blablador_model`` hätte diesen Fall unbemerkt durchgelassen.
    """
    arguments = _live_arguments(confirm=True)
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setenv("LENA_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setattr(
        multilingual_review,
        "load_settings",
        lambda: _provider_settings(tmp_path, formulator_model="different-model"),
    )
    monkeypatch.setattr(
        multilingual_review,
        "run_interpreter_live_gate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner_must_not_start")),
    )

    with pytest.raises(SystemExit, match="model_identifier_mismatch"):
        multilingual_review.main()


def test_live_smoke_rejects_changed_provider_domain_before_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments = _live_arguments(confirm=True)
    arguments[arguments.index("provider.example")] = "unexpected.example"
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setenv("LENA_ALLOW_LIVE_SMOKE", "true")
    monkeypatch.setattr(multilingual_review, "load_settings", lambda: _provider_settings(tmp_path))
    monkeypatch.setattr(
        multilingual_review,
        "run_interpreter_live_gate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner_must_not_start")),
    )

    with pytest.raises(SystemExit, match="provider_domain_mismatch"):
        multilingual_review.main()
