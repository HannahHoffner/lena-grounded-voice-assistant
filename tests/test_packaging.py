"""Build-, Inventar- und Clean-Install-Tests der LENA-Distribution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest

from app import __version__
from app.main import create_app
from app.resources import bootstrap_data_root, static_root
from app.version import software_version
import app.version as version_module


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.1.0"
BOOTSTRAP_FILES = {
    "app/resources/bootstrap/canonical/offers.json",
    "app/resources/bootstrap/i18n/manual_overrides.json",
    "app/resources/bootstrap/i18n/offer_translations.json",
    "app/resources/bootstrap/wfs/current.geojson",
    "app/resources/bootstrap/wfs/last_change_report.json",
}
FRONTEND_FILES = {
    "app/static/index.html",
    "app/static/app.js",
    "app/static/styles.css",
    "app/static/vendor/leaflet/leaflet.css",
    "app/static/vendor/leaflet/leaflet.js",
    "app/static/vendor/leaflet/images/marker-icon.png",
    "app/static/vendor/leaflet/images/marker-icon-2x.png",
    "app/static/vendor/leaflet/images/marker-shadow.png",
    "app/static/vendor/leaflet/images/layers.png",
    "app/static/vendor/leaflet/images/layers-2x.png",
}


def _run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


@pytest.fixture(scope="session")
def distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    output = tmp_path_factory.mktemp("distribution")
    _run(sys.executable, "-m", "build", "--outdir", str(output))
    return next(output.glob("*.whl")), next(output.glob("*.tar.gz"))


def _wheel_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def test_version_is_shared_by_metadata_api_and_source(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))

    assert metadata["Version"] == EXPECTED_VERSION
    assert __version__ == software_version() == EXPECTED_VERSION
    assert create_app().version == EXPECTED_VERSION


def test_source_checkout_version_fallback_is_explicit(monkeypatch) -> None:
    def missing_metadata(_: str) -> str:
        raise version_module.PackageNotFoundError

    monkeypatch.setattr(version_module, "version", missing_metadata)
    assert version_module.software_version() == "0+unknown"


def test_wheel_contains_only_runtime_code_and_read_only_resources(
    distributions: tuple[Path, Path],
) -> None:
    wheel, _ = distributions
    names = _wheel_names(wheel)

    assert FRONTEND_FILES | BOOTSTRAP_FILES <= names
    assert not any(name.startswith(("tests/", "docs/", "runtime/")) for name in names)
    assert not any("sessions.json" in name or "interactions.jsonl" in name for name in names)
    assert not any("pending" in name.casefold() or name.endswith((".env", ".env.local")) for name in names)
    assert not any(".data/data/data/" in name for name in names)


def test_frontend_references_resolve_inside_packaged_static_tree() -> None:
    root = static_root()
    html = (root / "index.html").read_text(encoding="utf-8")
    css_files = [root / "styles.css", root / "vendor" / "leaflet" / "leaflet.css"]
    references = re.findall(r'(?:src|href)="([^"]+)"', html)
    for reference in references:
        if reference.startswith(("http://", "https://", "#")):
            continue
        resource_path = reference.partition("?")[0].partition("#")[0]
        assert (root / resource_path.removeprefix("/static/")).is_file(), reference
    for css_path in css_files:
        for reference in re.findall(r"url\(['\"]?([^)'\"]+)", css_path.read_text(encoding="utf-8")):
            if reference.startswith(("data:", "#")):
                continue
            assert (css_path.parent / reference).resolve().is_file(), reference


def test_bootstrap_resources_are_complete_and_cwd_independent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = bootstrap_data_root()
    for relative in (
        "canonical/offers.json",
        "i18n/offer_translations.json",
        "i18n/manual_overrides.json",
        "wfs/current.geojson",
        "wfs/last_change_report.json",
    ):
        assert (root / relative).is_file()


def test_sdist_is_sufficient_and_excludes_local_state(distributions: tuple[Path, Path], tmp_path: Path) -> None:
    wheel, source = distributions
    with tarfile.open(source, "r:gz") as archive:
        names = {name.split("/", 1)[-1] for name in archive.getnames() if "/" in name}
    assert {"README.md", ".env.example", "pyproject.toml", "MANIFEST.in"} <= names
    assert any(name.startswith("tests/") for name in names)
    assert any(name.startswith("docs/") for name in names)
    assert not any(name.startswith("runtime/") or name in {".env", ".env.local"} for name in names)

    rebuilt = tmp_path / "rebuilt"
    rebuilt.mkdir()
    _run(sys.executable, "-m", "pip", "wheel", str(source), "--no-deps", "-w", str(rebuilt))
    rebuilt_wheel = next(rebuilt.glob("*.whl"))
    assert rebuilt_wheel.name == wheel.name
    assert _wheel_names(rebuilt_wheel) == _wheel_names(wheel)


def test_clean_wheel_install_starts_outside_checkout(
    distributions: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    wheel, _ = distributions
    environment = tmp_path / "venv"
    outside = tmp_path / "outside"
    runtime = outside / "runtime"
    data = outside / "data"
    outside.mkdir()
    _run(sys.executable, "-m", "venv", str(environment))
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    _run(str(python), "-m", "pip", "install", str(wheel))
    sensitive_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH", "BLABLADOR", "SPEECH")
    clean_env = {
        name: value
        for name, value in os.environ.items()
        if name != "PYTHONPATH" and not any(marker in name.upper() for marker in sensitive_markers)
    }
    clean_env.update(
        {
            "LENA_RUNTIME_DIR": str(runtime),
            "LENA_DATA_DIR": str(data),
            "WFS_AUTO_SYNC": "false",
            "REWRITE_PROVIDER": "template",
        }
    )
    script = """
