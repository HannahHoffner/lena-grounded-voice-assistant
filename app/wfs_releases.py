"""Unveränderliche WFS-Releases und atomarer Active-Pointer."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import Settings
from .models import OfferRecord


LOGGER = logging.getLogger(__name__)
RELEASE_FILES = {"offers.json", "snapshot.geojson", "diff.json"}
RELEASE_ID_RE = re.compile(r"^(?:\d{8}T\d{6}Z-[0-9a-f]{12}-[0-9a-f]{8}|legacy-[0-9a-f]{12})$")
_RELEASE_LOCK = threading.RLock()


class WfsReleaseError(RuntimeError):
    """Signalisiert einen ungültigen oder nicht atomar aktivierbaren Release."""


class ReleaseFile(BaseModel):
    """Bindet eine Release-Datei an ihre unveränderten Bytes."""

    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class WfsReleaseManifest(BaseModel):
    """Versionierter Vertrag eines vollständig geschriebenen WFS-Releases."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    release_id: str
    created_at: datetime
    source: Literal["leipzig-wfs"] = "leipzig-wfs"
    source_url: str
    record_count: int = Field(gt=0)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    base_release_id: str | None = None
    validation_status: Literal["valid"] = "valid"
    files: dict[str, ReleaseFile]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_contract(self) -> "WfsReleaseManifest":
        if not valid_release_id(self.release_id):
            raise ValueError("invalid release_id")
        if self.base_release_id is not None and not valid_release_id(self.base_release_id):
            raise ValueError("invalid base_release_id")
        if set(self.files) != RELEASE_FILES:
            raise ValueError("manifest must describe the exact release file set")
        return self


class ActiveReleasePointer(BaseModel):
    """Kleiner atomar austauschbarer Verweis auf genau einen Release."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    release_id: str
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    activated_at: datetime

    @model_validator(mode="after")
    def validate_release_id(self) -> "ActiveReleasePointer":
        if not valid_release_id(self.release_id):
            raise ValueError("invalid release_id")
        return self


@dataclass(frozen=True)
class WfsReleasePaths:
    """Kontrollierte Wurzeln für Legacy-, Pending- und aktive Datenstände."""

    legacy_canonical: Path
    legacy_snapshot: Path
    legacy_diff: Path
    releases: Path
    pending: Path
    pointer: Path
    state: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> "WfsReleasePaths":
        data_wfs = (settings.data_dir or settings.app_root / "data") / "wfs"
        bootstrap_wfs = (settings.bootstrap_data_dir or settings.app_root / "data") / "wfs"
        runtime = settings.runtime_dir or settings.app_root / "runtime"
        return cls(
            legacy_canonical=settings.kb_path,
            legacy_snapshot=bootstrap_wfs / "current.geojson",
            legacy_diff=bootstrap_wfs / "last_change_report.json",
            releases=data_wfs / "releases",
            pending=runtime / "wfs" / "pending",
            pointer=data_wfs / "active_release.json",
            state=runtime / "wfs" / "state.json",
        )


@dataclass(frozen=True)
class VerifiedRelease:
    release_id: str
    path: Path
    manifest: WfsReleaseManifest

    @property
    def offers_path(self) -> Path:
        return self.path / "offers.json"


def valid_release_id(release_id: str) -> bool:
    return bool(RELEASE_ID_RE.fullmatch(release_id))


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _manifest_hash(manifest: WfsReleaseManifest) -> str:
    payload = manifest.model_dump(mode="json", exclude={"manifest_sha256"})
    return _sha256(_json_bytes(payload))


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_synced(path: Path, content: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _new_release_id(content_hash: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{content_hash[:12]}-{uuid.uuid4().hex[:8]}"


def _safe_source_url(url: str) -> str:
    """Entfernt Credentials, Query und Fragment aus der Quellenreferenz."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def create_pending_release(
    settings: Settings,
    *,
    raw: dict[str, Any],
    canonical: dict[str, Any],
    diff: dict[str, Any],
    base_release_id: str | None,
    release_id: str | None = None,
) -> VerifiedRelease:
    """Schreibt einen vollständigen Release unsichtbar und finalisiert ihn einmalig."""
    paths = WfsReleasePaths.from_settings(settings)
    content_hash = str(canonical.get("source", {}).get("content_hash", ""))
    selected_id = release_id or _new_release_id(content_hash)
    if not valid_release_id(selected_id):
        raise WfsReleaseError("Invalid release ID")
    with _RELEASE_LOCK:
        base = verify_release(settings, base_release_id) if base_release_id else None
        if diff.get("current_hash") != content_hash:
            raise WfsReleaseError("Diff current hash differs from canonical data")
        if base and diff.get("previous_hash") != base.manifest.content_hash:
            raise WfsReleaseError("Diff previous hash differs from base release")
        final = paths.pending / selected_id
        if final.exists() or (paths.releases / selected_id).exists():
            raise WfsReleaseError("Release ID already exists")
        temporary = paths.pending / f".tmp-{uuid.uuid4().hex}"
        try:
            temporary.mkdir(parents=True)
            payloads = {
                "offers.json": _json_bytes(canonical),
                "snapshot.geojson": _json_bytes(raw),
                "diff.json": _json_bytes({**diff, "base_release_id": base_release_id}),
            }
            for name, content in payloads.items():
                _write_synced(temporary / name, content)
            files = {
                name: ReleaseFile(sha256=_sha256(content), size_bytes=len(content))
                for name, content in payloads.items()
            }
            manifest = WfsReleaseManifest(
                release_id=selected_id,
                created_at=datetime.now(UTC),
                source_url=_safe_source_url(settings.wfs_url),
                record_count=len(canonical.get("offers", [])),
                content_hash=content_hash,
                base_release_id=base_release_id,
                files=files,
                manifest_sha256="0" * 64,
            )
            manifest.manifest_sha256 = _manifest_hash(manifest)
            _write_synced(
                temporary / "manifest.json",
                _json_bytes(manifest.model_dump(mode="json")),
            )
            verified = verify_release_path(temporary, expected_id=selected_id)
            paths.pending.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, final)
            LOGGER.info(
                "wfs.release.created",
                extra={"release_id": selected_id, "record_count": manifest.record_count},
            )
            return VerifiedRelease(selected_id, final, verified.manifest)
        except Exception as exc:
            shutil.rmtree(temporary, ignore_errors=True)
            LOGGER.warning("wfs.release.validation_failed", extra={"error_type": type(exc).__name__})
            if isinstance(exc, WfsReleaseError):
                raise
            raise WfsReleaseError("WFS release creation failed") from exc


