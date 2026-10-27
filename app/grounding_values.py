"""Presentation normalization for values; never infer or repair a contact."""

import re
import unicodedata
from decimal import Decimal


def normalize_name_typography(text: str) -> str:
    """Normalize spacing/hyphen glyphs, never letters or word boundaries."""
    return " ".join(unicodedata.normalize("NFC", text).translate(
        str.maketrans({char: "-" for char in "\u2010\u2011\ufe63\uff0d"})
    ).split())


EURO_RE = re.compile(r"(?<![\w.,+-])[+-]?\d+(?:[,.]\d{1,2})?\s*€")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d ().-]*\d(?!\w)")


def euro_amount(value: str) -> Decimal:
    return Decimal(value.removesuffix("€").strip().replace(",", "."))


def euro_values(text: str) -> set[Decimal]:
    return {euro_amount(match.group()) for match in EURO_RE.finditer(text)}


def phone_number(value: str) -> str:
    """The source's number without the separate person/operating-hours label."""
    return normalize_name_typography(value).split(" (", 1)[0]


def mask_known_phones(text: str, values: list[str]) -> tuple[str, bool]:
    """Validate complete digit sequences; do not join parts of different facts.

    Seven or more digits distinguish contacts from ordinary address/age values.
    Spaces and hyphens may vary, but country codes/extensions cannot change.
    The caller separately checks short numeric values and operating conditions.
    """
    known = {re.sub(r"\D", "", phone_number(value)) for value in values}
    normalized = normalize_name_typography(text)
    invalid = False

    def replace(match: re.Match[str]) -> str:
        nonlocal invalid
        if match.group().count("(") != match.group().count(")"):
            # 'Plautstr. 18 (04179 Leipzig)' is a house number/postcode,
            # not a phone formed by concatenating those two values.
            return match.group()
        digits = re.sub(r"\D", "", match.group())
        if len(digits) < 7:
            return match.group()
        if digits not in known:
            invalid = True
            return match.group()
        return " "

    return _PHONE_RE.sub(replace, normalized), invalid
