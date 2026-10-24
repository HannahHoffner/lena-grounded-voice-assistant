"""Tatsächlich serialisierte technische Logs (Audit F-09, C-36).

Der frühere ``basicConfig``-Formatter gab nur den Ereignisnamen aus; die über
``extra`` übergebenen Diagnosefelder fehlten im Container-Log. Diese Tests
prüfen die Ausgabe des tatsächlichen Formatters, nicht nur LogRecord-Attribute.
"""

from __future__ import annotations

import ast
import io
import logging
from pathlib import Path

import pytest

from app.logging_setup import ALLOWED_EXTRA_FIELDS, TechnicalLogFormatter, configure_technical_logging


APP = Path(__file__).resolve().parents[1] / "app"


def _record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.main", logging.WARNING, __file__, 1, message, None, None)
    record.__dict__.update(extra)
    return record


def test_allowlisted_fields_are_rendered_on_the_event_line() -> None:
    line = TechnicalLogFormatter().format(_record(
        "request.completed", method="POST", path="/api/query", status_code=200, duration_ms=12.5,
    ))
    assert line.endswith("request.completed method=POST path=/api/query status_code=200 duration_ms=12.5")


@pytest.mark.parametrize("field", ["query", "user_query", "answer", "api_key", "session_id", "authorization", "text"])
def test_free_text_session_and_secret_fields_are_never_rendered(field: str) -> None:
    line = TechnicalLogFormatter().format(_record("tts.failed", error_code="tts_timeout", **{field: "SENSITIVE"}))
    assert "SENSITIVE" not in line and "error_code=tts_timeout" in line


def test_values_stay_single_line_and_bounded() -> None:
    line = TechnicalLogFormatter().format(_record("x", error_type="a b\nc", schema_issues=[{"field_path": "x" * 500}]))
    assert "\n" not in line
    assert 'error_type="a b\\nc"' in line
    assert len(line) < 400


def _extra_keys_in_app_code() -> set[str]:
    keys: set[str] = set()
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "extra" and isinstance(node.value, ast.Dict):
                keys.update(key.value for key in node.value.keys if isinstance(key, ast.Constant))
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id == "log_context" and isinstance(node.value, ast.Dict):
                        keys.update(key.value for key in node.value.keys if isinstance(key, ast.Constant))
                    if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                            and target.value.id == "log_context" and isinstance(target.slice, ast.Constant)):
                        keys.add(target.slice.value)
    return keys


def test_every_structured_field_used_by_the_application_is_classified() -> None:
    used = _extra_keys_in_app_code()
    assert used, "scanner found no structured log fields"
    assert sorted(used - set(ALLOWED_EXTRA_FIELDS)) == []


def test_configuration_installs_the_formatter_only_without_existing_handlers() -> None:
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        root.handlers = []
        configure_technical_logging("INFO")
        assert len(root.handlers) == 1 and isinstance(root.handlers[0].formatter, TechnicalLogFormatter)
        stream = io.StringIO()
        root.handlers[0].setStream(stream)
        logging.getLogger("app.main").info("request.completed", extra={"status_code": 200, "query": "Essen"})
        assert "request.completed status_code=200" in stream.getvalue()
        assert "Essen" not in stream.getvalue()
        configure_technical_logging("DEBUG")  # idempotent, kein zweiter Handler
        assert len(root.handlers) == 1
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
