from __future__ import annotations

from pathlib import Path

from app.config import _default_piper_voice_models


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