def verify_release_path(path: Path, *, expected_id: str | None = None) -> VerifiedRelease:
    """Prüft Manifest, exakte Dateien und die tatsächlich gespeicherten Bytes."""
    try:
        manifest_bytes = (path / "manifest.json").read_bytes()
        manifest_data = json.loads(manifest_bytes.decode("utf-8"))
        manifest = WfsReleaseManifest.model_validate(manifest_data)
        if manifest_bytes != _json_bytes(manifest.model_dump(mode="json")):
            raise WfsReleaseError("Manifest serialization is not canonical")
        release_id = expected_id or path.name
        if manifest.release_id != release_id or path.name not in {release_id} and not path.name.startswith(".tmp-"):
            raise WfsReleaseError("Release directory and manifest differ")
        if _manifest_hash(manifest) != manifest.manifest_sha256:
            raise WfsReleaseError("Manifest hash mismatch")
        names = {item.name for item in path.iterdir() if item.is_file()}
        if names != RELEASE_FILES | {"manifest.json"}:
            raise WfsReleaseError("Unexpected or missing release files")
        for name, descriptor in manifest.files.items():
            content = (path / name).read_bytes()
            if len(content) != descriptor.size_bytes or _sha256(content) != descriptor.sha256:
                raise WfsReleaseError("Release file hash mismatch")
        canonical = json.loads((path / "offers.json").read_text(encoding="utf-8"))
        raw = json.loads((path / "snapshot.geojson").read_text(encoding="utf-8"))
        diff = json.loads((path / "diff.json").read_text(encoding="utf-8"))
        offers = [OfferRecord.model_validate(item) for item in canonical["offers"]]
        if len(offers) != manifest.record_count or len({item.id for item in offers}) != len(offers):
            raise WfsReleaseError("Release record count is invalid")
        if canonical.get("source", {}).get("content_hash") != manifest.content_hash:
            raise WfsReleaseError("Canonical content hash differs from manifest")
        if raw.get("type") != "FeatureCollection" or not isinstance(raw.get("features"), list):
            raise WfsReleaseError("Snapshot is not a FeatureCollection")
        if len(raw["features"]) != manifest.record_count:
            raise WfsReleaseError("Snapshot record count differs")
        if diff.get("base_release_id") != manifest.base_release_id:
            raise WfsReleaseError("Diff base release differs from manifest")
        if diff.get("current_hash") != manifest.content_hash:
            raise WfsReleaseError("Diff current hash differs from manifest")
    except WfsReleaseError:
        raise
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WfsReleaseError("Release validation failed") from exc
    LOGGER.info("wfs.release.verified", extra={"release_id": manifest.release_id})
    return VerifiedRelease(manifest.release_id, path, manifest)