import json
from pathlib import Path
from fastapi.testclient import TestClient
import app
from app.config import load_settings
from app.main import create_app

settings = load_settings()
assert 'site-packages' in str(Path(app.__file__).resolve()).casefold(), app.__file__
assert settings.kb_path.is_file()
assert settings.runtime_dir == Path(__import__('os').environ['LENA_RUNTIME_DIR']).resolve()
assert settings.data_dir == Path(__import__('os').environ['LENA_DATA_DIR']).resolve()
with TestClient(create_app(settings)) as client:
    assert client.get('/').status_code == 200
    assert client.get('/static/styles.css').status_code == 200
    health = client.get('/api/health').json()
    assert health['kb_loaded'] is True and health['data_release_id'].startswith('bootstrap-')
    response = client.post('/api/query', json={'query': 'Wo gibt es Essen?', 'language': 'de'})
    assert response.status_code == 200 and response.json()['cards']
assert (settings.runtime_dir / 'sessions.json').is_file()
record = json.loads((settings.runtime_dir / 'logs' / 'interactions.jsonl').read_text(encoding='utf-8'))
assert record['software_version'] == app.__version__
assert record['data_release_id'].startswith('bootstrap-')
package = Path(app.__file__).resolve().parent
assert not (package / 'runtime').exists()
print(json.dumps({'version': app.__version__, 'app_file': str(app.__file__)}))
"""
    smoke = _run(str(python), "-c", script, cwd=outside, env=clean_env)
    result = __import__("json").loads(smoke.stdout.strip().splitlines()[-1])
    assert result["version"] == EXPECTED_VERSION
    assert str(ROOT).casefold() not in result["app_file"].casefold()
    assert _run(str(python), "-m", "app", "--version", cwd=outside, env=clean_env).stdout.strip() == EXPECTED_VERSION

    installed_bootstrap = (
        Path(result["app_file"]).resolve().parent / "resources" / "bootstrap" / "canonical" / "offers.json"
    )
    backup = installed_bootstrap.with_suffix(".json.test-backup")
    shutil.move(installed_bootstrap, backup)
    failure_script = """
from fastapi.testclient import TestClient
from app.config import load_settings
from app.main import create_app
settings = load_settings()
with TestClient(create_app(settings)) as client:
    health = client.get('/api/health').json()
    assert health['status'] == 'error' and health['kb_loaded'] is False
"""
    try:
        _run(str(python), "-c", failure_script, cwd=outside, env=clean_env)
    finally:
        shutil.move(backup, installed_bootstrap)

    pointer = data / "wfs" / "active_release.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text("not-json", encoding="utf-8")
    try:
        _run(str(python), "-c", failure_script, cwd=outside, env=clean_env)
    finally:
        pointer.unlink()
