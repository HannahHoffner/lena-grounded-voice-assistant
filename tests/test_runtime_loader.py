"""Sicherheitsvertrag fuer die einzige kuratierte Runtime-Wissensbasis."""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.kb_loader import KnowledgeBaseError, load_active_knowledge_base
from app.main import create_app
from app.wfs_releases import (
    ActiveReleasePointer,
    WfsReleasePaths,
    create_pending_release,
    promote_release,
    verify_release,
)
from app.wfs_sync import canonical_payload, diff_canonical, migrate_legacy_release


ROOT = Path(__file__).resolve().parents[1]
CURATION_PATH = ROOT / "app" / "resources" / "bootstrap" / "curation" / "social_offers.json"
RAW_PATH = ROOT / "data" / "wfs" / "current.geojson"
BOUND_RELEASE_ID = "legacy-3b72f95a88f9"
BOUND_SOURCE_HASH = "3b72f95a88f98c57778f50beaa4c66af61b58493fe995feb1deb6f7756d7bf9c"
EXCLUDED_IDS = {"1", "2", "3", "4"}


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        app_root=tmp_path,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=False,
        bootstrap_data_dir=ROOT / "data",
        data_dir=tmp_path / "data",
        runtime_dir=tmp_path / "runtime",
        curation_path=CURATION_PATH,
    )


def _raw() -> dict:
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def _install_bound_release(settings: Settings) -> None:
    migrated = migrate_legacy_release(settings)
    assert migrated is not None
    assert migrated.release_id == BOUND_RELEASE_ID


def _new_release(settings: Settings, mutation: str, *, promote: bool = True):
    raw = _raw()
    if mutation == "uncritical":
        raw["timeStamp"] = "2099-01-01T00:00:00Z"
    elif mutation == "modified":
        raw["features"][10]["properties"]["name"] += " geaendert"
    elif mutation == "removed":
        raw["features"].pop()
    elif mutation == "added":
        added = copy.deepcopy(raw["features"][-1])
        added["id"] = "wohnungslosenhilfe.99"
        added["properties"]["lnr"] = "99"
        added["properties"]["name"] = "Ungeprueftes neues Angebot"
        raw["features"].append(added)
    else:  # pragma: no cover - test helper contract
        raise AssertionError(mutation)

    feature_count = len(raw["features"])
    raw["numberMatched"] = feature_count
    raw["numberReturned"] = feature_count
    raw["totalFeatures"] = feature_count
    canonical = canonical_payload(raw, settings)
    previous = json.loads(
        (
            WfsReleasePaths.from_settings(settings).releases
            / BOUND_RELEASE_ID
            / "offers.json"
        ).read_text(encoding="utf-8")
    )
    pending = create_pending_release(
        settings,
        raw=raw,
        canonical=canonical,
        diff=diff_canonical(previous, canonical),
        base_release_id=BOUND_RELEASE_ID,
    )
    return promote_release(settings, pending.release_id) if promote else pending


def _assert_bound_runtime(kb, *, source_status: str, runtime_source: str) -> None:
    assert len(kb.offers) == 28
    assert {offer.id for offer in kb.offers}.isdisjoint(EXCLUDED_IDS)
    assert kb.source_hash == BOUND_SOURCE_HASH
    assert kb.metadata["source_status"] == source_status
    assert kb.metadata["runtime_source"] == runtime_source
    official = kb.metadata["official_offer_source"]
    assert official["source_version"] == "vkkj-2026-08-20"
    assert official["record_count"] == 2
    assert len(official["source_hash"]) == 64
    assert all(
        offer.source_hash == official["source_hash"]
        for offer in kb.offers
        if offer.id.startswith("vkkj_")
    )


def test_active_bound_release_is_the_healthy_runtime_source(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)

    kb = load_active_knowledge_base(settings)

    _assert_bound_runtime(kb, source_status="current", runtime_source="active_bound_release")
    assert kb.metadata["runtime_kb_status"] == "ok"


@pytest.mark.parametrize("mutation", ["uncritical", "modified", "removed", "added"])
def test_new_active_release_never_replaces_bound_curated_runtime(
    tmp_path: Path,
    mutation: str,
) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)
    original = load_active_knowledge_base(settings)
    new_release = _new_release(settings, mutation)

    kb = load_active_knowledge_base(settings)

    assert new_release.release_id != BOUND_RELEASE_ID
    _assert_bound_runtime(kb, source_status="change_pending", runtime_source="bound_release_fallback")
    assert kb.metadata["runtime_kb_status"] == "degraded"
    assert kb.runtime_kb_fingerprint == original.runtime_kb_fingerprint
    assert kb.metadata["curation"]["review_monitoring"]["review_required_due_to_source_change"] is True
    assert (
        kb.metadata["curation"]["review_monitoring"]["source_review_status"]
        == "stale_due_to_source_change"
    )


