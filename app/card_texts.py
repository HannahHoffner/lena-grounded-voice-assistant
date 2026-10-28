"""Closed display translations for operational card prose, never source facts."""

from functools import lru_cache
import re

from .application_texts import application_text, load_application_texts
from .models import Language
from .translation_contract import LinguisticReviewStatus, TranslationRuntimePolicy
from .translation_tokens import PROTECTED_TOKEN_RE


@lru_cache(maxsize=1)
def _source_ids() -> dict[str, str]:
    texts = load_application_texts().languages[Language.DE].texts
    return {value: key for key, value in texts.items() if key.startswith("card.literal.")}


def localize_card_text(
    value: str, language: Language,
    policy: TranslationRuntimePolicy = TranslationRuntimePolicy.REVIEWED_OR_MACHINE,
) -> str:
    """Translate known annotations; retain unknown text and every numeric literal.

    Exact source matches deliberately avoid general substitutions inside names
    or addresses. Callers must not pass name/address identity fields here.
    """
    if language == Language.DE or policy == TranslationRuntimePolicy.SOURCE_LANGUAGE_FALLBACK:
        return value
    inventory = load_application_texts().languages[language]
    if policy == TranslationRuntimePolicy.REVIEWED_ONLY and inventory.linguistic_review_status != LinguisticReviewStatus.REVIEWED:
        return value
    prefix = re.match(r"^>\s*", value)
    core = value[prefix.end():] if prefix else value
    key = _source_ids().get(core)
    translated = application_text(language, key) if key else core
    if not key and (phone := re.fullmatch(r"([+\d][\d ()/-]*\d) \(([^)]+)\)", core)):
        number, annotation = phone.groups()
        if annotation == "nur zu Einsatzzeiten des Busses":
            annotation = application_text(language, "card.phone.operating_only")
        elif annotation == "Allgemein":
            annotation = application_text(language, "card.phone.general")
        elif title := re.fullmatch(r"(Herr|Frau) (.+)", annotation):
            annotation = application_text(language, "card.phone.mr" if title[1] == "Herr" else "card.phone.ms", name=title[2])
        translated = f"{number} ({annotation})"
    result = (prefix.group() if prefix else "") + translated
    # Bad resource edits must never change operational numbers, URLs or emails.
    if PROTECTED_TOKEN_RE.findall(value) != PROTECTED_TOKEN_RE.findall(result):
        raise RuntimeError("card_translation_literal_mismatch")
    return result
