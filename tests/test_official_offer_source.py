"""Vertragstests fuer paketierte, verifizierte Betreiberangebote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.maps import build_map_data, offer_wgs84
from app.models import Language
from app.official_offer_source import OfficialSourceError, load_official_offer_source


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "app" / "resources" / "bootstrap" / "official" / "verified_offers.json"


def test_verified_vkkj_source_is_minimal_hash_bound_and_traceable() -> None:
    source, source_hash = load_official_offer_source(SOURCE_PATH)

    assert source.source_version == "vkkj-2026-08-25"
    assert len(source_hash) == 64
    assert {offer.id for offer in source.offers} == {
        "vkkj_notschlafstelle",
        "vkkj_jugendnotdienst",
    }
    assert all(offer.source_hash == source_hash for offer in source.offers)
    assert all(not offer.raw_fields and not offer.raw_properties for offer in source.offers)
    assert {str(reference.url) for reference in source.sources} == {
        "https://www.vkkj.de/verzeichnis/visitenkarte.php?mandat=240969",
        "https://www.vkkj.de/verzeichnis/visitenkarte.php?mandat=230429",
    }

    night = next(offer for offer in source.offers if offer.id == "vkkj_notschlafstelle")
    emergency = next(offer for offer in source.offers if offer.id == "vkkj_jugendnotdienst")
    assert night.address == "Breite Straße 10, 04317 Leipzig"
    assert night.opening_hours_raw == ["Täglich 22:00–10:00 Uhr"]
    assert night.geometry == {
        "type": "Point",
        "coordinates": [12.4080206, 51.3372778],
        "crs": "urn:ogc:def:crs:OGC::CRS84",
    }
    assert emergency.address == "Ringstraße 4, 04209 Leipzig"
    assert emergency.opening_hours_raw == ["Rund um die Uhr"]
    assert emergency.geometry == {
        "type": "Point",
        "coordinates": [12.294794, 51.314376],
        "crs": "urn:ogc:def:crs:OGC::CRS84",
    }

    assert offer_wgs84(night) == pytest.approx((51.3372778, 12.4080206))
    assert offer_wgs84(emergency) == pytest.approx((51.314376, 12.294794))
    map_data = build_map_data([night, emergency], language=Language.DE)
    assert map_data is not None
    assert [destination.id for destination in map_data.destinations] == [
        "vkkj_notschlafstelle",
        "vkkj_jugendnotdienst",
    ]
    assert [destination.address for destination in map_data.destinations] == [
        "Breite Straße 10, 04317 Leipzig",
        "Ringstraße 4, 04209 Leipzig",
    ]

    unsupported_crs = night.model_copy(
        update={"geometry": {"type": "Point", "coordinates": [12.4, 51.3], "crs": "EPSG:9999"}}
    )
    outside_leipzig = night.model_copy(
        update={
            "geometry": {
                "type": "Point",
                "coordinates": [13.405, 52.52],
                "crs": "urn:ogc:def:crs:OGC::CRS84",
            }
        }
    )
    assert offer_wgs84(unsupported_crs) is None
    assert offer_wgs84(outside_leipzig) is None


def test_official_source_rejects_missing_invalid_and_wfs_shaped_payloads(tmp_path: Path) -> None:
    with pytest.raises(OfficialSourceError, match="missing"):
        load_official_offer_source(tmp_path / "missing.json")

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    with pytest.raises(OfficialSourceError, match="invalid"):
        load_official_offer_source(invalid)

    payload = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    payload["offers"][0]["raw_fields"] = {"ap1": ["not permitted"]}
    shaped = tmp_path / "wfs-shaped.json"
    shaped.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(OfficialSourceError, match="must not imitate WFS"):
        load_official_offer_source(shaped)
