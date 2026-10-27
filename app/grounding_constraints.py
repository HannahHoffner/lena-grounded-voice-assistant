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
    detect_service_concepts,
)
from .models import Language
from .grounding_values import normalize_name_typography, EURO_RE, euro_amount, mask_known_phones


_FEE_WORDS = {
    Language.DE: (r"\b(?:kostenlos|kostenfrei|gratis)\b", r"\bkostenpflichtig\b"),
    Language.EN: (r"\b(?:free|no charge)\b", r"\b(?:paid|costs money)\b"),
    Language.PL: (r"\b(?:bezp[łl]atn\w*|darmow\w*)\b", r"\bp[łl]atn\w*\b"),
    Language.RO: (r"\b(?:gratuit\w*|gratis|fara plata)\b", r"\b(?:contra cost|cu plata)\b"),
    Language.RU: (r"\bbesplatn\w*\b", r"\bplatn\w*\b"),
}
_PAYMENT_WORDS = {
    Language.DE: (r"\b(?:bar|bargeld)\b", r"\b(?:karte|kartenzahlung)\b", r"\bnur\b"),
    Language.EN: (r"\bcash\b", r"\bcard\b", r"\bonly\b"),
    Language.PL: (r"\bgotow\w*\b", r"\bkart\w*\b", r"\btylko\b"),
    Language.RO: (r"\bnumerar\b", r"\bcard\w*\b", r"\b(?:doar|numai)\b"),
    Language.RU: (r"\bnalich\w*\b", r"\bkart\w*\b", r"\btolko\b"),
}
_PAYMENT_CONTEXT = {
    Language.DE: r"\b(?:zahl\w*|bezah\w*|kost\w*|entgelt|gebuhr\w*|bar|bargeld|akzeptier\w*)\b",
    Language.EN: r"\b(?:pay\w*|cash|fee|cost\w*|charge|accepted)\b|\bcard only\b",
    Language.PL: r"\b(?:p[łl]ac\w*|op[łl]at\w*|koszt\w*|gotow\w*)\b",
    Language.RO: r"\b(?:plat\w*|cost|tax\w*|numerar)\b",
    Language.RU: r"\b(?:oplat\w*|plat\w*|nalich\w*|stoit)\b",
}


def fee_or_payment_word(word: str, language: Language) -> bool:
    """True for a single transliterated word that ``fee_claim_matches`` evaluates."""
    patterns = (*_FEE_WORDS[language], *_PAYMENT_WORDS[language], _PAYMENT_CONTEXT[language])
    return any(re.fullmatch(pattern.replace(r"\b", ""), word) for pattern in patterns)


def fee_claim_matches(text: str, facts: Sequence[Fact], language: Language) -> bool:
    """Omitted fees are fine; explicit free/paid claims require that status."""
    status = next((value for kind, value in facts if kind == "fee_status"), None)
    if status is None:
        return True  # Other service prices keep their independent checks.
    normalized = transliterated(text)
    if language == Language.EN and any(
        kind == "facility" and transliterated(value).strip() == "barrier-free"
        for kind, value in facts
    ):
        normalized = re.sub(r"\bbarrier[-\s]free\b", " ", normalized)
    free, paid = _FEE_WORDS[language]
    if ((re.search(free, normalized) and status != "free")
            or (re.search(paid, normalized) and status != "paid")):
        return False
    supplied = transliterated(" ".join(value for kind, value in facts if kind == "fee"))
    cash, card, only = _PAYMENT_WORDS[language]
    claimed = {i for i, pattern in enumerate((cash, card))
               if re.search(_PAYMENT_CONTEXT[language], normalized) and re.search(pattern, normalized)}
    available = {i for i, pattern in enumerate((cash, card)) if re.search(pattern, supplied)}
    return claimed <= available and not (claimed and re.search(only, normalized) and claimed != available)


