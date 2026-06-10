from __future__ import annotations

import asyncio
from pathlib import Path

from app.models import Language
from app.providers.tts import PiperTtsProvider, create_tts_provider, normalize_for_tts, normalize_tts_text


def test_normalize_tts_text_expands_common_abbreviations() -> None:
    text = "Tafel Leipzig e.V., Str. 7, Mo-Fr 9:30 - 10:30 Uhr"
    normalized = normalize_tts_text(text, Language.DE)
    assert "eingetragener Verein" in normalized
    assert "Strasse" in normalized
    assert "Montag bis Freitag" in normalized
    assert "9:30 bis 10:30 Uhr" in normalized


def test_normalize_for_tts_speaks_german_phone_numbers_digit_by_digit() -> None:
    examples = {
        "Notruf 112": "Notruf eins eins zwei",
        "Polizei 110": "Polizei eins eins null",
        "Telefon 116 117": "Telefon eins eins sechs, eins eins sieben",
        "Telefon 0800 1110111": "Telefon null acht null null, eins eins eins null eins eins eins",
        "Telefon 0341 123456": "Telefon null drei vier eins, eins zwei drei vier fuenf sechs",
        "Telefon +49 341 123456": "Telefon plus vier neun, drei vier eins, eins zwei drei vier fuenf sechs",
        "Telefon 0341/123456": "Telefon null drei vier eins, eins zwei drei vier fuenf sechs",
        "Telefon 0341-123456": "Telefon null drei vier eins, eins zwei drei vier fuenf sechs",
        "Telefon (0341) 123456": "Telefon null drei vier eins, eins zwei drei vier fuenf sechs",
    }
    for raw, expected in examples.items():
        assert expected in normalize_for_tts(raw, Language.DE)


def test_normalize_for_tts_does_not_change_dates_times_or_postal_codes_without_phone_context() -> None:
    normalized = normalize_for_tts("Am 07.06.2026 um 09:30 Uhr in 04103 Leipzig.", Language.DE)
    assert "07.06.2026" in normalized
    assert "09:30 Uhr" in normalized
    assert "04103" in normalized
    assert "null vier eins null drei" not in normalized


def test_umlaut_normalization_is_speech_only_and_opt_in() -> None:
    display_text = "Die Tür ist geöffnet. Straße."
    assert normalize_for_tts(display_text, Language.DE) == display_text
    assert normalize_for_tts(display_text, Language.DE, normalize_umlauts=True) == "Die Tuer ist geoeffnet. Strasse."


def test_piper_provider_reports_fallback_reason_when_assets_are_missing() -> None:
    provider = create_tts_provider(
        "piper",
        binary="C:/missing/piper.exe",
        voice_models={"de": "C:/missing/de.onnx"},
    )
    health = provider.health()
    assert provider.name == "mock"
    assert health["configured_provider"] == "piper"
    assert health["active_provider"] == "mock"
    assert health["ready"] is False
    assert health["fallback_from"] == "piper"
    assert "Missing Piper binary" in str(health["detail"])


def test_piper_provider_selects_language_specific_voice_for_all_supported_languages(tmp_path: Path) -> None:
    binary = _touch(tmp_path / "piper.exe")
    voices = _create_voice_set(tmp_path, ["de", "en", "pl", "ro", "ru"])

    provider = create_tts_provider("piper", binary=str(binary), voice_models=voices)

    assert isinstance(provider, PiperTtsProvider)
    for language in Language:
        voice = provider.select_voice(language)
        assert voice is not None
        assert voice.model_path == Path(voices[language.value])
        assert voice.config_path == Path(voices[language.value] + ".json")
        assert voice.fallback is False


def test_piper_provider_uses_default_voice_when_language_voice_is_missing(tmp_path: Path) -> None:
    binary = _touch(tmp_path / "piper.exe")
    default_voice = _create_voice(tmp_path, "fallback")

    provider = create_tts_provider(
        "piper",
        binary=str(binary),
        voice_models={"de": str(_create_voice(tmp_path, "de")), "default": str(default_voice)},
    )

    assert isinstance(provider, PiperTtsProvider)
    voice = provider.select_voice(Language.EN)
    assert voice is not None
    assert voice.model_path == default_voice
    assert voice.fallback is True


def test_piper_provider_returns_none_for_missing_language_without_default(tmp_path: Path) -> None:
    binary = _touch(tmp_path / "piper.exe")
    provider = create_tts_provider(
        "piper",
        binary=str(binary),
        voice_models={"de": str(_create_voice(tmp_path, "de"))},
    )

    assert isinstance(provider, PiperTtsProvider)
    assert asyncio.run(provider.synthesize("Hello", Language.EN, tmp_path / "audio")) is None


def test_piper_provider_returns_unavailable_without_configured_voice(tmp_path: Path) -> None:
    binary = _touch(tmp_path / "piper.exe")
    provider = create_tts_provider("piper", binary=str(binary), voice_models={})

    assert provider.name == "mock"
    assert asyncio.run(provider.synthesize("Hallo", Language.DE, tmp_path / "audio")) is None


def test_piper_provider_passes_explicit_config_path_to_piper(monkeypatch, tmp_path: Path) -> None:
    binary = _touch(tmp_path / "piper.exe")
    model = _touch(tmp_path / "voice.onnx")
    config = _touch(tmp_path / "voice-config.json")
    calls: list[list[str]] = []

    def fake_run(command, input, text, encoding, check):  # noqa: ANN001
        calls.append(command)
        assert isinstance(input, str)
        assert encoding == "utf-8"

    monkeypatch.setattr("app.providers.tts.subprocess.run", fake_run)
    provider = create_tts_provider(
        "piper",
        binary=str(binary),
        voice_models={"en": str(model)},
        voice_configs={"en": str(config)},
    )

    assert isinstance(provider, PiperTtsProvider)
    audio_url = asyncio.run(provider.synthesize("Where can I get help today?", Language.EN, tmp_path / "audio"))

    assert audio_url is not None
    assert calls
    assert calls[0][calls[0].index("--model") + 1] == str(model)
    assert calls[0][calls[0].index("--config") + 1] == str(config)


def _create_voice_set(tmp_path: Path, languages: list[str]) -> dict[str, str]:
    return {language: str(_create_voice(tmp_path, language)) for language in languages}


def _create_voice(tmp_path: Path, stem: str) -> Path:
    model = _touch(tmp_path / f"{stem}.onnx")
    _touch(Path(str(model) + ".json"))
    return model


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path
