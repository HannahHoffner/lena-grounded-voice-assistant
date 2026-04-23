from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .config import Settings
from .kb import KnowledgeBase
from .models import (
    AnswerStatus,
    KnowledgeAnswer,
    MapData,
    MapDestination,
    MapOrigin,
    PageMetadata,
    QueryAnswerResponse,
)


LEIPZIG_LAT_RANGE = (51.26, 51.41)
LEIPZIG_LON_RANGE = (12.20, 12.52)
MAP_ELIGIBLE_STATUSES: set[AnswerStatus] = {"ok", "weak_match"}


@dataclass(slots=True)
class MapBuilder:
    settings: Settings
    max_destinations: int = 3

    def build_for_answer(
        self,
        answer: KnowledgeAnswer | QueryAnswerResponse,
        kb: KnowledgeBase,
    ) -> MapData | None:
        if answer.status not in MAP_ELIGIBLE_STATUSES:
            return None

        destinations: list[MapDestination] = []
        seen_keys: set[str] = set()
        origin = MapOrigin(
            id=self.settings.map_origin_id,
            label=self.settings.map_origin_label,
            address=self.settings.map_origin_address,
            latitude=self.settings.map_origin_latitude,
            longitude=self.settings.map_origin_longitude,
        )

        top_page = self._top_page(answer, kb)
        if top_page and self._is_explicitly_out_of_scope_place(top_page):
            return None

        for page_id in answer.retrieved_page_ids:
            try:
                page = kb.get_page(page_id)
            except KeyError:
                continue
            if not self._is_concrete_destination(page):
                continue

            dedupe_key = self._dedupe_key(page)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            destinations.append(
                MapDestination(
                    id=page.page_id,
                    page_id=page.page_id,
                    label=page.title,
                    organization_label=page.organization or page.publisher,
                    service_type=page.service_type,
                    address=page.address or "",
                    latitude=page.latitude or 0.0,
                    longitude=page.longitude or 0.0,
                    distance_meters=_haversine_distance_meters(
                        origin.latitude,
                        origin.longitude,
                        page.latitude or 0.0,
                        page.longitude or 0.0,
                    ),
                    description=_short_description(page),
                    opening_hours=page.opening_hours[:4],
                )
            )
            if len(destinations) == self.max_destinations:
                break

        if not destinations:
            return None

        return MapData(
            origin=origin,
            destinations=destinations,
            selected_destination_id=destinations[0].id,
        )

    def _is_concrete_destination(self, page: PageMetadata) -> bool:
        if page.service_type == "service_catalog" or page.entity_kind == "service_program":
            return False
        if page.latitude is None or page.longitude is None:
            return False
        if page.geo_status in {"missing_address", "failed", "filtered_out"}:
            return False
        if not page.address:
            return False
        return self._is_leipzig_coordinate(page.latitude, page.longitude)

    def _is_leipzig_coordinate(self, latitude: float, longitude: float) -> bool:
        return (
            LEIPZIG_LAT_RANGE[0] <= latitude <= LEIPZIG_LAT_RANGE[1]
            and LEIPZIG_LON_RANGE[0] <= longitude <= LEIPZIG_LON_RANGE[1]
        )

    def _dedupe_key(self, page: PageMetadata) -> str:
        if page.entity_signature:
            return page.entity_signature
        normalized_address = _normalize_address(page.address or page.normalized_address or "")
        return f"{page.title.casefold().strip()}|{normalized_address}"

    def _top_page(self, answer: KnowledgeAnswer | QueryAnswerResponse, kb: KnowledgeBase) -> PageMetadata | None:
        if not answer.retrieved_page_ids:
            return None
        try:
            return kb.get_page(answer.retrieved_page_ids[0])
        except KeyError:
            return None

    def _is_explicitly_out_of_scope_place(self, page: PageMetadata) -> bool:
        if page.service_type == "service_catalog" or page.entity_kind == "service_program":
            return False
        if not page.address:
            return False
        if not _looks_like_leipzig_address(page.address):
            return True
        if page.geo_status == "filtered_out":
            return True
        if page.latitude is not None and page.longitude is not None and not self._is_leipzig_coordinate(page.latitude, page.longitude):
            return True
        return False


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(round(radius_m * c))


def _short_description(page: PageMetadata) -> str | None:
    description = (page.description or "").strip()
    if description:
        return description[:200].rstrip()
    summary = (page.summary or "").strip()
    if summary:
        return summary[:200].rstrip()
    return None


def _normalize_address(address: str) -> str:
    german_equivalents = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
    normalized = address.casefold().translate(german_equivalents)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _looks_like_leipzig_address(address: str) -> bool:
    normalized = _normalize_address(address)
    if any(term in normalized for term in ("markkleeberg", "markranstadt", "markranstaedt", "borna")):
        return False
    if "leipzig" in normalized:
        return True
    return bool(re.search(r"\b04[123]\d{2}\b", normalized))
