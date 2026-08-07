"""Deterministische Eligibility-, Karten- und Antwortprojektion für Infrastruktur."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal

from .candidate_contract import CandidateDecision, CandidateRole
from .infrastructure import (
    CoordinatesStatus,
    DrinkingFountainRecord,
    FeeStatus,
    OperationStatus,
    PotableWaterStatus,
    PublicToiletRecord,
    SeasonalStatus,
    TOILET_FACILITY_TRANSLATIONS,
    TOILET_FEE_TRANSLATIONS,
    TOILET_HOURS_TRANSLATIONS,
    ToiletAvailability,
    localize_toilet_text,
)
from .maps import build_map_data
from .models import (
    DrinkingFountainCard,
    Language,
    MapData,
    MapDestination,
    MapOrigin,
    OfferRecord,
    PublicToiletCard,
)
from .result_ordering import social_result_distance
from .spatial import LEIPZIG_HBF, distance_from_hbf, is_valid_leipzig_coordinate
from .spoken_text import fountain_spoken_text, toilet_spoken_text


MAX_SPOKEN_TOILETS = 3
MAX_SPOKEN_WATER_RESULTS = 3


class WaterReasonCode(str, Enum):
    DRINKING_WATER_CAPABILITY_MATCH = "drinking_water_capability_match"
    PUBLIC_DRINKING_FOUNTAIN = "public_drinking_fountain"
    VERIFIED_FREE_WATER = "verified_free_water"
    SEASONAL_OPERATION = "seasonal_operation"
    OPERATION_STATUS_UNKNOWN = "operation_status_unknown"
    DETERMINISTIC_HBF_DISTANCE = "deterministic_hbf_distance"


@dataclass(frozen=True)
class DrinkingWaterResult:
    id: str
    record_type: Literal["social_offer", "drinking_fountain"]
    mandatory: bool
    role: CandidateRole
    distance_meters: int | None
    reason_codes: tuple[WaterReasonCode, ...]
    social_offer: OfferRecord | None = None
    fountain: DrinkingFountainRecord | None = None


@dataclass(frozen=True)
class DrinkingWaterResultSet:
    eligible: tuple[DrinkingWaterResult, ...]
    spoken_results: tuple[DrinkingWaterResult, ...]
    card_results: tuple[DrinkingWaterResult, ...]
    map_results: tuple[DrinkingWaterResult, ...]
    fountain_season_active: bool

    @property
    def spoken_result_ids(self) -> list[str]:
        return [result.id for result in self.spoken_results]

    @property
    def card_ids(self) -> list[str]:
        return [result.id for result in self.card_results]


@dataclass(frozen=True)
class PublicToiletResultSet:
    eligible: tuple[PublicToiletRecord, ...]
    spoken_results: tuple[PublicToiletRecord, ...]
    card_results: tuple[PublicToiletRecord, ...]
    map_results: tuple[PublicToiletRecord, ...]

    @property
    def spoken_result_ids(self) -> list[str]:
        return [record.id for record in self.spoken_results]

    @property
    def card_ids(self) -> list[str]:
        return [record.id for record in self.card_results]

    @property
    def map_marker_ids(self) -> list[str]:
        return [record.id for record in self.map_results]


def select_public_toilets(
    records: tuple[PublicToiletRecord, ...], *, origin: MapOrigin = LEIPZIG_HBF
) -> PublicToiletResultSet:
    """Filtert belegte Schließungen und ordnet nach HBF-Luftlinie plus stabiler ID."""

    eligible = tuple(
        sorted(
            (
                record
                for record in records
                if record.availability_status == ToiletAvailability.AVAILABLE
                and record.coordinates_status == CoordinatesStatus.VALID
                and record.latitude is not None
                and record.longitude is not None
                and is_valid_leipzig_coordinate(record.latitude, record.longitude)
            ),
            key=lambda record: (
                distance_from_hbf(record.latitude, record.longitude, origin=origin),
                record.id,
            ),
        )
    )
    spoken = eligible[:MAX_SPOKEN_TOILETS]
    return PublicToiletResultSet(eligible, spoken, spoken, eligible)


def toilet_card(
    record: PublicToiletRecord, language: Language, *, origin: MapOrigin = LEIPZIG_HBF
) -> PublicToiletCard:
    """Projiziert freigegebene Quellenfelder; übersetzt nur den kleinen geschlossenen Wortschatz."""

    assert record.latitude is not None and record.longitude is not None
    return PublicToiletCard(
        id=record.id,
        name=record.display_name,
        operator_name=record.operator_name,
        district=record.district,
        opening_hours_raw=[localize_toilet_text(record.opening_hours_raw, TOILET_HOURS_TRANSLATIONS, language)],
        facilities=[localize_toilet_text(value, TOILET_FACILITY_TRANSLATIONS, language) for value in record.facilities],
        fee_status=record.fee_status.value,
        fee_cents=record.fee_cents,
        fee_raw=localize_toilet_text(record.fee_raw, TOILET_FEE_TRANSLATIONS, language),
        service_phone=record.service_phone,
        distance_meters=distance_from_hbf(record.latitude, record.longitude, origin=origin),
        spoken_text=toilet_spoken_text(record, language),
    )


def toilet_map_data(
    records: tuple[PublicToiletRecord, ...], language: Language, *, origin: MapOrigin = LEIPZIG_HBF
) -> MapData | None:
    destinations = []
    for record in records:
        assert record.latitude is not None and record.longitude is not None
        destinations.append(MapDestination(
            id=record.id,
            label=record.display_name,
            address=record.district,
            latitude=record.latitude,
            longitude=record.longitude,
            distance_meters=distance_from_hbf(record.latitude, record.longitude, origin=origin),
            description=record.operator_name,
            phone_numbers=[record.service_phone] if record.service_phone else [],
            opening_hours=[record.opening_hours_raw],
            record_type="public_toilet",
            fee_raw=record.fee_raw,
            facilities=record.facilities,
            source_attribution="Stadt Leipzig",
            spoken_text=toilet_spoken_text(record, language),
        ))
    if not destinations:
        return None
    return MapData(
        origin=origin,
        destinations=destinations,
        selected_destination_id=destinations[0].id,
    )


def _fountain_is_in_documented_season(record: DrinkingFountainRecord, now: datetime) -> bool:
    return (
        record.seasonal_status == SeasonalStatus.APRIL_TO_OCTOBER
        and record.season_start == "april"
        and record.season_end == "october"
        and 4 <= now.month <= 10
    )


def select_drinking_water_results(
    decision: CandidateDecision,
    social_offers: list[OfferRecord],
    fountains: tuple[DrinkingFountainRecord, ...],
    *,
    now: datetime,
    fountain_only: bool = False,
    origin: MapOrigin = LEIPZIG_HBF,
) -> DrinkingWaterResultSet:
    """Combines only approved water evidence and applies mandatory/HBF order."""

    by_id = {offer.id: offer for offer in social_offers}
    mandatory_order = {
        item.offer_id: index for index, item in enumerate(decision.mandatory_candidates)
    }
    social_items = [*decision.mandatory_candidates, *decision.selectable_candidates]
    results: list[DrinkingWaterResult] = []
    for item in social_items:
        offer = by_id.get(item.offer_id)
        if offer is None or "drinking_water" not in offer.capabilities:
            continue
        results.append(DrinkingWaterResult(
            id=offer.id,
            record_type="social_offer",
            mandatory=offer.id in mandatory_order,
            role=item.role,
            distance_meters=social_result_distance(offer, service="drinking_water", origin=origin),
            reason_codes=(
                WaterReasonCode.DRINKING_WATER_CAPABILITY_MATCH,
                WaterReasonCode.DETERMINISTIC_HBF_DISTANCE,
            ),
            social_offer=offer,
        ))
    active_fountains = [
        record
        for record in fountains
        if record.runtime_eligible
        and record.geometry_status == CoordinatesStatus.VALID
        and record.latitude is not None
        and record.longitude is not None
        and record.operation_status != OperationStatus.INACTIVE
        and record.potable_water_status == PotableWaterStatus.VERIFIED
        and record.cost_status == FeeStatus.FREE
        and _fountain_is_in_documented_season(record, now)
    ]
    if fountain_only and active_fountains:
        results = [result for result in results if result.record_type != "social_offer"]
    for record in active_fountains:
        assert record.latitude is not None and record.longitude is not None
        reasons = [
            WaterReasonCode.PUBLIC_DRINKING_FOUNTAIN,
            WaterReasonCode.VERIFIED_FREE_WATER,
            WaterReasonCode.SEASONAL_OPERATION,
            WaterReasonCode.DETERMINISTIC_HBF_DISTANCE,
        ]
        if record.operation_status == OperationStatus.UNKNOWN:
            reasons.append(WaterReasonCode.OPERATION_STATUS_UNKNOWN)
        results.append(DrinkingWaterResult(
            id=record.id,
            record_type="drinking_fountain",
            mandatory=False,
            role=CandidateRole.DIRECT_SERVICE,
            distance_meters=distance_from_hbf(record.latitude, record.longitude, origin=origin),
            reason_codes=tuple(reasons),
            fountain=record,
        ))

    def result_key(result: DrinkingWaterResult) -> tuple[int, int, int, str]:
        if result.mandatory:
            return 0, mandatory_order[result.id], 0, result.id
        return (
            1,
            0 if result.distance_meters is not None else 1,
            result.distance_meters or 0,
            result.id,
        )

    eligible = tuple(sorted(results, key=result_key))
    map_results = tuple(result for result in eligible if result.distance_meters is not None)
    spoken = eligible[:MAX_SPOKEN_WATER_RESULTS]
    return DrinkingWaterResultSet(
        eligible=eligible,
        spoken_results=spoken,
        card_results=spoken,
        map_results=map_results,
        fountain_season_active=bool(active_fountains),
    )


def drinking_fountain_card(
    record: DrinkingFountainRecord, language: Language, *, origin: MapOrigin = LEIPZIG_HBF
) -> DrinkingFountainCard:
    assert record.latitude is not None and record.longitude is not None
    return DrinkingFountainCard(
        id=record.id,
        name=record.name,
        location_description=record.location_description,
        address=record.address,
        cost_status=record.cost_status.value,
        potable_water_status=record.potable_water_status.value,
        operation_status=record.operation_status.value,
        seasonal_status=record.seasonal_status.value,
        season_start=record.season_start,
        season_end=record.season_end,
        distance_meters=distance_from_hbf(record.latitude, record.longitude, origin=origin),
        spoken_text=fountain_spoken_text(record, language),
    )


def drinking_water_map_data(
    results: tuple[DrinkingWaterResult, ...], language: Language, *, origin: MapOrigin = LEIPZIG_HBF
) -> MapData | None:
    social = [result.social_offer for result in results if result.social_offer is not None]
    social_map = build_map_data(social, limit=None, service="drinking_water", origin=origin, language=language)
    destinations = list(social_map.destinations if social_map else [])
    for result in results:
        record = result.fountain
        if record is None or record.latitude is None or record.longitude is None:
            continue
        destinations.append(MapDestination(
            id=record.id,
            label=record.name,
            address=record.location_description or record.name,
            latitude=record.latitude,
            longitude=record.longitude,
            distance_meters=result.distance_meters,
            description="Trinkwasserbrunnen",
            record_type="drinking_fountain",
            cost_status=record.cost_status.value,
            potable_water_status=record.potable_water_status.value,
            seasonal_status=record.seasonal_status.value,
            source_attribution="Leipziger Wasserwerke",
            spoken_text=fountain_spoken_text(record, language),
        ))
    order = {result.id: index for index, result in enumerate(results)}
    destinations.sort(key=lambda destination: (
        order.get(destination.id.split("-stand-", 1)[0], len(order)),
        destination.distance_meters if destination.distance_meters is not None else 10**9,
        destination.id,
    ))
    if not destinations:
        return None
    return MapData(
        origin=origin,
        destinations=destinations,
        selected_destination_id=destinations[0].id,
    )
