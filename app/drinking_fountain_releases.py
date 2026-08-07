"""Manuell aktivierte, reproduzierbare Releases der Trinkbrunnenquelle."""

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
from .drinking_fountain_source import (
    DRINKING_FOUNTAIN_KML_URL,
    DRINKING_FOUNTAIN_NORMALIZATION_VERSION,
    DRINKING_FOUNTAIN_SOURCE_PAGE_URL,
    LEIPZIG_BOUNDARY_URL,
    DrinkingFountainSourceError,
    diff_drinking_fountain_records,
    drinking_fountain_release_id,
    normalize_drinking_fountain_kml,
    release_material_hash,
)
from .infrastructure import DrinkingFountainRecordCollection, StrictModel
from .release_storage import atomic_write, canonical_json_bytes, sha256_bytes
from .resources import packaged_bootstrap_data_root


FOUNTAIN_RELEASE_SCHEMA_VERSION = "1"
FOUNTAIN_POINTER_SCHEMA_VERSION = "1"
FOUNTAIN_RELEASE_FILES = {
    "snapshot.kml",
    "municipality_boundary.geojson",
    "source_evidence.json",
    "records.json",
    "diff.json",
}
FOUNTAIN_RELEASE_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
MIN_RUNTIME_ELIGIBLE_COUNT = 10
MAX_FIXED_RECORD_REDUCTION_RATIO = 0.5


