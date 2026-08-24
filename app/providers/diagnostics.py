"""Redigierte Providerfehlerklassen ohne Request- oder Antwortinhalte."""

from __future__ import annotations

from enum import Enum

import httpx


class ProviderFailureKind(str, Enum):
    """Geschlossene Diagnosewerte für lokale technische Laufreports."""

    RATE_LIMITED = "rate_limited"
    UPSTREAM_4XX = "upstream_4xx"
    UPSTREAM_5XX = "upstream_5xx"
    UPSTREAM_HTTP_ERROR = "upstream_http_error"
    CONNECTION_ERROR = "connection_error"
    PROTOCOL_ERROR = "protocol_error"
    TRANSPORT_ERROR = "transport_error"
    PROVIDER_ERROR = "provider_error"


HTTP_STATUS_FAILURE_KINDS = frozenset({
    ProviderFailureKind.RATE_LIMITED,
    ProviderFailureKind.UPSTREAM_4XX,
    ProviderFailureKind.UPSTREAM_5XX,
    ProviderFailureKind.UPSTREAM_HTTP_ERROR,
})
SAFE_PROVIDER_FAILURE_KINDS = frozenset(item.value for item in ProviderFailureKind)


def classify_provider_failure(exc: BaseException) -> tuple[ProviderFailureKind, int | None]:
    """Klassifiziert nur Typ und Status; Nachricht, URL und Body bleiben verworfen."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            return ProviderFailureKind.RATE_LIMITED, status
        if 400 <= status <= 499:
            return ProviderFailureKind.UPSTREAM_4XX, status
        if 500 <= status <= 599:
            return ProviderFailureKind.UPSTREAM_5XX, status
        return ProviderFailureKind.UPSTREAM_HTTP_ERROR, status
    if isinstance(exc, httpx.ConnectError):
        return ProviderFailureKind.CONNECTION_ERROR, None
    if isinstance(exc, httpx.ProtocolError):
        return ProviderFailureKind.PROTOCOL_ERROR, None
    if isinstance(exc, httpx.RequestError):
        return ProviderFailureKind.TRANSPORT_ERROR, None
    return ProviderFailureKind.PROVIDER_ERROR, None
