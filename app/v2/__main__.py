from __future__ import annotations

import argparse
import os

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the clean LENA v2 local service.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the service to.")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind the v2 service to.")
    parser.add_argument("--reload", dest="reload", action="store_true", default=True, help="Enable auto-reload.")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload.")
    parser.add_argument("--rewrite-provider", choices=["template", "blablador", "openai_compatible"], help="V2 answer provider.")
    parser.add_argument("--stt-provider", choices=["mock", "faster_whisper"], help="Speech-to-text provider.")
    parser.add_argument("--tts-provider", choices=["mock", "piper"], help="Text-to-speech provider.")
    parser.add_argument("--llm-model", help="OpenAI-compatible or Blablador model alias.")
    parser.add_argument("--llm-base-url", help="OpenAI-compatible base URL.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.rewrite_provider:
        os.environ["LENA_REWRITE_PROVIDER"] = args.rewrite_provider
    if args.stt_provider:
        os.environ["LENA_STT_PROVIDER"] = args.stt_provider
    if args.tts_provider:
        os.environ["LENA_TTS_PROVIDER"] = args.tts_provider
    if args.llm_model:
        os.environ["LENA_LLM_MODEL"] = args.llm_model
    if args.llm_base_url:
        os.environ["LENA_LLM_BASE_URL"] = args.llm_base_url

    uvicorn.run(
        "app.v2.main:create_v2_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
