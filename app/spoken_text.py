"""Baut den serverseitig freigegebenen, laut vorlesbaren Text pro Tafel.

`/api/speech/synthesize` synthetisiert ausschließlich Text, den der Server für
die aktuelle Session bereits selbst erzeugt hat (siehe
`QueryService`-Aufrufer von `sessions.add_turn(..., speakable_texts=...)` und
`main.py::synthesize_speech`). Diese Funktionen sind die einzige Stelle, an
der dieser Text entsteht -- Karte, Kartenpunkt-Tafel und TTS-Freigabe zitieren
damit garantiert denselben Wortlaut.
"""

from __future__ import annotations

import re

from .application_texts import application_text
from .infrastructure import DrinkingFountainRecord, PublicToiletRecord
from .models import Language, OfferRecord

_BULLET_PREFIX = re.compile(r"^>\s*")


def _clean(value: str) -> str:
    return _BULLET_PREFIX.sub("", value).strip()


def _field(language: Language, key: str, values: list[str]) -> str | None:
    cleaned = [_clean(value) for value in values if value and value.strip()]
    if not cleaned:
        return None
    label = application_text(language, f"ui.{key}")
    return f"{label}: {', '.join(cleaned)}"


def _spoken_text(name: str, language: Language, fields: list[tuple[str, list[str]]]) -> str:
    """Reiht `name` und jedes nicht-leere (Label, Werte)-Feld zu einem Satz auf."""
    parts = [name]
    for key, values in fields:
        field = _field(language, key, values)
        if field:
            parts.append(field)
    return ". ".join(parts)


def offer_spoken_text(
    offer: OfferRecord,
    language: Language,
    *,
    short_description: str | None = None,
    services: list[str] | None = None,
    opening_hours_raw: list[str] | None = None,
    notes: list[str] | None = None,
) -> str:
    """Fasst genau die Felder zusammen, die die Angebotskarte anzeigt.

    Optionale Parameter übernehmen bereits lokalisierten Text (siehe
    `localize_offer_card`); ohne sie wird der unlokalisierte Datensatz gelesen.
    """
    description = short_description if short_description is not None else offer.short_description
    return _spoken_text(
        offer.display_name or offer.name,
        language,
        [
            ("description", [description] if description else []),
            ("services", services if services is not None else offer.services),
            ("address", [offer.address] if offer.address else []),
            ("phone", offer.phone_numbers),
            ("hours", opening_hours_raw if opening_hours_raw is not None else offer.opening_hours_raw),
            ("standTimes", offer.standzeiten_raw),
            ("notes", notes if notes is not None else offer.notes),
        ],
    )


def toilet_spoken_text(record: PublicToiletRecord, language: Language) -> str:
    return _spoken_text(
        record.display_name,
        language,
        [
            ("district", [record.district] if record.district else []),
            ("hours", [record.opening_hours_raw] if record.opening_hours_raw else []),
            ("facilities", record.facilities),
            ("fee", [record.fee_raw] if record.fee_raw else []),
            ("source", ["Stadt Leipzig"]),
        ],
    )


def fountain_spoken_text(record: DrinkingFountainRecord, language: Language) -> str:
    location = record.location_description or record.address
    return _spoken_text(
        record.name,
        language,
        [
            ("drinkingFountain", [location] if location else []),
            ("address", [record.address] if record.address else []),
            ("fee", [application_text(language, "ui.freeWater")] if record.cost_status.value == "free" else []),
            (
                "hours",
                [application_text(language, "ui.seasonalOperation")]
                if record.seasonal_status.value == "april_to_october"
                else [],
            ),
            ("source", ["Leipziger Wasserwerke"]),
        ],
    )
