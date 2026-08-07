"""Kontrollierter Alias-, UI- und Zeitkontext der Kandidatenstufe."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

from .candidate_contract import AliasSelectionContext, CandidateSelectionContext, FactsUsed
from .curation import OrganizationAliasBinding
from .interpreter import Need, QueryInterpretation, RequestedDay
from .models import Category, OfferRecord


def normalize_candidate_text(value: str) -> str:
    """Normalisiert ausschließlich kontrollierte Alias- und Hinweisvergleiche."""
    text = unicodedata.normalize("NFKD", value.casefold().replace("ß", "ss"))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _contains(text: str, phrase: str) -> bool:
    phrase_value = normalize_candidate_text(phrase)
    return bool(phrase_value and f" {phrase_value} " in f" {text} ")


def build_selection_context(
    *,
    query: str,
    interpretation: QueryInterpretation,
    offers: list[OfferRecord],
    organization_aliases: tuple[OrganizationAliasBinding, ...],
    ui_category: Category | None,
) -> CandidateSelectionContext:
    """Extrahiert nur kuratierte Aliasbindungen und den schwachen UI-Hinweis."""
    text = normalize_candidate_text(query)
    offer_aliases = [
        (alias, offer.id)
        for offer in offers
        for alias in offer.offer_aliases
        if _contains(text, alias)
    ]
    if offer_aliases:
        alias, offer_id = max(
            offer_aliases,
            key=lambda item: len(normalize_candidate_text(item[0])),
        )
        resolved = AliasSelectionContext(
            alias=alias,
            alias_kind="offer",
            offer_ids=[offer_id],
        )
    else:
        matches = [
            binding
            for binding in organization_aliases
            if _contains(text, binding.alias)
        ]
        matches = [
            binding
            for binding in matches
            if normalize_candidate_text(binding.alias) != "mobile"
            or text == "mobile"
            or any(
                _contains(text, phrase)
                for phrase in (
                    "mobile jugendarbeit",
                    "zu mobile",
                    "bei mobile",
                    "wo ist mobile",
                    "kontakt mobile",
                    "suche mobile",
                )
            )
        ]
        resolved = None
        if matches:
            binding = max(
                matches,
                key=lambda item: len(normalize_candidate_text(item.alias)),
            )
            offer_ids = list(binding.offer_ids)
            district = interpretation.explicit_facts.district
            if district:
                district_ids = [
                    offer.id
                    for offer in offers
                    if offer.id in offer_ids
                    and any(
                        _contains(normalize_candidate_text(value), district)
                        for value in [offer.district or "", *offer.search_phrases]
                    )
                ]
                if district_ids:
                    offer_ids = district_ids
            resolved = AliasSelectionContext(
                alias=binding.alias,
                alias_kind="organization",
                offer_ids=offer_ids,
                district_narrowed=len(offer_ids) < len(binding.offer_ids),
            )
    ui_need = {
        Category.FOOD: Need.FOOD,
        Category.SLEEP: Need.SLEEP,
        Category.MEDICAL: Need.MEDICAL,
        Category.ADVICE: Need.ADVICE,
        Category.TOILET: Need.TOILET,
    }.get(ui_category)
    return CandidateSelectionContext(ui_need_hint=ui_need, alias=resolved)


def _weekday(day: RequestedDay | None, now: datetime) -> int | None:
    if day is None:
        return None
    if day in {RequestedDay.TODAY, RequestedDay.TONIGHT}:
        return now.weekday()
    if day == RequestedDay.TOMORROW:
        return (now + timedelta(days=1)).weekday()
    return list(RequestedDay)[:7].index(day)


def schedule_matches(rule: str, facts: FactsUsed, now: datetime) -> bool | None:
    """Prüft nur katalogzugelassene Einsatzzeitregeln gegen explizite Zeitfakten."""
    weekday = _weekday(facts.requested_day, now)
    minutes = None
    if facts.requested_time:
        hour, minute = (int(value) for value in facts.requested_time.split(":"))
        minutes = hour * 60 + minute
    if weekday is None and minutes is None:
        return None
    rules: dict[str, tuple[set[int], int | None, int | None]] = {
        "tuesday_17_18": ({1}, 17 * 60, 18 * 60),
        "thursday_16_1730": ({3}, 16 * 60, 17 * 60 + 30),
        "thursday_16_19": ({3}, 16 * 60, 19 * 60),
        "sunday_20_21": ({6}, 20 * 60, 21 * 60),
        "daily_18_23": (set(range(7)), 18 * 60, 23 * 60),
        "mobile_alternative_stands": ({1, 2, 3, 4}, None, None),
        "medibus_and_clinics": ({0, 1, 2, 3, 4, 6}, None, None),
    }
    days, start, end = rules[rule]
    if weekday is None and days != set(range(7)):
        return None
    if weekday is not None and weekday not in days:
        return False
    if minutes is not None and start is not None and not start <= minutes <= end:
        return False
    return True
