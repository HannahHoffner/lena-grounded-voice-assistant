"""Kommandozeileneinstieg für den lokalen Uvicorn-Server."""

from __future__ import annotations

import argparse
import os

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the minimal LENA service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--reload", action="store_true", help="Enable development auto-reload.")
    parser.add_argument("--rewrite-provider", choices=["template", "blablador"])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.rewrite_provider:
        os.environ["REWRITE_PROVIDER"] = args.rewrite_provider
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
