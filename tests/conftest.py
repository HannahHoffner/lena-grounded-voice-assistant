"""Suite-wide isolation from checkout configuration and external transports."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Generator
from typing import Any

import httpx
import pytest

import app.config as config


PROVIDER_ENV_NAMES = {
    "REWRITE_PROVIDER",
    "LENA_REWRITE_PROVIDER",
    "BLABLADOR_BASE_URL",
    "LENA_LLM_BASE_URL",
    "BLABLADOR_API_KEY",
    "LENA_LLM_API_KEY",
    "BLABLADOR_MODEL",
    "LENA_LLM_MODEL",
    "SPEECH_TRANSCRIPTION_BASE_URL",
    "LENA_STT_BASE_URL",
    "SPEECH_TRANSCRIPTION_API_KEY",
    "LENA_STT_API_KEY",
    "SPEECH_TRANSCRIPTION_MODEL",
    "LENA_STT_MODEL",
    "SPEECH_SYNTHESIS_BASE_URL",
    "LENA_TTS_BASE_URL",
    "SPEECH_SYNTHESIS_API_KEY",
    "LENA_TTS_API_KEY",
    "SPEECH_SYNTHESIS_MODEL",
    "LENA_TTS_MODEL",
    "SPEECH_SYNTHESIS_PROVIDER",
    "LENA_TTS_PROVIDER",
    "LENA_ALLOW_LIVE_SMOKE",
}


def _loopback_host(host: object) -> bool:
    value = str(host).strip().strip("[]")
    if value.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


@pytest.fixture(scope="session", autouse=True)
def isolate_checkout_settings_and_external_network(
) -> Generator[None, None, None]:
    """Make forgotten live configuration or transport use fail inside pytest."""

    monkeypatch = pytest.MonkeyPatch()
    for name in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LENA_ENV_FILE_MODE", "disabled")
    monkeypatch.setattr(config, "_load_env_file", lambda *_args, **_kwargs: None)

    async def block_async_http(
        _transport: httpx.AsyncHTTPTransport,
        _request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError("external_network_call_blocked")

    def block_sync_http(
        _transport: httpx.HTTPTransport,
        _request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError("external_network_call_blocked")

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(instance: socket.socket, address: Any) -> Any:
        if isinstance(address, tuple) and address and not _loopback_host(address[0]):
            raise AssertionError("external_network_call_blocked")
        return real_connect(instance, address)

    def guarded_connect_ex(instance: socket.socket, address: Any) -> int:
        if isinstance(address, tuple) and address and not _loopback_host(address[0]):
            raise AssertionError("external_network_call_blocked")
        return real_connect_ex(instance, address)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", block_async_http)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", block_sync_http)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    try:
        yield
    finally:
        monkeypatch.undo()
