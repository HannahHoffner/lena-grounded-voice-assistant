"""Validiert, staged und aktiviert den städtischen WFS-Datenbestand atomar."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx

from .config import Settings, load_settings
from .models import OfferRecord
from .wfs_releases import (
    WfsReleaseError,
    WfsReleasePaths,
    create_pending_release,
    list_releases,
    load_active_release,
    promote_release,
    rollback_release,
    verify_release,
)


FEATURE_TYPE = "OpenData:wohnungslosenhilfe"
LOGGER = logging.getLogger(__name__)
EXPECTED_FIELDS = {
    "lnr", "name", "kat", "adr", "str", "hnr", "hnrz", "plz", "ort", "ot", "sbz",
    "oeffn", "angebot", "ap1", "ap2", "ap3", "ap4", "ap5", "tel1", "tel2", "tel3",
    "tel4", "tel5", "fax1", "fax2", "fax3", "mail1", "mail2", "mail3", "mail4", "pdf",
    "webseite", "sonst", "str_hnr_kombi", "fme_tstamp",
}
REQUIRED_FIELDS = {"lnr", "name", "kat", "adr"}
LICENSE = {
    "provider": "Stadt Leipzig",
    "name": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
    "identifier": "dl-de/by-2-0",
    "url": "https://www.govdata.de/dl-de/by-2-0",
    "modified_notice": "Daten automatisiert strukturiert und für LENA aufbereitet.",
}
TIME_RE = re.compile(r"\b\d{1,2}\s*[:.]\s*\d{2}\b")
WEEKDAY_RE = re.compile(
    r"\b(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|wochenende|feiertag)\b",
    re.IGNORECASE,
)


class WfsSyncError(RuntimeError):
    """Blockiert eine Synchronisation bei Transport- oder Vertragsverletzungen."""
    pass


class WfsTimeoutError(WfsSyncError):
    """Kennzeichnet einen Verbindungs- oder Lesetimeout der WFS-Quelle."""


@dataclass(frozen=True)
class WfsSyncResult:
    checked_at: str
    changed: bool
    promoted: bool
    offer_count: int
    content_hash: str
    added: int
    removed: int
    modified: int
    release_id: str | None = None
    active_release_id: str | None = None


def load_wfs_state(settings: Settings) -> dict[str, Any]:
    return _read_json(WfsReleasePaths.from_settings(settings).state) or {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _stable_id(value: Any) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise WfsSyncError(f"Invalid lnr value: {value!r}") from exc
    return str(int(number)) if number == number.to_integral_value() else format(number.normalize(), "f")


def _lines(value: Any) -> list[str]:
    if value is None:
        return []
    return [line.strip() for line in str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]


def _values(properties: dict[str, Any], prefix: str, count: int) -> list[str]:
    return [str(properties[f"{prefix}{index}"]).strip() for index in range(1, count + 1) if properties.get(f"{prefix}{index}")]


def _stand_times(services: list[str], hours: list[str], notes: list[str]) -> list[str]:
    values: list[str] = []
    for group in (services, hours, notes):
        active = False
        for line in group:
            if "standzeit" in line.casefold():
                active = True
                values.append(line)
            elif active and (TIME_RE.search(line) or WEEKDAY_RE.search(line)):
                values.append(line)
            elif active:
                active = False
    return list(dict.fromkeys(values))


def _feature_hash(feature: dict[str, Any]) -> str:
    stable = {"properties": feature.get("properties", {}), "geometry": feature.get("geometry")}
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dataset_hash(features: list[dict[str, Any]]) -> str:
    stable = [
        {"id": _stable_id(feature["properties"]["lnr"]), "hash": _feature_hash(feature)}
        for feature in sorted(features, key=lambda item: Decimal(str(item["properties"]["lnr"])))
    ]
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_feature_collection(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Prüft Vollständigkeit, Pflichtfelder, IDs und Geometrien einer WFS-Antwort.

    Raises:
        WfsSyncError: Wenn der Datensatz nicht sicher normalisiert werden kann.
    """
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise WfsSyncError("WFS response is not a GeoJSON FeatureCollection")
    features = payload["features"]
    if not features:
        raise WfsSyncError("WFS returned no offers")
    matched = payload.get("numberMatched", payload.get("totalFeatures"))
    returned = payload.get("numberReturned", len(features))
    if isinstance(matched, int) and (returned != matched or len(features) != matched):
        raise WfsSyncError("WFS response is incomplete")

    ids: set[str] = set()
    for feature in features:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise WfsSyncError("WFS feature has no properties")
        fields = set(properties)
        if fields != EXPECTED_FIELDS:
            added = sorted(fields - EXPECTED_FIELDS)
            removed = sorted(EXPECTED_FIELDS - fields)
            raise WfsSyncError(f"WFS schema changed; added={added}, removed={removed}")
        missing = sorted(field for field in REQUIRED_FIELDS if properties.get(field) in {None, ""})
        if missing:
            raise WfsSyncError(f"WFS feature lacks required values: {missing}")
        offer_id = _stable_id(properties["lnr"])
        if offer_id in ids:
            raise WfsSyncError(f"Duplicate lnr in WFS response: {offer_id}")
        ids.add(offer_id)
        geometry = feature.get("geometry")
        if geometry is not None and geometry.get("type") != "Point":
            raise WfsSyncError(f"Unexpected geometry type for offer {offer_id}")
    return features


