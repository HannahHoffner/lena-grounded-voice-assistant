"""Suite-wide isolation from checkout configuration and external transports."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx
import pytest

import app.config as config


CHECKOUT_ROOT = Path(__file__).resolve().parents[1]

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
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[None, None, None]:
    """Make forgotten live configuration or transport use fail inside pytest."""

    monkeypatch = pytest.MonkeyPatch()
    for name in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LENA_ENV_FILE_MODE", "disabled")
    # Without this, every test that builds Settings via load_settings() resolves
    # the runtime root to the checkout's own runtime/ and writes there. The
    # shared session store is then rewritten with test sessions, evicting the
    # local research/session data the README marks as sensitive.
    runtime_root = tmp_path_factory.mktemp("lena-runtime")
    monkeypatch.setenv("LENA_RUNTIME_DIR", str(runtime_root))
    monkeypatch.setattr(config, "_load_env_file", lambda *_args, **_kwargs: None)

    # Most tests build Settings directly and pass the checkout as app_root so
    # that data/ is reachable. runtime_dir and interaction_log_path then default
    # into the checkout's own runtime/, and a test run rewrites the local
    # session store and interaction log -- files the README marks as sensitive
    # local research data. Redirect exactly those two checkout defaults onto the
    # temporary root; Settings that already name their own runtime directory
    # (the majority) are left untouched.
    checkout_runtime = CHECKOUT_ROOT / "runtime"
    real_post_init = config.Settings.__post_init__

    def isolated_post_init(self: config.Settings) -> None:
        real_post_init(self)
        if self.runtime_dir is not None and Path(self.runtime_dir).resolve() == checkout_runtime:
            object.__setattr__(self, "runtime_dir", runtime_root)
            if self.interaction_log_path is not None and checkout_runtime in Path(
                self.interaction_log_path
            ).resolve().parents:
                object.__setattr__(
                    self, "interaction_log_path", runtime_root / "logs" / "interactions.jsonl"
                )

    monkeypatch.setattr(config.Settings, "__post_init__", isolated_post_init)

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
