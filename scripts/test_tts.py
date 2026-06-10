from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.config import load_settings
from app.models import Language
from app.providers.tts import create_tts_provider


async def _run(language: Language, text: str, output_dir: Path | None) -> int:
    settings = load_settings()
    audio_root = output_dir or settings.audio_root
    provider = create_tts_provider(
        settings.tts_provider,
        binary=settings.piper_binary,
        voice_models=settings.piper_voice_models,
        voice_configs=settings.piper_voice_configs,
        default_voice_model=settings.piper_default_voice_model,
        default_voice_config=settings.piper_default_voice_config,
    )
    audio_url = await provider.synthesize(text, language, audio_root)
    if not audio_url:
        print(f"TTS unavailable for language '{language.value}' with active provider '{provider.name}'.")
        detail = provider.health().get("detail")
        if detail:
            print(f"Detail: {detail}")
        return 1
    print(f"Generated audio: {audio_root / Path(audio_url).name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize a short LENA TTS sample with the configured local provider.")
    parser.add_argument("--lang", choices=[language.value for language in Language], required=True, help="Request/UI language.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output-dir", type=Path, help="Optional output directory for the WAV file.")
    args = parser.parse_args()
    return asyncio.run(_run(Language(args.lang), args.text, args.output_dir))


if __name__ == "__main__":
    raise SystemExit(main())