_OPERATIONAL_WORDS = {
    Language.DE: "der die das er sie es bus fahrt einsatzzeiten einsatz geoffnet offnungszeiten offnungszeit ist sind von bis um uhr taglich telefon telefonnummer ruf an adresse am im in und oder mo di mi do fr sa so",
    Language.EN: "the it is are bus operates daily from to at opening hours time phone call address and or documented",
    Language.PL: "jest sa autobus codziennie od do godziny otwarcia telefon zadzwon adres i lub",
    Language.RO: "este sunt autobuz zilnic de la pana ora program telefon adresa si sau contra cost poti plati cu cardul",
    Language.RU: "avtobus ezhednevno s do chasy raboty telefon adres i ili pozvoni po telefonu esche raz",
}

# Öffentliche, unveränderliche Sicht derselben neutralen Beschriftungen für die
# claimtypunabhängige Inhaltsprüfung (grounding_content), ohne zweite Liste.
OPERATIONAL_LABEL_WORDS: dict[Language, frozenset[str]] = {
    language: frozenset(words.split()) for language, words in _OPERATIONAL_WORDS.items()
}


def supported_operational_statement(text: str, facts: Sequence[Fact], language: Language) -> bool:
    """Accept a mislabelled operational block only within a bounded vocabulary.

    All remaining words must come from supplied operational facts or neutral
    labels. Each clock clause must match one window with its day/time order;
    words elsewhere cannot justify a reversed interval or an invented place.
    Unknown services and negation are not neutral labels.
    """
    normalized = transliterated(text)
    operational = [(kind, value) for kind, value in facts
                   if kind in {"opening_time", "stand_time", "service_condition", "phone", "address", "email", "url", "fee", "fee_status"}]
    allowed = set(_OPERATIONAL_WORDS[language].split()) | {
        word for _, value in operational for word in re.findall(r"\w+", transliterated(value))
    }
    words = set(re.findall(r"\w+", normalized))
    if not words or not words <= allowed:
        return False
    clock_clauses = [clause for clause in re.split(r"[,;.!?]", text) if re.search(r"\d{1,2}:\d{2}", clause)]
    if clock_clauses:
        return all(any(
            kind in {"opening_time", "stand_time", "service_condition"}
            and schedule_matches(clause, normalize_name_typography(value).replace(": ", " "), language, complete=False)
            for kind, value in operational
        ) for clause in clock_clauses)
    return any(value.casefold() in text.casefold() for kind, value in operational) or any(
        kind == "fee" and re.search(r"\d", value)
        and set(re.findall(r"\d+", value)) <= set(re.findall(r"\d+", text))
        for kind, value in operational
    )


_PRICE = EURO_RE
_PRICE_CLAUSE = re.compile(r"\b(?:und|and|oraz|si|i)\b|[;.!?]")
_LAUNDRY = {
    Language.DE: r"\bwasche", Language.EN: r"\blaundr",
    Language.PL: r"\bpran", Language.RO: r"\b(?:rufe|spalat)",
    Language.RU: r"\bstirk",
}


def contains_fee_literal(text: str, literal: str) -> bool:
    """Allow parentheses/non-decimal commas, preserving the complete fee wording.

    No amount, currency, or payment term is inferred or omitted. Decimal commas
    stay intact; a whole literal cannot match inside a larger/decimal amount.
    """
    def presentation(value: str) -> str:
        return " ".join(re.sub(r"[()]|(?<!\d),|,(?!\d)", " ", value.casefold()).split())

    fee = presentation(literal)
    return bool(fee and re.search(rf"(?<![\w.,]){re.escape(fee)}(?!\w)", presentation(text)))