def normalize_feature(feature: dict[str, Any], crs: str) -> OfferRecord:
    """Überführt ein validiertes WFS-Feature verlustarm in ein ``OfferRecord``."""
    properties = feature["properties"]
    offer_id = _stable_id(properties["lnr"])
    services = _lines(properties.get("angebot"))
    hours = _lines(properties.get("oeffn"))
    notes = _lines(properties.get("sonst"))
    district_parts = [str(properties[key]).strip() for key in ("sbz", "ot") if properties.get(key)]
    raw_fields = {key: _lines(value) for key, value in properties.items() if value is not None}
    feature_hash = _feature_hash(feature)
    geometry = feature.get("geometry")
    normalized_geometry = None
    if geometry:
        normalized_geometry = {
            "type": geometry.get("type"),
            "coordinates": geometry.get("coordinates"),
            "crs": crs,
        }
    return OfferRecord(
        id=offer_id,
        source_index=0,
        source_title=str(properties["name"]).strip(),
        name=str(properties["name"]).strip(),
        source_category=str(properties["kat"]).strip(),
        short_description=str(properties["kat"]).strip(),
        district=" / ".join(district_parts) or None,
        address=str(properties["adr"]).strip(),
        header_address=str(properties["str_hnr_kombi"]).strip() if properties.get("str_hnr_kombi") else None,
        services=services,
        opening_hours_raw=hours,
        standzeiten_raw=_stand_times(services, hours, notes),
        phone_numbers=_values(properties, "tel", 5),
        emails=_values(properties, "mail", 4),
        website=str(properties["webseite"]).strip() if properties.get("webseite") else None,
        notes=notes,
        raw_fields=raw_fields,
        raw_text=json.dumps(properties, ensure_ascii=False, sort_keys=True),
        geometry=normalized_geometry,
        source_feature_id=str(feature.get("id")) if feature.get("id") else None,
        source_updated_at=str(properties["fme_tstamp"]),
        source_hash=feature_hash,
        raw_properties=properties,
    )


