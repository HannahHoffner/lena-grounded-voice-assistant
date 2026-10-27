"""Check literal clock windows and their local day/place scope, not word lists."""

import re

from .grounding_claims import Fact, WEEKDAY_NAMES, transliterated
from .grounding_constraints import stated_weekdays
from .grounding_values import normalize_name_typography
from .models import Language

_CLOCK = r"\b\d{1,2}:\d{2}\b"
_WINDOW = re.compile(rf"({_CLOCK})\s*(?:[-–—]|bis|to|do|până la|pana la|до|a)\s*({_CLOCK})", re.I)
_PLACE_AFTER_CLOCK = re.compile(
    rf"{_CLOCK}\s*(?:(?:Uhr|o'clock|ч\.|godz\.)\s+|(?:at|in|am|bei|na|w|la|на|в)\s+)"
    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß.-]+)"
)


def _source_days(value: str, requested: Language) -> set[int]:
    days = stated_weekdays(value, requested)
    if days:
        return days
    # Infrastructure evidence can keep German labels even for an EN answer.
    # Require a full weekday word before trying another source language; a
    # Polish 'do' by itself must never become the German abbreviation for Thu.
    for language in (Language.DE, Language.EN):
        if any(transliterated(day) in transliterated(value) for day in WEEKDAY_NAMES[language]):
            return stated_weekdays(value, language)
    return set()


def fact_schedule_matches(text: str, facts: list[Fact], language: Language) -> bool:
    """Validate each stated window separately against this offer's facts.

    Postal windows may be source notes. Contact or service wording does not
    need to belong to a closed vocabulary. An explicit unbacked place remains
    invalid, as do a reversed interval and a day borrowed from another window.
    """
    text = normalize_name_typography(text)
    schedules = [normalize_name_typography(value) for kind, value in facts
                 if kind in {"opening_time", "stand_time", "service_condition", "service", "note"}
                 and re.search(_CLOCK, value)]
    all_values = " ".join(normalize_name_typography(value) for _, value in facts)
    for match in _PLACE_AFTER_CLOCK.finditer(text):
        place = match[1].rstrip(".,-")
        if not re.search(rf"(?<!\w){re.escape(place)}(?!\w)", all_values, re.I):
            return False
    windows = list(_WINDOW.finditer(text))
    covered = {position for match in windows for position in range(match.start(), match.end())}
    units = [(m.start(), m.end(), [m[1], m[2]]) for m in windows]
    units += [(m.start(), m.end(), [m.group()]) for m in re.finditer(_CLOCK, text)
              if m.start() not in covered]
    previous = 0
    for start, end, times in sorted(units):
        prefix = text[previous:start]
        # A new sentence has its own local day scope, not a prior service's day.
        prefix = re.split(r"[;.!?]", prefix)[-1]
        days = stated_weekdays(prefix, language)
        candidates = [value for value in schedules
                      if (times == re.findall(_CLOCK, value) if len(times) > 1
                          else times[0] in re.findall(_CLOCK, value))]
        if not any(not days or days <= _source_days(value, language) for value in candidates):
            return False
        previous = end
    return True
