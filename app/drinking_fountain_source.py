"""Deterministische Normalisierung der geprüften Trinkbrunnenquellen."""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone

from .infrastructure import (
    CoordinatesStatus,
    DrinkingFountainPageEvidence,
    DrinkingFountainRecord,
    DrinkingFountainRecordCollection,
    DrinkingFountainSourceMetadata,
    FountainExclusionReason,
    InstallationType,
    MunicipalityBoundaryMetadata,
)
from .release_storage import sha256_bytes
from .spatial import wgs84_to_utm33n


DRINKING_FOUNTAIN_NORMALIZATION_VERSION = "1"
DRINKING_FOUNTAIN_SOURCE_PAGE_URL = (
    "https://www.l.de/wasserwerke/leipziger-wasser/trinkwasserbrunnen/"
)
DRINKING_FOUNTAIN_MAP_VIEWER_URL = (
    "https://www.google.com/maps/d/viewer?"
    "mid=1X3y_V9KdgtfsEucc4T-tmNV_hYe8rdEP&femb=1&"
    "ll=51.30705144270525%2C12.405211867667303&z=12"
)
DRINKING_FOUNTAIN_KML_URL = (
    "https://www.google.com/maps/d/kml?"
    "mid=1X3y_V9KdgtfsEucc4T-tmNV_hYe8rdEP&forcekml=1"
)
LEIPZIG_BOUNDARY_URL = (
    "https://static.leipzig.de/fileadmin/mediendatenbank/leipzig-de/Stadt/"
    "02.1_Dez1_Allgemeine_Verwaltung/12_Statistik_und_Wahlen/Geodaten/"
    "StatistischeBezirke_Leipzig_UTM33N.json"
)
FIXED_FOLDER = "Trinkbrunnen (stationär)"
MOBILE_FOLDER = "Trinkbrunnen (mobil)"
KML_NAMESPACE = {"kml": "http://www.opengis.net/kml/2.2"}


