"""Gemeinsame Ergebnisordnung nach Fachpriorität und HBF-Luftlinie."""

from __future__ import annotations

from .maps import offer_stand_destinations, offer_wgs84, uses_stand_location_instead_of_office
from .models import MapOrigin, OfferRecord
from .spatial import LEIPZIG_HBF, distance_from_hbf


def social_result_distance(
    offer: OfferRecord, *, service: str | None = None, origin: MapOrigin = LEIPZIG_HBF
) -> int | None:
    """Nutzt belegte Standorte vor Büroadressen und rät fehlende Orte nicht."""

    stands = offer_stand_destinations(offer, service=service, origin=origin)
    if stands:
        return min(
            destination.distance_meters
            for destination in stands
            if destination.distance_meters is not None
        )
    if uses_stand_location_instead_of_office(offer, service=service):
        return None
    coordinates = offer_wgs84(offer)
    return distance_from_hbf(*coordinates, origin=origin) if coordinates else None


def order_social_results(
    offers: list[OfferRecord],
    *,
    mandatory_order: list[str] | None = None,
    service: str | None = None,
    priority_tiers: dict[str, int] | None = None,
    origin: MapOrigin = LEIPZIG_HBF,
) -> list[OfferRecord]:
    """Erhält verbindliche Reihenfolge und sortiert erst danach räumlich stabil."""

    mandatory = {offer_id: index for index, offer_id in enumerate(mandatory_order or [])}
    priorities = priority_tiers or {}

    def key(offer: OfferRecord) -> tuple[int, int, int, int, str]:
        if offer.id in mandatory:
            return 0, mandatory[offer.id], 0, 0, offer.id
        distance = social_result_distance(offer, service=service, origin=origin)
        return 1, priorities.get(offer.id, 50), 0 if distance is not None else 1, distance or 0, offer.id

    return sorted(offers, key=key)
