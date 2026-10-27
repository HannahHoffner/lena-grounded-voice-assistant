"""Atomare Validierung sichtbarer Formulatorausgaben gegen ein Evidence-Paket."""

from __future__ import annotations

import re
from dataclasses import dataclass
from .answer_plan import FormulatorPlan, render_answer_plan

from .formulation import (
    AnswerType,
    BindingPolicy,
    ClaimType,
    EvidenceFact,
    FactType,
    FormulatorError,
    FormulatorEvidence,
    FormulatorResponse,
    GroundingDiagnosticCode,
)
from .grounding_claims import (
    ClaimSupport,
    CONCEPT_CAPABILITIES,
    assess_service_claim,
    assess_target_claim,
    claims_admission,
    claims_current_availability,
    claims_personal_receipt,
    claims_suitability,
    condition_capability,
    detect_service_concepts,
    supported_service_concepts,
)
from .interpreter import Need
from .grounding_constraints import (
    contradicts_age_bound, has_negation, schedule_matches, service_text_without_cited_qualifiers,
    price_services_match, fee_claim_matches, normalize_name_typography,
    supported_operational_statement,
)
from .models import Language
from .grounding_references import resolve_offer_evidence
from .policy_facts import EMERGENCY_NUMBER
from .grounding_values import EURO_RE, euro_values, mask_known_phones, phone_number
from .grounding_surface import (
    evidenced_venue, german_boundary, has_foreign_prose, mask_evidenced_places,
    mask_status_uncertainty, normalized_policy_text, operating_restriction_present,
)
from .grounding_schedules import fact_schedule_matches


GROUNDING_VALIDATOR_VERSION = "10"

URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
NUMBER_RE = re.compile(r"\d+")
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
        # Unlike a general abbreviation exception, this cannot consume a new
        # prose sentence after "tel."; a following number must still pass the
        # independent operational-value checks against this offer's facts.
        if token == "tel" and re.match(r"\s*\+?\d", text[match.start() + 1:]):
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
# Ein satzinitiales Pronomen kann sich nur auf etwas beziehen, das vorher schon
# genannt wurde. Deshalb entscheidet hier die Position, nicht die Anredeform.
_AFTER_SENTENCE_END_RE = re.compile(r"[.!?] *[\"„“«(]? *$")


def _uses_formal_register(prose: str) -> bool:
    """Entscheidet die deutsche Anrede nur dort, wo sie eindeutig ist.

    Eine grossgeschriebene Hoeflichkeitsform mitten im Satz ist eindeutig: dort
    schreibt das Deutsche weder ``sie`` noch ``ihr`` gross. Am Satzanfang ist sie
    es nicht, denn dort wird jedes Wort grossgeschrieben. Ein satzinitiales
    ``Sie``/``Ihr`` gilt deshalb nur dann als Hoeflichkeitsform, wenn ihm kein
    Satz vorausgeht, auf den es sich beziehen koennte.

    Live reproduziert: "Melde dich bei X. Sie bieten Uebernachtungen fuer 5,00
    Euro pro Nacht an." meinte den Traeger und wurde als Hoeflichkeitsform
    verworfen, obwohl die Antwort durchgehend duzt.

    Grenze: Steht eine echte Hoeflichkeitsform selbst am Anfang eines
    Folgesatzes, ist sie mit diesem Verfahren nicht von ``sie`` zu unterscheiden
    und wird nicht erkannt.
    """
    return any(
        not _AFTER_SENTENCE_END_RE.search(prose[: match.start()])
        for match in GERMAN_FORMAL_RE.finditer(prose)
    )
