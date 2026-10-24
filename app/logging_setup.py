"""Technisches Logformat mit Erlaubnisliste für strukturierte Ereignisfelder.

Die Anwendung schreibt Ereignisse als kurze Namen (``request.completed``) und
übergibt Diagnosedaten über ``extra``. Der Standardformatter von ``logging``
verwirft diese Felder. Dieser Formatter rendert ausschließlich Felder einer
geschlossenen Erlaubnisliste als ``key=value``. Freie Nutzereingaben,
Antworttexte, Session-IDs, Provider-Rohantworten, URLs mit Query-Strings und
Secrets stehen nicht auf der Liste und erscheinen deshalb auch dann nicht,
wenn ein künftiger Aufrufer sie versehentlich als ``extra`` übergibt.
"""

from __future__ import annotations

import json
import logging
import math
import re


TECHNICAL_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# Ausschließlich technische, inhaltsfreie Felder. Neue Felder müssen hier
# bewusst ergänzt werden; tests/test_observability.py prüft, dass alle im
# Anwendungscode verwendeten ``extra``-Schlüssel klassifiziert sind.
ALLOWED_EXTRA_FIELDS: tuple[str, ...] = (
    "method",
    "path",
    "status_code",
    "duration_ms",
    "error_type",
    "error_code",
    "diagnostic_code",
    "upstream_status",
    "provider_failure_kind",
    "stage",
    "attempt",
    "contract_version",
    "result_count",
    "selection_status",
    "selected_count",
    "safety_path",
    "changed",
    "promoted",
    "record_count",
    "release_id",
    "removed_count",
    "invalid_count",
    "session_count",
    "retained_count",
    "schema_issues",
    "service",
    "provider",
    "configured",
    "reason",
    "setting",
)

# Werte bleiben kurz und einzeilig; Diagnosefelder sind nie Freitext.
_MAX_VALUE_CHARS = 200
_UNSAFE_CHARS_RE = re.compile(r"[\s=\"\\]")


def _render_value(value: object) -> str:
    if isinstance(value, bool) or value is None:
        rendered = json.dumps(value)
    elif isinstance(value, int):
        rendered = str(value)
    elif isinstance(value, float):
        rendered = str(value) if math.isfinite(value) else json.dumps(str(value))
    elif isinstance(value, str):
        rendered = value if value and not _UNSAFE_CHARS_RE.search(value) else json.dumps(value, ensure_ascii=False)
    else:
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(rendered) > _MAX_VALUE_CHARS:
        rendered = rendered[: _MAX_VALUE_CHARS - 1] + "…"
    return rendered


class TechnicalLogFormatter(logging.Formatter):
    """Hängt erlaubte strukturierte Felder an die Ereignisnachricht an."""

    def __init__(self, fmt: str = TECHNICAL_LOG_FORMAT, datefmt: str | None = None) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        fields = [
            f"{name}={_render_value(getattr(record, name))}"
            for name in ALLOWED_EXTRA_FIELDS
            if name in record.__dict__
        ]
        if not fields:
            return base
        # Exception-Tracebacks hängt der Basisformatter nach der Nachricht an;
        # die Felder gehören in die erste Zeile zum Ereignisnamen.
        head, separator, tail = base.partition("\n")
        return f"{head} {' '.join(fields)}{separator}{tail}"


def configure_technical_logging(level_name: str) -> None:
    """Richtet das Root-Logging einmalig mit dem technischen Formatter ein.

    Bereits vorhandene Root-Handler (etwa von pytest oder einer einbettenden
    Anwendung) bleiben samt Level unverändert, wie zuvor bei
    ``logging.basicConfig``; die einbettende Umgebung bestimmt dann das Format.
    """
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(TechnicalLogFormatter())
    root.addHandler(handler)
    root.setLevel(level)