class DrinkingFountainSourceError(RuntimeError):
    """Redigierter Fehler der KML- oder Verwaltungsquellprüfung."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def release_material_hash(kml: bytes, boundary: bytes, evidence: bytes) -> str:
    """Bindet alle drei normalisierungsrelevanten Eingaben ohne Metadatenmix."""

    return sha256_bytes(kml + b"\0" + boundary + b"\0" + evidence)


def drinking_fountain_release_id(
    kml: bytes,
    boundary: bytes,
    evidence: bytes,
    retrieved_at: datetime,
) -> str:
    digest = release_material_hash(kml, boundary, evidence)
    return f"{retrieved_at.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{digest[:12]}"


def _slug(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(character for character in folded if not unicodedata.combining(character))
    ascii_text = ascii_text.replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:72]


def _clean_description(value: str) -> str | None:
    with_breaks = re.sub(r"<br\s*/?>", "; ", value, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", " ", with_breaks)
    normalized = " ".join(html.unescape(plain).split())
    return normalized[:500] or None


def _point_in_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous = len(ring) - 1
    for index, coordinate in enumerate(ring):
        xi, yi = float(coordinate[0]), float(coordinate[1])
        xj, yj = float(ring[previous][0]), float(ring[previous][1])
        crosses = (yi > y) != (yj > y)
        if crosses and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        previous = index
    return inside


def _point_in_geometry(point: tuple[float, float], geometry: dict[str, object]) -> bool:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type not in {"Polygon", "MultiPolygon"} or not isinstance(coordinates, list):
        raise DrinkingFountainSourceError("drinking_fountain_boundary_invalid")
    polygons = [coordinates] if geometry_type == "Polygon" else coordinates
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise DrinkingFountainSourceError("drinking_fountain_boundary_invalid")
        rings = polygon
        if _point_in_ring(point, rings[0]) and not any(_point_in_ring(point, ring) for ring in rings[1:]):
            return True
    return False


def _boundary_features(content: bytes) -> tuple[dict[str, object], list[dict[str, object]]]:
    try:
        payload = json.loads(content.decode("utf-8-sig"))
        crs = payload["crs"]["properties"]["name"]
        features = payload["features"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise DrinkingFountainSourceError("drinking_fountain_boundary_invalid") from exc
    if payload.get("type") != "FeatureCollection" or crs != "EPSG:25833" or not isinstance(features, list):
        raise DrinkingFountainSourceError("drinking_fountain_boundary_invalid")
    if not features:
        raise DrinkingFountainSourceError("drinking_fountain_boundary_empty")
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("geometry"), dict):
            raise DrinkingFountainSourceError("drinking_fountain_boundary_invalid")
    return payload, features


def _inside_leipzig(
    latitude: float,
    longitude: float,
    features: list[dict[str, object]],
) -> bool:
    try:
        point = wgs84_to_utm33n(latitude, longitude)
    except (ValueError, OverflowError) as exc:
        raise DrinkingFountainSourceError("drinking_fountain_geometry_invalid") from exc
    return any(_point_in_geometry(point, feature["geometry"]) for feature in features)


def _parse_coordinate(value: str) -> tuple[CoordinatesStatus, float | None, float | None]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) not in {2, 3} or not all(parts[:2]):
        return CoordinatesStatus.INVALID, None, None
    try:
        longitude, latitude = float(parts[0]), float(parts[1])
    except ValueError:
        return CoordinatesStatus.INVALID, None, None
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        return CoordinatesStatus.INVALID, None, None
    return CoordinatesStatus.VALID, latitude, longitude


def _placemarks(content: bytes) -> list[dict[str, object]]:
    if not content or content.lstrip().startswith(b"<html"):
        raise DrinkingFountainSourceError("drinking_fountain_source_not_kml")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise DrinkingFountainSourceError("drinking_fountain_source_not_kml") from exc
    document_name = root.findtext(".//kml:Document/kml:name", namespaces=KML_NAMESPACE)
    if " ".join((document_name or "").split()) != "Leipziger Trinkbrunnen":
        raise DrinkingFountainSourceError("drinking_fountain_source_identity_mismatch")
    rows: list[dict[str, object]] = []
    for folder in root.findall(".//kml:Folder", KML_NAMESPACE):
        folder_name = " ".join((folder.findtext("./kml:name", namespaces=KML_NAMESPACE) or "").split())
        if folder_name not in {FIXED_FOLDER, MOBILE_FOLDER}:
            continue
        installation = InstallationType.FIXED if folder_name == FIXED_FOLDER else InstallationType.MOBILE
        for placemark in folder.findall("./kml:Placemark", KML_NAMESPACE):
            name = " ".join((placemark.findtext("./kml:name", namespaces=KML_NAMESPACE) or "").split())
            coordinate_nodes = placemark.findall(".//kml:Point/kml:coordinates", KML_NAMESPACE)
            if not name or len(coordinate_nodes) != 1 or not coordinate_nodes[0].text:
                raise DrinkingFountainSourceError("drinking_fountain_record_invalid")
            status, latitude, longitude = _parse_coordinate(coordinate_nodes[0].text.strip())
            description = _clean_description(
                placemark.findtext("./kml:description", default="", namespaces=KML_NAMESPACE)
            )
            fixed_slug = _slug(name)
            if not fixed_slug:
                raise DrinkingFountainSourceError("drinking_fountain_record_invalid")
            if installation == InstallationType.FIXED:
                source_id = fixed_slug
            else:
                material = f"{name}\0{description or ''}\0{latitude}\0{longitude}"
                source_id = f"mobile-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:12]}"
            rows.append({
                "folder": folder_name,
                "installation": installation,
                "name": name,
                "description": description,
                "source_id": source_id,
                "geometry_status": status,
                "latitude": latitude,
                "longitude": longitude,
            })
    if not rows:
        raise DrinkingFountainSourceError("drinking_fountain_source_empty")
    fixed_ids = [str(row["source_id"]) for row in rows if row["installation"] == InstallationType.FIXED]
    if len(fixed_ids) != len(set(fixed_ids)):
        raise DrinkingFountainSourceError("drinking_fountain_duplicate_id")
    return rows


def normalize_drinking_fountain_kml(
    kml: bytes,
    boundary: bytes,
    page_evidence_bytes: bytes,
    *,
    retrieved_at: datetime,
    content_type: str,
    kml_url: str = DRINKING_FOUNTAIN_KML_URL,
    boundary_url: str = LEIPZIG_BOUNDARY_URL,
    source_last_modified: str | None = None,
    boundary_last_modified: str | None = None,
) -> DrinkingFountainRecordCollection:
    """Normalisiert KML-Punkte und prüft Leipzig lokal gegen amtliche Polygone."""

    if content_type.split(";", 1)[0].strip().casefold() not in {"text/xml", "application/vnd.google-earth.kml+xml"}:
        raise DrinkingFountainSourceError("drinking_fountain_source_not_kml")
    try:
        evidence = DrinkingFountainPageEvidence.model_validate_json(page_evidence_bytes)
    except ValueError as exc:
        raise DrinkingFountainSourceError("drinking_fountain_page_evidence_invalid") from exc
    if evidence.source_url != DRINKING_FOUNTAIN_SOURCE_PAGE_URL:
        raise DrinkingFountainSourceError("drinking_fountain_source_identity_mismatch")
    _boundary, features = _boundary_features(boundary)
    rows = _placemarks(kml)
    coordinate_counts = Counter(
        (row["latitude"], row["longitude"])
        for row in rows
        if row["geometry_status"] == CoordinatesStatus.VALID
    )
    source_hash = sha256_bytes(kml)
    release_id = drinking_fountain_release_id(kml, boundary, page_evidence_bytes, retrieved_at)
    records: list[DrinkingFountainRecord] = []
    for row in rows:
        geometry_status = row["geometry_status"]
        latitude = row["latitude"]
        longitude = row["longitude"]
        if geometry_status == CoordinatesStatus.VALID and coordinate_counts[(latitude, longitude)] > 1:
            geometry_status = CoordinatesStatus.DUPLICATE
            latitude = longitude = None
        inside = bool(
            geometry_status == CoordinatesStatus.VALID
            and latitude is not None
            and longitude is not None
            and _inside_leipzig(latitude, longitude, features)
        )
        installation = row["installation"]
        exclusion: FountainExclusionReason | None = None
        if installation == InstallationType.MOBILE:
            exclusion = FountainExclusionReason.MOBILE_SCHEDULE_NOT_VERIFIED
        elif geometry_status == CoordinatesStatus.DUPLICATE:
            exclusion = FountainExclusionReason.DUPLICATE_LOCATION
        elif geometry_status != CoordinatesStatus.VALID:
            exclusion = FountainExclusionReason.INVALID_GEOMETRY
        elif not inside:
            exclusion = FountainExclusionReason.OUTSIDE_LEIPZIG
        runtime_eligible = exclusion is None
        source_id = str(row["source_id"])
        records.append(DrinkingFountainRecord(
            id=f"drinking_fountain:{source_id}",
            source_id=source_id,
            source_name=str(row["name"]),
            source_url=kml_url,
            source_record_reference=f"{row['folder']}/{row['name']}" + (
                "" if installation == InstallationType.FIXED else f"/{source_id}"
            ),
            name=str(row["name"]),
            municipality="Leipzig" if inside else None,
            location_description=row["description"],
            latitude=latitude,
            longitude=longitude,
            geometry_status=geometry_status,
            cost_status=evidence.cost_status,
            cost_amount=0,
            potable_water_status=evidence.potable_water_status,
            installation_type=installation,
            operation_status=evidence.operation_status,
            seasonal_status=evidence.seasonal_status,
            season_start=evidence.season_start,
            season_end=evidence.season_end,
            source_updated_at=source_last_modified,
            retrieved_at=retrieved_at,
            source_hash=source_hash,
            release_id=release_id,
            runtime_eligible=runtime_eligible,
            exclusion_reason=exclusion,
        ))
    try:
        return DrinkingFountainRecordCollection(
            normalization_version=DRINKING_FOUNTAIN_NORMALIZATION_VERSION,
            source=DrinkingFountainSourceMetadata(
                source_page_url=DRINKING_FOUNTAIN_SOURCE_PAGE_URL,
                map_viewer_url=DRINKING_FOUNTAIN_MAP_VIEWER_URL,
                kml_url=kml_url,
                retrieved_at=retrieved_at,
                content_type="text/xml",
                size_bytes=len(kml),
                sha256=source_hash,
                source_last_modified=source_last_modified,
            ),
            municipality_boundary=MunicipalityBoundaryMetadata(
                resource_url=boundary_url,
                retrieved_at=retrieved_at,
                source_last_modified=boundary_last_modified,
                feature_count=len(features),
                size_bytes=len(boundary),
                sha256=sha256_bytes(boundary),
            ),
            page_evidence=evidence,
            records=records,
        )
    except ValueError as exc:
        raise DrinkingFountainSourceError("drinking_fountain_record_invalid") from exc


def diff_drinking_fountain_records(
    previous: DrinkingFountainRecordCollection | None,
    current: DrinkingFountainRecordCollection,
) -> dict[str, list[str]]:
    """Vergleicht Fachfelder, ohne reine Release-Metadaten als Scheindiff."""

    def comparable(record: DrinkingFountainRecord) -> dict[str, object]:
        return record.model_dump(
            mode="json",
            exclude={"retrieved_at", "source_hash", "release_id", "source_updated_at"},
        )

    previous_by_id = {record.id: record for record in previous.records} if previous else {}
    current_by_id = {record.id: record for record in current.records}
    return {
        "added": sorted(current_by_id.keys() - previous_by_id.keys()),
        "removed": sorted(previous_by_id.keys() - current_by_id.keys()),
        "modified": sorted(
            record_id
            for record_id in current_by_id.keys() & previous_by_id.keys()
            if comparable(current_by_id[record_id]) != comparable(previous_by_id[record_id])
        ),
    }
