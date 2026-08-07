"""Deterministische Europe/Berlin-Zeitprüfung für belegte Essensausgaben."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from .candidate_contract import FactsUsed
from .interpreter import RequestedDay


TIME_RANGE_RE = re.compile(
    r"(?P<start_h>\d{1,2})(?::(?P<start_m>\d{2}))?\s*(?:-|bis)\s*"
    r"(?P<end_h>\d{1,2})(?::(?P<end_m>\d{2}))?",
    re.IGNORECASE,
)
WEEKDAY_TOKENS = {
    0: "montag",
    1: "dienstag",
    2: "mittwoch",
    3: "donnerstag",
    4: "freitag",
    5: "samstag",
    6: "sonntag",
}
WEEKDAY_INDEX = {token: index for index, token in WEEKDAY_TOKENS.items()}
WEEKDAY_RANGE_RE = re.compile(
    rf"(?P<start>{'|'.join(WEEKDAY_INDEX)})\s*(?:-|bis)\s*(?P<end>{'|'.join(WEEKDAY_INDEX)})"
)


@dataclass(frozen=True)
class ServiceWindow:
    weekdays: frozenset[int]
    start_minute: int
    end_minute: int


SCHEDULE_WINDOWS: dict[str, tuple[ServiceWindow, ...]] = {
    "tuesday_17_18": (ServiceWindow(frozenset({1}), 17 * 60, 18 * 60),),
    "thursday_16_1730": (ServiceWindow(frozenset({3}), 16 * 60, 17 * 60 + 30),),
    "thursday_16_19": (ServiceWindow(frozenset({3}), 16 * 60, 19 * 60),),
    "sunday_20_21": (ServiceWindow(frozenset({6}), 20 * 60, 21 * 60),),
    "daily_18_23": (ServiceWindow(frozenset(range(7)), 18 * 60, 23 * 60),),
}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _weekdays(text: str) -> frozenset[int]:
    folded = _fold(text)
    if "taglich" in folded or "jeden tag" in folded:
        return frozenset(range(7))
    result = {index for index, token in WEEKDAY_TOKENS.items() if token in folded}
    for match in WEEKDAY_RANGE_RE.finditer(folded):
        start = WEEKDAY_INDEX[match.group("start")]
        end = WEEKDAY_INDEX[match.group("end")]
        cursor = start
        while True:
            result.add(cursor)
            if cursor == end:
                break
            cursor = (cursor + 1) % 7
    if "feiertag" in folded:
        # Feiertage benötigen einen Kalender und werden in 8A nicht geraten.
        result.discard(6)
    return frozenset(result)


def opening_windows(lines: list[str]) -> tuple[ServiceWindow, ...]:
    windows: list[ServiceWindow] = []
    for line in lines:
        days = _weekdays(line)
        if not days:
            continue
        if "ganztagig" in _fold(line):
            windows.append(ServiceWindow(days, 0, 24 * 60))
            continue
        for match in TIME_RANGE_RE.finditer(line):
            start = int(match.group("start_h")) * 60 + int(match.group("start_m") or 0)
            end = int(match.group("end_h")) * 60 + int(match.group("end_m") or 0)
            if 0 <= start < 24 * 60 and 0 <= end <= 24 * 60:
                windows.append(ServiceWindow(days, start, end))
    return tuple(windows)


def relevant_weekday(facts: FactsUsed, now: datetime) -> tuple[int, bool]:
    """Liefert Wochentag und ob die aktuelle Uhrzeit berücksichtigt werden muss."""

    day = facts.requested_day
    if day is None or day in {RequestedDay.TODAY, RequestedDay.TONIGHT}:
        return now.weekday(), True
    if day == RequestedDay.TOMORROW:
        return (now + timedelta(days=1)).weekday(), False
    return list(RequestedDay)[:7].index(day), False


def windows_match(windows: tuple[ServiceWindow, ...], facts: FactsUsed, now: datetime) -> bool:
    weekday, current_day = relevant_weekday(facts, now)
    relevant = [window for window in windows if weekday in window.weekdays]
    if not relevant:
        return False
    if facts.requested_time:
        hour, minute = (int(value) for value in facts.requested_time.split(":"))
        requested_minute = hour * 60 + minute
        return any(_contains(window, requested_minute) for window in relevant)
    if not current_day:
        return True
    current_minute = now.hour * 60 + now.minute
    return any(_not_finished(window, current_minute) for window in relevant)


def _contains(window: ServiceWindow, minute: int) -> bool:
    if window.end_minute > window.start_minute:
        return window.start_minute <= minute <= window.end_minute
    return minute >= window.start_minute or minute <= window.end_minute


def _not_finished(window: ServiceWindow, minute: int) -> bool:
    if window.end_minute > window.start_minute:
        return minute <= window.end_minute
    return minute >= window.start_minute or minute <= window.end_minute


def food_schedule_matches(
    schedule_rule: str | None,
    opening_hours: list[str],
    facts: FactsUsed,
    now: datetime,
) -> bool:
    """Prüft Essen gegen belegte Ausgabezeit; unbekannte Zeiten sind nicht passend."""

    windows = SCHEDULE_WINDOWS.get(schedule_rule or "") or opening_windows(opening_hours)
    return bool(windows) and windows_match(windows, facts, now)
