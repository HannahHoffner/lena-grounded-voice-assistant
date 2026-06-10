from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _ignore_developer_env_file(monkeypatch) -> None:
    monkeypatch.setenv("LENA_ENV_FILE", str(ROOT / ".pytest-no-env"))
