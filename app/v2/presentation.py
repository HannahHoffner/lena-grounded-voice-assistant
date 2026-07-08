from __future__ import annotations

import re

from .models import V2Offer


DISPLAY_NAMES = {
    "hilfebus": "Hilfebus",
    "uebernachtungshaus-maenner-leutzsch": "Rücke",
    "safe-team-wohnen": "SAFE Team Wohnen",
    "safe-team-konsum": "SAFE Team Konsum",
    "diakonie-streetwork": "Diakonie Streetwork",
    "alternative-i-notschlafstelle": "Alternative I",
    "alternative-iii-notschlafstelle": "Alternative III",
    "kontaktcafe-alternative-i": "Kontaktcafé Alternative I",
    "mobile-alternative": "Mobile Alternative",
    "uvo-medical-outreach": "UVO Medibus",
    "cabl-clearingstelle": "CABL Clearingstelle",
}

PRIMARY_PHONE_OVERRIDES = {
    "hilfebus": "0152 33661087 (nur zu Einsatzzeiten)",
}


def display_name(offer: V2Offer) -> str:
    return DISPLAY_NAMES.get(offer.offer_id, offer.name)


def primary_phone(offer: V2Offer) -> str | None:
    if offer.offer_id in PRIMARY_PHONE_OVERRIDES:
        return PRIMARY_PHONE_OVERRIDES[offer.offer_id]
    if not offer.phone:
        return None
    first = offer.phone.split(";")[0].strip()
    first = re.sub(r"\s*\((?:Herr|Frau|Leitung|stellv\.).*?\)\s*", "", first).strip()
    return first or None


def compact_names(offers: list[V2Offer], *, limit: int = 3) -> str:
    names: list[str] = []
    for offer in offers:
        name = display_name(offer)
        if name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return ", ".join(names)
