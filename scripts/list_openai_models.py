from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.config import load_settings


def _redact(value: str, secret: str | None) -> str:
    if secret:
        value = value.replace(secret, "[redacted]")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="List models from an OpenAI-compatible LENA LLM endpoint.")
    parser.add_argument("--base-url", help="Override LENA_LLM_BASE_URL.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds.")
    args = parser.parse_args()

    settings = load_settings()
    base_url = (args.base_url or settings.llm_base_url or "").rstrip("/")
    if not base_url:
        print("No base URL configured. Set LENA_LLM_BASE_URL or use --base-url.", file=sys.stderr)
        return 2
    if not settings.llm_api_key:
        print("No API key configured. Set LENA_LLM_API_KEY.", file=sys.stderr)
        return 2

    try:
        with httpx.Client(timeout=args.timeout) as client:
            response = client.get(f"{base_url}/models", headers={"Authorization": f"Bearer {settings.llm_api_key}"})
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        detail = _redact(str(exc), settings.llm_api_key)
        print(f"Could not list models from {base_url}: {detail}", file=sys.stderr)
        return 1

    models = body.get("data", [])
    for item in models:
        if isinstance(item, dict) and item.get("id"):
            print(item["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
