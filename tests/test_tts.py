from __future__ import annotations

from app.models import Language
from app.providers.tts import create_tts_provider, normalize_tts_text


def test_normalize_tts_text_expands_common_abbreviations() -> None:
    text = "Tafel Leipzig e.V., Str. 7, Mo-Fr 9:30 - 10:30 Uhr"
    normalized = normalize_tts_text(text, Language.DE)
    assert "eingetragener Verein" in normalized
    assert "Strasse" in normalized
    assert "Montag bis Freitag" in normalized
    assert "9:30 bis 10:30 Uhr" in normalized


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
