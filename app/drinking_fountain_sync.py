"""CLI und optionaler Hintergrundabruf der geprüften Trinkbrunnenquellen."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import Settings, load_settings
from .drinking_fountain_releases import (
    DrinkingFountainReleaseError,
    DrinkingFountainReleasePaths,
    activate_drinking_fountain_release,
    create_pending_drinking_fountain_release,
    list_drinking_fountain_releases,
    load_active_drinking_fountain_release,
    load_drinking_fountain_runtime,
    load_packaged_drinking_fountain_release,
    rollback_drinking_fountain_release,
    verify_drinking_fountain_release,
)
from .drinking_fountain_source import (
    DrinkingFountainSourceError,
    diff_drinking_fountain_records,
    normalize_drinking_fountain_kml,
    release_material_hash,
)
from .release_storage import atomic_write, canonical_json_bytes


@dataclass(frozen=True)
class DrinkingFountainFetchResult:
    status: str
    changed: bool
    record_count: int
    runtime_eligible_count: int
    source_hash: str
    pending_release_id: str | None
    active_release_id: str | None


async def _download(settings: Settings) -> tuple[bytes, str, str | None, bytes, str | None]:
    timeout = httpx.Timeout(
        connect=settings.drinking_fountain_connect_timeout_seconds,
        read=settings.drinking_fountain_read_timeout_seconds,
        write=settings.drinking_fountain_read_timeout_seconds,
        pool=settings.drinking_fountain_connect_timeout_seconds,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            kml_response = await client.get(
                settings.drinking_fountain_source_url,
                headers={"Accept": "application/vnd.google-earth.kml+xml,text/xml"},
            )
            kml_response.raise_for_status()
            boundary_response = await client.get(
                settings.drinking_fountain_boundary_url,
                headers={"Accept": "application/geo+json,application/json"},
            )
            boundary_response.raise_for_status()
            return (
                kml_response.content,
                kml_response.headers.get("content-type", ""),
                kml_response.headers.get("last-modified"),
                boundary_response.content,
                boundary_response.headers.get("last-modified"),
            )
    except httpx.TimeoutException as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_source_timeout") from exc
    except httpx.HTTPError as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_source_unavailable") from exc


def _write_state(settings: Settings, payload: dict[str, object]) -> None:
    atomic_write(DrinkingFountainReleasePaths.from_settings(settings).state, canonical_json_bytes(payload))


def load_drinking_fountain_state(settings: Settings) -> dict[str, object]:
    try:
        payload = json.loads(
            DrinkingFountainReleasePaths.from_settings(settings).state.read_text(encoding="utf-8")
        )
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _page_evidence(runtime) -> bytes:
    try:
        return (runtime.path / "source_evidence.json").read_bytes()
    except OSError as exc:
        raise DrinkingFountainReleaseError("drinking_fountain_page_evidence_invalid") from exc


async def fetch_drinking_fountains(
    settings: Settings,
    *,
    stage: bool = True,
) -> DrinkingFountainFetchResult:
    """Ruft öffentliche Quellen ab; Aktivierung ist absichtlich kein Parameter."""

    checked_at = datetime.now(timezone.utc)
    kml, content_type, source_modified, boundary, boundary_modified = await _download(settings)
    runtime = load_drinking_fountain_runtime(settings)
    evidence = _page_evidence(runtime)
    try:
        collection = normalize_drinking_fountain_kml(
            kml,
            boundary,
            evidence,
            retrieved_at=checked_at,
            content_type=content_type,
            kml_url=settings.drinking_fountain_source_url,
            boundary_url=settings.drinking_fountain_boundary_url,
            source_last_modified=source_modified,
            boundary_last_modified=boundary_modified,
        )
    except DrinkingFountainSourceError as exc:
        raise DrinkingFountainReleaseError(exc.code) from exc
    material_hash = release_material_hash(kml, boundary, evidence)
    changed = material_hash != runtime.material_hash
    pending_release_id = None
    if stage and changed:
        for release_id in list_drinking_fountain_releases(settings, pending=True):
            try:
                pending = verify_drinking_fountain_release(settings, release_id, pending=True)
            except DrinkingFountainReleaseError:
                continue
            if pending.manifest.material_sha256 == material_hash:
                pending_release_id = pending.release_id
                break
        if pending_release_id is None:
            pending_release_id = create_pending_drinking_fountain_release(
                settings,
                kml,
                boundary,
                evidence,
                collection,
                base_release_id=runtime.release_id,
                base_collection=runtime.collection,
            ).release_id
    active = None
    try:
        active = load_active_drinking_fountain_release(settings)
    except DrinkingFountainReleaseError:
        pass
    result = DrinkingFountainFetchResult(
        status="change_pending" if changed else "current",
        changed=changed,
        record_count=len(collection.records),
        runtime_eligible_count=sum(record.runtime_eligible for record in collection.records),
        source_hash=collection.source.sha256,
        pending_release_id=pending_release_id,
        active_release_id=active.release_id if active else runtime.release_id,
    )
    _write_state(settings, {
        "last_checked_at": checked_at.isoformat(),
        "last_status": result.status,
        "pending_changes": result.changed,
        "source_hash": result.source_hash,
        "pending_release_id": result.pending_release_id,
    })
    return result


async def diff_live_source(settings: Settings) -> dict[str, object]:
    kml, content_type, source_modified, boundary, boundary_modified = await _download(settings)
    runtime = load_drinking_fountain_runtime(settings)
    evidence = _page_evidence(runtime)
    try:
        collection = normalize_drinking_fountain_kml(
            kml,
            boundary,
            evidence,
            retrieved_at=datetime.now(timezone.utc),
            content_type=content_type,
            kml_url=settings.drinking_fountain_source_url,
            boundary_url=settings.drinking_fountain_boundary_url,
            source_last_modified=source_modified,
            boundary_last_modified=boundary_modified,
        )
    except DrinkingFountainSourceError as exc:
        raise DrinkingFountainReleaseError(exc.code) from exc
    return {
        "source_hash": collection.source.sha256,
        "record_count": len(collection.records),
        "runtime_eligible_count": sum(record.runtime_eligible for record in collection.records),
        "active_release_id": runtime.release_id,
        **diff_drinking_fountain_records(runtime.collection, collection),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage approved Leipzig drinking-fountain releases.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show redacted source and release state.")
    commands.add_parser("fetch", help="Fetch, validate and stage a change without activation.")
    validate = commands.add_parser("validate", help="Validate a release without changing activation.")
    validate.add_argument("release_id", nargs="?")
    validate.add_argument("--pending", action="store_true")
    commands.add_parser("diff", help="Compare live sources with the runtime release without writing.")
    activate = commands.add_parser("activate", help="Explicitly activate a verified pending release.")
    activate.add_argument("release_id")
    rollback = commands.add_parser("rollback", help="Explicitly reactivate a verified prior release.")
    rollback.add_argument("release_id")
    return parser


async def run_command(settings: Settings, args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "fetch":
        return asdict(await fetch_drinking_fountains(settings))
    if args.command == "diff":
        return await diff_live_source(settings)
    if args.command == "activate":
        return activate_drinking_fountain_release(settings, args.release_id).manifest.model_dump(mode="json")
    if args.command == "rollback":
        return rollback_drinking_fountain_release(settings, args.release_id).manifest.model_dump(mode="json")
    if args.command == "validate":
        if args.release_id:
            release = verify_drinking_fountain_release(settings, args.release_id, pending=args.pending)
        else:
            release = load_active_drinking_fountain_release(settings) or load_packaged_drinking_fountain_release()
        return release.manifest.model_dump(mode="json")
    runtime = load_drinking_fountain_runtime(settings)
    active = None
    try:
        active = load_active_drinking_fountain_release(settings)
    except DrinkingFountainReleaseError:
        pass
    return {
        "active_release_id": active.release_id if active else None,
        "runtime_release_id": runtime.release_id,
        "runtime_status": runtime.runtime_status,
        "runtime_source": runtime.runtime_source,
        "source_status": runtime.source_status,
        "record_count": len(runtime.collection.records),
        "runtime_eligible_count": sum(record.runtime_eligible for record in runtime.collection.records),
        "releases": list_drinking_fountain_releases(settings),
        "pending": list_drinking_fountain_releases(settings, pending=True),
        "sync": load_drinking_fountain_state(settings),
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(run_command(load_settings(), args))
    except DrinkingFountainReleaseError as exc:
        raise SystemExit(exc.code) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