# Die frühere rein lexikalische Leistungs- und Zielgruppenerkennung ist nach
# app/grounding_claims.py gewandert. Dort wird nicht mehr nur erkannt, DASS ein
# Konzept genannt wird, sondern geprüft, ob die zitierten WERTE es tragen.
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
        "kann dir nicht helfen", "kann ich dir nicht helfen",
        "kann diese frage nicht beantworten",
        "nicht weiterhelfen",
    ),
    Language.EN: ("cannot answer", "can't answer", "cannot help with", "can't help with"),
    Language.PL: ("nie mog\u0119 odpowiedzie\u0107", "nie odpowiem", "nie mo\u017ce odpowiedzie\u0107"),
    Language.RO: ("nu pot r\u0103spunde", "nu \u00ee\u021bi pot spune", "nu pot spune", "nu poate r\u0103spunde"),
    Language.RU: (
        "\u043d\u0435 \u043c\u043e\u0433\u0443 \u043e\u0442\u0432\u0435\u0442\u0438\u0442\u044c",
        "\u043d\u0435 \u043c\u043e\u0433\u0443 \u0441\u043a\u0430\u0437\u0430\u0442\u044c",
        "\u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u043e\u0442\u0432\u0435\u0442\u0438\u0442\u044c",
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
    Language.EN: ("no matching offer", "nothing suitable", "could not find a matching", "couldn't find a matching"),
    Language.PL: ("nie udało mi się znaleźć pasującej oferty", "brak pasuj\u0105cej oferty", "nie ma pasuj\u0105cej oferty", "nie znalaz\u0142am", "nie znalaz\u0142em",
                  "nie znaleziono pasuj\u0105cej oferty", "w bazie lena nie ma dost\u0119pnych ofert"),
    Language.RO: ("nicio ofert\u0103 potrivit\u0103", "nu am g\u0103sit o ofert\u0103 potrivit\u0103"),
    Language.RU: (
        "не удалось найти подходящ", "не нашла подходящ", "не нашёл подходящ", "не нашел подходящ",
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
    reference_assessment: dict[str, object] | None = None


def _canonical(value: str) -> str:
    return " ".join(value.casefold().split())


def _ungrounded(diagnostic_code: GroundingDiagnosticCode) -> FormulatorError:
    return FormulatorError(
        "formulator_ungrounded_claim",
        diagnostic_code=diagnostic_code,
    )


def _contains_exact_literal(text: str, literal: str, *, ignore_case: bool = False) -> bool:
    """Findet einen vollständigen Literalwert statt eines Wortpräfixes.

    Kuratierte Namen dürfen nur in Leerraum und Unicode-Bindestrichen abweichen,
    nicht flektiert oder um zusätzliche Wortzeichen erweitert werden.
    Der optionale case-insensitive Lauf dient nur dazu, eine
    mögliche Namensnennung zu erkennen; die anschließende Freigabe bleibt
    case-sensitiv.
    """
    text, literal = normalize_name_typography(text), normalize_name_typography(literal)
    flags = re.IGNORECASE if ignore_case else 0
    return re.search(rf"(?<!\w){re.escape(literal)}(?!\w)", text, flags) is not None


def _without_contact_literals(text: str) -> str:
    """Blendet E-Mail-Adressen und URLs aus, bevor Namen gesucht werden.

    In ``uvo@cab-leipzig.de`` steckt der Eigenname ``UVO``, aber die Adresse ist
    keine Namensnennung. ``@`` ist kein Wortzeichen, deshalb genuegte die
    bisherige Wortgrenze nicht. E-Mails und URLs haben eigene exakte Pruefungen
    (``EMAIL_NOT_CITED``, ``URL_NOT_CITED``); hier geht keine Zusicherung
    verloren, nur eine Doppelpruefung mit falschem Treffer.
    """
    return URL_RE.sub(" ", EMAIL_RE.sub(" ", text))


def _strip_evidence_literals(
    text: str, evidence: FormulatorEvidence, *, preserve_phone_numbers: bool = False,
) -> str:
    stripped = normalize_name_typography(text)
    literals = [
        fact.value
        for offer in evidence.selected_offers
        for fact in offer.facts
        if fact.fact_type in {
            FactType.DISPLAY_NAME, FactType.ALIAS, FactType.ADDRESS, FactType.PHONE,
            FactType.EMAIL, FactType.URL, FactType.OPENING_TIME, FactType.STAND_TIME,
        }
        and (not preserve_phone_numbers or fact.fact_type != FactType.PHONE)
    ]
    # Schedule values may carry a presentation-only quote/list marker. Match
    # the entire evidenced remainder, never an abbreviation or arbitrary prefix.
    literals.extend(
        fact.value[2:]
        for offer in evidence.selected_offers
        for fact in offer.facts
        if fact.fact_type in {FactType.OPENING_TIME, FactType.STAND_TIME}
        and fact.value.startswith("> ") and fact.value[2:].strip()
    )
    for literal in sorted(literals, key=len, reverse=True):
        stripped = re.sub(re.escape(normalize_name_typography(literal)), " ", stripped, flags=re.IGNORECASE)
    return stripped


def _validate_language(text: str, evidence: FormulatorEvidence) -> None:
    prose = _strip_evidence_literals(text, evidence)
    prose = mask_evidenced_places(prose, [fact.value for offer in evidence.selected_offers for fact in offer.facts])
    if has_foreign_prose(prose, evidence.requested_language):
        raise FormulatorError("formulator_invalid_language")
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


def _validate_policy_answer(text: str, evidence: FormulatorEvidence) -> None:
    """Bindet angebotsfreie Modellantworten an eng begrenzte Policy-Inhalte."""
    folded = normalized_policy_text(text)
    if evidence.answer_type == AnswerType.OUT_OF_SCOPE:
        anchors = DOMAIN_BOUNDARY_ANCHORS[evidence.requested_language]
        if not any(anchor in folded for anchor in anchors) and not (
            evidence.requested_language == Language.DE and german_boundary(text)
        ):
            raise _ungrounded(GroundingDiagnosticCode.DOMAIN_BOUNDARY_MISSING)
    elif evidence.answer_type == AnswerType.NO_VERIFIED_RESULT:
        if not any(anchor in folded for anchor in NO_RESULT_ANCHORS[evidence.requested_language]):
            raise _ungrounded(GroundingDiagnosticCode.NO_RESULT_BOUNDARY_MISSING)


def _validate_operational_tokens(text: str, facts: list[EvidenceFact], *, medical_policy: bool = False) -> None:
    cited = "\n".join(fact.value for fact in facts)
    cited_folded = cited.casefold()
    for url in URL_RE.findall(text):
        if url.rstrip(".,;)") not in {item.rstrip(".,;)") for item in URL_RE.findall(cited)}:
            raise _ungrounded(GroundingDiagnosticCode.URL_NOT_CITED)
    for email in EMAIL_RE.findall(text):
        if email.casefold() not in {item.casefold() for item in EMAIL_RE.findall(cited)}:
            raise _ungrounded(GroundingDiagnosticCode.EMAIL_NOT_CITED)
    for _address in ADDRESS_RE.findall(text):
        if _address not in cited:
            raise _ungrounded(GroundingDiagnosticCode.ADDRESS_NOT_CITED)
    for time_value in TIME_RE.findall(text):
        if time_value not in TIME_RE.findall(cited):
            raise _ungrounded(GroundingDiagnosticCode.TIME_NOT_CITED)
    if not euro_values(text).issubset(euro_values(cited)):
        raise _ungrounded(GroundingDiagnosticCode.PRICE_NOT_CITED)
    # Phone labels are prose/conditions, not part of the contact's digit value.
    phone_text = URL_RE.sub(" ", EMAIL_RE.sub(" ", text))
    number_text, invalid_phone = mask_known_phones(
        phone_text, [fact.value for fact in facts if fact.fact_type == FactType.PHONE],
    )
    cited_numbers = set(NUMBER_RE.findall(EURO_RE.sub(" ", cited)))
    if medical_policy:
        cited_numbers.add(EMERGENCY_NUMBER)
    if any(number not in cited_numbers for number in NUMBER_RE.findall(EURO_RE.sub(" ", number_text))):
        raise _ungrounded(GroundingDiagnosticCode.NUMBER_NOT_CITED)
    if invalid_phone:
        raise _ungrounded(GroundingDiagnosticCode.PHONE_NOT_EXACT)
    for fact in facts:
        if fact.fact_type == FactType.PHONE and "nur zu Einsatzzeiten" in fact.value:
            digits = re.sub(r"\D", "", phone_number(fact.value))
            if digits in re.sub(r"\D", "", text) and not operating_restriction_present(text):
                raise _ungrounded(GroundingDiagnosticCode.SERVICE_CONDITION_MISSING)
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
        raise _ungrounded(GroundingDiagnosticCode.WEEKDAY_NOT_CITED)
    if any(claim in text.casefold() for claim in UNSAFE_CLAIMS):
        raise _ungrounded(GroundingDiagnosticCode.UNSAFE_REALTIME_CLAIM)
    if "€" in text and "€" not in cited_folded:
        raise _ungrounded(GroundingDiagnosticCode.CURRENCY_NOT_CITED)


def _validate_service_conditions(
    text: str,
    offer,
    pool: list[EvidenceFact],
    language: Language,
    visible_offer_text: str,
) -> None:
    """Hält leistungsgebundene Zeitfenster der kuratierten Daten auseinander.

    Die Kuratierung unterscheidet beim Hilfebus Essensausgabe sonntags
    20:00-21:00 von Beratung und Vermittlung täglich 18:00-23:00. Eine
    allgemeine Leistungsaussage bleibt zulässig; eine Zeitangabe darf aber nicht
    von einer anderen Leistung stammen, und eine an die fragende Person
    gerichtete Erhaltzusage braucht die belegte Bedingung selbst.
    """
    conditions = {
        capability: fact
        for fact in offer.facts
        if fact.fact_type == FactType.SERVICE_CONDITION
        and (capability := condition_capability(fact.value)) is not None
    }
    if not conditions:
        return
    named = {
        capability
        for concept in detect_service_concepts(text, language)
        for capability in CONCEPT_CAPABILITIES.get(concept, frozenset())
        if capability in conditions
    }
    if not named:
        return
    cited = {fact.fact_id for fact in pool}
    for capability in sorted(named):
        condition = conditions[capability]
        if not schedule_matches(text, condition.value, language, complete=False):
            raise _ungrounded(GroundingDiagnosticCode.SERVICE_CONDITION_MISMATCH)
        if claims_personal_receipt(text, language) and (
            condition.fact_id not in cited
            or not schedule_matches(visible_offer_text, condition.value, language, complete=True)
        ):
            raise _ungrounded(GroundingDiagnosticCode.SERVICE_CONDITION_MISSING)


def _validate_cited_names(
    response: FormulatorResponse,
    texts: list[str],
    pools: dict[str, list[EvidenceFact]],
) -> None:
    """Verlangt jeden zitierten Namen genau einmal exakt in seinem Angebot.

    Belegt sein muss der Inhalt, nicht die Position einer Fakt-ID. Ein Satz darf
    den Namensfakt seines Angebots mitzitieren, um Telefon oder E-Mail
    zuzuordnen, ohne den Namen erneut auszuschreiben. Erscheint der Name
    irgendwo im Text, muss er unveraendert erscheinen; eine gebeugte oder sonst
    veraenderte Schreibweise bleibt unzulaessig.

    Grenze: Steht der Name in einem Satz exakt und in einem anderen gebeugt, so
    erkennt die satzweise Pruefung die Beugung nur, wenn sie als Namensnennung
    erkennbar bleibt.
    """
    rendered: dict[str, list[str]] = {}
    for sentence, text in zip(response.sentences, texts):
        if sentence.offer_id is not None:
            rendered.setdefault(sentence.offer_id, []).append(text)
    for offer_id, pool in pools.items():
        answer_text = _without_contact_literals(" ".join(rendered.get(offer_id, ())))
        for fact in pool:
            if fact.fact_type in {
                FactType.DISPLAY_NAME, FactType.ALIAS,
            } and not _contains_exact_literal(answer_text, fact.value):
                raise _ungrounded(GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT)


def _validate_sentence(
    sentence,
    evidence: FormulatorEvidence,
    offers_by_id: dict[str, object],
    facts_by_id: dict[str, tuple[str, EvidenceFact]],
    allowed_policies: set[BindingPolicy],
    pools: dict[str, list[EvidenceFact]],
    visible_offer_texts: dict[str, str],
) -> str:
    text = " ".join(sentence.text.split())
    if not text or HTML_OR_MARKDOWN_RE.search(text):
        raise FormulatorError("formulator_contract_violation")
    if VISIBLE_ID_RE.search(text) or any(fact_id in text for fact_id in facts_by_id):
        raise FormulatorError("formulator_contract_violation")
    if any(policy.value in text for policy in BindingPolicy):
        raise FormulatorError("formulator_contract_violation")
    if not set(sentence.policy_ids).issubset(allowed_policies):
        raise FormulatorError("formulator_invalid_fact")

    pool: list[EvidenceFact] = []
    if sentence.offer_id is None:
        if sentence.claim_type not in {
            ClaimType.UNCERTAINTY, ClaimType.DOMAIN_BOUNDARY, ClaimType.NO_RESULT,
        }:
            raise FormulatorError("formulator_contract_violation")
    else:
        offer = offers_by_id[sentence.offer_id]
        pool = pools[sentence.offer_id]
        pool_values = [(fact.fact_type.value, fact.value) for fact in pool]
        language = evidence.requested_language
        if not price_services_match(text, pool_values, language):
            raise _ungrounded(GroundingDiagnosticCode.PRICE_SERVICE_MISMATCH)
        if not fee_claim_matches(text, pool_values, language):
            raise _ungrounded(GroundingDiagnosticCode.FEE_CLAIM_UNSUPPORTED)
        # Die Rolle beschreibt, warum das Angebot ausgewaehlt wurde, nicht seinen
        # Leistungsumfang. Ein referral_contact darf seine belegten eigenen
        # Leistungen beschreiben; entscheidend ist der Beleg, nicht der Enumwert.
        if sentence.claim_type == ClaimType.REFERRAL and offer.candidate_role != "referral_contact":
            raise _ungrounded(GroundingDiagnosticCode.REFERRAL_ROLE_MISMATCH)

        # Names and contact literals are not service/target claims in their own
        # right. Preserve other fact text so that its semantics are still checked.
        semantic_text = normalize_name_typography(_without_contact_literals(text))
        for fact in offer.facts:
            if fact.fact_type in {FactType.DISPLAY_NAME, FactType.ALIAS}:
                semantic_text = semantic_text.replace(normalize_name_typography(fact.value), " ")
        operational_support = supported_operational_statement(semantic_text, pool_values, language)
        if sentence.claim_type == ClaimType.SERVICE and not operational_support and not any(
            fact.fact_type in {FactType.SERVICE, FactType.CAPABILITY, FactType.DESCRIPTION}
            for fact in pool
        ):
            raise _ungrounded(GroundingDiagnosticCode.SERVICE_ROLE_MISMATCH)
        exact_negative_fact = any(
            fact.fact_type in {FactType.SERVICE, FactType.DESCRIPTION, FactType.NOTE}
            and has_negation(fact.value, language)
            and _canonical(fact.value).rstrip(".!?") == _canonical(semantic_text).rstrip(".!?")
            for fact in pool
        )
        # The same evidence-bound audience masking applies to both directions:
        # "people without healthcare" neither negates counselling nor proves care.
        service_text = service_text_without_cited_qualifiers(semantic_text, pool_values, language)
        scoped_values = [
            (kind, service_text_without_cited_qualifiers(value, pool_values, language))
            for kind, value in pool_values
        ]
        # Negative service text cannot prove a positive service by keyword alone.
        service_values = [
            (kind, value) for kind, value in scoped_values
            if not any(has_negation(value, lang) for lang in {language, Language.DE, Language.EN})
        ]
        _, service_concepts = assess_service_claim(service_text, service_values, language)
        negative_values = [
            (kind, value) for kind, value in scoped_values
            if any(has_negation(value, lang) for lang in {language, Language.DE, Language.EN})
        ]
        if not exact_negative_fact and service_concepts & (
            supported_service_concepts(negative_values, language)
            - supported_service_concepts(service_values, language)
        ):
            raise _ungrounded(GroundingDiagnosticCode.SERVICE_FACT_MISSING)
        if (sentence.claim_type == ClaimType.FACT and TIME_RE.search(text)
                and not fact_schedule_matches(text, pool_values, language)):
            # Check actual clock/day/place relations, regardless of whether a
            # closed vocabulary happens to recognize the surrounding service.
            raise _ungrounded(GroundingDiagnosticCode.TIME_NOT_CITED)
        # Lexical UNDECIDABLE is observational only after the ablation decision.
        all_values = [(fact.fact_type.value, fact.value) for fact in offer.facts]
        target_support, _ = assess_target_claim(
            semantic_text, pool_values, language, restrictions=all_values,
        )
        if contradicts_age_bound(
            semantic_text, all_values, language
        ):
            raise _ungrounded(GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED)
        if target_support is ClaimSupport.CONTRADICTED:
            raise _ungrounded(GroundingDiagnosticCode.TARGET_CLAIM_CONTRADICTED)
        if target_support is ClaimSupport.UNDECIDABLE:
            raise _ungrounded(GroundingDiagnosticCode.TARGET_FACT_MISSING)
        # Positive concept occurrence does not support a negated claim. Exact
        # cited negative facts may be quoted; arbitrary negative paraphrases
        # remain undecidable instead of being mistaken for positive evidence.
        if service_concepts and has_negation(service_text, language) and not exact_negative_fact:
            raise _ungrounded(GroundingDiagnosticCode.SERVICE_FACT_MISSING)

        # Aus einer belegten Leistungsbeschreibung folgt weder eine Aufnahme noch
        # eine persoenliche Eignung noch eine aktuelle Verfuegbarkeit.
        if claims_admission(semantic_text, language):
            raise _ungrounded(GroundingDiagnosticCode.ADMISSION_CLAIM_UNSUPPORTED)
        if claims_suitability(semantic_text, language):
            raise _ungrounded(GroundingDiagnosticCode.SUITABILITY_CLAIM_UNSUPPORTED)
        if claims_current_availability(
            mask_status_uncertainty(semantic_text, language), language,
            known_unknown_values=[fact.value for fact in pool if fact.fact_type == FactType.NOTE],
        ):
            raise _ungrounded(GroundingDiagnosticCode.CURRENT_AVAILABILITY_UNSUPPORTED)
        _validate_service_conditions(
            semantic_text, offer, pool, language, visible_offer_texts[sentence.offer_id],
        )

        if sentence.claim_type == ClaimType.FACT and not any(
            fact.fact_type not in {FactType.DISPLAY_NAME, FactType.ALIAS}
            for fact in pool
        ):
            raise _ungrounded(GroundingDiagnosticCode.FACT_CLAIM_MISSING)

        # Die Forderung, einen zitierten Namensfakt exakt wiederzugeben, gilt
        # antwortweit je Angebot (siehe _validate_cited_names) und nicht mehr je
        # Satz: ein Satz darf den Namen mitzitieren, ohne ihn zu wiederholen.
        named_text = normalize_name_typography(_without_contact_literals(text))
        for candidate in evidence.selected_offers:
            naming_facts = [
                fact for fact in candidate.facts
                if fact.fact_type in {FactType.DISPLAY_NAME, FactType.ALIAS} and len(fact.value) >= 2
            ]
            name_like = [
                fact for fact in naming_facts
                if normalize_name_typography(fact.value).casefold() in named_text.casefold()
            ]
            if any(not _contains_exact_literal(named_text, fact.value) for fact in name_like):
                raise _ungrounded(GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT)
            mentioned = [
                fact
                for fact in naming_facts
                if _contains_exact_literal(named_text, fact.value, ignore_case=True)
            ]
            if mentioned and candidate.offer_id != sentence.offer_id:
                if all(evidenced_venue(text, fact.value, pool_values) for fact in mentioned):
                    continue
                raise FormulatorError("formulator_invalid_fact")
            if mentioned and not {fact.fact_id for fact in mentioned}.intersection(
                {cited.fact_id for cited in pool}
            ):
                raise FormulatorError("formulator_invalid_fact")
            if mentioned and any(
                not _contains_exact_literal(named_text, fact.value) for fact in mentioned
            ):
                raise _ungrounded(GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT)

    _validate_operational_tokens(text, pool, medical_policy=BindingPolicy.MEDICAL_EMERGENCY in allowed_policies)
    return text


def validate_formulation(
    response: FormulatorResponse | FormulatorPlan,
    evidence: FormulatorEvidence,
) -> ValidatedFormulation:
    """Validate model prose atomically; preserve accepted model wording.

    Current prose uses contract 7. Contract 5 and rendered plan 6 remain
    explicit historical protocols, not alternative runtime modes.
    """
    if isinstance(response, FormulatorPlan):
        answer, cards, assessment = render_answer_plan(response, evidence)
        return ValidatedFormulation(answer, cards, len(response.sentences), evidence.answer_type, assessment)
    if response.language != evidence.requested_language:
        raise FormulatorError("formulator_invalid_language")
    response, pools, reference_assessment = resolve_offer_evidence(response, evidence)
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

    visible_offer_texts = {
        offer_id: " ".join(sentence.text for sentence in response.sentences if sentence.offer_id == offer_id)
        for offer_id in pools
    }
    texts = [
        _validate_sentence(sentence, evidence, offers_by_id, facts_by_id, allowed_policies, pools, visible_offer_texts)
        for sentence in response.sentences
    ]
    declared_pools = {
        key: [facts_by_id[fact_id][1] for fact_id in ids]
        for key, ids in reference_assessment["declared_fact_ids"].items()
    }
    _validate_cited_names(response, texts, declared_pools)
    answer = " ".join(texts)
    if len(answer) > evidence.max_answer_chars:
        raise FormulatorError("formulator_contract_violation")
    _validate_language(answer, evidence)
    _validate_policy_answer(answer, evidence)
    # Presentation observations never imply false content or trigger a fallback.
    observations = []
    if any(_contains_sentence_break(_strip_evidence_literals(text, evidence, preserve_phone_numbers=True)) for text in texts):
        observations.append("multiple_sentences_in_block")
    if evidence.requested_language == Language.DE and _uses_formal_register(_strip_evidence_literals(answer, evidence)):
        observations.append("formal_register")
    if len({_canonical(text) for text in texts}) != len(texts):
        observations.append("repeated_block")
    reference_assessment["presentation_observations"] = observations
    if response.contract_version == "7":
        reference_assessment["mode"] = "grounded_model_prose"
        reference_assessment["formulator_contract_version"] = response.contract_version

    if evidence.need in {Need.TOILET, Need.DRINKING_WATER} and evidence.selected_offers:
        primary = evidence.selected_offers[0]
        if response.sentences[0].offer_id != primary.offer_id:
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
        reference_assessment=reference_assessment,
    )
