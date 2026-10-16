"""Redigierte Providerfehlerklassen ohne Request- oder Antwortinhalte."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import ValidationError


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

# Never persist Pydantic msg/input/ctx or model-supplied extra-key names.
_SCHEMA_PATH_PARTS = frozenset({
    "$", "*", "<extra>", "contract_version", "need", "explicit_service_requests",
    "scope_status", "input_language", "explicit_facts", "age", "age_group",
    "gender", "drug_use", "no_social_benefit_entitlement", "district",
    "requested_day", "requested_time", "uncertain_hints", "field", "value",
    "potentially_missing_information", "clarification_may_be_needed", "acute_risk_status",
})
_SEMANTIC_SCHEMA_ERRORS = {
    "Value error, numeric age and age_group disagree": "age_group_mismatch",
    "Value error, district must contain text": "blank_district",
    "Value error, explicit_service_requests must be unique": "duplicate_services",
    "Value error, potentially_missing_information must be unique": "duplicate_missing_information",
    "Value error, out_of_scope requires need=unknown": "out_of_scope_need_mismatch",
    "Value error, clarification flag and missing-information list disagree": "clarification_mismatch",
}
_SCHEMA_ERROR_TYPES = frozenset({
    "missing", "extra_forbidden", "enum", "literal_error", "int_type",
    "bool_type", "string_type", "string_too_short", "string_too_long",
    "string_pattern_mismatch", "list_type", "too_long", "model_type",
    "greater_than_equal", "less_than_equal", "value_error", "validation_error",
    *_SEMANTIC_SCHEMA_ERRORS.values(),
})
MAX_SCHEMA_ISSUES = 8


@dataclass(frozen=True)
class SchemaValidationIssue:
    """Closed metadata only; paths contain no values or unknown field names."""

    field_path: str
    error_type: str

    def __post_init__(self) -> None:
        if type(self.field_path) is not str or type(self.error_type) is not str:
            raise ValueError("schema diagnostics must contain plain strings")
        parts = self.field_path.split(".")
        if len(parts) > 4 or any(part not in _SCHEMA_PATH_PARTS for part in parts):
            raise ValueError("schema field path is not allowlisted")
        if self.error_type not in _SCHEMA_ERROR_TYPES:
            raise ValueError("schema error type is not allowlisted")


def interpreter_schema_issues(exc: ValidationError) -> tuple[SchemaValidationIssue, ...]:
    """Project at most eight errors; unknown keys/types become fixed markers."""
    issues = []
    for error in exc.errors(include_input=False, include_context=False, include_url=False)[:MAX_SCHEMA_ISSUES]:
        parts = [
            "*" if isinstance(part, int) else part if part in _SCHEMA_PATH_PARTS else "<extra>"
            for part in error["loc"][:4]
        ]
        error_type = error["type"]
        if error_type == "value_error":
            error_type = _SEMANTIC_SCHEMA_ERRORS.get(error["msg"], "value_error")
        if error_type not in _SCHEMA_ERROR_TYPES:
            error_type = "validation_error"
        issues.append(SchemaValidationIssue(".".join(parts) or "$", error_type))
    return tuple(issues)


def schema_issue_records(issues: tuple[SchemaValidationIssue, ...]) -> list[dict[str, str]]:
    """Validate the internal boundary again before logging or report persistence."""
    if not isinstance(issues, tuple) or len(issues) > MAX_SCHEMA_ISSUES:
        raise ValueError("schema diagnostics must be a bounded tuple")
    records = []
    for issue in issues:
        if type(issue) is not SchemaValidationIssue:
            raise ValueError("schema diagnostic is not allowlisted")
        SchemaValidationIssue(issue.field_path, issue.error_type)
        records.append({"field_path": issue.field_path, "error_type": issue.error_type})
    return records


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
