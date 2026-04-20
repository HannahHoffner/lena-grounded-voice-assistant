from __future__ import annotations

import argparse
import os

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LENA local service.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the service to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the service to.")
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=True,
        help="Enable auto-reload for local development.",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload.",
    )
    parser.add_argument(
        "--rewrite-provider",
        choices=["template", "ollama"],
        help="Override the configured rewrite provider for this run.",
    )
    parser.add_argument(
        "--stt-provider",
        choices=["mock", "faster_whisper"],
        help="Override the configured speech-to-text provider for this run.",
    )
    parser.add_argument(
        "--tts-provider",
        choices=["mock", "piper"],
        help="Override the configured text-to-speech provider for this run.",
    )
    parser.add_argument(
        "--ollama-model",
        help="Override the configured Ollama model for this run.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.rewrite_provider:
        os.environ["LENA_REWRITE_PROVIDER"] = args.rewrite_provider
    if args.stt_provider:
        os.environ["LENA_STT_PROVIDER"] = args.stt_provider
    if args.tts_provider:
        os.environ["LENA_TTS_PROVIDER"] = args.tts_provider
    if args.ollama_model:
        os.environ["LENA_OLLAMA_MODEL"] = args.ollama_model

    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