class DrinkingFountainReleaseError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class FountainReleaseFile(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class DrinkingFountainReleaseManifest(StrictModel):
    schema_version: Literal[FOUNTAIN_RELEASE_SCHEMA_VERSION] = FOUNTAIN_RELEASE_SCHEMA_VERSION
    release_id: str = Field(pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    created_at: datetime
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    boundary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: Literal[DRINKING_FOUNTAIN_KML_URL] = DRINKING_FOUNTAIN_KML_URL
    source_page_url: Literal[DRINKING_FOUNTAIN_SOURCE_PAGE_URL] = DRINKING_FOUNTAIN_SOURCE_PAGE_URL
    boundary_url: Literal[LEIPZIG_BOUNDARY_URL] = LEIPZIG_BOUNDARY_URL
    validation_status: Literal["validated"] = "validated"
    review_status: Literal["reviewed_for_prototype"] = "reviewed_for_prototype"
    record_count: int = Field(ge=1, le=500)
    runtime_eligible_count: int = Field(ge=0, le=500)
    outside_leipzig_count: int = Field(ge=0, le=500)
    mobile_excluded_count: int = Field(ge=0, le=500)
    valid_geometry_count: int = Field(ge=0, le=500)
    normalization_version: Literal[DRINKING_FOUNTAIN_NORMALIZATION_VERSION] = (
        DRINKING_FOUNTAIN_NORMALIZATION_VERSION
    )
    base_release_id: str | None = Field(default=None, pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    files: dict[str, FountainReleaseFile]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_manifest(self) -> "DrinkingFountainReleaseManifest":
        if set(self.files) != FOUNTAIN_RELEASE_FILES:
            raise ValueError("drinking-fountain release file inventory differs")
        payload = self.model_dump(mode="json", exclude={"manifest_sha256"})
        if sha256_bytes(canonical_json_bytes(payload)) != self.manifest_sha256:
            raise ValueError("drinking-fountain manifest hash differs")
        return self


class DrinkingFountainActivePointer(StrictModel):
    schema_version: Literal[FOUNTAIN_POINTER_SCHEMA_VERSION] = FOUNTAIN_POINTER_SCHEMA_VERSION
    release_id: str = Field(pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    activated_at: datetime


@dataclass(frozen=True)
class DrinkingFountainReleasePaths:
    data_root: Path
    releases: Path
    pending: Path
    pointer: Path
    verified_pointer: Path
    previous_pointer: Path
    state: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> "DrinkingFountainReleasePaths":
        data_root = (settings.data_dir or settings.app_root / "data") / "drinking_fountains"
        runtime_root = (settings.runtime_dir or settings.app_root / "runtime") / "drinking_fountains"
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
class VerifiedDrinkingFountainRelease:
    release_id: str
    path: Path
    manifest: DrinkingFountainReleaseManifest
    collection: DrinkingFountainRecordCollection


@dataclass(frozen=True)
class DrinkingFountainRuntime:
    collection: DrinkingFountainRecordCollection
    release_id: str
    path: Path
    source_hash: str
    material_hash: str
    runtime_source: Literal[
        "active_release",
        "last_verified_release",
        "previous_verified_release",
        "packaged_bootstrap",
    ]
    runtime_status: Literal["ok", "degraded"]
    source_status: Literal["current", "pointer_error", "release_error", "change_pending"]


def _normalized_hash(collection: DrinkingFountainRecordCollection) -> str:
    return sha256_bytes(canonical_json_bytes(collection.model_dump(mode="json")))


def _make_manifest(payload: dict[str, object]) -> DrinkingFountainReleaseManifest:
    prepared = {
        **payload,
        "files": {
            name: FountainReleaseFile.model_validate(value)
            for name, value in dict(payload["files"]).items()
        },
    }
    provisional = DrinkingFountainReleaseManifest.model_construct(
        **prepared,
        manifest_sha256="0" * 64,
    )
    complete = {
        **prepared,
        "manifest_sha256": sha256_bytes(
            canonical_json_bytes(provisional.model_dump(mode="json", exclude={"manifest_sha256"}))
        ),
    }
    return DrinkingFountainReleaseManifest.model_validate(complete)


def _require_source_identity(
    release: VerifiedDrinkingFountainRelease,
    settings: Settings,
) -> VerifiedDrinkingFountainRelease:
    if (
        release.manifest.source_url != settings.drinking_fountain_source_url
        or release.manifest.source_page_url != settings.drinking_fountain_source_page_url
        or release.manifest.boundary_url != settings.drinking_fountain_boundary_url
    ):
        raise DrinkingFountainReleaseError("drinking_fountain_source_identity_mismatch")
    return release


def verify_drinking_fountain_release_path(
    path: Path,
    *,
    expected_id: str | None = None,
) -> VerifiedDrinkingFountainRelease:
    try:
        manifest = DrinkingFountainReleaseManifest.model_validate_json(
            (path / "manifest.json").read_text(encoding="utf-8")
        )
        release_id = expected_id or path.name
        if manifest.release_id != release_id:
            raise ValueError("release ID differs")
        if {item.name for item in path.iterdir() if item.is_file()} != FOUNTAIN_RELEASE_FILES | {"manifest.json"}:
            raise ValueError("release file inventory differs")
        for name, descriptor in manifest.files.items():
            content = (path / name).read_bytes()
            if len(content) != descriptor.size_bytes or sha256_bytes(content) != descriptor.sha256:
                raise ValueError("release file hash differs")
        kml = (path / "snapshot.kml").read_bytes()
        boundary = (path / "municipality_boundary.geojson").read_bytes()
        evidence = (path / "source_evidence.json").read_bytes()
        collection = DrinkingFountainRecordCollection.model_validate_json(
            (path / "records.json").read_text(encoding="utf-8")
        )
        if (
            manifest.source_url != collection.source.kml_url
            or manifest.source_page_url != collection.source.source_page_url
            or manifest.boundary_url != collection.municipality_boundary.resource_url
            or manifest.source_sha256 != collection.source.sha256
            or manifest.boundary_sha256 != collection.municipality_boundary.sha256
            or any(record.release_id != manifest.release_id for record in collection.records)
        ):
            raise ValueError("release source identity differs")
        diff = json.loads((path / "diff.json").read_text(encoding="utf-8"))
        if set(diff) != {"base_release_id", "added", "removed", "modified"}:
            raise ValueError("diff schema differs")
        if diff["base_release_id"] != manifest.base_release_id:
            raise ValueError("diff base differs")
        if (
            sha256_bytes(kml) != manifest.source_sha256
            or sha256_bytes(boundary) != manifest.boundary_sha256
            or sha256_bytes(evidence) != manifest.evidence_sha256
            or release_material_hash(kml, boundary, evidence) != manifest.material_sha256
        ):
            raise ValueError("source material hash differs")
        reproduced = normalize_drinking_fountain_kml(
            kml,
            boundary,
            evidence,
            retrieved_at=collection.source.retrieved_at,
            content_type=collection.source.content_type,
            kml_url=collection.source.kml_url,
            boundary_url=collection.municipality_boundary.resource_url,
            source_last_modified=collection.source.source_last_modified,
            boundary_last_modified=collection.municipality_boundary.source_last_modified,
        )
        if canonical_json_bytes(reproduced.model_dump(mode="json")) != canonical_json_bytes(
            collection.model_dump(mode="json")
        ):
            raise ValueError("normalization is not reproducible")
        if _normalized_hash(collection) != manifest.normalized_sha256:
            raise ValueError("normalized hash differs")
        counts = _collection_counts(collection)
        for key, value in counts.items():
            if getattr(manifest, key) != value:
                raise ValueError("manifest count differs")
        return VerifiedDrinkingFountainRelease(release_id, path, manifest, collection)
    except (OSError, ValueError, json.JSONDecodeError, DrinkingFountainSourceError) as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_release_invalid") from exc


def verify_drinking_fountain_release(
    settings: Settings,
    release_id: str,
    *,
    pending: bool = False,
) -> VerifiedDrinkingFountainRelease:
    if not FOUNTAIN_RELEASE_ID_RE.fullmatch(release_id):
        raise DrinkingFountainReleaseError("drinking_fountain_release_id_invalid")
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    return verify_drinking_fountain_release_path(
        (paths.pending if pending else paths.releases) / release_id,
        expected_id=release_id,
    )


def _packaged_release() -> VerifiedDrinkingFountainRelease:
    root = packaged_bootstrap_data_root() / "drinking_fountains"
    try:
        pointer = DrinkingFountainActivePointer.model_validate_json(
            (root / "active_release.json").read_text(encoding="utf-8")
        )
        release = verify_drinking_fountain_release_path(
            root / "releases" / pointer.release_id,
            expected_id=pointer.release_id,
        )
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise ValueError("packaged pointer differs")
        return release
    except (OSError, ValueError, DrinkingFountainReleaseError) as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_bound_release_unavailable") from exc


def load_packaged_drinking_fountain_release() -> VerifiedDrinkingFountainRelease:
    return _packaged_release()


def _load_pointer(
    settings: Settings,
    pointer_path: Path,
    *,
    error_code: str,
) -> VerifiedDrinkingFountainRelease | None:
    if not pointer_path.is_file():
        return None
    try:
        pointer = DrinkingFountainActivePointer.model_validate_json(pointer_path.read_text(encoding="utf-8"))
        release = verify_drinking_fountain_release(settings, pointer.release_id)
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise ValueError("pointer hash differs")
        return _require_source_identity(release, settings)
    except (OSError, ValueError, DrinkingFountainReleaseError) as exc:
        raise DrinkingFountainReleaseError(error_code) from exc


def load_active_drinking_fountain_release(settings: Settings) -> VerifiedDrinkingFountainRelease | None:
    return _load_pointer(
        settings,
        DrinkingFountainReleasePaths.from_settings(settings).pointer,
        error_code="drinking_fountain_pointer_invalid",
    )


def load_drinking_fountain_runtime(settings: Settings) -> DrinkingFountainRuntime:
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    source_status: Literal["current", "pointer_error", "release_error", "change_pending"] = "current"
    local_state_exists = paths.data_root.exists()
    candidates: list[tuple[Path, str, str]] = [
        (paths.pointer, "active_release", "drinking_fountain_pointer_invalid"),
        (paths.verified_pointer, "last_verified_release", "drinking_fountain_last_verified_invalid"),
        (paths.previous_pointer, "previous_verified_release", "drinking_fountain_previous_verified_invalid"),
    ]
    for pointer, runtime_source, error_code in candidates:
        try:
            release = _load_pointer(settings, pointer, error_code=error_code)
        except DrinkingFountainReleaseError:
            release = None
            source_status = "pointer_error" if runtime_source == "active_release" else "release_error"
        if release is not None:
            return DrinkingFountainRuntime(
                release.collection,
                release.release_id,
                release.path,
                release.manifest.source_sha256,
                release.manifest.material_sha256,
                runtime_source,  # type: ignore[arg-type]
                "ok" if runtime_source == "active_release" else "degraded",
                source_status if runtime_source != "active_release" else "current",
            )
    try:
        packaged = _require_source_identity(_packaged_release(), settings)
    except DrinkingFountainReleaseError as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_bound_release_unavailable") from exc
    pristine = not local_state_exists and source_status == "current"
    return DrinkingFountainRuntime(
        packaged.collection,
        packaged.release_id,
        packaged.path,
        packaged.manifest.source_sha256,
        packaged.manifest.material_sha256,
        "packaged_bootstrap",
        "ok" if pristine else "degraded",
        "current" if pristine else source_status if source_status != "current" else "pointer_error",
    )


def _collection_counts(collection: DrinkingFountainRecordCollection) -> dict[str, int]:
    return {
        "record_count": len(collection.records),
        "runtime_eligible_count": sum(record.runtime_eligible for record in collection.records),
        "outside_leipzig_count": sum(
            record.exclusion_reason is not None and record.exclusion_reason.value == "outside_leipzig"
            for record in collection.records
        ),
        "mobile_excluded_count": sum(
            record.installation_type.value == "mobile" for record in collection.records
        ),
        "valid_geometry_count": sum(
            record.geometry_status.value == "valid" for record in collection.records
        ),
    }


def create_pending_drinking_fountain_release(
    settings: Settings,
    kml: bytes,
    boundary: bytes,
    evidence: bytes,
    collection: DrinkingFountainRecordCollection,
    *,
    base_release_id: str | None,
    base_collection: DrinkingFountainRecordCollection | None = None,
) -> VerifiedDrinkingFountainRelease:
    release_id = drinking_fountain_release_id(kml, boundary, evidence, collection.source.retrieved_at)
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    if (paths.pending / release_id).exists() or (paths.releases / release_id).exists():
        raise DrinkingFountainReleaseError("drinking_fountain_release_exists")
    counts = _collection_counts(collection)
    if counts["runtime_eligible_count"] < MIN_RUNTIME_ELIGIBLE_COUNT:
        raise DrinkingFountainReleaseError("drinking_fountain_source_incomplete")
    previous = base_collection
    if previous is None and base_release_id:
        previous = verify_drinking_fountain_release(settings, base_release_id).collection
    current_fixed = sum(record.installation_type.value == "fixed" for record in collection.records)
    previous_fixed = sum(record.installation_type.value == "fixed" for record in previous.records) if previous else 0
    if previous_fixed and current_fixed < previous_fixed * (1 - MAX_FIXED_RECORD_REDUCTION_RATIO):
        raise DrinkingFountainReleaseError("drinking_fountain_source_incomplete")
    diff = {"base_release_id": base_release_id, **diff_drinking_fountain_records(previous, collection)}
    file_bytes = {
        "snapshot.kml": kml,
        "municipality_boundary.geojson": boundary,
        "source_evidence.json": evidence,
        "records.json": canonical_json_bytes(collection.model_dump(mode="json")),
        "diff.json": canonical_json_bytes(diff),
    }
    manifest = _make_manifest({
        "schema_version": FOUNTAIN_RELEASE_SCHEMA_VERSION,
        "release_id": release_id,
        "created_at": collection.source.retrieved_at,
        "source_sha256": sha256_bytes(kml),
        "boundary_sha256": sha256_bytes(boundary),
        "evidence_sha256": sha256_bytes(evidence),
        "material_sha256": release_material_hash(kml, boundary, evidence),
        "normalized_sha256": _normalized_hash(collection),
        "source_url": collection.source.kml_url,
        "source_page_url": collection.source.source_page_url,
        "boundary_url": collection.municipality_boundary.resource_url,
        "validation_status": "validated",
        "review_status": "reviewed_for_prototype",
        **counts,
        "normalization_version": collection.normalization_version,
        "base_release_id": base_release_id,
        "files": {
            name: {"sha256": sha256_bytes(content), "size_bytes": len(content)}
            for name, content in file_bytes.items()
        },
    })
    paths.pending.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".tmp-{release_id}-", dir=paths.pending))
    try:
        for name, content in file_bytes.items():
            atomic_write(temporary / name, content)
        atomic_write(temporary / "manifest.json", canonical_json_bytes(manifest.model_dump(mode="json")))
        verify_drinking_fountain_release_path(temporary, expected_id=release_id)
        os.replace(temporary, paths.pending / release_id)
        return verify_drinking_fountain_release(settings, release_id, pending=True)
    except Exception as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        if isinstance(exc, DrinkingFountainReleaseError):
            raise
        raise DrinkingFountainReleaseError("drinking_fountain_release_write_failed") from exc


def _activate(paths: DrinkingFountainReleasePaths, release: VerifiedDrinkingFountainRelease) -> None:
    pointer = DrinkingFountainActivePointer(
        release_id=release.release_id,
        manifest_sha256=release.manifest.manifest_sha256,
        activated_at=datetime.now(timezone.utc),
    )
    content = canonical_json_bytes(pointer.model_dump(mode="json"))
    if paths.verified_pointer.is_file():
        try:
            previous = DrinkingFountainActivePointer.model_validate_json(
                paths.verified_pointer.read_text(encoding="utf-8")
            )
            if previous.release_id != release.release_id:
                atomic_write(paths.previous_pointer, canonical_json_bytes(previous.model_dump(mode="json")))
        except (OSError, ValueError):
            pass
    atomic_write(paths.verified_pointer, content)
    atomic_write(paths.pointer, content)


def activate_drinking_fountain_release(
    settings: Settings,
    release_id: str,
) -> VerifiedDrinkingFountainRelease:
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    pending = _require_source_identity(
        verify_drinking_fountain_release(settings, release_id, pending=True),
        settings,
    )
    paths.releases.mkdir(parents=True, exist_ok=True)
    destination = paths.releases / release_id
    if destination.exists():
        raise DrinkingFountainReleaseError("drinking_fountain_release_exists")
    os.replace(pending.path, destination)
    release = verify_drinking_fountain_release(settings, release_id)
    _activate(paths, release)
    return release


def rollback_drinking_fountain_release(
    settings: Settings,
    release_id: str,
) -> VerifiedDrinkingFountainRelease:
    """Reaktiviert einen zuvor bereits promoteten Release atomar erneut."""

    release = _require_source_identity(
        verify_drinking_fountain_release(settings, release_id),
        settings,
    )
    _activate(DrinkingFountainReleasePaths.from_settings(settings), release)
    return release


def list_drinking_fountain_releases(settings: Settings, *, pending: bool = False) -> list[str]:
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    root = paths.pending if pending else paths.releases
    if not root.is_dir():
        return []
    return sorted(item.name for item in root.iterdir() if item.is_dir() and FOUNTAIN_RELEASE_ID_RE.fullmatch(item.name))


def import_drinking_fountain_snapshot_as_pending(
    settings: Settings,
    kml: bytes,
    boundary: bytes,
    evidence: bytes,
    *,
    retrieved_at: datetime,
    content_type: str,
    source_last_modified: str | None = None,
    boundary_last_modified: str | None = None,
) -> VerifiedDrinkingFountainRelease:
    try:
        collection = normalize_drinking_fountain_kml(
            kml,
            boundary,
            evidence,
            retrieved_at=retrieved_at,
            content_type=content_type,
            kml_url=settings.drinking_fountain_source_url,
            boundary_url=settings.drinking_fountain_boundary_url,
            source_last_modified=source_last_modified,
            boundary_last_modified=boundary_last_modified,
        )
    except DrinkingFountainSourceError as exc:
        raise DrinkingFountainReleaseError(exc.code) from exc
    runtime = load_drinking_fountain_runtime(settings)
    return create_pending_drinking_fountain_release(
        settings,
        kml,
        boundary,
        evidence,
        collection,
        base_release_id=runtime.release_id,
        base_collection=runtime.collection,
    )
