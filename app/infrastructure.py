"""Strikte Quell- und Runtime-Modelle öffentlicher Infrastruktur."""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import Language
from .spatial import is_valid_leipzig_coordinate, utm33n_to_wgs84


TOILET_NORMALIZATION_VERSION = "1"
TOILET_SOURCE_TITLE = "Öffentliche Toiletten, Stadt Leipzig"
TOILET_DATASET_PAGE = "https://opendata.leipzig.de/dataset/offentliche-toiletten-stadt-leipzig1"
TOILET_RESOURCE_URL = (
    "https://geodaten.leipzig.de/open_data/organisationseinheit/"
    "Amt_fuer_Geoinformation_und_Bodenordnung/Toilettenstandorte/"
    "Oeffentliche_Toiletten_Stadt_Leipzig.csv"
)
TOILET_LICENSE = "Datenlizenz Deutschland – Namensnennung – Version 2.0"
TOILET_LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0"
TOILET_ATTRIBUTION = "Stadt Leipzig"
TOILET_SOURCE_REFERENCE_ID = "leipzig-public-toilets-csv"

# Kleiner geschlossener Wortschatz der amtlichen CSV; unbekannte Werte bleiben
# unübersetzt im deutschen Original statt eine falsche Übersetzung zu erfinden.
TOILET_FACILITY_TRANSLATIONS: dict[str, dict[Language, str]] = {
    "Barrierefrei": {
        Language.EN: "Accessible",
        Language.PL: "Bez barier",
        Language.RO: "Fără bariere",
        Language.RU: "Без барьеров",
    },
    "Barrierearm": {
        Language.EN: "Low-barrier access",
        Language.PL: "Ograniczone bariery",
        Language.RO: "Acces cu bariere reduse",
        Language.RU: "С ограниченными барьерами",
    },
    "Wickeltisch": {
        Language.EN: "Baby changing table",
        Language.PL: "Przewijak",
        Language.RO: "Masă de înfășat",
        Language.RU: "Пеленальный столик",
    },
}
TOILET_FEE_TRANSLATIONS: dict[str, dict[Language, str]] = {
    "kostenfrei": {
        Language.EN: "free of charge",
        Language.PL: "bezpłatne",
        Language.RO: "gratuit",
        Language.RU: "бесплатно",
    },
    "50 Cent (Barzahlung oder mit Karte)": {
        Language.EN: "50 cents (cash or card)",
        Language.PL: "50 centów (gotówka lub karta)",
        Language.RO: "50 de cenți (numerar sau card)",
        Language.RU: "50 центов (наличными или картой)",
    },
}
TOILET_HOURS_TRANSLATIONS: dict[str, dict[Language, str]] = {
    "ganztägig": {
        Language.EN: "all day",
        Language.PL: "całodobowo",
        Language.RO: "non-stop",
        Language.RU: "круглосуточно",
    },
    "geschlossen": {
        Language.EN: "closed",
        Language.PL: "zamknięte",
        Language.RO: "închis",
        Language.RU: "закрыто",
    },
}


def localize_toilet_text(value: str, table: dict[str, dict[Language, str]], language: Language) -> str:
    """Übersetzt nur bekannte Werte aus dem geschlossenen Wortschatz; sonst Original."""
    if language == Language.DE:
        return value
    return table.get(value, {}).get(language, value)
