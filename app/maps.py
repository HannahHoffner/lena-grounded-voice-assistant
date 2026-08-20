"""Erzeugt sichere WGS84-Kartenziele aus WFS-Angeboten und Standorten."""

from __future__ import annotations

from .models import Language, MapData, MapDestination, MapOrigin, OfferRecord
from .spatial import LEIPZIG_HBF, distance_from_hbf, utm33n_to_wgs84
from .spoken_text import offer_spoken_text


def build_map_data(
    offers: list[OfferRecord],
    *,
    language: Language,
    limit: int | None = 4,
    service: str | None = None,
    origin: MapOrigin = LEIPZIG_HBF,
) -> MapData | None:
    """Erstellt deduplizierte Kartenziele oder ``None`` ohne nutzbare Koordinaten."""
    destinations: list[MapDestination] = []
    seen: set[tuple[str, str]] = set()
    for offer in offers:
        for stand_destination in offer_stand_destinations(offer, language, service=service, origin=origin):
            key = (stand_destination.label.casefold().strip(), stand_destination.address.casefold().strip())
            if key in seen:
                continue
            seen.add(key)
            destinations.append(stand_destination)
            if limit is not None and len(destinations) >= limit:
                break
        if limit is not None and len(destinations) >= limit:
            break
        if uses_stand_location_instead_of_office(offer, service=service):
            continue
        coordinates = offer_wgs84(offer)
        if not coordinates or not offer.address:
            continue
        latitude, longitude = coordinates
        key = (offer.name.casefold().strip(), offer.address.casefold().strip())
        if key in seen:
            continue
        seen.add(key)
        destinations.append(
            MapDestination(
                id=offer.id,
                label=offer.name,
                address=offer.address,
                latitude=latitude,
                longitude=longitude,
                distance_meters=distance_from_hbf(latitude, longitude, origin=origin),
                description=offer.short_description,
                phone_numbers=offer.phone_numbers,
                opening_hours=offer.opening_hours_raw[:4],
                services=offer.services,
                standzeiten_raw=offer.standzeiten_raw,
                notes=offer.notes,
                spoken_text=offer_spoken_text(offer, language),
            )
        )
        if limit is not None and len(destinations) >= limit:
            break
    if not destinations:
        return None
    return MapData(
        origin=origin,
        destinations=destinations,
        selected_destination_id=destinations[0].id,
    )


def offer_stand_destinations(
    offer: OfferRecord,
    language: Language | None = None,
    *,
    service: str | None = None,
    origin: MapOrigin = LEIPZIG_HBF,
) -> list[MapDestination]:
    """`language=None` skips building `spoken_text` -- for pure distance/order
    computations (see result_ordering.py::social_result_distance) that throw
    the destinations away immediately and would otherwise waste a
    per-candidate, per-sort-comparison text build."""
    schedule_rules = (
        {offer.service_schedules[service]}
        if service and service in offer.service_schedules
        else set(offer.service_schedules.values())
        if service is None
        else set()
    )
    if (
        offer.place_type == "help_bus"
        and service in {"food", "drinking_water"}
        and "sunday_20_21" in schedule_rules
    ):
        return [
            _stand_destination(
                offer,
                language,
                destination_id=f"{offer.id}:hbf-west",
                label="Hilfebus - Westseite Hauptbahnhof",
                address="Westseite des Hauptbahnhofes, 04109 Leipzig",
                latitude=51.34556,
                longitude=12.37935,
                description="Suppenausgabe: Sonntag 20:00-21:00 Uhr",
                opening_hours=["> Sonntag: 20:00 - 21:00 Uhr an der Westseite des Hauptbahnhofes"],
                origin=origin,
            )
        ]
    if "tuesday_17_18" in schedule_rules:
        return [
            _stand_destination(
                offer,
                language,
                destination_id=f"{offer.id}:schwanenteich",
                label="Schwanenteich - Goethestraße",
                address="Goethestraße / Schwanenteich, 04109 Leipzig",
                latitude=51.34135,
                longitude=12.38135,
                description="Standzeit: Dienstag 17:00-18:00 Uhr",
                opening_hours=["> Dienstag: 17:00 - 18:00 Uhr"],
                origin=origin,
            )
        ]
    if "medibus_and_clinics" in schedule_rules:
        return [
            _stand_destination(
                offer,
                language,
                destination_id=f"{offer.id}:hbf-medibus",
                label="Medibus - Hauptbahnhof",
                address="Hauptbahnhof, 04109 Leipzig",
                latitude=51.3452,
                longitude=12.3813,
                description="Mobiles medizinisches Angebot am Hauptbahnhof",
                opening_hours=[
                    "> Mittwoch: 18:30 Uhr Hauptbahnhof",
                    "> Freitag: 14:00 Uhr Hauptbahnhof",
                    "> Sonntag: 20:00 Uhr Hauptbahnhof",
                ],
                origin=origin,
            )
        ]
    return []


def _stand_destination(
    offer: OfferRecord,
    language: Language | None,
    *,
    destination_id: str,
    label: str,
    address: str,
    latitude: float,
    longitude: float,
    description: str,
    opening_hours: list[str],
    origin: MapOrigin = LEIPZIG_HBF,
) -> MapDestination:
    return MapDestination(
        id=destination_id,
        label=label,
        address=address,
        latitude=latitude,
        longitude=longitude,
        distance_meters=distance_from_hbf(latitude, longitude, origin=origin),
        description=description,
        phone_numbers=offer.phone_numbers,
        opening_hours=opening_hours,
        services=offer.services,
        standzeiten_raw=offer.standzeiten_raw,
        notes=offer.notes,
        spoken_text=offer_spoken_text(offer, language) if language is not None else "",
    )


def uses_stand_location_instead_of_office(offer: OfferRecord, *, service: str | None = None) -> bool:
    stand_only_rules = {
        "tuesday_17_18",
        "thursday_16_1730",
        "thursday_16_19",
        "sunday_20_21",
        "mobile_alternative_stands",
        "medibus_and_clinics",
    }
    relevant_rules = (
        {offer.service_schedules[service]}
        if service and service in offer.service_schedules
        else set(offer.service_schedules.values())
        if service is None
        else set()
    )
    return offer.place_type == "help_bus" or bool(
        stand_only_rules.intersection(relevant_rules)
    )


def offer_wgs84(offer: OfferRecord) -> tuple[float, float] | None:
    geometry = offer.geometry or {}
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coordinates, list | tuple) or len(coordinates) < 2:
        return None
    try:
        easting = float(coordinates[0])
        northing = float(coordinates[1])
    except (TypeError, ValueError):
        return None
    return utm33n_to_wgs84(easting, northing)
