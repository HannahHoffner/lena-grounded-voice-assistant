"""Fachliche Zielgruppenklassifikation für Übernachtungsangebote."""

from __future__ import annotations

from .models import OfferRecord
from .retrieval import normalize_text


def sleep_roles(offers: list[OfferRecord]) -> dict[str, list[OfferRecord]]:
    roles: dict[str, list[OfferRecord]] = {"ruecke": [], "men": [], "women": [], "drug": []}
    for offer in offers:
        name = normalize_text(offer.name)
        address = normalize_text(offer.address or "")
        is_sleep_house = "ubernachtungshaus" in name or "notschlafstelle" in name
        is_men = is_sleep_house and "manner" in name
        is_women = is_sleep_house and "frauen" in name
        is_drug = "drogenkonsum" in name or "drogengebrauch" in normalize_text(" ".join(offer.services))
        if is_men and "ruckmarsdorfer" in address:
            roles["ruecke"].append(offer)
        if is_men:
            roles["men"].append(offer)
        if is_women:
            roles["women"].append(offer)
        if is_sleep_house and is_drug:
            roles["drug"].append(offer)
    for values in roles.values():
        values.sort(key=lambda offer: offer.source_index)
    return roles