REQUIRED_COLUMNS = (
    "ID",
    "Betreiber",
    "Ort",
    "Ortsteil",
    "Oeffnungszeiten",
    "Ausstattung",
    "Entgelt",
    "Servicenummer",
    "lat",
    "long",
    "utm_east",
    "utm_north",
)
SOURCE_ID_RE = re.compile(r"^[0-9]{4}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InfrastructureType(str, Enum):
    PUBLIC_TOILET = "public_toilet"
    DRINKING_FOUNTAIN = "drinking_fountain"


class FeeStatus(str, Enum):
    FREE = "free"
    PAID = "paid"
    UNKNOWN = "unknown"


class ToiletAvailability(str, Enum):
    AVAILABLE = "available"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class CoordinatesStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"
    INCONSISTENT = "inconsistent"
    DUPLICATE = "duplicate"


class PotableWaterStatus(str, Enum):
    VERIFIED = "verified"
    UNKNOWN = "unknown"


class OperationStatus(str, Enum):
    UNKNOWN = "unknown"
    INACTIVE = "inactive"


class SeasonalStatus(str, Enum):
    APRIL_TO_OCTOBER = "april_to_october"
    UNKNOWN = "unknown"


class InstallationType(str, Enum):
    FIXED = "fixed"
    MOBILE = "mobile"


class FountainExclusionReason(str, Enum):
    OUTSIDE_LEIPZIG = "outside_leipzig"
    INVALID_GEOMETRY = "invalid_geometry"
    DUPLICATE_LOCATION = "duplicate_location"
    MOBILE_SCHEDULE_NOT_VERIFIED = "mobile_schedule_not_verified"
    SOURCE_NOT_APPROVED = "source_not_approved"


class PublicToiletRecord(StrictModel):
    """Positivlistenprojektion eines validierten CSV-Datensatzes."""

    id: str = Field(pattern=r"^toilet:[0-9]{4}$")
    source_id: str = Field(pattern=r"^[0-9]{4}$")
    source_reference_id: Literal[TOILET_SOURCE_REFERENCE_ID] = TOILET_SOURCE_REFERENCE_ID
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_type: Literal[InfrastructureType.PUBLIC_TOILET] = InfrastructureType.PUBLIC_TOILET
    display_name: str = Field(min_length=1, max_length=200)
    operator_name: str = Field(min_length=1, max_length=160)
    district: str = Field(min_length=1, max_length=120)
    opening_hours_raw: str = Field(min_length=1, max_length=240)
    availability_status: ToiletAvailability
    facilities: list[str] = Field(default_factory=list, max_length=12)
    wheelchair_accessible: bool | None = None
    all_gender: bool | None = None
    changing_table: bool | None = None
    fee_status: FeeStatus
    fee_cents: int | None = Field(default=None, ge=0, le=10_000)
    fee_currency: Literal["EUR"] | None = None
    fee_raw: str = Field(default="", max_length=160)
    service_phone: str | None = Field(default=None, max_length=80)
    source_latitude_raw: str = Field(default="", max_length=80)
    source_longitude_raw: str = Field(default="", max_length=80)
    source_easting_raw: str = Field(default="", max_length=80)
    source_northing_raw: str = Field(default="", max_length=80)
    latitude: float | None = None
    longitude: float | None = None
    source_easting: float | None = None
    source_northing: float | None = None
    coordinates_status: CoordinatesStatus
    source_crs: Literal["EPSG:25833"] = "EPSG:25833"
    display_crs: Literal["EPSG:4326"] = "EPSG:4326"

    @model_validator(mode="after")
    def validate_geometry_and_fee(self) -> "PublicToiletRecord":
        normalized = (self.latitude, self.longitude, self.source_easting, self.source_northing)
        if self.coordinates_status == CoordinatesStatus.VALID:
            if any(value is None for value in normalized):
                raise ValueError("valid toilet coordinate is incomplete")
            latitude, longitude, easting, northing = normalized
            assert latitude is not None and longitude is not None and easting is not None and northing is not None
            if not is_valid_leipzig_coordinate(latitude, longitude):
                raise ValueError("valid toilet coordinate is outside the Leipzig extent")
            if not all(math.isfinite(value) for value in (easting, northing)):
                raise ValueError("valid toilet source coordinate is not finite")
            transformed = utm33n_to_wgs84(easting, northing)
            if abs(transformed[0] - latitude) > 0.0001 or abs(transformed[1] - longitude) > 0.0001:
                raise ValueError("valid toilet coordinate representations disagree")
        elif any(value is not None for value in normalized):
            raise ValueError("non-valid toilet geometry must not enter runtime coordinates")
        if self.fee_status == FeeStatus.FREE and self.fee_cents != 0:
            raise ValueError("free toilet must have zero fee")
        if self.fee_status == FeeStatus.PAID and self.fee_cents is None:
            raise ValueError("paid toilet requires a fee amount")
        if self.fee_status == FeeStatus.UNKNOWN and self.fee_cents is not None:
            raise ValueError("unknown fee must not infer an amount")
        return self


class DrinkingFountainRecord(StrictModel):
    """Positive, source-bound projection of one KML placemark."""

    id: str = Field(pattern=r"^drinking_fountain:[a-z0-9][a-z0-9-]{0,79}$")
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    source_name: str = Field(min_length=1, max_length=240)
    source_url: str = Field(min_length=1, max_length=600)
    source_record_reference: str = Field(min_length=1, max_length=500)
    name: str = Field(min_length=1, max_length=240)
    infrastructure_type: Literal[InfrastructureType.DRINKING_FOUNTAIN] = InfrastructureType.DRINKING_FOUNTAIN
    operator: str | None = Field(default=None, max_length=180)
    municipality: Literal["Leipzig"] | None = None
    location_description: str | None = Field(default=None, max_length=500)
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = None
    longitude: float | None = None
    geometry_status: CoordinatesStatus
    cost_status: FeeStatus
    cost_amount: int | None = Field(default=None, ge=0, le=10_000)
    cost_currency: Literal["EUR"] | None = None
    potable_water_status: PotableWaterStatus
    installation_type: InstallationType
    operation_status: OperationStatus
    seasonal_status: SeasonalStatus
    season_start: Literal["april"] | None = None
    season_end: Literal["october"] | None = None
    source_updated_at: str | None = Field(default=None, max_length=120)
    retrieved_at: datetime
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    release_id: str = Field(pattern=r"^\d{8}T\d{6}Z-[0-9a-f]{12}$")
    review_status: Literal["reviewed_for_prototype"] = "reviewed_for_prototype"
    runtime_eligible: bool
    exclusion_reason: FountainExclusionReason | None = None

    @model_validator(mode="after")
    def validate_runtime_projection(self) -> "DrinkingFountainRecord":
        coordinates = (self.latitude, self.longitude)
        if self.geometry_status == CoordinatesStatus.VALID:
            if any(value is None for value in coordinates):
                raise ValueError("valid drinking-fountain geometry is incomplete")
            assert self.latitude is not None and self.longitude is not None
            if not (
                math.isfinite(self.latitude)
                and math.isfinite(self.longitude)
                and -90 <= self.latitude <= 90
                and -180 <= self.longitude <= 180
            ):
                raise ValueError("drinking-fountain geometry is invalid")
        elif any(value is not None for value in coordinates):
            raise ValueError("non-valid drinking-fountain geometry must not enter runtime coordinates")
        if self.cost_status == FeeStatus.FREE and self.cost_amount != 0:
            raise ValueError("free drinking water requires a zero amount")
        if self.cost_status != FeeStatus.FREE and self.cost_amount is not None:
            raise ValueError("non-free or unknown cost must not infer an amount")
        if self.seasonal_status == SeasonalStatus.APRIL_TO_OCTOBER:
            if (self.season_start, self.season_end) != ("april", "october"):
                raise ValueError("documented fountain season is incomplete")
        elif self.season_start is not None or self.season_end is not None:
            raise ValueError("unknown fountain season must not infer boundaries")
        if self.runtime_eligible:
            if (
                self.installation_type != InstallationType.FIXED
                or self.municipality != "Leipzig"
                or self.geometry_status != CoordinatesStatus.VALID
                or self.exclusion_reason is not None
            ):
                raise ValueError("runtime-eligible drinking fountain violates the approved scope")
        elif self.exclusion_reason is None:
            raise ValueError("excluded drinking fountain requires a reason")
        return self


class DrinkingFountainSourceMetadata(StrictModel):
    publisher: Literal["Leipziger Wasserwerke"] = "Leipziger Wasserwerke"
    source_page_url: str = Field(min_length=1, max_length=600)
    map_viewer_url: str = Field(min_length=1, max_length=800)
    kml_url: str = Field(min_length=1, max_length=800)
    retrieved_at: datetime
    content_type: Literal["text/xml"] = "text/xml"
    raw_format: Literal["KML 2.2"] = "KML 2.2"
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_last_modified: str | None = Field(default=None, max_length=120)
    license_status: Literal["not_explicitly_specified"] = "not_explicitly_specified"
    usage_scope: Literal["reviewed_prototype_source"] = "reviewed_prototype_source"


class MunicipalityBoundaryMetadata(StrictModel):
    publisher: Literal["Stadt Leipzig"] = "Stadt Leipzig"
    title: Literal["Geodaten der Statistischen Bezirke der Stadt Leipzig"] = (
        "Geodaten der Statistischen Bezirke der Stadt Leipzig"
    )
    resource_url: str = Field(min_length=1, max_length=800)
    retrieved_at: datetime
    source_last_modified: str | None = Field(default=None, max_length=120)
    content_type: Literal["application/json"] = "application/json"
    crs: Literal["EPSG:25833"] = "EPSG:25833"
    feature_count: int = Field(ge=1, le=5_000)
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license_status: Literal["not_explicitly_specified"] = "not_explicitly_specified"
    usage_scope: Literal["reviewed_prototype_source"] = "reviewed_prototype_source"


class DrinkingFountainPageEvidence(StrictModel):
    schema_version: Literal["1"] = "1"
    source_url: str = Field(min_length=1, max_length=600)
    reviewed_at: datetime
    review_status: Literal["reviewed_for_prototype"] = "reviewed_for_prototype"
    reviewed_by_role: Literal["technical source review"] = "technical source review"
    cost_status: Literal[FeeStatus.FREE] = FeeStatus.FREE
    potable_water_status: Literal[PotableWaterStatus.VERIFIED] = PotableWaterStatus.VERIFIED
    operation_status: Literal[OperationStatus.UNKNOWN] = OperationStatus.UNKNOWN
    seasonal_status: Literal[SeasonalStatus.APRIL_TO_OCTOBER] = SeasonalStatus.APRIL_TO_OCTOBER
    season_start: Literal["april"] = "april"
    season_end: Literal["october"] = "october"
    realtime_status_available: Literal[False] = False
    completeness_claimed: Literal[False] = False
    license_status: Literal["not_explicitly_specified"] = "not_explicitly_specified"
    usage_scope: Literal["reviewed_prototype_source"] = "reviewed_prototype_source"


class DrinkingFountainRecordCollection(StrictModel):
    schema_version: Literal["1"] = "1"
    normalization_version: Literal["1"] = "1"
    source: DrinkingFountainSourceMetadata
    municipality_boundary: MunicipalityBoundaryMetadata
    page_evidence: DrinkingFountainPageEvidence
    records: list[DrinkingFountainRecord] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_records(self) -> "DrinkingFountainRecordCollection":
        ids = [record.id for record in self.records]
        source_ids = [record.source_id for record in self.records]
        if len(ids) != len(set(ids)) or len(source_ids) != len(set(source_ids)):
            raise ValueError("drinking-fountain IDs must be unique")
        if any(record.source_hash != self.source.sha256 for record in self.records):
            raise ValueError("drinking-fountain record source hashes differ")
        if any(record.source_url != self.source.kml_url for record in self.records):
            raise ValueError("drinking-fountain record source URLs differ")
        if self.page_evidence.source_url != self.source.source_page_url:
            raise ValueError("drinking-fountain page evidence source differs")
        if len({record.release_id for record in self.records}) != 1:
            raise ValueError("drinking-fountain record release IDs differ")
        return self


class ToiletSourceMetadata(StrictModel):
    publisher: Literal["Stadt Leipzig"] = "Stadt Leipzig"
    title: Literal[TOILET_SOURCE_TITLE] = TOILET_SOURCE_TITLE
    dataset_page: Literal[TOILET_DATASET_PAGE] = TOILET_DATASET_PAGE
    resource_url: str = Field(min_length=1, max_length=600)
    fetched_at: datetime
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    encoding: Literal["utf-8-sig"] = "utf-8-sig"
    delimiter: Literal[","] = ","
    license_name: Literal[TOILET_LICENSE] = TOILET_LICENSE
    license_url: Literal[TOILET_LICENSE_URL] = TOILET_LICENSE_URL
    attribution: Literal[TOILET_ATTRIBUTION] = TOILET_ATTRIBUTION
    source_last_modified: str | None = Field(default=None, max_length=120)


class ToiletRecordCollection(StrictModel):
    schema_version: Literal["1"] = "1"
    normalization_version: Literal[TOILET_NORMALIZATION_VERSION] = TOILET_NORMALIZATION_VERSION
    source: ToiletSourceMetadata
    records: list[PublicToiletRecord] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unique_records(self) -> "ToiletRecordCollection":
        ids = [record.id for record in self.records]
        source_ids = [record.source_id for record in self.records]
        if len(ids) != len(set(ids)) or len(source_ids) != len(set(source_ids)):
            raise ValueError("public toilet IDs must be unique")
        return self


class ToiletSourceError(RuntimeError):
    """Redigierter Fehler einer Toilette-Quellprüfung."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _availability(value: str) -> ToiletAvailability:
    normalized = value.casefold().strip()
    if normalized == "geschlossen":
        return ToiletAvailability.CLOSED
    if normalized == "ganztägig":
        return ToiletAvailability.AVAILABLE
    return ToiletAvailability.UNKNOWN


def _fee(value: str) -> tuple[FeeStatus, int | None, Literal["EUR"] | None]:
    normalized = value.casefold().strip()
    if normalized in {"0", "kostenfrei", "kostenlos", "frei"}:
        return FeeStatus.FREE, 0, None
    euro = re.fullmatch(r"(\d+)(?:[,.](\d{1,2}))?\s*(?:€|eur|euro)", normalized)
    if euro:
        cents = int(euro.group(1)) * 100 + int((euro.group(2) or "0").ljust(2, "0"))
        return (FeeStatus.FREE if cents == 0 else FeeStatus.PAID), cents, "EUR"
    match = re.fullmatch(r"(\d+)\s*cent(?:\s*\([^)]*\))?", normalized)
    if match:
        cents = int(match.group(1))
        return (FeeStatus.FREE if cents == 0 else FeeStatus.PAID), cents, "EUR"
    return FeeStatus.UNKNOWN, None, None


def _coordinates(row: dict[str, str]) -> tuple[CoordinatesStatus, float | None, float | None, float | None, float | None]:
    raw = [row["lat"].strip(), row["long"].strip(), row["utm_east"].strip(), row["utm_north"].strip()]
    if not all(raw):
        return CoordinatesStatus.MISSING, None, None, None, None
    try:
        latitude, longitude, easting, northing = (float(value) for value in raw)
    except ValueError:
        return CoordinatesStatus.INVALID, None, None, None, None
    if not all(math.isfinite(value) for value in (latitude, longitude, easting, northing)):
        return CoordinatesStatus.INVALID, None, None, None, None
    if not is_valid_leipzig_coordinate(latitude, longitude):
        return CoordinatesStatus.INVALID, None, None, None, None
    try:
        transformed = utm33n_to_wgs84(easting, northing)
    except (ValueError, OverflowError):
        return CoordinatesStatus.INVALID, None, None, None, None
    if abs(transformed[0] - latitude) > 0.0001 or abs(transformed[1] - longitude) > 0.0001:
        return CoordinatesStatus.INCONSISTENT, None, None, None, None
    return CoordinatesStatus.VALID, latitude, longitude, easting, northing


def normalize_toilet_csv(
    content: bytes,
    *,
    fetched_at: datetime,
    content_type: str,
    resource_url: str = TOILET_RESOURCE_URL,
    source_last_modified: str | None = None,
) -> ToiletRecordCollection:
    """Parst ausschließlich das geprüfte CSV-Schema in eine Runtime-Positivliste."""

    if not content:
        raise ToiletSourceError("toilet_source_empty")
    if content.lstrip().startswith(b"<"):
        raise ToiletSourceError("toilet_source_not_csv")
    if not content.startswith(b"\xef\xbb\xbf"):
        raise ToiletSourceError("toilet_source_encoding_invalid")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ToiletSourceError("toilet_source_encoding_invalid") from exc
    try:
        reader = csv.DictReader(io.StringIO(decoded), delimiter=",")
        fieldnames = tuple(reader.fieldnames or ())
        if (
            len(fieldnames) != len(set(fieldnames))
            or not set(REQUIRED_COLUMNS).issubset(fieldnames)
        ):
            raise ToiletSourceError("toilet_schema_changed")
        rows = list(reader)
    except csv.Error as exc:
        raise ToiletSourceError("toilet_source_not_csv") from exc
    if content_type.split(";", 1)[0].strip().casefold() not in {"text/csv", "application/csv"}:
        raise ToiletSourceError("toilet_source_not_csv")
    if not rows:
        raise ToiletSourceError("toilet_source_empty")
    records: list[PublicToiletRecord] = []
    source_hash = hashlib.sha256(content).hexdigest()
    seen_source_ids: set[str] = set()
    try:
        for row in rows:
            required_values = ("ID", "Betreiber", "Ort", "Ortsteil", "Oeffnungszeiten", "Ausstattung")
            if (
                None in row
                or any(row.get(name) is None for name in REQUIRED_COLUMNS)
                or any(not row[name].strip() for name in required_values)
            ):
                raise ToiletSourceError("toilet_record_invalid")
            source_id = row["ID"].strip()
            if not SOURCE_ID_RE.fullmatch(source_id):
                raise ToiletSourceError("toilet_record_invalid")
            if source_id in seen_source_ids:
                raise ToiletSourceError("toilet_duplicate_id")
            seen_source_ids.add(source_id)
            facilities = [part.strip() for part in row["Ausstattung"].split(",") if part.strip()]
            facility_keys = {item.casefold() for item in facilities}
            fee_status, fee_cents, fee_currency = _fee(row["Entgelt"])
            if fee_cents is not None and fee_cents > 10_000:
                raise ToiletSourceError("toilet_fee_invalid")
            coordinates_status, latitude, longitude, easting, northing = _coordinates(row)
            records.append(
                PublicToiletRecord(
                    id=f"toilet:{source_id}",
                    source_id=source_id,
                    source_hash=source_hash,
                    display_name=row["Ort"].strip(),
                    operator_name=row["Betreiber"].strip(),
                    district=row["Ortsteil"].strip(),
                    opening_hours_raw=row["Oeffnungszeiten"].strip(),
                    availability_status=_availability(row["Oeffnungszeiten"]),
                    facilities=facilities,
                    wheelchair_accessible=True if "barrierefrei" in facility_keys else None,
                    all_gender=True if "all gender" in facility_keys else None,
                    changing_table=True if "wickeltisch" in facility_keys else None,
                    fee_status=fee_status,
                    fee_cents=fee_cents,
                    fee_currency=fee_currency,
                    fee_raw=row["Entgelt"].strip(),
                    service_phone=(
                        None if row["Servicenummer"].strip() in {"", "-"} else row["Servicenummer"].strip()
                    ),
                    source_latitude_raw=row["lat"].strip(),
                    source_longitude_raw=row["long"].strip(),
                    source_easting_raw=row["utm_east"].strip(),
                    source_northing_raw=row["utm_north"].strip(),
                    latitude=latitude,
                    longitude=longitude,
                    source_easting=easting,
                    source_northing=northing,
                    coordinates_status=coordinates_status,
                )
            )
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ToiletSourceError):
            raise
        raise ToiletSourceError("toilet_record_invalid") from exc
    try:
        coordinates: dict[tuple[float, float], list[PublicToiletRecord]] = {}
        for record in records:
            if record.coordinates_status == CoordinatesStatus.VALID:
                assert record.latitude is not None and record.longitude is not None
                coordinates.setdefault((record.latitude, record.longitude), []).append(record)
        for duplicate_records in coordinates.values():
            if len(duplicate_records) > 1:
                for record in duplicate_records:
                    record.coordinates_status = CoordinatesStatus.DUPLICATE
                    record.latitude = None
                    record.longitude = None
                    record.source_easting = None
                    record.source_northing = None
        return ToiletRecordCollection(
            source=ToiletSourceMetadata(
                resource_url=resource_url,
                fetched_at=fetched_at,
                content_type=content_type.split(";", 1)[0].strip().casefold(),
                size_bytes=len(content),
                sha256=source_hash,
                source_last_modified=source_last_modified,
            ),
            records=records,
        )
    except ValueError as exc:
        raise ToiletSourceError("toilet_record_invalid") from exc


def diff_toilet_records(
    previous: ToiletRecordCollection | None,
    current: ToiletRecordCollection,
) -> dict[str, object]:
    """Erzeugt einen stabilen, fachdatensparsamen ID-Diff zweier Releases."""

    previous_by_id = {record.id: record for record in previous.records} if previous else {}
    current_by_id = {record.id: record for record in current.records}
    added = sorted(current_by_id.keys() - previous_by_id.keys())
    removed = sorted(previous_by_id.keys() - current_by_id.keys())
    modified = sorted(
        record_id
        for record_id in current_by_id.keys() & previous_by_id.keys()
        if current_by_id[record_id].model_dump(mode="json", exclude={"source_hash"})
        != previous_by_id[record_id].model_dump(mode="json", exclude={"source_hash"})
    )
    return {"added": added, "removed": removed, "modified": modified}
