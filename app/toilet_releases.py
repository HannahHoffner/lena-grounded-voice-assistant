"""Separater, manuell freigegebener Releasepfad öffentlicher Toiletten."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .config import Settings
from .infrastructure import (
    ToiletRecordCollection,
    ToiletSourceError,
    ToiletSourceMetadata,
    diff_toilet_records,
    normalize_toilet_csv,
)
from .release_storage import atomic_write, canonical_json_bytes, sha256_bytes
from .resources import packaged_bootstrap_data_root


TOILET_RELEASE_SCHEMA_VERSION = "1"
TOILET_POINTER_SCHEMA_VERSION = "1"
TOILET_RELEASE_FILES = {"snapshot.csv", "records.json", "diff.json"}
TOILET_RELEASE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
MIN_VALID_GEOMETRY_RATIO = 0.5
MAX_RECORD_REDUCTION_RATIO = 0.5


class ToiletReleaseError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


from .infrastructure import StrictModel  # imported here to keep release contracts source-local


class ToiletReleaseFile(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ToiletReleaseManifest(StrictModel):
    schema_version: Literal[TOILET_RELEASE_SCHEMA_VERSION] = TOILET_RELEASE_SCHEMA_VERSION
    release_id: str = Field(pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    created_at: datetime
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ToiletSourceMetadata
    normalized_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_status: Literal["validated"] = "validated"
    record_count: int = Field(ge=1, le=500)
    normalization_version: str = Field(min_length=1, max_length=20)
    base_release_id: str | None = Field(default=None, pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    files: dict[str, ToiletReleaseFile]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_files(self) -> "ToiletReleaseManifest":
        if set(self.files) != TOILET_RELEASE_FILES:
            raise ValueError("toilet release manifest has an unexpected file set")
        payload = self.model_dump(mode="json", exclude={"manifest_sha256"})
        if sha256_bytes(canonical_json_bytes(payload)) != self.manifest_sha256:
            raise ValueError("toilet release manifest hash is invalid")
        return self


class ToiletActivePointer(StrictModel):
    schema_version: Literal[TOILET_POINTER_SCHEMA_VERSION] = TOILET_POINTER_SCHEMA_VERSION
    release_id: str = Field(pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    promoted_at: datetime


@dataclass(frozen=True)
class ToiletReleasePaths:
    data_root: Path
    releases: Path
    pending: Path
    pointer: Path
    verified_pointer: Path
    previous_pointer: Path
    state: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> "ToiletReleasePaths":
        data_root = (settings.data_dir or settings.app_root / "data") / "toilets"
        runtime_root = (settings.runtime_dir or settings.app_root / "runtime") / "toilets"
        return cls(
            data_root=data_root,
            releases=data_root / "releases",
            pending=runtime_root / "pending",
            pointer=data_root / "active_release.json",
            verified_pointer=data_root / "last_verified_release.json",
            previous_pointer=data_root / "previous_verified_release.json",
            state=runtime_root / "sync_state.json",
        )


@dataclass(frozen=True)
class VerifiedToiletRelease:
    release_id: str
    path: Path
    manifest: ToiletReleaseManifest
    collection: ToiletRecordCollection


@dataclass(frozen=True)
class ToiletRuntime:
    collection: ToiletRecordCollection
    release_id: str
    source_hash: str
    runtime_source: Literal[
        "active_release",
        "last_verified_release",
        "previous_verified_release",
        "packaged_bootstrap",
    ]
    runtime_status: Literal["ok", "degraded"]
    source_status: Literal["current", "pointer_error", "release_error", "change_pending"]


def _release_id(source_hash: str, created_at: datetime) -> str:
    return f"{created_at.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{source_hash[:12]}"


def _normalized_content_hash(collection: ToiletRecordCollection) -> str:
    """Bindet ausschließlich Schema, Normalisierungsversion und Datensätze."""

    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": collection.schema_version,
                "normalization_version": collection.normalization_version,
                "records": [record.model_dump(mode="json") for record in collection.records],
            }
        )
    )


def _manifest(payload: dict[str, object]) -> ToiletReleaseManifest:
    normalized = {
        **payload,
        "created_at": datetime.fromisoformat(str(payload["created_at"])),
        "files": {
            name: ToiletReleaseFile.model_validate(descriptor)
            for name, descriptor in dict(payload["files"]).items()
        },
        "source": ToiletSourceMetadata.model_validate(payload["source"]),
    }
    provisional = ToiletReleaseManifest.model_construct(
        **normalized,
        manifest_sha256="0" * 64,
    )
    normalized["manifest_sha256"] = sha256_bytes(
        canonical_json_bytes(provisional.model_dump(mode="json", exclude={"manifest_sha256"}))
    )
    return ToiletReleaseManifest.model_validate(normalized)


def verify_toilet_release_path(path: Path, *, expected_id: str | None = None) -> VerifiedToiletRelease:
    try:
        manifest_path = path / "manifest.json"
        manifest = ToiletReleaseManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        release_id = expected_id or path.name
        if manifest.release_id != release_id:
            raise ValueError("release ID differs")
        actual_files = {item.name for item in path.iterdir() if item.is_file()}
        if actual_files != TOILET_RELEASE_FILES | {"manifest.json"}:
            raise ValueError("unexpected release files")
        for name, descriptor in manifest.files.items():
            content = (path / name).read_bytes()
            if len(content) != descriptor.size_bytes or sha256_bytes(content) != descriptor.sha256:
                raise ValueError("release file hash differs")
        snapshot = (path / "snapshot.csv").read_bytes()
        records = ToiletRecordCollection.model_validate_json((path / "records.json").read_text(encoding="utf-8"))
        diff = json.loads((path / "diff.json").read_text(encoding="utf-8"))
        if records.source != manifest.source:
            raise ValueError("source metadata differs")
        if records.source.sha256 != manifest.source_sha256 or sha256_bytes(snapshot) != manifest.source_sha256:
            raise ValueError("source hash differs")
        reproduced = normalize_toilet_csv(
            snapshot,
            fetched_at=records.source.fetched_at,
            content_type=records.source.content_type,
            resource_url=records.source.resource_url,
            source_last_modified=records.source.source_last_modified,
        )
        if canonical_json_bytes(reproduced.model_dump(mode="json")) != canonical_json_bytes(
            records.model_dump(mode="json")
        ):
            raise ValueError("normalized records are not reproducible from snapshot")
        if _normalized_content_hash(records) != manifest.normalized_sha256:
            raise ValueError("normalized content hash differs")
        if len(records.records) != manifest.record_count:
            raise ValueError("record count differs")
        if set(diff) != {"base_release_id", "added", "removed", "modified"}:
            raise ValueError("diff schema differs")
        if diff["base_release_id"] != manifest.base_release_id:
            raise ValueError("diff base differs")
        return VerifiedToiletRelease(manifest.release_id, path, manifest, records)
    except (OSError, ValueError, json.JSONDecodeError, ToiletSourceError) as exc:
        raise ToiletReleaseError("toilet_release_invalid") from exc


def verify_toilet_release(settings: Settings, release_id: str, *, pending: bool = False) -> VerifiedToiletRelease:
    if not TOILET_RELEASE_ID_RE.fullmatch(release_id):
        raise ToiletReleaseError("toilet_release_id_invalid")
    paths = ToiletReleasePaths.from_settings(settings)
    return verify_toilet_release_path((paths.pending if pending else paths.releases) / release_id, expected_id=release_id)


def _require_source_identity(
    release: VerifiedToiletRelease,
    expected_resource_url: str,
) -> VerifiedToiletRelease:
    """Reject internally valid releases from a different configured source."""

    if release.manifest.source.resource_url.strip() != expected_resource_url.strip():
        raise ToiletReleaseError("toilet_source_identity_mismatch")
    return release


def _packaged_release() -> VerifiedToiletRelease:
    root = packaged_bootstrap_data_root() / "toilets"
    try:
        pointer = ToiletActivePointer.model_validate_json((root / "active_release.json").read_text(encoding="utf-8"))
        release = verify_toilet_release_path(root / "releases" / pointer.release_id, expected_id=pointer.release_id)
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise ValueError("packaged pointer differs")
        return release
    except (OSError, ValueError, ToiletReleaseError) as exc:
        raise ToiletReleaseError("toilet_bound_release_unavailable") from exc


def load_packaged_toilet_release() -> VerifiedToiletRelease:
    """Verifiziert den gebundenen Paket-Bootstrap für CLI und Runtime."""

    return _packaged_release()


def load_active_toilet_release(settings: Settings) -> VerifiedToiletRelease | None:
    paths = ToiletReleasePaths.from_settings(settings)
    if not paths.pointer.is_file():
        return None
    try:
        pointer = ToiletActivePointer.model_validate_json(paths.pointer.read_text(encoding="utf-8"))
        release = verify_toilet_release(settings, pointer.release_id)
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise ValueError("active pointer differs")
        return _require_source_identity(release, settings.toilet_source_url)
    except (OSError, ValueError, ToiletReleaseError) as exc:
        raise ToiletReleaseError("toilet_pointer_invalid") from exc


def _load_pointer_release(settings: Settings, path: Path) -> VerifiedToiletRelease | None:
    paths = ToiletReleasePaths.from_settings(settings)
    if not path.is_file():
        return None
    try:
        pointer = ToiletActivePointer.model_validate_json(path.read_text(encoding="utf-8"))
        release = verify_toilet_release(settings, pointer.release_id)
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise ValueError("verified pointer differs")
        return _require_source_identity(release, settings.toilet_source_url)
    except (OSError, ValueError, ToiletReleaseError) as exc:
        raise ToiletReleaseError("toilet_last_verified_release_invalid") from exc


def _load_last_verified_toilet_release(settings: Settings) -> VerifiedToiletRelease | None:
    return _load_pointer_release(settings, ToiletReleasePaths.from_settings(settings).verified_pointer)


def load_toilet_runtime(settings: Settings) -> ToiletRuntime:
    """Lädt nur einen verifizierten aktiven Release oder den Paket-Bootstrap."""

    source_status: Literal["current", "pointer_error", "release_error", "change_pending"] = "current"
    paths = ToiletReleasePaths.from_settings(settings)
    local_state_exists = paths.data_root.exists()
    try:
        active = load_active_toilet_release(settings)
    except ToiletReleaseError:
        active = None
        source_status = "pointer_error"
    if active is not None:
        return ToiletRuntime(active.collection, active.release_id, active.manifest.source_sha256, "active_release", "ok", source_status)
    try:
        last_verified = _load_last_verified_toilet_release(settings)
    except ToiletReleaseError:
        last_verified = None
        source_status = "release_error"
    if last_verified is not None:
        return ToiletRuntime(
            last_verified.collection,
            last_verified.release_id,
            last_verified.manifest.source_sha256,
            "last_verified_release",
            "degraded",
            source_status if source_status != "current" else "pointer_error",
        )
    try:
        previous = _load_pointer_release(settings, paths.previous_pointer)
    except ToiletReleaseError:
        previous = None
    if previous is not None:
        return ToiletRuntime(
            previous.collection,
            previous.release_id,
            previous.manifest.source_sha256,
            "previous_verified_release",
            "degraded",
            "release_error",
        )
    try:
        packaged = _require_source_identity(_packaged_release(), settings.toilet_source_url)
    except ToiletReleaseError as exc:
        raise ToiletReleaseError("toilet_bound_release_unavailable") from exc
    if not local_state_exists and source_status == "current":
        return ToiletRuntime(
            packaged.collection,
            packaged.release_id,
            packaged.manifest.source_sha256,
            "packaged_bootstrap",
            "ok",
            "current",
        )
    return ToiletRuntime(
        packaged.collection,
        packaged.release_id,
        packaged.manifest.source_sha256,
        "packaged_bootstrap",
        "degraded",
        source_status if source_status != "current" else "pointer_error",
    )


def create_pending_toilet_release(
    settings: Settings,
    snapshot: bytes,
    collection: ToiletRecordCollection,
    *,
    base_release_id: str | None,
    base_collection: ToiletRecordCollection | None = None,
    created_at: datetime | None = None,
) -> VerifiedToiletRelease:
    """Erzeugt einen vollständig verifizierten Pending-Release ohne Aktivierung."""

    created = created_at or datetime.now(timezone.utc)
    release_id = _release_id(collection.source.sha256, created)
    paths = ToiletReleasePaths.from_settings(settings)
    if (paths.pending / release_id).exists() or (paths.releases / release_id).exists():
        raise ToiletReleaseError("toilet_release_exists")
    previous = base_collection
    if previous is None and base_release_id:
        previous = verify_toilet_release(settings, base_release_id).collection
    valid_geometry_count = sum(record.coordinates_status.value == "valid" for record in collection.records)
    if valid_geometry_count / len(collection.records) < MIN_VALID_GEOMETRY_RATIO:
        raise ToiletReleaseError("toilet_geometry_invalid")
    if previous and len(collection.records) < len(previous.records) * (1 - MAX_RECORD_REDUCTION_RATIO):
        raise ToiletReleaseError("toilet_record_invalid")
    diff = {"base_release_id": base_release_id, **diff_toilet_records(previous, collection)}
    file_bytes = {
        "snapshot.csv": snapshot,
        "records.json": canonical_json_bytes(collection.model_dump(mode="json")),
        "diff.json": canonical_json_bytes(diff),
    }
    manifest = _manifest(
        {
            "schema_version": TOILET_RELEASE_SCHEMA_VERSION,
            "release_id": release_id,
            "created_at": created.isoformat(),
            "source_sha256": collection.source.sha256,
            "source": collection.source.model_dump(mode="json"),
            "normalized_sha256": _normalized_content_hash(collection),
            "validation_status": "validated",
            "record_count": len(collection.records),
            "normalization_version": collection.normalization_version,
            "base_release_id": base_release_id,
            "files": {
                name: {"sha256": sha256_bytes(content), "size_bytes": len(content)}
                for name, content in file_bytes.items()
            },
        }
    )
    paths.pending.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".tmp-{release_id}-", dir=paths.pending))
    try:
        for name, content in file_bytes.items():
            atomic_write(temporary / name, content)
        atomic_write(temporary / "manifest.json", canonical_json_bytes(manifest.model_dump(mode="json")))
        verify_toilet_release_path(temporary, expected_id=release_id)
        os.replace(temporary, paths.pending / release_id)
        return verify_toilet_release(settings, release_id, pending=True)
    except Exception as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        if isinstance(exc, ToiletReleaseError):
            raise
        raise ToiletReleaseError("toilet_release_write_failed") from exc


def _activate(paths: ToiletReleasePaths, release: VerifiedToiletRelease) -> None:
    pointer = ToiletActivePointer(
        release_id=release.release_id,
        manifest_sha256=release.manifest.manifest_sha256,
        promoted_at=datetime.now(timezone.utc),
    )
    content = canonical_json_bytes(pointer.model_dump(mode="json"))
    if paths.verified_pointer.is_file():
        try:
            previous = ToiletActivePointer.model_validate_json(
                paths.verified_pointer.read_text(encoding="utf-8")
            )
            if previous.release_id != release.release_id:
                atomic_write(paths.previous_pointer, canonical_json_bytes(previous.model_dump(mode="json")))
        except (OSError, ValueError):
            pass
    atomic_write(paths.verified_pointer, content)
    atomic_write(paths.pointer, content)


def promote_toilet_release(settings: Settings, release_id: str) -> VerifiedToiletRelease:
    paths = ToiletReleasePaths.from_settings(settings)
    pending = _require_source_identity(
        verify_toilet_release(settings, release_id, pending=True),
        settings.toilet_source_url,
    )
    paths.releases.mkdir(parents=True, exist_ok=True)
    destination = paths.releases / release_id
    if destination.exists():
        raise ToiletReleaseError("toilet_release_exists")
    os.replace(pending.path, destination)
    release = verify_toilet_release(settings, release_id)
    _activate(paths, release)
    return release


def rollback_toilet_release(settings: Settings, release_id: str) -> VerifiedToiletRelease:
    release = _require_source_identity(
        verify_toilet_release(settings, release_id),
        settings.toilet_source_url,
    )
    _activate(ToiletReleasePaths.from_settings(settings), release)
    return release


def list_toilet_releases(settings: Settings, *, pending: bool = False) -> list[str]:
    paths = ToiletReleasePaths.from_settings(settings)
    root = paths.pending if pending else paths.releases
    if not root.is_dir():
        return []
    return sorted(item.name for item in root.iterdir() if item.is_dir() and TOILET_RELEASE_ID_RE.fullmatch(item.name))


def import_snapshot_as_pending(
    settings: Settings,
    snapshot: bytes,
    *,
    fetched_at: datetime,
    content_type: str,
    source_last_modified: str | None = None,
) -> VerifiedToiletRelease:
    """Validiert einen Abruf vor jeglicher Release-Schreiboperation."""

    try:
        collection = normalize_toilet_csv(
            snapshot,
            fetched_at=fetched_at,
            content_type=content_type,
            resource_url=settings.toilet_source_url,
            source_last_modified=source_last_modified,
        )
    except ToiletSourceError as exc:
        raise ToiletReleaseError(exc.code) from exc
    runtime = load_toilet_runtime(settings)
    return create_pending_toilet_release(
        settings,
        snapshot,
        collection,
        base_release_id=runtime.release_id,
        base_collection=runtime.collection,
        created_at=fetched_at,
    )