def verify_release(settings: Settings, release_id: str, *, pending: bool = False) -> VerifiedRelease:
    if not valid_release_id(release_id):
        raise WfsReleaseError("Invalid release ID")
    paths = WfsReleasePaths.from_settings(settings)
    root = paths.pending if pending else paths.releases
    try:
        release = verify_release_path(root / release_id, expected_id=release_id)
        if release.manifest.base_release_id:
            base = verify_release_path(
                paths.releases / release.manifest.base_release_id,
                expected_id=release.manifest.base_release_id,
            )
            diff = json.loads((release.path / "diff.json").read_text(encoding="utf-8"))
            if diff.get("previous_hash") != base.manifest.content_hash:
                raise WfsReleaseError("Diff does not describe its base release")
        return release
    except Exception as exc:
        LOGGER.warning(
            "wfs.release.validation_failed",
            extra={"release_id": release_id, "error_type": type(exc).__name__},
        )
        if isinstance(exc, WfsReleaseError):
            raise
        raise WfsReleaseError("Release validation failed") from exc


def _activate(paths: WfsReleasePaths, release: VerifiedRelease) -> None:
    pointer = ActiveReleasePointer(
        release_id=release.release_id,
        manifest_sha256=release.manifest.manifest_sha256,
        activated_at=datetime.now(UTC),
    )
    _atomic_write(paths.pointer, _json_bytes(pointer.model_dump(mode="json")))


def promote_release(settings: Settings, release_id: str) -> VerifiedRelease:
    """Aktiviert exakt einen vorhandenen Pending-Release ohne Netzwerkzugriff."""
    if not valid_release_id(release_id):
        raise WfsReleaseError("Invalid release ID")
    paths = WfsReleasePaths.from_settings(settings)
    with _RELEASE_LOCK:
        LOGGER.info("wfs.promotion.started", extra={"release_id": release_id})
        try:
            destination = paths.releases / release_id
            pending_path = paths.pending / release_id
            if pending_path.is_dir():
                source = verify_release(settings, release_id, pending=True)
                paths.releases.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise WfsReleaseError("Release destination already exists")
                os.replace(source.path, destination)
            elif not destination.is_dir():
                raise WfsReleaseError("Pending release does not exist")
            release = verify_release_path(destination, expected_id=release_id)
            _activate(paths, release)
        except Exception as exc:
            LOGGER.error(
                "wfs.promotion.failed",
                extra={"release_id": release_id, "error_type": type(exc).__name__},
            )
            if isinstance(exc, WfsReleaseError):
                raise
            raise WfsReleaseError("WFS promotion failed") from exc
        LOGGER.info("wfs.promotion.completed", extra={"release_id": release_id})
        return release


def rollback_release(settings: Settings, release_id: str) -> VerifiedRelease:
    """Wechselt atomar auf einen bereits vorhandenen validen Release zurück."""
    paths = WfsReleasePaths.from_settings(settings)
    with _RELEASE_LOCK:
        release = verify_release(settings, release_id)
        _activate(paths, release)
        LOGGER.info("wfs.rollback.completed", extra={"release_id": release_id})
        return release


def load_active_release(settings: Settings) -> VerifiedRelease | None:
    """Liest den Active-Pointer einmal und liefert genau den bezeichneten Release."""
    paths = WfsReleasePaths.from_settings(settings)
    if not paths.pointer.exists():
        return None
    try:
        pointer = ActiveReleasePointer.model_validate_json(paths.pointer.read_text(encoding="utf-8"))
        release = verify_release(settings, pointer.release_id)
        if release.manifest.manifest_sha256 != pointer.manifest_sha256:
            raise WfsReleaseError("Active pointer manifest hash mismatch")
    except (OSError, ValueError) as exc:
        raise WfsReleaseError("Active release pointer is invalid") from exc
    LOGGER.info("wfs.active_release.loaded", extra={"release_id": release.release_id})
    return release


def list_releases(settings: Settings, *, pending: bool = False) -> list[str]:
    root = WfsReleasePaths.from_settings(settings).pending if pending else WfsReleasePaths.from_settings(settings).releases
    if not root.is_dir():
        return []
    return sorted(item.name for item in root.iterdir() if item.is_dir() and valid_release_id(item.name))
