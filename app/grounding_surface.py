"""Bounded place, language and policy checks without changing visible prose."""

import re

from .grounding_claims import Fact, transliterated
from .grounding_values import normalize_name_typography
from .models import Language

_STREET = re.compile(r"\b[\wÄÖÜäöüß.-]+\s*(?:straße|str\.?|allee|weg|platz)\b(?:\s+\d+[a-z]?)?", re.I)
_LOCATIVE = r"(?:at|in|im|bei|w|we|la|în|в|на)\s+(?:the\s+)?[„\"'«]?"


def mask_evidenced_places(text: str, values: list[str]) -> str:
    """Mask street literals found inside source notes, not arbitrary prose."""
    normalized = normalize_name_typography(text)
    places = {match.group() for value in values
              for match in _STREET.finditer(normalize_name_typography(value))}
    for place in sorted(places, key=len, reverse=True):
        normalized = re.sub(rf"(?<!\w){re.escape(place)}(?!\w)", " ", normalized, flags=re.I)
    return normalized


def evidenced_venue(text: str, name: str, facts: list[Fact]) -> bool:
    """Another offer's name is allowed only as this offer's sourced venue."""
    name = normalize_name_typography(name)
    pattern = rf"(?<!\w){_LOCATIVE}{re.escape(name)}(?!\w)"
    if not re.search(pattern, normalize_name_typography(text), re.I):
        return False
    return any(kind in {"note", "service", "stand_time", "opening_time", "address"}
               and re.search(pattern, normalize_name_typography(value), re.I)
               for kind, value in facts)


_FOREIGN_PROSE = {
    Language.DE: r"\b(?:du (?:kannst|bekommst|erhältst)|(?:ruf|melde|wende) (?:du |dich )?|sie (?:bieten|sind)|es gibt)\b",
    Language.EN: r"\b(?:you (?:can|will|receive)|(?:they|it) (?:offer|offers|provide|provides|is|are))\b",
    Language.PL: r"\b(?:możesz|skontaktuj się|oferuje|zadzwoń)\b",
    Language.RO: r"\b(?:poți|poţi|oferă|contactează|sună)\b",
    Language.RU: r"[\u0400-\u04FF]{2,}",
}


def has_foreign_prose(prose: str, requested: Language) -> bool:
    """Catch clear foreign clauses, including ASCII German in an EN answer."""
    return any(language != requested and re.search(pattern, prose, re.I)
               for language, pattern in _FOREIGN_PROSE.items())


def normalized_policy_text(text: str) -> str:
    return " ".join(text.casefold().replace("’", "'").replace("‘", "'").split())


def german_boundary(text: str) -> bool:
    return bool(re.search(r"\b(?:ich )?kann (?:ich )?dir (?:dabei |hier |leider )*nicht (?:helfen|weiterhelfen)\b",
                          normalized_policy_text(text)))


_OPERATING_RESTRICTION = (
    r"\b(?:zu|wahrend) (?:den |der )?einsatzzeiten\b|\bnur zu einsatzzeiten\b|"
    r"\bduring (?:the |its )?(?:deployment|operating|service) (?:times|hours)\b|"
    r"\bw (?:godzinach|czasie) (?:ich )?(?:pracy|dyzuru|dzia[łl]a(?:nia|n))\b|"
    r"\bin timpul (?:orelor de interventie|programului|orelor de functionare)\b|"
    r"\bv (?:ih )?chasy (?:ih )?raboty\b"
)


def operating_restriction_present(text: str) -> bool:
    normalized = transliterated(text)
    if re.search(r"\b(?:not during|outside|nicht wahrend|ausserhalb|poza godzinami|nie (?:tylko )?w (?:godzinach|czasie)|in afara|vne chasov)\b", normalized):
        return False
    return bool(re.search(_OPERATING_RESTRICTION, normalized))


def mask_status_uncertainty(text: str, language: Language) -> str:
    """Remove only a complete parenthetical status-unknown statement.

    No outside clause, service assertion or personal receipt is hidden. A bare
    'unknown' elsewhere never exempts a current-availability promise.
    """
    phrases = {
        Language.DE: r"(?:aktueller |aktueller betriebs)?status (?:ist )?unbekannt",
        Language.EN: r"(?:current |current operating )?status (?:is )?unknown",
        Language.PL: r"(?:aktualny )?status (?:jest )?nieznany",
        Language.RO: r"(?:status(?:ul)? (?:actual )?(?:este )?necunoscut)",
        Language.RU: r"(?:tekuschiy )?status (?:neizvesten|neizvestno)",
    }
    # A parenthesis can include a sourced seasonal qualifier before the status.
    pattern = rf"(?<=[,(;])\s*{phrases[language]}\s*(?=[);])"
    return re.sub(pattern, " ", transliterated(text))