def canonical_payload(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    features = validate_feature_collection(payload)
    crs = str(payload.get("crs", {}).get("properties", {}).get("name") or "urn:ogc:def:crs:EPSG::25833")
    offers = [normalize_feature(feature, crs) for feature in features]
    offers.sort(key=lambda offer: Decimal(offer.id))
    for position, offer in enumerate(offers, start=1):
        offer.source_index = position
    content_hash = _dataset_hash(features)
    return {
        "schema_version": 2,
        "generated_at": _now(),
        "source": {
            "kind": "WFS",
            "service_url": settings.wfs_url,
            "feature_type": FEATURE_TYPE,
            "response_timestamp": payload.get("timeStamp"),
            "crs": crs,
            "feature_count": len(offers),
            "content_hash": content_hash,
        },
        "license": {
            **LICENSE,
            "dataset_url": (
                f"{settings.wfs_url}?REQUEST=GetCapabilities&SERVICE=WFS"
            ),
        },
        "offers": [offer.model_dump(mode="json") for offer in offers],
    }


def diff_canonical(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    old_by_id = {str(item["id"]): item for item in (previous or {}).get("offers", [])}
    new_by_id = {str(item["id"]): item for item in current.get("offers", [])}
    added = sorted(new_by_id.keys() - old_by_id.keys(), key=Decimal)
    removed = sorted(old_by_id.keys() - new_by_id.keys(), key=Decimal)
    modified: list[dict[str, Any]] = []
    ignored = {"source_hash", "raw_text", "raw_fields", "raw_properties"}
    for offer_id in sorted(new_by_id.keys() & old_by_id.keys(), key=Decimal):
        old = old_by_id[offer_id]
        new = new_by_id[offer_id]
        fields = sorted(
            key for key in set(old) | set(new) if key not in ignored and old.get(key) != new.get(key)
        )
        if old.get("source_hash") != new.get("source_hash") or fields:
            modified.append({"id": offer_id, "name": new.get("name"), "changed_fields": fields})
    return {
        "created_at": _now(),
        "previous_schema_version": (previous or {}).get("schema_version"),
        "current_schema_version": current.get("schema_version"),
        "normalization_changed": (previous or {}).get("schema_version") != current.get("schema_version"),
        "previous_hash": (previous or {}).get("source", {}).get("content_hash"),
        "current_hash": current.get("source", {}).get("content_hash"),
        "added": [{"id": offer_id, "name": new_by_id[offer_id].get("name")} for offer_id in added],
        "removed": [{"id": offer_id, "name": old_by_id[offer_id].get("name")} for offer_id in removed],
        "modified": modified,
    }


async def fetch_wfs(settings: Settings) -> dict[str, Any]:
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": FEATURE_TYPE,
        "COUNT": "10000",
        "OUTPUTFORMAT": "application/json",
    }
    try:
        timeout = httpx.Timeout(
            connect=settings.wfs_connect_timeout_seconds,
            read=settings.wfs_read_timeout_seconds,
            write=settings.wfs_read_timeout_seconds,
            pool=settings.wfs_connect_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(settings.wfs_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise WfsTimeoutError("WFS request timed out") from exc
    except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
        raise WfsSyncError("WFS request failed") from exc
    if not isinstance(payload, dict):
        raise WfsSyncError("WFS returned an invalid JSON document")
    return payload


def migrate_legacy_release(settings: Settings):
    """Übernimmt den bestehenden aktiven Stand idempotent ohne WFS-Abruf."""
    active = load_active_release(settings)
    if active is not None:
        return active
    paths = WfsReleasePaths.from_settings(settings)
    if not paths.legacy_canonical.is_file() or not paths.legacy_snapshot.is_file():
        return None
    canonical = _read_json(paths.legacy_canonical)
    raw = _read_json(paths.legacy_snapshot)
    if canonical is None or raw is None:
        raise WfsSyncError("Legacy WFS release is invalid")
    validate_feature_collection(raw)
    normalized = canonical_payload(raw, settings)
    content_hash = str(canonical.get("source", {}).get("content_hash", ""))
    if normalized.get("source", {}).get("content_hash") != content_hash:
        raise WfsSyncError("Legacy canonical data and snapshot differ")
    release_id = f"legacy-{content_hash[:12]}"
    paths = WfsReleasePaths.from_settings(settings)
    if (paths.releases / release_id).is_dir():
        return rollback_release(settings, release_id)
    if not (paths.pending / release_id).is_dir():
        report = diff_canonical(None, canonical)
        create_pending_release(
            settings,
            raw=raw,
            canonical=canonical,
            diff=report,
            base_release_id=None,
            release_id=release_id,
        )
    return promote_release(settings, release_id)


async def sync_wfs(settings: Settings, *, promote: bool = False) -> WfsSyncResult:
    """Erzeugt aus genau einem WFS-Abruf einen unveränderlichen Release.

    Args:
        settings: WFS-URL und Projektpfade.
        promote: Aktiviert den soeben erzeugten Release bei tatsächlicher Änderung.

    Returns:
        Status, Hashes und Zeitpunkte des Synchronisationslaufs.

    Raises:
        WfsSyncError: Bei Netzwerk-, Schema- oder Schreibfehlern.
    """
    checked_at = _now()
    try:
        active = migrate_legacy_release(settings)
    except WfsReleaseError as exc:
        raise WfsSyncError("Legacy WFS migration failed") from exc
    paths = WfsReleasePaths.from_settings(settings)
    raw = await fetch_wfs(settings)
    current = canonical_payload(raw, settings)
    previous = _read_json(active.offers_path) if active else _read_json(paths.legacy_canonical)
    report = diff_canonical(previous, current)
    changed = bool(
        report["previous_hash"] != report["current_hash"] or report["normalization_changed"]
    )
    try:
        pending = create_pending_release(
            settings,
            raw=raw,
            canonical=current,
            diff=report,
            base_release_id=active.release_id if active else None,
        )
        promoted_release = promote_release(settings, pending.release_id) if changed and promote else None
    except WfsReleaseError as exc:
        raise WfsSyncError("WFS release processing failed") from exc
    promoted = promoted_release is not None
    active_release_id = promoted_release.release_id if promoted_release else (active.release_id if active else None)

    state = {
        "last_checked_at": checked_at,
        "last_status": "ok",
        "source_response_timestamp": current["source"].get("response_timestamp"),
        "source_feature_count": current["source"]["feature_count"],
        "source_content_hash": current["source"]["content_hash"],
        "pending_changes": bool(changed and not promoted),
        "pending_release_id": pending.release_id if not promoted else None,
        "active_release_id": active_release_id,
        "last_promoted_at": checked_at if promoted else (_read_json(paths.state) or {}).get("last_promoted_at"),
    }
    _atomic_json(paths.state, state)
    return WfsSyncResult(
        checked_at=checked_at,
        changed=changed,
        promoted=promoted,
        offer_count=current["source"]["feature_count"],
        content_hash=current["source"]["content_hash"],
        added=len(report["added"]),
        removed=len(report["removed"]),
        modified=len(report["modified"]),
        release_id=pending.release_id,
        active_release_id=active_release_id,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check and normalize the Leipzig Wohnungslosenhilfe WFS.")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Check and stage changes without activating them.")
    action.add_argument("--promote", metavar="RELEASE_ID", help="Validate and activate an existing pending release.")
    action.add_argument("--verify", metavar="RELEASE_ID", help="Verify an active release without changing it.")
    action.add_argument("--rollback", metavar="RELEASE_ID", help="Atomically activate a previous valid release.")
    action.add_argument("--list", action="store_true", help="List active and pending release IDs.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()
    if args.promote:
        result: Any = promote_release(settings, args.promote).manifest.model_dump(mode="json")
    elif args.verify:
        pending = args.verify in list_releases(settings, pending=True)
        result = verify_release(settings, args.verify, pending=pending).manifest.model_dump(mode="json")
    elif args.rollback:
        result = rollback_release(settings, args.rollback).manifest.model_dump(mode="json")
    elif args.list:
        active = load_active_release(settings)
        result = {
            "active": active.release_id if active else None,
            "releases": list_releases(settings),
            "pending": list_releases(settings, pending=True),
        }
    else:
        result = asyncio.run(sync_wfs(settings, promote=False)).__dict__
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
