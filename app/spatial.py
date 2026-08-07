"""Gemeinsame, rein lokale Geometrie- und Entfernungsfunktionen."""

from __future__ import annotations

import math

from .models import MapOrigin


LEIPZIG_HBF = MapOrigin(
    id="leipzig-hbf",
    label="Leipzig Hauptbahnhof",
    address="Willy-Brandt-Platz 5, 04109 Leipzig",
    latitude=51.34556,
    longitude=12.38222,
)


def is_valid_leipzig_coordinate(latitude: float, longitude: float) -> bool:
    """Begrenzt Marker auf einen konservativen Leipziger Umgebungsrahmen."""

    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and 51.1 <= latitude <= 51.6
        and 12.0 <= longitude <= 12.8
    )


def haversine_distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> int:
    """Berechnet Luftlinie in Metern; die Funktion behauptet keine Wegstrecke."""

    radius_m = 6_371_000
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return int(round(radius_m * central_angle))


def distance_from_hbf(latitude: float, longitude: float, *, origin: MapOrigin = LEIPZIG_HBF) -> int:
    """Liefert die Luftlinie vom konfigurierten Hauptbahnhof-Ursprung."""

    return haversine_distance_meters(
        origin.latitude,
        origin.longitude,
        latitude,
        longitude,
    )


def wgs84_to_utm33n(latitude: float, longitude: float) -> tuple[float, float]:
    """Transformiert WGS84 nach ETRS89 / UTM Zone 33N für Leipzig.

    WGS84 und ETRS89 unterscheiden sich im lokalen Prototypmaßstab nur um
    wenige Dezimeter. Die Funktion dient ausschließlich der reproduzierbaren
    administrativen Punkt-in-Polygon-Prüfung, nicht einer Routenberechnung.
    """

    if not (-80.0 <= latitude <= 84.0 and -180.0 <= longitude <= 180.0):
        raise ValueError("coordinate is outside the UTM domain")
    semi_major = 6_378_137.0
    flattening = 1 / 298.257223563
    scale = 0.9996
    eccentricity_sq = flattening * (2 - flattening)
    eccentricity_prime_sq = eccentricity_sq / (1 - eccentricity_sq)
    phi = math.radians(latitude)
    longitude_rad = math.radians(longitude)
    central_meridian = math.radians(15.0)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)
    radius = semi_major / math.sqrt(1 - eccentricity_sq * sin_phi**2)
    t = tan_phi**2
    c = eccentricity_prime_sq * cos_phi**2
    a = cos_phi * (longitude_rad - central_meridian)
    meridional_arc = semi_major * (
        (1 - eccentricity_sq / 4 - 3 * eccentricity_sq**2 / 64 - 5 * eccentricity_sq**3 / 256) * phi
        - (3 * eccentricity_sq / 8 + 3 * eccentricity_sq**2 / 32 + 45 * eccentricity_sq**3 / 1024)
        * math.sin(2 * phi)
        + (15 * eccentricity_sq**2 / 256 + 45 * eccentricity_sq**3 / 1024) * math.sin(4 * phi)
        - 35 * eccentricity_sq**3 / 3072 * math.sin(6 * phi)
    )
    easting = 500_000.0 + scale * radius * (
        a
        + (1 - t + c) * a**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * eccentricity_prime_sq) * a**5 / 120
    )
    northing = scale * (
        meridional_arc
        + radius
        * tan_phi
        * (
            a**2 / 2
            + (5 - t + 9 * c + 4 * c**2) * a**4 / 24
            + (61 - 58 * t + t**2 + 600 * c - 330 * eccentricity_prime_sq) * a**6 / 720
        )
    )
    return easting, northing


def utm33n_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Transformiert ETRS89 / UTM Zone 33N (EPSG:25833) nach WGS84."""

    semi_major = 6_378_137.0
    flattening = 1 / 298.257223563
    scale = 0.9996
    zone_origin_lon = math.radians(15.0)
    eccentricity_sq = flattening * (2 - flattening)
    eccentricity_prime_sq = eccentricity_sq / (1 - eccentricity_sq)
    x = easting - 500_000.0
    meridional_arc = northing / scale
    mu = meridional_arc / (
        semi_major
        * (1 - eccentricity_sq / 4 - 3 * eccentricity_sq**2 / 64 - 5 * eccentricity_sq**3 / 256)
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
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * eccentricity_prime_sq - 3 * c1**2)
        * d**6
        / 720
    )
    longitude = zone_origin_lon + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * eccentricity_prime_sq + 24 * t1**2)
        * d**5
        / 120
    ) / cos_phi1
    return math.degrees(latitude), math.degrees(longitude)
