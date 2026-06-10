from __future__ import annotations

from pathlib import Path

from app.config import _default_piper_voice_models, load_settings
from scripts.list_openai_models import _redact


def test_default_piper_voice_models_prefers_thorsten_high_for_german(tmp_path: Path) -> None:
    voices_root = tmp_path / "voices" / "piper"
    voices_root.mkdir(parents=True)
    (voices_root / "de_DE-ramona-low.onnx").touch()
    (voices_root / "de_DE-thorsten-high.onnx").touch()
    (voices_root / "en_GB-alan-medium.onnx").touch()

    selected = _default_piper_voice_models(tmp_path)

    assert selected["de"].endswith("de_DE-thorsten-high.onnx")
    assert selected["en"].endswith("en_GB-alan-medium.onnx")


def test_default_piper_voice_models_falls_back_to_ramona_for_german(tmp_path: Path) -> None:
    voices_root = tmp_path / "voices" / "piper"
    voices_root.mkdir(parents=True)
    (voices_root / "de_DE-ramona-low.onnx").touch()

    selected = _default_piper_voice_models(tmp_path)

    assert selected["de"].endswith("de_DE-ramona-low.onnx")


def test_blablador_settings_default_to_alias_and_base_url(monkeypatch) -> None:
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "blablador")
    monkeypatch.delenv("LENA_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("LENA_LLM_API_KEY", "secret-token-for-test")

    settings = load_settings(env_file=Path("does-not-exist.env"))

    assert settings.rewrite_provider == "blablador"
    assert settings.llm_base_url == "https://api.blablador.fz-juelich.de/v1/"
    assert settings.llm_model == "alias-large"
    assert "secret-token-for-test" not in repr(settings)


def test_openai_compatible_settings_do_not_assume_blablador_base_url(monkeypatch) -> None:
    monkeypatch.setenv("LENA_REWRITE_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LENA_LLM_BASE_URL", raising=False)

    settings = load_settings(env_file=Path("does-not-exist.env"))

    assert settings.rewrite_provider == "openai_compatible"
    assert settings.llm_base_url is None


def test_load_settings_reads_local_env_without_leaking_secret(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LENA_REWRITE_PROVIDER=blablador",
                "LENA_LLM_API_KEY=dotenv-secret-token",
                "LENA_LLM_MODEL=alias-fast",
                "LENA_LLM_TEMPERATURE=0.1",
                "LENA_LLM_MAX_TOKENS=321",
            ]
        ),
        encoding="utf-8",
    )
    for key in [
        "LENA_REWRITE_PROVIDER",
        "LENA_LLM_API_KEY",
        "LENA_LLM_MODEL",
        "LENA_LLM_TEMPERATURE",
        "LENA_LLM_MAX_TOKENS",
        "LENA_LLM_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = load_settings(env_file=env_file)

    assert settings.rewrite_provider == "blablador"
    assert settings.llm_base_url == "https://api.blablador.fz-juelich.de/v1/"
    assert settings.llm_api_key == "dotenv-secret-token"
    assert settings.llm_model == "alias-fast"
    assert settings.llm_temperature == 0.1
    assert settings.llm_max_tokens == 321
    assert "dotenv-secret-token" not in repr(settings)


def test_process_environment_overrides_local_env(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LENA_LLM_MODEL=alias-fast\n", encoding="utf-8")
    monkeypatch.setenv("LENA_LLM_MODEL", "alias-large")

    settings = load_settings(env_file=env_file)

    assert settings.llm_model == "alias-large"


def test_piper_voice_settings_parse_language_specific_env(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LENA_PIPER_VOICE_DE=data/voices/piper/de.onnx",
                "LENA_PIPER_VOICE_EN=data/voices/piper/en.onnx",
                "LENA_PIPER_VOICE_PL=data/voices/piper/pl.onnx",
                "LENA_PIPER_VOICE_RO=data/voices/piper/ro.onnx",
                "LENA_PIPER_VOICE_RU=data/voices/piper/ru.onnx",
                "LENA_PIPER_VOICE_CONFIG_EN=data/voices/piper/en.onnx.json",
                "LENA_PIPER_DEFAULT_VOICE=data/voices/piper/default.onnx",
                "LENA_PIPER_DEFAULT_VOICE_CONFIG=data/voices/piper/default.onnx.json",
            ]
        ),
        encoding="utf-8",
    )
    for key in [
        "LENA_PIPER_VOICE_MODELS",
        "LENA_PIPER_VOICE_CONFIGS",
        "LENA_PIPER_VOICE_DE",
        "LENA_PIPER_VOICE_EN",
        "LENA_PIPER_VOICE_PL",
        "LENA_PIPER_VOICE_RO",
        "LENA_PIPER_VOICE_RU",
        "LENA_PIPER_VOICE_CONFIG_EN",
        "LENA_PIPER_DEFAULT_VOICE",
        "LENA_PIPER_DEFAULT_VOICE_CONFIG",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = load_settings(env_file=env_file)

    assert settings.piper_voice_models == {
        "de": "data/voices/piper/de.onnx",
        "en": "data/voices/piper/en.onnx",
        "pl": "data/voices/piper/pl.onnx",
        "ro": "data/voices/piper/ro.onnx",
        "ru": "data/voices/piper/ru.onnx",
        "default": "data/voices/piper/default.onnx",
    }
    assert settings.piper_voice_configs["en"] == "data/voices/piper/en.onnx.json"
    assert settings.piper_default_voice_model == "data/voices/piper/default.onnx"
    assert settings.piper_default_voice_config == "data/voices/piper/default.onnx.json"


def test_model_listing_redacts_api_key_from_error_details() -> None:
    assert _redact("failed with dotenv-secret-token", "dotenv-secret-token") == "failed with [redacted]"
