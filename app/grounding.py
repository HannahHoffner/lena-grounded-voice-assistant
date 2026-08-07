"""Atomare Validierung sichtbarer Formulatorausgaben gegen ein Evidence-Paket."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .formulation import (
    AnswerType,
    BindingPolicy,
    ClaimType,
    EvidenceFact,
    FactType,
    FormulatorError,
    FormulatorEvidence,
    FormulatorResponse,
)
from .interpreter import Need
from .models import Language


URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
NUMBER_RE = re.compile(r"\d+")
MONEY_RE = re.compile(r"\b\d+(?:[,.]\d{1,2})?\s*\u20ac")
ADDRESS_RE = re.compile(
    r"\b[\wÄÖÜäöüß.-]+(?:straße|str\.?|street|road|allee|weg|platz)\s+\d+[a-z]?\b",
    re.IGNORECASE,
)
HTML_OR_MARKDOWN_RE = re.compile(r"<[^>]+>|```|`|\*\*|__|\[[^\]]+\]\([^)]*\)|^\s*#{1,6}\s", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"[.!?]\s+\S")
# Kurze deutsche Abkürzungen, die vor einem Satzzeichen keinen Satzbruch bedeuten
# (z. B. "CABL e. V." oder "Nürnberger Str. 31"). Eine feste Lookbehind-Liste
# reicht nicht, da re keine unterschiedlich langen Alternativen im Lookbehind
# erlaubt; deshalb wird das vorangehende Wort separat geprüft.
_ABBREVIATION_TOKENS = {"str", "e", "v", "dr", "nr", "ca", "ggf", "bzw", "u", "a", "z", "b", "co"}


def _contains_sentence_break(text: str) -> bool:
    """Erkennt einen echten Satzbruch, ohne auf kurze Abkürzungen anzuschlagen."""
    for match in _SENTENCE_END_RE.finditer(text):
        preceding = re.search(r"([A-Za-zÄÖÜäöüß]+)$", text[: match.start()])
        token = preceding.group(1).casefold() if preceding else ""
        if token in _ABBREVIATION_TOKENS or token.endswith("str"):
            continue
        return True
    return False
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
LATIN_SCRIPT_SIGNATURES: dict[Language, re.Pattern[str]] = {
    Language.DE: re.compile(r"[\u00E4\u00F6\u00FC\u00DF]", re.IGNORECASE),
    Language.PL: re.compile(r"[\u0105\u0107\u0119\u0142\u0144\u015B\u017A\u017C]", re.IGNORECASE),
    Language.RO: re.compile(r"[\u0103\u00E2\u00EE\u0219\u015F\u021B\u0163]", re.IGNORECASE),
}
INTERNAL_TERM_RE = re.compile(
    r"\b(?:offer_id|fact_id|policy_id|candidate|selector|formulator|grounding|contract_version|OFFER_RECORDS|CANDIDATES)\b",
    re.IGNORECASE,
)
VISIBLE_ID_RE = re.compile(r"\b(?:internal\s+)?(?:offer|record|source|card)?\s*ID\s*[:#-]?\s*\d", re.IGNORECASE)
GERMAN_FORMAL_RE = re.compile(r"\b(?:Sie|Ihnen|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihres)\b")
SERVICE_ASSERTION_RE = re.compile(
    r"\b(?:essen|mahlzeit|wasser|schlaf|\u00fcbernacht|wundversorgung|medizin|behandel|toilet|dusche|hygiene|beratung|"
    r"food|meal|water|sleep|overnight|wound|medical|treat|toilet|shower|hygiene|advice|"
    r"jedzen|posi\u0142|wod|nocleg|medycz|leczen|toalet|prysznic|higien|porad|"
    r"m\u00e2ncare|mas\u0103|ap\u0103|dorm|medical|tratament|toalet|du\u0219|igien|consili|"
    r"\u0435\u0434|\u043f\u0438\u0449|\u0432\u043e\u0434|\u0441\u043f\u0430\u0442|\u043d\u043e\u0447\u043b\u0435\u0433|"
    r"\u043c\u0435\u0434\u0438\u0446|\u043b\u0435\u0447\u0435\u043d|\u0442\u0443\u0430\u043b\u0435\u0442|\u0434\u0443\u0448|"
    r"\u0433\u0438\u0433\u0438\u0435\u043d|\u043a\u043e\u043d\u0441\u0443\u043b\u044c\u0442)\w*\b",
    re.IGNORECASE,
)
# "men"/"mann" duerfen NICHT mit \w*-Suffix in der Hauptgruppe stehen, da "men" sonst
# Praefix von "Menschen" (Personen) ist und "mann" Praefix von "Mannschaft"/"Mannheim"
# waere; deshalb exakte Wortgrenze ohne Suffixerweiterung. Das bare Pronomen "man" wird
# ganz ausgeschlossen: Es ist das deutsche unpersoenliche Pronomen ("man kann sich
# melden...", "man erreicht..."), keine Geschlechts-/Zielgruppenbehauptung; das englische
# "men" (Plural) bleibt zur Erkennung von Geschlechtsbehauptungen ausreichend.
# Live reproduziert: "UVO - Umfeldnahe Versorgung von Menschen ohne festen Wohnsitz" loeste
# ueber "men" in "Menschen" faelschlich eine Zielgruppen-Behauptung aus und erzwang den
# Formulator-Fallback, obwohl der Satz nur den zitierten Angebotsnamen wiedergab.
TARGET_ASSERTION_RE = re.compile(
    r"\b(?:frau|frauen|m\u00e4nner|minderj\u00e4hr|erwachsen|jugendlich|"
    r"woman|women|minor|adult|young|"
    r"kobiet|m\u0119\u017cczy|niepe\u0142nolet|doros\u0142|m\u0142od|"
    r"femei|b\u0103rbat|minor|adult|t\u00e2n\u0103r|"
    r"\u0436\u0435\u043d\u0449\u0438\u043d|\u043c\u0443\u0436\u0447\u0438\u043d|"
    r"\u043d\u0435\u0441\u043e\u0432\u0435\u0440\u0448\u0435\u043d\u043d\u043e\u043b\u0435\u0442|"
    r"\u0432\u0437\u0440\u043e\u0441\u043b|\u043c\u043e\u043b\u043e\u0434)\w*\b"
    r"|\b(?:mann|men)\b",
    re.IGNORECASE,
)

UNSAFE_CLAIMS = (
    "freie plätze", "platz frei", "garantierte aufnahme", "jetzt geöffnet", "aktuell geöffnet",
    "nimmt dich auf", "ist für dich geeignet", "aktuelle kapazität",
    "free places", "space available", "guaranteed admission", "open now", "currently open",
    "will admit you", "suitable for you", "current capacity",
    "funktioniert gerade", "ist gerade in betrieb", "currently working", "working now",
    "wolne miejsca", "teraz otwarte", "przyjmie cię",
    "locuri libere", "deschis acum", "te primește",
    "свободные места", "сейчас открыто", "тебя примут",
)

WEEKDAYS = {
    0: {"montag", "monday", "poniedziałek", "luni", "понедельник"},
    1: {"dienstag", "tuesday", "wtorek", "marți", "вторник"},
    2: {"mittwoch", "wednesday", "środa", "miercuri", "среда"},
    3: {"donnerstag", "thursday", "czwartek", "joi", "четверг"},
    4: {"freitag", "friday", "piątek", "vineri", "пятница"},
    5: {"samstag", "saturday", "sobota", "sâmbătă", "суббота"},
    6: {"sonntag", "sunday", "niedziela", "duminică", "воскресенье"},
}

DOMAIN_BOUNDARY_ANCHORS = {
    Language.DE: (
        "nicht beantworten",
        "kann dir nicht sagen",
        "beantworte diese frage nicht",
        "beantwortet diese frage nicht",
    ),
    Language.EN: ("cannot answer", "can't answer"),
    Language.PL: ("nie mog\u0119 odpowiedzie\u0107", "nie odpowiem"),
    Language.RO: ("nu pot r\u0103spunde", "nu \u00ee\u021bi pot spune", "nu pot spune"),
    Language.RU: (
        "\u043d\u0435 \u043c\u043e\u0433\u0443 \u043e\u0442\u0432\u0435\u0442\u0438\u0442\u044c",
        "\u043d\u0435 \u043c\u043e\u0433\u0443 \u0441\u043a\u0430\u0437\u0430\u0442\u044c",
    ),
}
SUPPORTED_DOMAIN_STEMS = {
    Language.DE: ("essen", "wasser", "schlaf", "medizin", "beratung", "toilet"),
    Language.EN: ("food", "water", "sleep", "medical", "advice", "toilet"),
    Language.PL: ("jedzen", "wod", "nocleg", "medycz", "porad", "toalet"),
    Language.RO: ("m\u00e2ncare", "ap\u0103", "dorm", "medical", "consili", "toalet"),
    Language.RU: (
        "\u0435\u0434",
        "\u0432\u043e\u0434",
        "\u0441\u043f\u0430",
        "\u043d\u043e\u0447",
        "\u043c\u0435\u0434\u0438\u0446\u0438\u043d",
        "\u043a\u043e\u043d\u0441\u0443\u043b\u044c\u0442",
        "\u0442\u0443\u0430\u043b\u0435\u0442",
    ),
}
NO_RESULT_ANCHORS = {
    Language.DE: ("kein passendes angebot", "nichts passendes"),
    Language.EN: ("no matching offer", "nothing suitable"),
    Language.PL: ("brak pasuj\u0105cej oferty", "nie ma pasuj\u0105cej oferty"),
    Language.RO: ("nicio ofert\u0103 potrivit\u0103", "nu am g\u0103sit o ofert\u0103 potrivit\u0103"),
    Language.RU: (
        "\u043d\u0435\u0442 \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0435\u0433\u043e \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f",
        "\u043d\u0435 \u043d\u0430\u0448\u043b\u043e\u0441\u044c \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0435\u0433\u043e",
    ),
}


@dataclass(frozen=True, slots=True)
class ValidatedFormulation:
    answer: str
    card_ids: list[str]
    sentence_count: int
    answer_type: AnswerType


def _canonical(value: str) -> str:
    return " ".join(value.casefold().split())


def _strip_evidence_literals(text: str, evidence: FormulatorEvidence) -> str:
    stripped = text
    literals = [
        fact.value
        for offer in evidence.selected_offers
        for fact in offer.facts
        if fact.fact_type in {
            FactType.DISPLAY_NAME, FactType.ALIAS, FactType.ADDRESS, FactType.PHONE,
            FactType.EMAIL, FactType.URL, FactType.OPENING_TIME, FactType.STAND_TIME,
        }
    ]
    for literal in sorted(literals, key=len, reverse=True):
        stripped = re.sub(re.escape(literal), " ", stripped, flags=re.IGNORECASE)
    return stripped


def _validate_language(text: str, evidence: FormulatorEvidence) -> None:
    prose = _strip_evidence_literals(text, evidence)
    if evidence.requested_language == Language.RU:
        if len(CYRILLIC_RE.findall(prose)) < 2:
            raise FormulatorError("formulator_invalid_language")
    elif CYRILLIC_RE.search(prose):
        raise FormulatorError("formulator_invalid_language")
    else:
        for other_language, signature in LATIN_SCRIPT_SIGNATURES.items():
            if other_language != evidence.requested_language and signature.search(prose):
                raise FormulatorError("formulator_invalid_language")
    if INTERNAL_TERM_RE.search(prose):
        raise FormulatorError("formulator_contract_violation")
    if evidence.requested_language == Language.DE and GERMAN_FORMAL_RE.search(prose):
        raise FormulatorError("formulator_contract_violation")


def _validate_policy_answer(text: str, evidence: FormulatorEvidence) -> None:
    """Bindet angebotsfreie Modellantworten an eng begrenzte Policy-Inhalte."""
    folded = text.casefold()
    if evidence.answer_type == AnswerType.OUT_OF_SCOPE:
        anchors = DOMAIN_BOUNDARY_ANCHORS[evidence.requested_language]
        domain_stems = SUPPORTED_DOMAIN_STEMS[evidence.requested_language]
        if not any(anchor in folded for anchor in anchors):
            raise FormulatorError("formulator_ungrounded_claim")
        if sum(stem in folded for stem in domain_stems) < 3:
            raise FormulatorError("formulator_ungrounded_claim")
    elif evidence.answer_type == AnswerType.NO_VERIFIED_RESULT:
        if not any(anchor in folded for anchor in NO_RESULT_ANCHORS[evidence.requested_language]):
            raise FormulatorError("formulator_ungrounded_claim")


def _validate_operational_tokens(text: str, facts: list[EvidenceFact]) -> None:
    cited = "\n".join(fact.value for fact in facts)
    cited_folded = cited.casefold()
    for url in URL_RE.findall(text):
        if url.rstrip(".,;)") not in {item.rstrip(".,;)") for item in URL_RE.findall(cited)}:
            raise FormulatorError("formulator_ungrounded_claim")
    for email in EMAIL_RE.findall(text):
        if email.casefold() not in {item.casefold() for item in EMAIL_RE.findall(cited)}:
            raise FormulatorError("formulator_ungrounded_claim")
    for _address in ADDRESS_RE.findall(text):
        if _address not in cited:
            raise FormulatorError("formulator_ungrounded_claim")
    for time_value in TIME_RE.findall(text):
        if time_value not in TIME_RE.findall(cited):
            raise FormulatorError("formulator_ungrounded_claim")
    cited_numbers = set(NUMBER_RE.findall(cited))
    if any(number not in cited_numbers for number in NUMBER_RE.findall(text)):
        raise FormulatorError("formulator_ungrounded_claim")
    for phone in (fact.value for fact in facts if fact.fact_type == FactType.PHONE):
        groups = NUMBER_RE.findall(phone)
        text_groups = NUMBER_RE.findall(text)
        if groups and all(group in text_groups for group in groups) and phone not in text:
            raise FormulatorError("formulator_ungrounded_claim")
    cited_money = MONEY_RE.findall(cited)
    if any(value not in cited_money for value in MONEY_RE.findall(text)):
        raise FormulatorError("formulator_ungrounded_claim")
    mentioned_days = {
        day_index
        for day_index, names in WEEKDAYS.items()
        if any(re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE) for name in names)
    }
    cited_days = {
        day_index
        for day_index, names in WEEKDAYS.items()
        if any(re.search(rf"\b{re.escape(name)}\b", cited, re.IGNORECASE) for name in names)
    }
    if not mentioned_days.issubset(cited_days):
        raise FormulatorError("formulator_ungrounded_claim")
    if any(claim in text.casefold() for claim in UNSAFE_CLAIMS):
        raise FormulatorError("formulator_ungrounded_claim")
    if "€" in text and "€" not in cited_folded:
        raise FormulatorError("formulator_ungrounded_claim")


def _validate_sentence(
    sentence,
    evidence: FormulatorEvidence,
    offers_by_id: dict[str, object],
    facts_by_id: dict[str, tuple[str, EvidenceFact]],
    allowed_policies: set[BindingPolicy],
) -> str:
    text = " ".join(sentence.text.split())
    if not text or len(text.split()) > 32 or HTML_OR_MARKDOWN_RE.search(text):
        raise FormulatorError("formulator_contract_violation")
    prose_without_evidence = _strip_evidence_literals(text, evidence).strip()
    if not re.search(r"[.!?]$", text) or _contains_sentence_break(prose_without_evidence):
        raise FormulatorError("formulator_contract_violation")
    if VISIBLE_ID_RE.search(text) or any(fact_id in text for fact_id in facts_by_id):
        raise FormulatorError("formulator_contract_violation")
    if any(policy.value in text for policy in BindingPolicy):
        raise FormulatorError("formulator_contract_violation")
    if not set(sentence.policy_ids).issubset(allowed_policies):
        raise FormulatorError("formulator_invalid_fact")

    cited_facts: list[EvidenceFact] = []
    if sentence.offer_id is None:
        if sentence.claim_type not in {
            ClaimType.UNCERTAINTY, ClaimType.DOMAIN_BOUNDARY, ClaimType.NO_RESULT,
        }:
            raise FormulatorError("formulator_contract_violation")
    else:
        offer = offers_by_id.get(sentence.offer_id)
        if offer is None:
            raise FormulatorError("formulator_invalid_fact")
        for fact_id in sentence.fact_ids:
            bound = facts_by_id.get(fact_id)
            if bound is None or bound[0] != sentence.offer_id:
                raise FormulatorError("formulator_invalid_fact")
            cited_facts.append(bound[1])
        if sentence.claim_type == ClaimType.SERVICE:
            if offer.candidate_role != "direct_service" or not any(
                fact.fact_type in {FactType.SERVICE, FactType.CAPABILITY, FactType.DESCRIPTION}
                for fact in cited_facts
            ):
                raise FormulatorError("formulator_ungrounded_claim")
        if sentence.claim_type == ClaimType.REFERRAL and offer.candidate_role != "referral_contact":
            raise FormulatorError("formulator_contract_violation")
        if offer.candidate_role == "referral_contact" and sentence.claim_type in {ClaimType.ACTION, ClaimType.SERVICE}:
            raise FormulatorError("formulator_ungrounded_claim")
        if SERVICE_ASSERTION_RE.search(text) and not any(
            fact.fact_type in {FactType.SERVICE, FactType.CAPABILITY, FactType.DESCRIPTION}
            for fact in cited_facts
        ):
            raise FormulatorError("formulator_ungrounded_claim")
        if TARGET_ASSERTION_RE.search(text) and not any(
            fact.fact_type in {
                FactType.TARGET_GROUP,
                FactType.MINIMUM_AGE,
                FactType.MAXIMUM_AGE,
                FactType.ELIGIBLE_GENDER,
                FactType.ACCESS,
            }
            for fact in cited_facts
        ):
            raise FormulatorError("formulator_ungrounded_claim")
        if sentence.claim_type == ClaimType.FACT and not any(
            fact.fact_type not in {FactType.DISPLAY_NAME, FactType.ALIAS}
            for fact in cited_facts
        ):
            raise FormulatorError("formulator_ungrounded_claim")

        for candidate in evidence.selected_offers:
            naming_facts = [
                fact for fact in candidate.facts
                if fact.fact_type in {FactType.DISPLAY_NAME, FactType.ALIAS} and len(fact.value) >= 2
            ]
            mentioned = [fact for fact in naming_facts if fact.value.casefold() in text.casefold()]
            if mentioned and candidate.offer_id != sentence.offer_id:
                raise FormulatorError("formulator_invalid_fact")
            if mentioned and not {fact.fact_id for fact in mentioned}.intersection(sentence.fact_ids):
                raise FormulatorError("formulator_invalid_fact")
            if mentioned and any(fact.value not in text for fact in mentioned):
                raise FormulatorError("formulator_ungrounded_claim")

    _validate_operational_tokens(text, cited_facts)
    return text


def validate_formulation(
    response: FormulatorResponse,
    evidence: FormulatorEvidence,
) -> ValidatedFormulation:
    """Validiert die gesamte Modellantwort; es gibt keine Teilübernahme."""
    if response.language != evidence.requested_language:
        raise FormulatorError("formulator_invalid_language")
    offers_by_id = {offer.offer_id: offer for offer in evidence.selected_offers}
    facts_by_id = {
        fact.fact_id: (offer.offer_id, fact)
        for offer in evidence.selected_offers
        for fact in offer.facts
    }
    allowed_policies = {policy.policy_id for policy in evidence.binding_policies}
    if any(card_id not in offers_by_id for card_id in response.card_ids):
        raise FormulatorError("formulator_invalid_card")
    if not offers_by_id and response.card_ids:
        raise FormulatorError("formulator_invalid_card")

    texts = [
        _validate_sentence(sentence, evidence, offers_by_id, facts_by_id, allowed_policies)
        for sentence in response.sentences
    ]
    if len({_canonical(text) for text in texts}) != len(texts):
        raise FormulatorError("formulator_contract_violation")
    answer = " ".join(texts)
    if len(answer) > 600:
        raise FormulatorError("formulator_contract_violation")
    _validate_language(answer, evidence)
    _validate_policy_answer(answer, evidence)

    if evidence.need.value == "toilet" and evidence.selected_offers:
        primary = evidence.selected_offers[0]
        if response.sentences[0].offer_id != primary.offer_id:
            raise FormulatorError("formulator_contract_violation")
        fee_status = next(
            (fact for fact in primary.facts if fact.fact_type == FactType.FEE_STATUS),
            None,
        )
        if fee_status and fee_status.value == "paid":
            fee = next((fact for fact in primary.facts if fact.fact_type == FactType.FEE), None)
            cited_ids = {
                fact_id
                for sentence in response.sentences
                if sentence.offer_id == primary.offer_id
                for fact_id in sentence.fact_ids
            }
            if fee is None or fee.fact_id not in cited_ids or fee.value not in answer:
                raise FormulatorError("formulator_ungrounded_claim")

    if evidence.need == Need.DRINKING_WATER and evidence.selected_offers:
        primary = evidence.selected_offers[0]
        if response.sentences[0].offer_id != primary.offer_id:
            raise FormulatorError("formulator_contract_violation")
        primary_names = [
            fact
            for fact in primary.facts
            if fact.fact_type == FactType.DISPLAY_NAME
        ]
        first_sentence = response.sentences[0]
        if not primary_names or not any(
            fact.fact_id in first_sentence.fact_ids and fact.value in first_sentence.text
            for fact in primary_names
        ):
            raise FormulatorError("formulator_ungrounded_claim")

    first_claim = response.sentences[0].claim_type
    expected_first = {
        AnswerType.GROUNDED_RESULT: {ClaimType.ACTION, ClaimType.SERVICE},
        AnswerType.GROUNDED_REFERRAL: {ClaimType.REFERRAL},
        AnswerType.AMBIGUOUS_HELP_FALLBACK: {ClaimType.REFERRAL},
        AnswerType.OUT_OF_SCOPE: {ClaimType.DOMAIN_BOUNDARY},
        AnswerType.NO_VERIFIED_RESULT: {ClaimType.NO_RESULT},
    }.get(evidence.answer_type)
    if expected_first and first_claim not in expected_first:
        raise FormulatorError("formulator_contract_violation")

    referenced = {sentence.offer_id for sentence in response.sentences if sentence.offer_id}
    required_cards = {
        offer.offer_id for offer in evidence.selected_offers if offer.mandatory
    } | referenced | set(response.card_ids)
    card_ids = [offer.offer_id for offer in evidence.selected_offers if offer.offer_id in required_cards]
    return ValidatedFormulation(
        answer=answer,
        card_ids=card_ids,
        sentence_count=len(response.sentences),
        answer_type=evidence.answer_type,
    )