def price_services_match(text: str, facts: Sequence[Fact], language: Language) -> bool:
    """Bind recognized service/price pairs; a number elsewhere is not support.

    This is a bounded check for euro amounts and the existing service vocabulary
    plus laundry. Unrecognized grammar is not a semantic-entailment guarantee.
    """
    def concepts(value: str, languages: Sequence[Language]) -> set[str]:
        found: set[str] = set()
        for lang in languages:
            found |= detect_service_concepts(value, lang)
            if re.search(_LAUNDRY[lang], transliterated(value)):
                found.add("laundry")
        return found

    prices = list(_PRICE.finditer(text))
    for index, price in enumerate(prices):
        before = text[prices[index - 1].end() if index else 0:price.start()]
        after = text[price.end():prices[index + 1].start() if index + 1 < len(prices) else len(text)]
        clause = _PRICE_CLAUSE.split(transliterated(before))[-1] + " " + _PRICE_CLAUSE.split(transliterated(after))[0]
        stated = concepts(clause, (language,))
        amount = euro_amount(price.group())
        matching = [(kind, value) for kind, value in facts
                    if amount in {euro_amount(m.group()) for m in _PRICE.finditer(value)}]
        if not matching:
            return False
        if stated and not any(
            kind == "fee" or stated.issubset(concepts(value, (language, Language.DE, Language.EN)))
            for kind, value in matching
        ):
            return False
    return True


# Patterns describe age bounds, not arbitrary numbers (phone/address/time).
# Values are inclusive integer ages after interpreting the comparison.
_AGE_PATTERNS = {
    Language.DE: ((r"\bunter (\d+)\b", "lt"), (r"\bab (\d+)\b", "ge"),
                  (r"\buber (\d+)\b", "gt"), (r"\bbis (\d+) jah", "le")),
    Language.EN: ((r"\bunder (\d+)\b", "lt"), (r"\bover (\d+)\b", "gt"),
                  (r"\b(?:from age |at least )(\d+)\b", "ge"),
                  (r"\b(\d+) (?:and |or )?(?:over|older)\b", "ge"),
                  (r"\bup to (\d+)\b", "le")),
    Language.PL: ((r"\bponizej (\d+)\b", "lt"), (r"\bod (\d+)(?=\s+(?:lat|do\b))", "ge"),
                  (r"\bpowyzej (\d+)\b", "gt"), (r"\bdo (\d+) lat", "le")),
    Language.RO: ((r"\bsub (\d+)\b", "lt"), (r"\bde la (\d+)\b", "ge"),
                  (r"\bpeste (\d+)\b", "gt"), (r"\bpana la (\d+)\b", "le")),
    Language.RU: ((r"\bmladshe (\d+)\b", "lt"), (r"\bot (\d+) let", "ge"),
                  (r"\bstarshe (\d+)\b", "gt"), (r"\bdo (\d+) let", "lt")),
}

