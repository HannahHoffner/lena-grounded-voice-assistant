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
from app.safety import load_safety_scenarios
from app.config import load_settings
from app.resources import bootstrap_data_root, packaged_bootstrap_data_root, static_root
from app.version import software_version
import app.version as version_module


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.2.0"
BOOTSTRAP_FILES = {
    "app/resources/bootstrap/canonical/offers.json",
    "app/resources/bootstrap/curation/runtime_manifest.json",
    "app/resources/bootstrap/curation/social_offers.json",
    "app/resources/bootstrap/evaluation/live_scenarios.json",
    "app/resources/bootstrap/i18n/application_texts.json",
    "app/resources/bootstrap/i18n/dynamic_scenarios.json",
    "app/resources/bootstrap/i18n/listening_review.json",
    "app/resources/bootstrap/i18n/offer_translations.json",
    "app/resources/bootstrap/official/verified_offers.json",
    "app/resources/bootstrap/safety/scenarios.json",
    "app/resources/bootstrap/wfs/current.geojson",
    "app/resources/bootstrap/wfs/last_change_report.json",
    "app/resources/bootstrap/toilets/active_release.json",
    "app/resources/bootstrap/toilets/releases/20260802T055552Z-fce215d4e7bd/snapshot.csv",
    "app/resources/bootstrap/toilets/releases/20260802T055552Z-fce215d4e7bd/records.json",
    "app/resources/bootstrap/toilets/releases/20260802T055552Z-fce215d4e7bd/diff.json",
    "app/resources/bootstrap/toilets/releases/20260802T055552Z-fce215d4e7bd/manifest.json",
    "app/resources/bootstrap/drinking_fountains/active_release.json",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/snapshot.kml",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/municipality_boundary.geojson",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/source_evidence.json",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/records.json",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/diff.json",
    "app/resources/bootstrap/drinking_fountains/releases/20260802T122318Z-58d55e2ab090/manifest.json",
}
FRONTEND_FILES = {
    "app/static/index.html",
    "app/static/app.js",
    "app/static/dialogue.js",
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
        "wfs/current.geojson",
        "wfs/last_change_report.json",
    ):
        assert (root / relative).is_file()
    packaged = packaged_bootstrap_data_root()
    for relative in (
        "i18n/application_texts.json",
        "i18n/dynamic_scenarios.json",
        "i18n/listening_review.json",
        "evaluation/live_scenarios.json",
        "official/verified_offers.json",
        "toilets/active_release.json",
        "drinking_fountains/active_release.json",
    ):
        assert (packaged / relative).is_file()
    assert load_settings().curation_path is not None
    assert load_settings().curation_path.is_file()


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
            "TOILET_AUTO_SYNC": "false",
            "DRINKING_FOUNTAIN_AUTO_SYNC": "false",
            "REWRITE_PROVIDER": "template",
            "SPEECH_SYNTHESIS_PROVIDER": "openai",
            # This smoke explicitly verifies logging in its isolated temp root;
            # do not inherit the runtime image's privacy-preserving default.
            "INTERACTION_LOGGING_ENABLED": "true",
            "LENA_ENV_FILE_MODE": "disabled",
            "LENA_ALLOW_LIVE_SMOKE": "false",
        }
    )
    script = """
import json
from pathlib import Path
from fastapi.testclient import TestClient
import app
from app.config import load_settings
from app.main import create_app
from app.safety import load_safety_scenarios

settings = load_settings()
assert len(load_safety_scenarios().scenarios) == 19
assert 'site-packages' in str(Path(app.__file__).resolve()).casefold(), app.__file__
assert settings.kb_path.is_file()
assert settings.runtime_dir == Path(__import__('os').environ['LENA_RUNTIME_DIR']).resolve()
assert settings.data_dir == Path(__import__('os').environ['LENA_DATA_DIR']).resolve()
app_instance = create_app(settings)
with TestClient(app_instance) as client:
    assert client.get('/').status_code == 200
    assert client.get('/static/styles.css').status_code == 200
    health = client.get('/api/health').json()
    assert health['kb_loaded'] is True and health['data_release_id'].startswith('curation-')
    assert health['offer_count'] == 28
    assert health['public_toilets']['record_count'] == 21
    assert health['public_toilets']['eligible_record_count'] == 20
    assert health['drinking_fountain_record_count'] == 35
    assert health['drinking_fountain_runtime_eligible_count'] == 21
    assert health['translations']['active_runtime_policy'] == 'reviewed_or_machine'
    assert health['application_texts']['resource_count_per_language'] > 0
    assert health['safety_policy_version'] == '2'
    assert health['technical_fallback_includes_emergency_guidance'] is True
    copy = client.get('/api/i18n/copy?language=pl').json()
    assert copy['copy_version'] == '11' and copy['language'] == 'pl' and copy['texts']
    # Der technische Fallback enthaelt zusaetzlich den
    # deterministischen Hilfebus-Kontakt statt eines reinen 112-Hinweises,
    # sofern die Wissensbasis ihn liefert (Untersuchung Zeile 5).
    hilfebus_id = next(o.id for o in app_instance.state.kb.offers if 'general_help_referral_first' in o.priority_rules)
    response = client.post('/api/query', json={'query': 'Wo gibt es Essen?', 'language': 'de'})
    assert response.status_code == 200
    assert response.json()['answer_type'] == 'technical_fallback'
    assert [card['id'] for card in response.json()['cards']] == [hilfebus_id]
    assert response.json()['map_data'] is None
    assert '112' in response.json()['answer']
    toilets = client.post('/api/query', json={'query': 'Wo ist eine Toilette?', 'language': 'de'}).json()
    assert [card['id'] for card in toilets['cards']] == [hilfebus_id]
    assert toilets['map_marker_ids'] == []
    assert toilets['answer_type'] == 'technical_fallback' and '112' in toilets['answer']
    fountains = client.post('/api/query', json={'query': 'Wo ist der nächste Trinkbrunnen?', 'language': 'de'}).json()
    assert [card['id'] for card in fountains['cards']] == [hilfebus_id]
    assert fountains['map_marker_ids'] == []
    assert fountains['answer_type'] == 'technical_fallback' and '112' in fountains['answer']
assert (settings.runtime_dir / 'sessions.json').is_file()
records = (settings.runtime_dir / 'logs' / 'interactions.jsonl').read_text(encoding='utf-8').splitlines()
record = json.loads(records[-1])
assert record['software_version'] == app.__version__ and record['schema_version'] == 11
assert record['data_release_id'].startswith('curation-')
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
    fallback_script = """
from fastapi.testclient import TestClient
from app.config import load_settings
from app.main import create_app
with TestClient(create_app(load_settings())) as client:
    health = client.get('/api/health').json()
    assert health['kb_loaded'] is True
    assert health['runtime_kb_status'] == 'degraded'
    assert health['source_status'] == 'pointer_error'
    assert health['runtime_source'] == 'packaged_bootstrap'
    assert health['offer_count'] == 28
"""
    try:
        _run(str(python), "-c", fallback_script, cwd=outside, env=clean_env)
    finally:
        pointer.unlink()
