"""Kommandozeileneinstieg für den lokalen Uvicorn-Server."""

from __future__ import annotations

import argparse
import ipaddress
import os

import uvicorn


def is_loopback_host(host: str) -> bool:
    """Prüft, ob ein Bind-Host ausschließlich den lokalen Rechner adressiert."""
    normalized = host.strip().strip("[]").casefold()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_bind_host(host: str, *, allow_public: bool) -> str:
    """Verlangt für LAN-/Public-Bindings eine ausdrückliche Freigabe."""
    if not allow_public and not is_loopback_host(host):
        raise ValueError("non-loopback hosts require --allow-public")
    return host


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the minimal LENA service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--allow-public",
        action="store_true",
        help="Allow binding to a non-loopback host; does not add TLS or authentication.",
    )
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--reload", action="store_true", help="Enable development auto-reload.")
    parser.add_argument("--rewrite-provider", choices=["template", "blablador"])
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        host = validate_bind_host(args.host, allow_public=args.allow_public)
    except ValueError as exc:
        parser.error(str(exc))
    if args.rewrite_provider:
        os.environ["REWRITE_PROVIDER"] = args.rewrite_provider
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
