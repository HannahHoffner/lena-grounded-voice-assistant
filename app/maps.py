"""Erzeugt sichere WGS84-Kartenziele aus WFS-Angeboten und Standorten."""

from __future__ import annotations

import math

from .models import MapData, MapDestination, MapOrigin, OfferRecord


LEIPZIG_HBF = MapOrigin(
    id="leipzig-hbf",
    label="Leipzig Hauptbahnhof",
    address="Willy-Brandt-Platz 5, 04109 Leipzig",
    latitude=51.34556,
    longitude=12.38222,
)


def build_map_data(offers: list[OfferRecord], *, limit: int = 4) -> MapData | None:
    """Erstellt deduplizierte Kartenziele oder ``None`` ohne nutzbare Koordinaten."""
    destinations: list[MapDestination] = []
    seen: set[tuple[str, str]] = set()
    for offer in offers:
        for stand_destination in _stand_destinations(offer):
            key = (stand_destination.label.casefold().strip(), stand_destination.address.casefold().strip())
            if key in seen:
                continue
            seen.add(key)
            destinations.append(stand_destination)
            if len(destinations) >= limit:
                break
        if len(destinations) >= limit:
            break
        if _uses_stand_location_instead_of_office(offer):
            continue
        coordinates = _offer_wgs84(offer)
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
                distance_meters=_haversine_distance_meters(
                    LEIPZIG_HBF.latitude,
                    LEIPZIG_HBF.longitude,
                    latitude,
                    longitude,
                ),
                description=offer.short_description,
                phone_numbers=offer.phone_numbers,
                opening_hours=offer.opening_hours_raw[:4],
            )
        )
        if len(destinations) >= limit:
            break
    if not destinations:
        return None
    return MapData(
        origin=LEIPZIG_HBF,
        destinations=destinations,
        selected_destination_id=destinations[0].id,
    )


def _stand_destinations(offer: OfferRecord) -> list[MapDestination]:
    text = " ".join([offer.name, *offer.services, *offer.opening_hours_raw, *offer.standzeiten_raw]).casefold()
    if "hilfebus" in text and "hauptbahnhof" in text:
        return [
            _stand_destination(
                offer,
                destination_id=f"{offer.id}:hbf-west",
                label="Hilfebus - Westseite Hauptbahnhof",
                address="Westseite des Hauptbahnhofes, 04109 Leipzig",
                latitude=51.34556,
                longitude=12.37935,
                description="Suppenausgabe: Sonntag 20:00-21:00 Uhr",
                opening_hours=["> Sonntag: 20:00 - 21:00 Uhr an der Westseite des Hauptbahnhofes"],
            )
        ]
    if offer.source_index in {13, 14}:
        return [
            _stand_destination(
                offer,
                destination_id=f"{offer.id}:schwanenteich",
                label="Schwanenteich - Goethestraße",
                address="Goethestraße / Schwanenteich, 04109 Leipzig",
                latitude=51.34135,
                longitude=12.38135,
                description="Standzeit: Dienstag 17:00-18:00 Uhr",
                opening_hours=["> Dienstag: 17:00 - 18:00 Uhr"],
            )
        ]
    if offer.source_index == 30:
        return [
            _stand_destination(
                offer,
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
            )
        ]
    return []


def _stand_destination(
    offer: OfferRecord,
    *,
    destination_id: str,
    label: str,
    address: str,
    latitude: float,
    longitude: float,
    description: str,
    opening_hours: list[str],
) -> MapDestination:
    return MapDestination(
        id=destination_id,
        label=label,
        address=address,
        latitude=latitude,
        longitude=longitude,
        distance_meters=_haversine_distance_meters(
            LEIPZIG_HBF.latitude,
            LEIPZIG_HBF.longitude,
            latitude,
            longitude,
        ),
        description=description,
        phone_numbers=offer.phone_numbers,
        opening_hours=opening_hours,
    )


def _uses_stand_location_instead_of_office(offer: OfferRecord) -> bool:
    text = " ".join([offer.name, *offer.services, *offer.opening_hours_raw, *offer.standzeiten_raw]).casefold()
    return (
        ("hilfebus" in text and "hauptbahnhof" in text)
        or offer.source_index in {13, 14, 30}
    )


def _offer_wgs84(offer: OfferRecord) -> tuple[float, float] | None:
    geometry = offer.geometry or {}
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coordinates, list | tuple) or len(coordinates) < 2:
        return None
    try:
        easting = float(coordinates[0])
        northing = float(coordinates[1])
    except (TypeError, ValueError):
        return None
    return _utm33n_to_wgs84(easting, northing)


def _utm33n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    # EPSG:25833 is ETRS89 / UTM zone 33N. For Leipzig-scale display, the
    # WGS84 difference is negligible; this standard UTM inverse is sufficient.
    semi_major = 6378137.0
    flattening = 1 / 298.257223563
    scale = 0.9996
    zone_origin_lon = math.radians(15.0)
    false_easting = 500000.0

    eccentricity_sq = flattening * (2 - flattening)
    eccentricity_prime_sq = eccentricity_sq / (1 - eccentricity_sq)
    x = easting - false_easting
    y = northing
    meridional_arc = y / scale
    mu = meridional_arc / (
        semi_major
        * (
            1
            - eccentricity_sq / 4
            - 3 * eccentricity_sq**2 / 64
            - 5 * eccentricity_sq**3 / 256
        )
    )

    e1 = (1 - math.sqrt(1 - eccentricity_sq)) / (1 + math.sqrt(1 - eccentricity_sq))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )

    sin_phi1 = math.sin(phi1)
    cos_phi1 = math.cos(phi1)
    tan_phi1 = math.tan(phi1)
    n1 = semi_major / math.sqrt(1 - eccentricity_sq * sin_phi1**2)
    r1 = semi_major * (1 - eccentricity_sq) / (1 - eccentricity_sq * sin_phi1**2) ** 1.5
    t1 = tan_phi1**2
    c1 = eccentricity_prime_sq * cos_phi1**2
    d = x / (n1 * scale)

    latitude = phi1 - (n1 * tan_phi1 / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * eccentricity_prime_sq) * d**4 / 24
        + (
            61
            + 90 * t1
            + 298 * c1
            + 45 * t1**2
            - 252 * eccentricity_prime_sq
            - 3 * c1**2
        )
        * d**6
        / 720
    )
    longitude = zone_origin_lon + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (
            5
            - 2 * c1
            + 28 * t1
            - 3 * c1**2
            + 8 * eccentricity_prime_sq
            + 24 * t1**2
        )
        * d**5
        / 120
    ) / cos_phi1

    return math.degrees(latitude), math.degrees(longitude)


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(radius_m * c))
