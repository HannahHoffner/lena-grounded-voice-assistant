"""Output-only Hilfebus contact and location roles from curated runtime data."""

import re

from .application_texts import application_text
from .models import Language, OfferRecord, OfferCard, QueryResponse
from .result_time import SCHEDULE_WINDOWS
from .spoken_text import offer_spoken_text
from .maps import offer_stand_destinations


def operational_phone(offer: OfferRecord) -> str:
    """Keep the source label for evidence; never use the staff phone in prose."""
    return next((value for value in offer.phone_numbers if "Einsatzzeiten" in value), "")


def contact_hint(offer: OfferRecord, language: Language) -> str:
    phone = operational_phone(offer).split(" (")[0]
    rule = offer.service_schedules.get("referral")
    windows = SCHEDULE_WINDOWS.get(rule, ())
    if not phone or not windows:
        return ""
    window = windows[0]
    def clock(minute: int) -> str:
        return str(minute // 60) if minute % 60 == 0 else f"{minute // 60}:{minute % 60:02d}"
    times = f"{clock(window.start_minute)}–{clock(window.end_minute)}"
    return application_text(language, "fallback.hilfebus_hint", times=times, phone=phone)


def needs_hint(answer_type: str | None, route: str) -> bool:
    return answer_type in {"no_verified_result", "out_of_scope", "technical_fallback", "ambiguous_help_fallback"} or route in {
        "dialog_hilfebus", "dialog_general_need",
    }


def sunday_food_hint(offer: OfferRecord, language: Language) -> str:
    """Fallback wording still reports the documented Sunday service window."""
    stands = offer_stand_destinations(offer, service="food")
    windows = SCHEDULE_WINDOWS.get(offer.service_schedules.get("food"), ())
    if not stands or not windows:
        return ""
    window = windows[0]
    times = f"{window.start_minute // 60}:00–{window.end_minute // 60}:00"
    return application_text(language, "fallback.hilfebus_sunday", stand=stands[0].address, times=times)


def prose_limit(offer: OfferRecord | None, language: Language, answer_type: str) -> int:
    if offer and needs_hint(answer_type, ""):
        return 600 - len(contact_hint(offer, language)) - 1
    return 600


def present_card(card: OfferCard, offer: OfferRecord, language: Language, *, stand=None) -> OfferCard:
    """A mobile contact has no place; only an actual Sunday result has one."""
    card.address = stand.address if stand else None
    if not stand:
        # No location in the always-present contact tile, including its speech.
        card.standzeiten_raw = []
        card.opening_hours_raw = [value for index, value in enumerate(card.opening_hours_raw)
                                  if "Hauptbahnhof" not in offer.opening_hours_raw[index]]
        card.services = [value for index, value in enumerate(card.services)
                         if not any(token in offer.services[index] for token in ("Standzeiten:", "Hauptbahnhof"))]
    card.spoken_text = offer_spoken_text(
        offer.model_copy(update={"address": card.address, "district": None,
                                 "phone_numbers": [operational_phone(offer)],
                                 "standzeiten_raw": card.standzeiten_raw}), language,
        short_description=card.short_description, services=card.services,
        opening_hours_raw=card.opening_hours_raw, notes=card.notes,
        phone_numbers=[card.phone_numbers[offer.phone_numbers.index(operational_phone(offer))]],
        standzeiten_raw=card.standzeiten_raw,
    )
    return card


def append_contact(response: QueryResponse, offer: OfferRecord, card: OfferCard, *, answer_type: str, route: str) -> None:
    """Run before session/TTS persistence; acute-risk paths remain untouched."""
    if answer_type in {"acute_risk", "acute_risk_clarification"}:
        return
    add_hint = needs_hint(answer_type, route)
    if add_hint and not re.search(r"\bhilfebus\b", response.answer, re.IGNORECASE):
        hint = contact_hint(offer, response.language)
        if hint:
            response.answer = f"{response.answer} {hint}".strip()
    if response.cards or add_hint:
        if any(item.id == offer.id for item in response.cards):
            response.cards = [card if item.id == offer.id else item for item in response.cards]
        else:
            response.cards.append(card)
        response.card_ids = [item.id for item in response.cards]
