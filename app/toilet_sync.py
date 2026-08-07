"""CLI und optionaler Hintergrundabruf der amtlichen Toiletten-CSV."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import Settings, load_settings
from .infrastructure import diff_toilet_records, normalize_toilet_csv
from .release_storage import atomic_write, canonical_json_bytes
from .toilet_releases import (
    ToiletReleaseError,
    ToiletReleasePaths,
    import_snapshot_as_pending,
    list_toilet_releases,
    load_active_toilet_release,
    load_packaged_toilet_release,
    load_toilet_runtime,
    promote_toilet_release,
    rollback_toilet_release,
    verify_toilet_release,
)


@dataclass(frozen=True)
class ToiletFetchResult:
    status: str
    changed: bool
    record_count: int
    source_hash: str
    pending_release_id: str | None
    active_release_id: str | None


async def _download(settings: Settings) -> tuple[bytes, str, str | None]:
    timeout = httpx.Timeout(
        connect=settings.toilet_connect_timeout_seconds,
        read=settings.toilet_read_timeout_seconds,
        write=settings.toilet_read_timeout_seconds,
        pool=settings.toilet_connect_timeout_seconds,
    )
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(settings.toilet_source_url, headers={"Accept": "text/csv"})
            response.raise_for_status()
            return response.content, response.headers.get("content-type", ""), response.headers.get("last-modified")
    except httpx.TimeoutException as exc:
        raise ToiletReleaseError("toilet_source_timeout") from exc
    except httpx.HTTPError as exc:
        raise ToiletReleaseError("toilet_source_unavailable") from exc


def _write_state(settings: Settings, payload: dict[str, object]) -> None:
    atomic_write(ToiletReleasePaths.from_settings(settings).state, canonical_json_bytes(payload))


def load_toilet_state(settings: Settings) -> dict[str, object]:
    path = ToiletReleasePaths.from_settings(settings).state
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


async def fetch_toilets(settings: Settings, *, stage: bool = True) -> ToiletFetchResult:
    """Ruft die Quelle ab; Aktivierung ist absichtlich kein Parameter."""

    checked_at = datetime.now(timezone.utc)
    snapshot, content_type, last_modified = await _download(settings)
    collection = normalize_toilet_csv(
        snapshot,
        fetched_at=checked_at,
        content_type=content_type,
        resource_url=settings.toilet_source_url,
        source_last_modified=last_modified,
    )
    runtime = load_toilet_runtime(settings)
    try:
        active = load_active_toilet_release(settings)
    except ToiletReleaseError:
        active = None
    active_hash = runtime.source_hash
    changed = collection.source.sha256 != active_hash
    pending_release_id = None
    if stage and changed:
        for release_id in list_toilet_releases(settings, pending=True):
            try:
                pending = verify_toilet_release(settings, release_id, pending=True)
            except ToiletReleaseError:
                continue
            if pending.manifest.source_sha256 == collection.source.sha256:
                pending_release_id = pending.release_id
                break
        if pending_release_id is None:
            pending_release_id = import_snapshot_as_pending(
                settings,
                snapshot,
                fetched_at=checked_at,
                content_type=content_type,
                source_last_modified=last_modified,
            ).release_id
    result = ToiletFetchResult(
        status="change_pending" if changed else "current",
        changed=changed,
        record_count=len(collection.records),
        source_hash=collection.source.sha256,
        pending_release_id=pending_release_id,
        active_release_id=active.release_id if active else runtime.release_id,
    )
    _write_state(
        settings,
        {
            "last_checked_at": checked_at.isoformat(),
            "last_status": result.status,
            "pending_changes": result.changed,
            "source_hash": result.source_hash,
            "pending_release_id": result.pending_release_id,
        },
    )
    return result


async def diff_live_source(settings: Settings) -> dict[str, object]:
    snapshot, content_type, last_modified = await _download(settings)
    collection = normalize_toilet_csv(
        snapshot,
        fetched_at=datetime.now(timezone.utc),
        content_type=content_type,
        resource_url=settings.toilet_source_url,
        source_last_modified=last_modified,
    )
    runtime = load_toilet_runtime(settings)
    try:
        active = load_active_toilet_release(settings)
    except ToiletReleaseError:
        active = None
    return {
        "source_hash": collection.source.sha256,
        "record_count": len(collection.records),
        "active_release_id": active.release_id if active else runtime.release_id,
        **diff_toilet_records(active.collection if active else runtime.collection, collection),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage separately approved Leipzig public-toilet releases.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fetch", help="Fetch, validate and stage a changed source without promotion.")
    validate = commands.add_parser("validate", help="Validate a release without changing state.")
    validate.add_argument("release_id", nargs="?")
    validate.add_argument("--pending", action="store_true")
    commands.add_parser("diff", help="Compare the live source with the active release without writing a release.")
    promote = commands.add_parser("promote", help="Explicitly promote a verified pending release.")
    promote.add_argument("release_id")
    rollback = commands.add_parser("rollback", help="Explicitly reactivate a verified prior release.")
    rollback.add_argument("release_id")
    commands.add_parser("status", help="Show redacted release and source state.")
    return parser


async def run_command(settings: Settings, args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "fetch":
        return asdict(await fetch_toilets(settings))
    if args.command == "diff":
        return await diff_live_source(settings)
    if args.command == "promote":
        return promote_toilet_release(settings, args.release_id).manifest.model_dump(mode="json")
    if args.command == "rollback":
        return rollback_toilet_release(settings, args.release_id).manifest.model_dump(mode="json")
    if args.command == "validate":
        if args.release_id:
            release = verify_toilet_release(settings, args.release_id, pending=args.pending)
        else:
            release = load_active_toilet_release(settings)
            if release is None:
                release = load_packaged_toilet_release()
        return release.manifest.model_dump(mode="json")
    runtime = load_toilet_runtime(settings)
    active = None
    try:
        active = load_active_toilet_release(settings)
    except ToiletReleaseError:
        pass
    return {
        "active_release_id": active.release_id if active else None,
        "runtime_release_id": runtime.release_id,
        "runtime_status": runtime.runtime_status,
        "runtime_source": runtime.runtime_source,
        "source_status": runtime.source_status,
        "record_count": len(runtime.collection.records),
        "releases": list_toilet_releases(settings),
        "pending": list_toilet_releases(settings, pending=True),
        "sync": load_toilet_state(settings),
    }


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(run_command(load_settings(), args))
    except ToiletReleaseError as exc:
        raise SystemExit(exc.code) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