@pytest.mark.parametrize(
    ("damage", "expected_status"),
    [
        ("missing", "pointer_error"),
        ("syntax", "pointer_error"),
        ("nonexistent", "release_error"),
    ],
)
def test_pointer_failures_use_only_the_intact_local_bound_release(
    tmp_path: Path,
    damage: str,
    expected_status: str,
) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)
    paths = WfsReleasePaths.from_settings(settings)
    if damage == "missing":
        paths.pointer.unlink()
    elif damage == "syntax":
        paths.pointer.write_text("not-json", encoding="utf-8")
    else:
        pointer = ActiveReleasePointer(
            release_id="legacy-aaaaaaaaaaaa",
            manifest_sha256="0" * 64,
            activated_at=datetime.now(UTC),
        )
        paths.pointer.write_text(pointer.model_dump_json(), encoding="utf-8")

    kb = load_active_knowledge_base(settings)

    _assert_bound_runtime(
        kb,
        source_status=expected_status,
        runtime_source="bound_release_fallback",
    )
    assert kb.metadata["runtime_kb_status"] == "degraded"


def test_damaged_active_bound_release_uses_verified_packaged_bootstrap(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)
    release = verify_release(settings, BOUND_RELEASE_ID)
    with (release.path / "offers.json").open("ab") as handle:
        handle.write(b"damage")

    kb = load_active_knowledge_base(settings)

    _assert_bound_runtime(kb, source_status="release_error", runtime_source="packaged_bootstrap")
    assert kb.metadata["runtime_kb_status"] == "degraded"


def test_packaged_bootstrap_works_without_pointer_or_local_release(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    kb = load_active_knowledge_base(settings)

    _assert_bound_runtime(kb, source_status="pointer_error", runtime_source="packaged_bootstrap")
    assert kb.metadata["runtime_kb_status"] == "degraded"


def test_missing_local_and_invalid_packaged_bound_release_is_a_controlled_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    invalid_package = tmp_path / "invalid-package"
    invalid_package.mkdir()
    monkeypatch.setattr("app.kb_loader.packaged_bootstrap_data_root", lambda: invalid_package)

    with pytest.raises(KnowledgeBaseError) as raised:
        load_active_knowledge_base(settings)
    health = TestClient(create_app(settings)).get("/api/health").json()

    assert raised.value.code == "bound_release_unavailable"
    assert health["runtime_kb_status"] == "error"
    assert health["error_code"] == "bound_release_unavailable"
    assert health["offer_count"] == 0


def test_invalid_packaged_manifest_is_rejected_without_unfiltered_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    package_copy = tmp_path / "package-copy"
    shutil.copytree(ROOT / "app" / "resources" / "bootstrap", package_copy)
    (package_copy / "curation" / "runtime_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.kb_loader.packaged_bootstrap_data_root", lambda: package_copy)

    with pytest.raises(KnowledgeBaseError) as raised:
        load_active_knowledge_base(settings)

    assert raised.value.code == "bound_release_unavailable"


def test_pending_release_is_never_used_without_promotion(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)
    pending = _new_release(settings, "modified", promote=False)

    kb = load_active_knowledge_base(settings)

    assert pending.path.parent == WfsReleasePaths.from_settings(settings).pending
    _assert_bound_runtime(kb, source_status="current", runtime_source="active_bound_release")


def test_runtime_fingerprint_changes_when_only_curation_changes(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _install_bound_release(settings)
    original = load_active_knowledge_base(settings)
    changed_catalog = json.loads(CURATION_PATH.read_text(encoding="utf-8"))
    changed_catalog["catalog_version"] = "1-test-change"
    changed_path = tmp_path / "changed-curation.json"
    changed_path.write_text(
        json.dumps(changed_catalog, ensure_ascii=False),
        encoding="utf-8",
    )

    changed = load_active_knowledge_base(replace(settings, curation_path=changed_path))

    assert changed.source_hash == original.source_hash
    assert changed.runtime_kb_fingerprint != original.runtime_kb_fingerprint
