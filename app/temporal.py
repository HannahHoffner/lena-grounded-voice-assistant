"""Vorsichtige Zeitregeln ohne Behauptung von Echtzeitverfügbarkeit."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .models import Category, Language, OfferRecord
from .retrieval import normalize_text


WEEKDAY_DE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
WEEKDAY_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


@dataclass(frozen=True)
class TemporalContext:
    now: datetime
    weekday_index: int
    requested_weekday_index: int | None
    requested_time_minutes: int | None
    explicit_day: bool
    explicit_time: bool
    nowish: bool

    @property
    def effective_weekday_index(self) -> int:
        return self.requested_weekday_index if self.requested_weekday_index is not None else self.weekday_index

    @property
    def effective_time_minutes(self) -> int:
        return self.requested_time_minutes if self.requested_time_minutes is not None else self.now.hour * 60 + self.now.minute


@dataclass(frozen=True)
class TemporalDecision:
    include: bool
    note: str | None = None
    boost: int = 0


def build_temporal_context(query: str, now: datetime | None = None) -> TemporalContext:
    tz = ZoneInfo("Europe/Berlin")
    current = now or datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)
    normalized = normalize_text(query)
    requested_day = _requested_weekday(normalized)
    explicit_day = requested_day is not None
    if requested_day is None and any(term in normalized for term in ("heute", "today", "jetzt", "now", "heute abend", "tonight")):
        requested_day = current.weekday()
        explicit_day = True
    if requested_day is None and any(term in normalized for term in ("morgen", "tomorrow")):
        requested_day = (current + timedelta(days=1)).weekday()
        explicit_day = True

    requested_time = _requested_time_minutes(query)
    nowish = any(
        term in normalized
        for term in ("jetzt", "now", "gerade", "heute", "today", "tonight", "abend", "abends", "tagsuber", "tagsueber", "daytime")
    )
    if requested_time is None and any(term in normalized for term in ("abend", "abends", "tonight")):
        requested_time = 18 * 60
    if requested_time is None and any(term in normalized for term in ("tagsuber", "tagsueber", "daytime")):
        requested_time = 12 * 60
    return TemporalContext(
        now=current,
        weekday_index=current.weekday(),
        requested_weekday_index=requested_day,
        requested_time_minutes=requested_time,
        explicit_day=explicit_day,
        explicit_time=requested_time is not None,
        nowish=nowish,
    )


def temporal_decision(offer: OfferRecord, category: Category | None, query: str, context: TemporalContext) -> TemporalDecision:
    if category == Category.FOOD:
        return _food_decision(offer, context)
    if category == Category.MEDICAL:
        return _medical_decision(offer, context)
    if category == Category.SLEEP:
        return _sleep_decision(offer, context)
    return TemporalDecision(include=True)


def apply_temporal_policy(
    offers: list[OfferRecord],
    category: Category | None,
    query: str,
    context: TemporalContext,
) -> tuple[list[OfferRecord], list[str]]:
    """Ordnet Angebote nach belegten Zeitregeln und liefert erklärende Hinweise."""
    if category not in {Category.FOOD, Category.MEDICAL, Category.SLEEP}:
        return offers, []
    kept: list[tuple[int, OfferRecord]] = []
    notes: list[str] = []
    for position, offer in enumerate(offers):
        decision = temporal_decision(offer, category, query, context)
        if not decision.include:
            continue
        kept.append((position - decision.boost, offer))
        if decision.note and decision.note not in notes:
            notes.append(decision.note)
    kept.sort(key=lambda item: item[0])
    return [offer for _, offer in kept], notes


def prepend_temporal_notes(answer: str, notes: list[str], language: Language) -> str:
    if not notes:
        return answer
    if language == Language.EN:
        prefix = "Important for the time: "
    elif language == Language.PL:
        prefix = "Ważne dla tego czasu: "
    elif language == Language.RO:
        prefix = "Important pentru acest timp: "
    elif language == Language.RU:
        prefix = "Важно по времени: "
    else:
        prefix = "Wichtig zur Zeit: "
    text = " ".join(_localized_note(note, language) for note in notes[:2])
    return f"{prefix}{text} {answer}"


def _localized_note(note: str, language: Language) -> str:
    if language == Language.DE:
        return note
    normalized = normalize_text(note)
    if "hilfebus" in normalized and "suppenausgabe nur sonntags" in normalized:
        translations = {
            Language.EN: "Hilfebus has soup only on Sunday 20:00-21:00 at the west side of Hauptbahnhof. The daily mobile service is 18:00-23:00 in the city; during the day you can call from 18:00.",
            Language.PL: "Hilfebus wydaje zupę tylko w niedzielę 20:00-21:00 po zachodniej stronie Hauptbahnhof. Codzienny mobilny dyżur jest 18:00-23:00 w mieście; w dzień możesz dzwonić od 18:00.",
            Language.RO: "Hilfebus oferă supă doar duminica 20:00-21:00 pe partea de vest a Hauptbahnhof. Serviciul mobil zilnic este 18:00-23:00 în oraș; ziua poți suna de la 18:00.",
            Language.RU: "Hilfebus выдает суп только в воскресенье 20:00-21:00 на западной стороне Hauptbahnhof. Ежедневный мобильный выезд работает 18:00-23:00 по городу; днем можно звонить с 18:00.",
        }
        return translations[language]
    if "hilfebus" in normalized and "warmes essen" in normalized:
        translations = {
            Language.EN: "Hilfebus works daily 18:00-23:00. Warm food or soup is listed only on Sunday 20:00-21:00 at Hauptbahnhof.",
            Language.PL: "Hilfebus działa codziennie 18:00-23:00. Ciepłe jedzenie albo zupa jest podane tylko w niedzielę 20:00-21:00 przy Hauptbahnhof.",
            Language.RO: "Hilfebus lucrează zilnic 18:00-23:00. Mâncarea caldă sau supa este trecută doar duminica 20:00-21:00 la Hauptbahnhof.",
            Language.RU: "Hilfebus работает ежедневно 18:00-23:00. Горячая еда или суп указаны только в воскресенье 20:00-21:00 у Hauptbahnhof.",
        }
        return translations[language]
    if "schwanenteich" in normalized and "17 00 18 00" in normalized:
        translations = {
            Language.EN: "The food or drinks at Schwanenteich are on Tuesday 17:00-18:00 at Goethestraße/Schwanenteich. The office time at Nürnberger Str. 37 or Demmeringstr. 32 is not food distribution.",
            Language.PL: "Jedzenie albo napoje przy Schwanenteich są we wtorek 17:00-18:00 przy Goethestraße/Schwanenteich. Godziny biura przy Nürnberger Str. 37 albo Demmeringstr. 32 nie są wydawaniem jedzenia.",
            Language.RO: "Mâncarea sau băuturile la Schwanenteich sunt marți 17:00-18:00 la Goethestraße/Schwanenteich. Programul de birou la Nürnberger Str. 37 sau Demmeringstr. 32 nu este distribuire de mâncare.",
            Language.RU: "Еда или напитки у Schwanenteich выдаются во вторник 17:00-18:00 по адресу Goethestraße/Schwanenteich. Офисное время на Nürnberger Str. 37 или Demmeringstr. 32 не является раздачей еды.",
        }
        return translations[language]
    if "medibus" in normalized and "hauptbahnhof" in normalized:
        translations = {
            Language.EN: "The mobile medical service/Medibus is only at the listed places and times: Wednesday Hauptbahnhof, Friday Koehlerstraße/Dresdner Straße and Hauptbahnhof, Sunday Hauptbahnhof.",
            Language.PL: "Mobilna pomoc medyczna/Medibus jest tylko w podanych miejscach i godzinach: środa Hauptbahnhof, piątek Koehlerstraße/Dresdner Straße i Hauptbahnhof, niedziela Hauptbahnhof.",
            Language.RO: "Serviciul medical mobil/Medibus este doar în locurile și la orele indicate: miercuri Hauptbahnhof, vineri Koehlerstraße/Dresdner Straße și Hauptbahnhof, duminică Hauptbahnhof.",
            Language.RU: "Мобильная медицинская помощь/Medibus работает только в указанных местах и в указанное время: среда Hauptbahnhof, пятница Koehlerstraße/Dresdner Straße и Hauptbahnhof, воскресенье Hauptbahnhof.",
        }
        return translations[language]
    if "mobile alternative" in normalized:
        translations = {
            Language.EN: "The mobile Alternative has fixed stand times. Use the place for the right day and time, not automatically the office address.",
            Language.PL: "Mobile Alternative ma stałe czasy postoju. Idź do miejsca pasującego do dnia i godziny, nie automatycznie na adres biura.",
            Language.RO: "Mobile Alternative are ore fixe de staționare. Folosește locul potrivit pentru ziua și ora corectă, nu automat adresa biroului.",
            Language.RU: "Mobile Alternative имеет фиксированные места и часы. Идите в место, подходящее к дню и времени, а не автоматически по адресу офиса.",
        }
        return translations[language]
    if "hilfebus" in normalized and "18 00 23 00" in normalized:
        translations = {
            Language.EN: "Hilfebus can be reached in the evening during service time 18:00-23:00; during the day you can call from 18:00.",
            Language.PL: "Z Hilfebus można skontaktować się wieczorem w czasie dyżuru 18:00-23:00; w dzień możesz dzwonić od 18:00.",
            Language.RO: "Hilfebus poate fi contactat seara în timpul programului 18:00-23:00; ziua poți suna de la 18:00.",
            Language.RU: "С Hilfebus можно связаться вечером во время работы 18:00-23:00; днем можно звонить с 18:00.",
        }
        return translations[language]
    return note


def _food_decision(offer: OfferRecord, context: TemporalContext) -> TemporalDecision:
    normalized_name = normalize_text(offer.name)
    weekday = context.effective_weekday_index
    minutes = context.effective_time_minutes
    explicit = context.explicit_day or context.nowish

    if "hilfebus" in normalized_name:
        if weekday == 6:
            return TemporalDecision(
                include=True,
                boost=6,
                note="Der Hilfebus hat die Suppenausgabe nur sonntags 20:00-21:00 Uhr an der Westseite des Hauptbahnhofes. Der tägliche mobile Einsatz 18:00-23:00 Uhr ist stadtweit; tagsüber kannst du ab 18:00 Uhr anrufen.",
            )
        if explicit:
            if 18 * 60 <= minutes <= 23 * 60:
                return TemporalDecision(
                    include=True,
                    boost=1,
                    note="Der Hilfebus ist täglich 18:00-23:00 Uhr im Einsatz. Warmes Essen/Suppe ist dort laut WFS nur sonntags 20:00-21:00 Uhr am Hauptbahnhof.",
                )
            return TemporalDecision(
                include=False,
                note="Der Hilfebus fährt täglich erst ab 18:00 Uhr. Die Suppenausgabe ist nur sonntags 20:00-21:00 Uhr am Hauptbahnhof.",
            )
        return TemporalDecision(include=True, boost=1)

    if offer.source_index in {13, 14}:
        if weekday == 1:
            return TemporalDecision(
                include=True,
                boost=8,
                note="Die Essens-/Getränkeausgabe am Schwanenteich ist dienstags 17:00-18:00 Uhr an der Goethestraße/Schwanenteich. Die Bürozeit in der Nürnberger Str. 37 bzw. Demmeringstr. 32 ist keine Essensausgabe.",
            )
        if explicit:
            return TemporalDecision(include=False)
        return TemporalDecision(include=True, note="Bei Schwanenteich-Angeboten ist die Ausgabe an die Standzeit gebunden, nicht an die Büroadresse.")

    if context.explicit_day and not _matches_day_for_offer(offer, weekday):
        return TemporalDecision(include=False)
    return TemporalDecision(include=True)


def _medical_decision(offer: OfferRecord, context: TemporalContext) -> TemporalDecision:
    weekday = context.effective_weekday_index
    explicit = context.explicit_day or context.nowish
    if offer.source_index == 30:
        if weekday in {2, 4, 6}:
            return TemporalDecision(
                include=True,
                boost=8,
                note="Das mobile medizinische Angebot/Medibus gilt nur an den genannten Standorten und Zeiten: Mittwoch Hauptbahnhof, Freitag Koehlerstraße/Dresdner Straße und Hauptbahnhof, Sonntag Hauptbahnhof.",
            )
        if explicit:
            return TemporalDecision(include=False)
    if offer.source_index == 15:
        if weekday in {1, 2, 3, 4}:
            return TemporalDecision(
                include=True,
                boost=5,
                note="Die mobile Alternative ist an feste Standzeiten gebunden. Nutze den Ort zur passenden Tageszeit, nicht automatisch die Büroadresse.",
            )
        if explicit:
            return TemporalDecision(include=False)
    if context.explicit_day and not _matches_day_for_offer(offer, weekday):
        return TemporalDecision(include=False)
    return TemporalDecision(include=True)


def _sleep_decision(offer: OfferRecord, context: TemporalContext) -> TemporalDecision:
    normalized_name = normalize_text(offer.name)
    minutes = context.effective_time_minutes
    if "hilfebus" in normalized_name:
        if 18 * 60 <= minutes <= 23 * 60:
            return TemporalDecision(include=True, note="Der Hilfebus ist abends zu den Einsatzzeiten 18:00-23:00 Uhr erreichbar.")
        if context.nowish:
            return TemporalDecision(include=True, note="Der Hilfebus fährt täglich 18:00-23:00 Uhr; tagsüber kannst du ab 18:00 Uhr anrufen.")
    return TemporalDecision(include=True)


def _requested_weekday(normalized: str) -> int | None:
    names = [
        ("montag", "monday"),
        ("dienstag", "dienstags", "tuesday"),
        ("mittwoch", "mittwochs", "wednesday"),
        ("donnerstag", "donnerstags", "thursday"),
        ("freitag", "freitags", "friday"),
        ("samstag", "saturday"),
        ("sonntag", "sonntags", "sunday"),
    ]
    for index, variants in enumerate(names):
        if any(variant in normalized for variant in variants):
            return index
    return None


def _requested_time_minutes(query: str) -> int | None:
    match = re.search(r"\b(\d{1,2})(?::|\.)(\d{2})\b", query)
    if not match:
        match = re.search(r"\b(?:um|gegen)\s+(\d{1,2})\s*uhr\b", query, re.IGNORECASE)
        if not match:
            return None
        hour = int(match.group(1))
        minute = 0
    else:
        hour = int(match.group(1))
        minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _matches_day_for_offer(offer: OfferRecord, weekday: int) -> bool:
    values = [*offer.opening_hours_raw, *offer.standzeiten_raw, *offer.services, *offer.notes]
    day_specific = False
    for value in values:
        normalized = normalize_text(value)
        days = _days_for_text(normalized)
        if days is None:
            continue
        day_specific = True
        if weekday in days:
            return True
    return not day_specific


def _days_for_text(normalized: str) -> set[int] | None:
    if any(term in normalized for term in ("taglich", "taeglich", "montag sonntag", "montag bis sonntag")):
        return set(range(7))
    if "montag freitag" in normalized or "montag bis freitag" in normalized:
        return set(range(5))
    if "wochenende" in normalized:
        return {5, 6}
    result: set[int] = set()
    for index, names in enumerate(
        (
            ("montag",),
            ("dienstag", "dienstags"),
            ("mittwoch", "mittwochs"),
            ("donnerstag", "donnerstags"),
            ("freitag", "freitags"),
            ("samstag",),
            ("sonntag", "sonntags"),
        )
    ):
        if any(name in normalized for name in names):
            result.add(index)
    return result or None
