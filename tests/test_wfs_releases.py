from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.kb_loader import KnowledgeBaseError, load_active_knowledge_base
from app.main import create_app
from app.wfs_releases import (
    WfsReleaseError,
    WfsReleasePaths,
    create_pending_release,
    list_releases,
    load_active_release,
    promote_release,
    rollback_release,
    verify_release,
)
from app.wfs_sync import canonical_payload, diff_canonical, migrate_legacy_release


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "wfs" / "current.geojson"


def _settings(root: Path, *, interactions: bool = False) -> Settings:
    return Settings(
        app_root=root,
        kb_path=root / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=interactions,
        interaction_log_path=root / "runtime" / "logs" / "interactions.jsonl",
    )


def _raw() -> dict:
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def _pending(settings: Settings, *, base: str | None = None):
    raw = _raw()
    canonical = canonical_payload(copy.deepcopy(raw), settings)
    previous = None
    if base:
        base_path = WfsReleasePaths.from_settings(settings).releases / base / "offers.json"
        previous = json.loads(base_path.read_text(encoding="utf-8"))
    return create_pending_release(
        settings,
        raw=raw,
        canonical=canonical,
        diff=diff_canonical(previous, canonical),
        base_release_id=base,
    )


def test_pending_release_has_valid_manifest_hashes_sizes_and_diff(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    release = _pending(settings)

    verified = verify_release(settings, release.release_id, pending=True)
    assert verified.manifest.record_count == 30
    assert set(verified.manifest.files) == {"offers.json", "snapshot.geojson", "diff.json"}
    for name, descriptor in verified.manifest.files.items():
        assert descriptor.size_bytes == (verified.path / name).stat().st_size
    assert json.loads((verified.path / "diff.json").read_text(encoding="utf-8"))["base_release_id"] is None
    assert list_releases(settings, pending=True) == [release.release_id]
    assert not any(item.name.startswith(".tmp-") for item in verified.path.parent.iterdir())


def test_promotion_uses_existing_release_and_atomic_pointer(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pending = _pending(settings)

    promoted = promote_release(settings, pending.release_id)

    active = load_active_release(settings)
    assert active is not None
    assert active.release_id == pending.release_id
    assert active.path == promoted.path
    assert not pending.path.exists()
    assert load_active_knowledge_base(settings).release_id == pending.release_id


@pytest.mark.parametrize("filename", ["offers.json", "snapshot.geojson", "diff.json", "manifest.json"])
def test_modified_release_file_is_rejected(tmp_path: Path, filename: str) -> None:
    settings = _settings(tmp_path)
    release = _pending(settings)
    target = release.path / filename
    target.write_bytes(target.read_bytes() + b" ")

    with pytest.raises(WfsReleaseError):
        promote_release(settings, release.release_id)
    assert load_active_release(settings) is None


def test_unexpected_file_and_uncontrolled_release_id_are_rejected(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    release = _pending(settings)
    (release.path / "extra.json").write_text("{}", encoding="utf-8")

    with pytest.raises(WfsReleaseError):
        verify_release(settings, release.release_id, pending=True)
    with pytest.raises(WfsReleaseError):
        verify_release(settings, "../outside", pending=True)


def test_pointer_replace_failure_keeps_old_release_and_is_retryable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    first = _pending(settings)
    promote_release(settings, first.release_id)
    second = _pending(settings, base=first.release_id)
    paths = WfsReleasePaths.from_settings(settings)
    real_replace = __import__("app.wfs_releases", fromlist=["os"]).os.replace

    def fail_pointer(source, destination) -> None:
        if Path(destination) == paths.pointer:
            raise OSError("simulated pointer failure")
        real_replace(source, destination)

    monkeypatch.setattr("app.wfs_releases.os.replace", fail_pointer)
    with pytest.raises(WfsReleaseError):
        promote_release(settings, second.release_id)
    assert load_active_release(settings).release_id == first.release_id  # type: ignore[union-attr]

    monkeypatch.setattr("app.wfs_releases.os.replace", real_replace)
    promote_release(settings, second.release_id)
    assert load_active_release(settings).release_id == second.release_id  # type: ignore[union-attr]


def test_rollback_switches_only_pointer_without_download(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first = _pending(settings)
    promote_release(settings, first.release_id)
    second = _pending(settings, base=first.release_id)
    promote_release(settings, second.release_id)

    rollback_release(settings, first.release_id)

    assert load_active_release(settings).release_id == first.release_id  # type: ignore[union-attr]
    assert (WfsReleasePaths.from_settings(settings).releases / second.release_id).is_dir()


def test_active_load_uses_pointer_only_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    first = _pending(settings)
    promote_release(settings, first.release_id)
    second = _pending(settings, base=first.release_id)
    paths = WfsReleasePaths.from_settings(settings)
    pointer_reads = 0
    original_read_text = Path.read_text

    def tracked_read(path: Path, *args, **kwargs):
        nonlocal pointer_reads
        if path == paths.pointer:
            pointer_reads += 1
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", tracked_read)
    loaded = load_active_knowledge_base(settings)

    assert loaded.release_id == first.release_id
    assert pointer_reads == 1
    assert second.path.is_dir()


def test_legacy_migration_is_idempotent_and_uses_no_network(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    paths = WfsReleasePaths.from_settings(settings)
    raw = _raw()
    canonical = canonical_payload(copy.deepcopy(raw), settings)
    paths.legacy_canonical.parent.mkdir(parents=True)
    paths.legacy_snapshot.parent.mkdir(parents=True)
    paths.legacy_canonical.write_text(json.dumps(canonical), encoding="utf-8")
    paths.legacy_snapshot.write_text(json.dumps(raw), encoding="utf-8")

    first = migrate_legacy_release(settings)
    second = migrate_legacy_release(settings)

    assert first is not None and second is not None
    assert first.release_id == second.release_id == f"legacy-{canonical['source']['content_hash'][:12]}"
    assert load_active_knowledge_base(settings).release_id == first.release_id


def test_corrupt_pointer_does_not_fall_back_to_pending_or_legacy(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    release = _pending(settings)
    settings.kb_path.parent.mkdir(parents=True)
    settings.kb_path.write_text(json.dumps(canonical_payload(_raw(), settings)), encoding="utf-8")
    paths = WfsReleasePaths.from_settings(settings)
    paths.pointer.parent.mkdir(parents=True, exist_ok=True)
    paths.pointer.write_text('{"release_id":"bad"}', encoding="utf-8")

    with pytest.raises(KnowledgeBaseError):
        load_active_knowledge_base(settings)
    assert release.path.is_dir()


def test_parallel_release_creation_produces_unique_complete_releases(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        releases = list(pool.map(lambda _: _pending(settings), range(4)))

    assert len({item.release_id for item in releases}) == 4
    assert len(list_releases(settings, pending=True)) == 4
    for release in releases:
        verify_release(settings, release.release_id, pending=True)


def test_interaction_records_release_used_for_answer(tmp_path: Path) -> None:
    settings = _settings(tmp_path, interactions=True)
    release = _pending(settings)
    promote_release(settings, release.release_id)

    response = TestClient(create_app(settings)).post("/api/query", json={"query": "Wo gibt es Essen?"})

    assert response.status_code == 200
    record = json.loads(settings.interaction_log_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert record["data_release_id"] == release.release_id
    assert record["schema_version"] == 2


def test_failed_release_write_leaves_no_visible_pending_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "app.wfs_releases._write_synced",
        lambda *_: (_ for _ in ()).throw(OSError("simulated")),
    )

    with pytest.raises(WfsReleaseError):
        _pending(settings)
    assert list_releases(settings, pending=True) == []
