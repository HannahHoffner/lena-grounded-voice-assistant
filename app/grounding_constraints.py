"""Bounded relational checks, not natural-language entailment.

The caller supplies authoritative facts. These helpers preserve direction and
polarity that a bag of concepts or numbers necessarily loses. Unrecognized
grammar remains outside their coverage; it is never proof of truth.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .grounding_claims import (
    DAILY_LABEL, WEEKDAY_NAMES, TARGET_SUPPORT_TEXT_FACT_TYPES, Fact, transliterated,
)
from .models import Language


# Patterns describe age bounds, not arbitrary numbers (phone/address/time).
# Values are inclusive integer ages after interpreting the comparison.
_AGE_PATTERNS = {
    Language.DE: ((r"\bunter (\d+)\b", "lt"), (r"\bab (\d+)\b", "ge"),
                  (r"\buber (\d+)\b", "gt"), (r"\bbis (\d+) jah", "le")),
    Language.EN: ((r"\bunder (\d+)\b", "lt"), (r"\bover (\d+)\b", "gt"),
                  (r"\b(?:from age |at least )(\d+)\b", "ge"),
                  (r"\b(\d+) (?:and |or )?(?:over|older)\b", "ge"),
                  (r"\bup to (\d+)\b", "le")),
    Language.PL: ((r"\bponizej (\d+)\b", "lt"), (r"\bod (\d+) lat", "ge"),
                  (r"\bpowyzej (\d+)\b", "gt"), (r"\bdo (\d+) lat", "le")),
    Language.RO: ((r"\bsub (\d+)\b", "lt"), (r"\bde la (\d+)\b", "ge"),
                  (r"\bpeste (\d+)\b", "gt"), (r"\bpana la (\d+)\b", "le")),
    Language.RU: ((r"\bmladshe (\d+)\b", "lt"), (r"\bot (\d+) let", "ge"),
                  (r"\bstarshe (\d+)\b", "gt"), (r"\bdo (\d+) let", "lt")),
}


def contradicts_age_bound(text: str, facts: Sequence[Fact], language: Language) -> bool:
    """Detect a stated age range that includes people outside curated bounds."""
    bounds = {kind: int(value) for kind, value in facts
              if kind in {"minimum_age", "maximum_age"} and value.isdigit()}
    if not bounds:
        return False
    lower, upper = bounds.get("minimum_age", 0), bounds.get("maximum_age", 150)
    stated_lower: int | None = None
    stated_upper: int | None = None
    normalized = transliterated(text)
    for pattern, relation in _AGE_PATTERNS.get(language, ()):
        for match in re.finditer(pattern, normalized):
            if normalized[match.end(1):].startswith(":"):
                continue  # "ab 17:00" is a clock time, not a minimum age.
            value = int(match.group(1))
            if relation in {"ge", "gt"}:
                stated_lower = max(stated_lower or 0, value + (relation == "gt"))
            else:
                stated_upper = min(stated_upper if stated_upper is not None else 150,
                                   value - (relation == "lt"))
    # A lower bound need not repeat a separate upper bound. An upper-only
    # eligibility statement, however, includes children unless bounded below.
    if stated_lower is not None and not lower <= stated_lower <= upper:
        return True
    if stated_upper is not None:
        return (not lower <= stated_upper <= upper
                or (stated_lower is None and lower > 0)
                or (stated_lower is not None and stated_lower > stated_upper))
    return False


_NEGATIONS = {
    Language.DE: r"\b(?:nicht|kein\w*)\b",
    Language.EN: r"\b(?:not|no|never|doesn['’]t|isn['’]t|cannot|can['’]t)\b",
    Language.PL: r"\b(?:nie|bez)\b",
    Language.RO: r"\b(?:nu|fara)\b",
    Language.RU: r"\b(?:ne|net|bez)\b",
}


def has_negation(text: str, language: Language) -> bool:
    """Flag polarity needing evidence; do not infer that every negation is false."""
    return bool(re.search(_NEGATIONS[language], transliterated(text)))


_AUDIENCE_WITHOUT = {
    Language.DE: r"(?:personen|menschen) ohne",
    Language.EN: r"(?:people|persons) without",
    Language.PL: r"(?:osob\w*|ludzi) bez",
    Language.RO: r"persoane(?:le)? fara",
    Language.RU: r"(?:lyudey|lyudi|lyudyam) bez",
}


def service_text_without_cited_audience(text: str, facts: Sequence[Fact], language: Language) -> str:
    """Separate a verbatim evidenced audience qualifier from a service claim.

    Counselling *for people without healthcare* is positive counselling, not
    absent counselling (nor a promise of healthcare). Only a complete cited
    qualifier is masked, ending at punctuation. Do not split at "and": it can
    coordinate two things the audience lacks, not two services being offered.
    Unmatched wording and every negation outside that span remain visible.
    Returned text is normalized only for internal lexical checks, never output.
    """
    normalized = transliterated(text)
    for lang in dict.fromkeys((language, Language.DE, Language.EN)):
        pattern = re.compile(rf"\b{_AUDIENCE_WITHOUT[lang]}\b[^,;.!?]*")
        qualifiers = {
            match.group().strip()
            for kind, value in facts
            if kind in TARGET_SUPPORT_TEXT_FACT_TYPES | {"target_group"}
            for match in pattern.finditer(transliterated(value))
        }
        normalized = pattern.sub(
            lambda match: " " if match.group().strip() in qualifiers else match.group(), normalized,
        )
    return normalized


def stated_weekdays(text: str, language: Language) -> set[int]:
    normalized = transliterated(text)
    daily = (DAILY_LABEL[language], {
        Language.DE: "jeden Tag", Language.EN: "every day",
        Language.PL: "każdego dnia", Language.RO: "în fiecare zi",
        Language.RU: "каждый день",
    }[language])
    if any(transliterated(label) in normalized for label in daily):
        return set(range(7))
    return {day for day, label in enumerate(WEEKDAY_NAMES[language])
            if transliterated(label) in normalized}


_TIMES = re.compile(r"\b\d{1,2}:\d{2}\b")


def schedule_matches(text: str, condition: str, language: Language, *, complete: bool) -> bool:
    """Compare day scope and ordered clock values with one projected condition.

    Multiple windows are checked individually, never by merging their tokens.
    Unspecified days are tolerated for general descriptions, not for personal
    receipt claims. A single time is conservatively not treated as an interval.
    """
    days = stated_weekdays(text, language)
    times = _TIMES.findall(text)
    windows = condition.split(": ", 1)[-1].split(";")
    for window in windows:
        expected_days = stated_weekdays(window, language)
        expected_times = _TIMES.findall(window)
        if days and not days.issubset(expected_days):
            continue
        if times and times != expected_times:
            continue
        if complete and (not days or times != expected_times):
            continue
        return True
    return False