_AGE_RANGES = {
    Language.DE: r"\b(?:alter\s*|von\s+|zwischen\s+)(\d+)\s*(?:-|bis|und)\s*(\d+)(?:\s+jah\w*)?\b",
    Language.EN: r"\b(?:aged?|ages?|between)\s+(\d+)\s*(?:-|to|and)\s*(\d+)\b",
    Language.PL: r"\bod\s+(\d+)\s+do\s+(\d+)\s+lat\b",
    Language.RO: r"\bintre\s+(\d+)\s*(?:-|si)\s*(\d+)\s+ani\b",
    Language.RU: r"\bot\s+(\d+)\s+do\s+(\d+)\s+let\b",
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
    # A contact instruction such as 'unter 0341 ...' is not an age bound.
    without_phones, _ = mask_known_phones(text, [value for kind, value in facts if kind == "phone"])
    normalized = transliterated(without_phones)
    for match in re.finditer(_AGE_RANGES[language], normalized):
        a, b = int(match[1]), int(match[2])
        if not lower <= a <= b <= upper:
            return True
        stated_lower, stated_upper = a, b
    normalized = re.sub(_AGE_RANGES[language], " ", normalized)
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

_SERVICE_COORDINATORS = {
    Language.DE: r"und",
    Language.EN: r"and",
    Language.PL: r"i|oraz",
    Language.RO: r"si",
    Language.RU: r"i",
}


def service_text_without_cited_audience(text: str, facts: Sequence[Fact], language: Language) -> str:
    """Separate a verbatim evidenced audience qualifier from a service claim.

    Counselling *for people without healthcare* is positive counselling, not
    absent counselling (nor a promise of healthcare). Only a complete supplied
    qualifier is masked, ending at punctuation. A coordinator alone is not a
    boundary: it can join two things the audience lacks. A supplied qualifier may
    end before a coordinator only when the entire suffix is a separately supplied,
    non-negated service value. That service and all other negation stay visible.
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
        services = {
            transliterated(value).lstrip("> ").rstrip(" .;!?")
            for kind, value in facts
            if kind == "service"
            and not any(has_negation(value, candidate) for candidate in (lang, Language.DE, Language.EN))
        }

        def mask(match: re.Match[str]) -> str:
            phrase = match.group().strip()
            if phrase in qualifiers:
                return " "
            # Longest first; never consume an extra, uncited audience condition.
            for qualifier in sorted(qualifiers, key=len, reverse=True):
                if not phrase.startswith(qualifier + " "):
                    continue
                suffix = phrase[len(qualifier):].lstrip()
                continuation = re.fullmatch(rf"(?:{_SERVICE_COORDINATORS[lang]})\s+(.+)", suffix)
                if continuation and continuation.group(1) in services:
                    return " " + suffix
            return match.group()

        normalized = pattern.sub(mask, normalized)
    return normalized


def service_text_without_cited_qualifiers(text: str, facts: Sequence[Fact], language: Language) -> str:
    """Scope out evidenced audience/facility qualifiers, never arbitrary negation.

    Polish ``bez barier`` qualifies accessibility, not absence of toilets.
    Mask only the complete supplied facility value. An immediately coordinated
    continuation may share ``bez`` (without barriers AND toilets), so remains
    conservatively unmasked. This projection is internal, not output text.
    """
    normalized = service_text_without_cited_audience(text, facts, language)
    qualifier = {Language.PL: "bez barier", Language.RO: "fara bariere", Language.RU: "bez barerov"}.get(language)
    if qualifier and any(
        kind == "facility" and transliterated(value).strip() == qualifier
        for kind, value in facts
    ):
        normalized = re.sub(rf"\b{qualifier}\b(?=\s*(?:[,;.!?]|$))", " ", normalized)
    if language == Language.RO and ("target_group", "people_experiencing_homelessness") in facts:
        if ("eligible_gender", "female") in facts or ("target_group", "women") in facts:
            normalized = re.sub(r"\b(femei(?: adulte)?) fara adapost(?=\s*(?:[,;.!?]|$))", r"\1", normalized)
    return normalized


def stated_weekdays(text: str, language: Language) -> set[int]:
    normalized = transliterated(normalize_name_typography(text))
    daily = (DAILY_LABEL[language], {
        Language.DE: "jeden Tag", Language.EN: "every day",
        Language.PL: "każdego dnia", Language.RO: "în fiecare zi",
        Language.RU: "каждый день",
    }[language])
    if any(transliterated(label) in normalized for label in daily):
        return set(range(7))
    labels = {transliterated(label): day for day, label in enumerate(WEEKDAY_NAMES[language])}
    # Preserve the earlier full-name stem recognition (montags, Mondays, ...).
    # Word boundaries belong only to short forms such as Mo/So, not inflections.
    found = {day for label, day in labels.items() if label in normalized}
    if language in {Language.DE, Language.EN}:
        short_names = (("mo", "di", "mi", "do", "fr", "sa", "so") if language == Language.DE
                       else ("mon", "tue", "wed", "thu", "fri", "sat", "sun"))
        abbreviations = {label: day for day, label in enumerate(short_names)}
        found.update(day for label, day in abbreviations.items() if re.search(rf"\b{label}\b", normalized))
        labels.update(abbreviations)
    tokens = "|".join(sorted(labels, key=len, reverse=True))
    inflection = "s?" if language in {Language.DE, Language.EN} else ""
    for match in re.finditer(rf"\b({tokens}){inflection}\.?\s*(?:-|bis|to|do)\s*({tokens}){inflection}\b", normalized):
        start, end = labels[match[1]], labels[match[2]]
        found.update((start + step) % 7 for step in range((end - start) % 7 + 1))
    return found


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
