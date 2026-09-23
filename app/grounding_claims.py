"""Begrenzte, wertbezogene Konzeptprüfung für die Groundingvalidierung.

Dieses Modul beantwortet genau eine Frage: Wird ein im sichtbaren Antworttext
erkanntes Konzept (Leistung, Zielgruppe, Aufnahme, aktuelle Verfügbarkeit) von
den *Werten* der zitierten Fakten getragen? Es ist bewusst kein
Entailment-Modell. Es arbeitet mit einem geschlossenen mehrsprachigen
Stammwortschatz und liefert drei Ergebnisse statt einer Ja/Nein-Wahrheit:

``SUPPORTED``     Das Konzept steht in einem zitierten Wert.
``CONTRADICTED``  Ein typisierter kuratierter Fakt schließt das Konzept aus.
``UNDECIDABLE``   Kein Beleg und kein Widerspruch; mit diesem Verfahren nicht
                  entscheidbar.

``UNDECIDABLE`` bedeutet ausdrücklich nicht „nachweislich falsch". Der Aufrufer
behandelt es dennoch als nicht freigebbar, weil unbelegte Aussagen nicht
ungeprüft ausgeliefert werden dürfen.

Erkennung und Beleg sind bewusst asymmetrisch sprachgebunden. Erkannt wird nur
mit dem Wortschatz der Antwortsprache, damit ein Stamm einer anderen Sprache
keine Forderung auslöst. Belegt werden darf zusätzlich aus deutschen und
englischen Werten, weil kuratierte Literalwerte wie ``food_distribution`` oder
„Kostenloser Trinkwasserbrunnen" nicht lokalisiert werden. Beide Richtungen
wirken damit gegen eine falsche Ablehnung, nicht für eine falsche Freigabe.

Das Modul importiert bewusst weder ``formulation`` noch ``grounding``: es
arbeitet auf ``(fact_type, value)``-Paaren und bleibt dadurch zyklenfrei und
isoliert testbar.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from enum import Enum

from .models import Language
from .result_time import SCHEDULE_WINDOWS, ServiceWindow


class ClaimSupport(str, Enum):
    """Drei Ergebnisse statt einer Gleichsetzung aller Abweichungen."""

    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNDECIDABLE = "undecidable"


def fold(value: str) -> str:
    """Normalisiert diakritikafrei und kleingeschrieben für Stammvergleiche."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _strip_combining(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


# Kyrillischer Text wird vor dem Vergleich transliteriert, damit derselbe
# gefaltete Vergleich für alle fünf Sprachen gilt und der Wortschatz unten in
# einer einzigen Schreibweise gepflegt werden kann.
_CYRILLIC_TRANSLITERATION = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def transliterated(value: str) -> str:
    """Bildet kyrillischen Text auf denselben lateinischen Vergleichsraum ab.

    Die Umschrift läuft vor dem Entfernen kombinierender Zeichen. Sonst zerlegt
    NFKD zuerst „й" in „и" plus Breve und die Umschrift sähe nur noch „i";
    „сейчас" würde dann zu „seichas" und ein Stamm „seychas" nie greifen.
    """
    return _strip_combining(value.casefold().translate(_CYRILLIC_TRANSLITERATION))


Vocabulary = dict[str, dict[Language, tuple[str, ...]]]
Fact = tuple[str, str]  # (fact_type, value)

# ---------------------------------------------------------------------------
# Geschlossener Stammwortschatz
# ---------------------------------------------------------------------------
# Die Konzeptschlüssel der Leistungen entsprechen den kuratierten
# Capability-Namen, damit belegte Zeitfenster ohne zweite Datenhaltung
# zugeordnet werden können. Der Umfang entspricht dem bisher geprüften
# Leistungsbereich; er wird hier nach Konzept und Sprache getrennt, nicht
# erweitert. Stämme werden am Wortanfang verglichen, nie als freie Teilzeichen-
# kette: „bed" darf nicht über „ed" und „Menschen" nicht über „men" auslösen.
SERVICE_CONCEPT_STEMS: Vocabulary = {
    "food": {
        Language.DE: ("essen", "mahlzeit", "verpflegung", "suppe", "lebensmittel"),
        Language.EN: ("food", "meal"),
        Language.PL: ("jedzen", "posil", "zywnos"),
        Language.RO: ("mancare", "masa", "alimente"),
        Language.RU: ("eda", "edu", "edy", "pisch", "pitani"),
    },
    "drinking_water": {
        Language.DE: ("wasser", "trinkwasser"),
        Language.EN: ("water",),
        Language.PL: ("wod",),
        Language.RO: ("apa",),
        Language.RU: ("vod",),
    },
    "sleep": {
        Language.DE: ("schlaf", "ubernacht", "unterkunft", "nachtlager", "bett", "notschlaf"),
        Language.EN: ("sleep", "overnight", "accommodation", "shelter", "bed"),
        Language.PL: ("nocleg", "schronis", "lozk", "spanie"),
        Language.RO: ("dorm", "adapost", "cazare", "pat"),
        Language.RU: ("spat", "nochleg", "priyut", "krovat", "nochev"),
    },
    "medical_care": {
        Language.DE: ("wundversorgung", "medizin", "behandl", "behandel", "arzt", "wunde"),
        Language.EN: ("wound", "medical", "treatment", "doctor"),
        Language.PL: ("medycz", "leczen", "rana", "lekarz"),
        Language.RO: ("medical", "tratament", "rana", "doctor"),
        Language.RU: ("medic", "lechen", "vrach", "rana"),
    },
    "hygiene": {
        Language.DE: ("dusche", "duschen", "hygiene", "waschen"),
        Language.EN: ("shower", "hygien", "wash"),
        Language.PL: ("prysznic", "higien", "mycie"),
        Language.RO: ("dus", "igien", "spalat"),
        Language.RU: ("dush", "gigien"),
    },
    "toilet": {
        Language.DE: ("toilet",),
        Language.EN: ("toilet",),
        Language.PL: ("toalet",),
        Language.RO: ("toalet",),
        Language.RU: ("tualet",),
    },
    "counselling": {
        Language.DE: ("beratung", "beraten"),
        Language.EN: ("advice", "counsel"),
        Language.PL: ("porad",),
        Language.RO: ("consili",),
        Language.RU: ("konsult", "sovet"),
    },
}

# Zielgruppenkonzepte. Mehrdeutig kurze Tokens stehen in ``EXACT_WORD_STEMS``
# und gelten nur als vollständiges Wort.
TARGET_CONCEPT_STEMS: Vocabulary = {
    "female": {
        Language.DE: ("frau",),
        Language.EN: ("woman", "women", "female"),
        Language.PL: ("kobiet",),
        Language.RO: ("femei",),
        Language.RU: ("zhenschin", "zhensk"),
    },
    "male": {
        Language.DE: ("mann", "manner"),
        Language.EN: ("men", "man", "male"),
        Language.PL: ("mezczy",),
        Language.RO: ("barbat",),
        Language.RU: ("muzhchin", "muzhsk"),
    },
    "minor": {
        Language.DE: ("minderjahr", "jugendlich"),
        Language.EN: ("minor", "youth", "underage"),
        Language.PL: ("niepelnolet", "mlodzie"),
        Language.RO: ("minor", "tanar", "tineri"),
        Language.RU: ("nesovershennolet", "molodezh", "podrost"),
    },
    # „volljährig" ist die kuratierte Schreibweise derselben Aussage; die
    # jeweilige Minderjährigkeitsform („niepełnolet", „nesovershennolet") wird
    # davon nicht getroffen, weil Stämme am Wortanfang verglichen werden.
    "adult": {
        Language.DE: ("erwachsen", "volljahr"),
        Language.EN: ("adult", "of legal age"),
        Language.PL: ("dorosl", "pelnolet"),
        Language.RO: ("adult", "majori"),
        Language.RU: ("vzrosl", "sovershennolet"),
    },
}
# Gegenseitig ausschließende Zielgruppenkonzepte.
TARGET_CONCEPT_CONFLICTS: dict[str, frozenset[str]] = {
    "female": frozenset({"male"}),
    "male": frozenset({"female"}),
    "minor": frozenset({"adult"}),
    "adult": frozenset({"minor"}),
}

# Kuratierte Literalwerte typisierter Fakten. Diese Werte sind nicht lokalisiert
# und werden deshalb exakt abgebildet, nicht über Stammsuche erkannt.
ELIGIBLE_GENDER_CONCEPTS = {"female": "female", "male": "male"}
TARGET_GROUP_CONCEPTS = {
    "women": "female",
    "men": "male",
    "adults": "adult",
    "minors": "minor",
}

TARGET_FACT_TYPES = frozenset(
    {"target_group", "minimum_age", "maximum_age", "eligible_gender", "access"}
)
SERVICE_FACT_TYPES = frozenset({"service", "capability", "description"})
# Namensfakten belegen niemals einen Inhalt; sie belegen nur den Namen selbst.
NAMING_FACT_TYPES = frozenset({"display_name", "alias"})
# Zusätzliche Werttypen, aus denen eine Leistung belegt werden darf.
SERVICE_SUPPORT_FACT_TYPES = SERVICE_FACT_TYPES | {
    "offer_type", "place_type", "service_condition",
}
# Freitextwerte, aus denen eine Zielgruppe belegt werden darf.
TARGET_SUPPORT_TEXT_FACT_TYPES = SERVICE_FACT_TYPES | {"access", "note"}
# Sprachen, deren Wortschatz bei der Belegsuche immer zusätzlich gilt, weil
# kuratierte Literalwerte in diesen Sprachen vorliegen.
CURATED_VALUE_LANGUAGES = (Language.DE, Language.EN)


# Stämme werden normalerweise am Wortanfang verglichen, damit Flexionsformen
# mitgefunden werden („frau" findet „Frauen"). Diese Tokens sind dafür zu kurz
# oder zu mehrdeutig und gelten nur als vollständiges Wort. Live reproduziert:
# „men" in „Menschen" löste früher eine Geschlechtsbehauptung aus, obwohl der
# Satz nur den zitierten Angebotsnamen wiedergab. Dieselbe Gefahr besteht in der
# Belegrichtung, wo sie zu einer falschen Freigabe führen würde.
EXACT_WORD_STEMS = frozenset({
    "men", "man", "male", "mann",
    "bed", "spot", "pat", "loc",
    "eda", "edu", "edy", "masa", "apa", "dus", "rana",
    "now", "acum", "gerade",
})


def _stems(vocabulary: Vocabulary, concept: str, languages: Iterable[Language]) -> tuple[str, ...]:
    per_language = vocabulary[concept]
    return tuple(stem for language in languages for stem in per_language.get(language, ()))


# Der Unterstrich trennt, statt zu verbinden: kuratierte Literalwerte liegen als
# ``drinking_water`` oder ``overnight_accommodation`` vor und sollen ihre
# Bestandteile belegen koennen.
_BOUNDARY = "[a-z0-9]"


def _contains_stem(haystack: str, stems: Iterable[str]) -> bool:
    return any(
        re.search(
            rf"(?<!{_BOUNDARY}){re.escape(stem)}(?!{_BOUNDARY})"
            if stem in EXACT_WORD_STEMS
            else rf"(?<!{_BOUNDARY}){re.escape(stem)}",
            haystack,
        )
        for stem in stems
    )


def _detect(text: str, vocabulary: Vocabulary, languages: Sequence[Language]) -> set[str]:
    haystack = transliterated(text)
    return {
        concept
        for concept in vocabulary
        if _contains_stem(haystack, _stems(vocabulary, concept, languages))
    }


def detect_service_concepts(text: str, language: Language) -> set[str]:
    """Erkennt benannte Leistungskonzepte im sichtbaren Text der Antwortsprache."""
    return _detect(text, SERVICE_CONCEPT_STEMS, (language,))


def detect_target_concepts(text: str, language: Language) -> set[str]:
    """Erkennt Zielgruppen-, Geschlechts- und Altersaussagen der Antwortsprache."""
    return _detect(text, TARGET_CONCEPT_STEMS, (language,))


def _support_languages(language: Language) -> tuple[Language, ...]:
    return tuple(dict.fromkeys((language, *CURATED_VALUE_LANGUAGES)))


# ---------------------------------------------------------------------------
# Belegermittlung aus zitierten Werten
# ---------------------------------------------------------------------------
def _values_of(facts: Sequence[Fact], allowed_types: frozenset[str]) -> list[str]:
    return [value for fact_type, value in facts if fact_type in allowed_types]


def supported_service_concepts(facts: Sequence[Fact], language: Language) -> set[str]:
    """Leistungskonzepte, die in einem zitierten Leistungs- oder Beschreibungswert stehen."""
    values = _values_of(facts, SERVICE_SUPPORT_FACT_TYPES)
    if not values:
        return set()
    return _detect(" \n".join(values), SERVICE_CONCEPT_STEMS, _support_languages(language))


def supported_target_concepts(facts: Sequence[Fact], language: Language) -> set[str]:
    """Zielgruppenkonzepte aus typisierten Literalwerten und aus Beschreibungstexten.

    Eine lokalisierte Beschreibung darf eine Zielgruppenaussage belegen. Das
    bloße Vorhandensein eines Fakts eines zulässigen Typs belegt sie nicht: es
    zählt nur, was im Wert selbst steht.
    """
    supported: set[str] = set()
    free_text: list[str] = []
    for fact_type, value in facts:
        folded = fold(value).strip()
        if fact_type == "eligible_gender":
            concept = ELIGIBLE_GENDER_CONCEPTS.get(folded)
            if concept:
                supported.add(concept)
        elif fact_type == "target_group":
            concept = TARGET_GROUP_CONCEPTS.get(folded)
            if concept:
                supported.add(concept)
            else:
                free_text.append(value)
        elif fact_type == "minimum_age":
            if folded.isdigit() and int(folded) >= 18:
                supported.add("adult")
        elif fact_type == "maximum_age":
            if folded.isdigit() and int(folded) < 18:
                supported.add("minor")
        elif fact_type in TARGET_SUPPORT_TEXT_FACT_TYPES:
            free_text.append(value)
    if free_text:
        supported |= _detect(
            " \n".join(free_text), TARGET_CONCEPT_STEMS, _support_languages(language)
        )
    return supported


def restricting_target_concepts(facts: Sequence[Fact]) -> set[str]:
    """Konzepte aus typisierten kuratierten Zugangsbeschränkungen.

    Nur typisierte kuratierte Werte gelten als Beschränkung und damit als
    Widerspruchswächter. Ein Beschreibungstext beschränkt nichts; er belegt
    höchstens.
    """
    restricting: set[str] = set()
    for fact_type, value in facts:
        folded = fold(value).strip()
        if fact_type == "eligible_gender" and folded in ELIGIBLE_GENDER_CONCEPTS:
            restricting.add(ELIGIBLE_GENDER_CONCEPTS[folded])
        elif fact_type == "target_group" and folded in TARGET_GROUP_CONCEPTS:
            restricting.add(TARGET_GROUP_CONCEPTS[folded])
        elif fact_type == "minimum_age" and folded.isdigit() and int(folded) >= 18:
            restricting.add("adult")
        elif fact_type == "maximum_age" and folded.isdigit() and int(folded) < 18:
            restricting.add("minor")
    return restricting


def assess_target_claim(
    text: str, facts: Sequence[Fact], language: Language
) -> tuple[ClaimSupport, set[str]]:
    """Bewertet die im Text genannten Zielgruppenkonzepte gegen die zitierten Werte."""
    claimed = detect_target_concepts(text, language)
    if not claimed:
        return ClaimSupport.SUPPORTED, set()
    open_concepts = claimed - supported_target_concepts(facts, language)
    restricting = restricting_target_concepts(facts)
    contradicted = {
        concept
        for concept in open_concepts
        if TARGET_CONCEPT_CONFLICTS.get(concept, frozenset()) & restricting
    }
    if contradicted:
        return ClaimSupport.CONTRADICTED, contradicted
    if open_concepts:
        return ClaimSupport.UNDECIDABLE, open_concepts
    return ClaimSupport.SUPPORTED, claimed


def assess_service_claim(
    text: str, facts: Sequence[Fact], language: Language
) -> tuple[ClaimSupport, set[str]]:
    """Bewertet die im Text genannten Leistungskonzepte gegen die zitierten Werte.

    Es gibt keine kuratierte Negativliste „Leistung X wird nicht angeboten";
    deshalb kennt diese Prüfung kein ``CONTRADICTED``, sondern nur Beleg oder
    Unentscheidbarkeit.
    """
    claimed = detect_service_concepts(text, language)
    if not claimed:
        return ClaimSupport.SUPPORTED, set()
    open_concepts = claimed - supported_service_concepts(facts, language)
    if open_concepts:
        return ClaimSupport.UNDECIDABLE, open_concepts
    return ClaimSupport.SUPPORTED, claimed


# ---------------------------------------------------------------------------
# Zusagen, die aus einer belegten Leistungsbeschreibung nicht folgen
# ---------------------------------------------------------------------------
# Persönliche Erhaltzusagen in der zweiten Person. Modale Möglichkeitsformen
# („du kannst dort duschen") sind bewusst nicht enthalten: sie geben eine
# belegte Leistung wieder, keine Zusage an die fragende Person.
PERSONAL_RECEIPT_PATTERNS: dict[Language, tuple[str, ...]] = {
    Language.DE: (
        "bekommst du", "du bekommst", "kriegst du", "du kriegst",
        "erhaltst du", "du erhaltst", "gibt dir", "geben dir",
    ),
    Language.EN: ("you will get", "you get", "you will receive", "you receive", "gives you", "give you"),
    Language.PL: ("dostaniesz", "otrzymasz", "da ci", "daja ci"),
    Language.RO: ("primesti", "iti da", "iti ofera"),
    Language.RU: ("poluchish", "tebe dadut", "tebe dayut"),
}
# Aufnahme- und Platzzusagen.
ADMISSION_PATTERNS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("aufgenommen", "nimmt dich auf", "nehmen dich auf"),
    Language.EN: ("admitted", "will take you in", "takes you in"),
    Language.PL: ("przyjmie cie", "zostaniesz przyjet"),
    Language.RO: ("te primeste", "vei fi primit"),
    Language.RU: ("tebya primut", "budesh prinyat"),
}
# Ortsbegriffe, die aus einer Erhaltzusage eine Aufnahmezusage machen.
PLACE_STEMS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("schlafplatz", "platz", "bett", "unterkunft"),
    Language.EN: ("place", "bed", "spot"),
    Language.PL: ("miejsc", "lozk"),
    Language.RO: ("loc", "pat"),
    Language.RU: ("mesto", "krovat", "koyk"),
}
# Zusicherungsmarker. Erst sie machen aus der Wiedergabe einer belegten
# Leistung („dort bekommst du einen Schlafplatz") eine Aufnahmezusage („gibt dir
# sicher einen Schlafplatz"). Ohne sie bleibt die Leistungsbeschreibung zulässig,
# solange die zitierten Werte sie tragen.
ASSURANCE_MARKERS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("sicher", "bestimmt", "garantiert", "auf jeden fall"),
    Language.EN: ("surely", "certainly", "guaranteed", "definitely", "for sure"),
    Language.PL: ("na pewno", "gwarantowan"),
    Language.RO: ("sigur", "garantat"),
    Language.RU: ("tochno", "obyazatelno", "garantirovan"),
}
# Marker für aktuelle Verfügbarkeit. Ein belegter Wochentag ist prüfbar,
# „jetzt" ist es nicht.
CURRENT_MARKERS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("jetzt", "gerade", "momentan", "aktuell"),
    Language.EN: ("now", "currently", "at the moment"),
    Language.PL: ("teraz", "obecnie"),
    Language.RO: ("acum", "in acest moment"),
    Language.RU: ("seychas", "v dannyy moment"),
}
# Marker für ausdrücklich offengelassene Angaben. Ein Satz, der einen Status als
# unbekannt kennzeichnet, behauptet keine aktuelle Verfügbarkeit, sondern das
# Gegenteil. Die kuratierten Trinkbrunnendaten führen genau so einen Wert
# („aktueller Betriebsstatus unbekannt"); ihn wiederzugeben ist erwünscht.
UNKNOWN_MARKERS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("unbekannt", "nicht bekannt", "weiss ich nicht", "weiß ich nicht"),
    Language.EN: ("unknown", "not known", "cannot say", "no information"),
    Language.PL: ("nieznany", "nieznane", "nie wiadomo"),
    Language.RO: ("necunoscut", "nu se stie"),
    Language.RU: ("neizvesten", "neizvestno", "neizvestna"),
}
# Eignungszusagen an die fragende Person.
SUITABILITY_PATTERNS: dict[Language, tuple[str, ...]] = {
    Language.DE: ("fur dich geeignet", "passt zu dir", "das richtige fur dich"),
    Language.EN: ("suitable for you", "right for you", "fits you"),
    Language.PL: ("odpowiedni dla ciebie", "odpowiednia dla ciebie", "odpowiednie dla ciebie", "pasuje do ciebie"),
    Language.RO: ("potrivit pentru tine", "potrivita pentru tine", "ti se potriveste"),
    Language.RU: ("podhodit tebe", "tebe podhodit"),
}


def _contains_phrase(haystack: str, phrases: Iterable[str]) -> bool:
    return any(phrase in haystack for phrase in phrases)


def claims_admission(text: str, language: Language) -> bool:
    """Erkennt eine persönliche Aufnahme- oder Platzzusage.

    Eine Leistungsbeschreibung fällt nicht darunter, auch nicht in zweiter
    Person („dort bekommst du einen Schlafplatz"): sie gibt wieder, was das
    Angebot laut zitierten Werten leistet. Erkannt werden ausdrückliche
    Aufnahmeaussagen („dort wirst du aufgenommen") und zugesicherte
    Platzvergaben („gibt dir sicher einen Schlafplatz"), für die es keinen
    Kapazitätsbeleg gibt und geben kann.
    """
    haystack = transliterated(text)
    if _contains_phrase(haystack, ADMISSION_PATTERNS.get(language, ())):
        return True
    return (
        _contains_phrase(haystack, PERSONAL_RECEIPT_PATTERNS.get(language, ()))
        and _contains_stem(haystack, PLACE_STEMS.get(language, ()))
        and _contains_stem(haystack, ASSURANCE_MARKERS.get(language, ()))
    )


def claims_personal_receipt(text: str, language: Language) -> bool:
    """Erkennt eine Erhaltzusage in der zweiten Person ohne Ortsbezug.

    „Dort bekommst du Essen" sagt mehr aus als „bietet Essen an": es richtet die
    Leistung an die fragende Person. Bei einer zeitlich gebundenen Leistung
    genügt dafür kein allgemeiner Leistungsfakt.
    """
    return _contains_phrase(transliterated(text), PERSONAL_RECEIPT_PATTERNS.get(language, ()))


def claims_suitability(text: str, language: Language) -> bool:
    """Erkennt eine Eignungszusage für die fragende Person."""
    return _contains_phrase(transliterated(text), SUITABILITY_PATTERNS.get(language, ()))


def claims_current_availability(text: str, language: Language) -> bool:
    """Erkennt eine auf die Gegenwart bezogene Leistungsaussage.

    Ein allgemeiner Leistungsfakt belegt keine aktuelle Verfügbarkeit; deshalb
    wird die Kombination aus Gegenwartsmarker und Leistungs- oder Erhaltaussage
    eigens erkannt.
    """
    haystack = transliterated(text)
    if not _contains_stem(haystack, CURRENT_MARKERS.get(language, ())):
        return False
    if _contains_phrase(haystack, UNKNOWN_MARKERS.get(language, ())):
        return False
    return bool(detect_service_concepts(text, language)) or _contains_phrase(
        haystack, PERSONAL_RECEIPT_PATTERNS.get(language, ())
    )


# ---------------------------------------------------------------------------
# Leistungsgebundene Zeitfenster aus den kuratierten Daten
# ---------------------------------------------------------------------------
# Die kuratierte Projektion bleibt die einzige Quelle. Hier werden vorhandene
# feste Fenster nur lesbar gemacht, nicht neu gepflegt.
WEEKDAY_NAMES: dict[Language, tuple[str, ...]] = {
    Language.DE: ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"),
    Language.EN: ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    Language.PL: ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"),
    Language.RO: ("luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"),
    Language.RU: (
        "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье",
    ),
}
DAILY_LABEL: dict[Language, str] = {
    Language.DE: "täglich",
    Language.EN: "daily",
    Language.PL: "codziennie",
    Language.RO: "zilnic",
    Language.RU: "ежедневно",
}
CAPABILITY_LABELS: dict[str, dict[Language, str]] = {
    "food": {
        Language.DE: "Essensausgabe",
        Language.EN: "food distribution",
        Language.PL: "wydawanie jedzenia",
        Language.RO: "distribuire de mâncare",
        Language.RU: "раздача еды",
    },
    "drinking_water": {
        Language.DE: "Trinkwasser",
        Language.EN: "drinking water",
        Language.PL: "woda pitna",
        Language.RO: "apă potabilă",
        Language.RU: "питьевая вода",
    },
    "hygiene": {
        Language.DE: "Hygieneangebot",
        Language.EN: "hygiene service",
        Language.PL: "oferta higieniczna",
        Language.RO: "serviciu de igienă",
        Language.RU: "гигиена",
    },
    "clothing": {
        Language.DE: "Kleiderausgabe",
        Language.EN: "clothing distribution",
        Language.PL: "wydawanie odzieży",
        Language.RO: "distribuire de haine",
        Language.RU: "выдача одежды",
    },
    "counselling": {
        Language.DE: "Beratung",
        Language.EN: "counselling",
        Language.PL: "poradnictwo",
        Language.RO: "consiliere",
        Language.RU: "консультация",
    },
    "referral": {
        Language.DE: "Vermittlung",
        Language.EN: "referral",
        Language.PL: "pośrednictwo",
        Language.RO: "intermediere",
        Language.RU: "посредничество",
    },
    "medical_care": {
        Language.DE: "medizinische Versorgung",
        Language.EN: "medical care",
        Language.PL: "opieka medyczna",
        Language.RO: "îngrijire medicală",
        Language.RU: "медицинская помощь",
    },
    "mobile_outreach": {
        Language.DE: "aufsuchende Arbeit",
        Language.EN: "mobile outreach",
        Language.PL: "praca uliczna",
        Language.RO: "muncă stradală",
        Language.RU: "выездная работа",
    },
}
# Leistungskonzepte und die kuratierten Capabilities, die sie meinen. Nur diese
# Konzepte können ein leistungsgebundenes Zeitfenster verletzen.
CONCEPT_CAPABILITIES: dict[str, frozenset[str]] = {
    "food": frozenset({"food"}),
    "drinking_water": frozenset({"drinking_water"}),
    "hygiene": frozenset({"hygiene"}),
    "medical_care": frozenset({"medical_care"}),
    "counselling": frozenset({"counselling", "referral"}),
}


def _clock(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _window_text(windows: Sequence[ServiceWindow], language: Language) -> str:
    names = WEEKDAY_NAMES[language]
    parts: list[str] = []
    for window in windows:
        days = sorted(window.weekdays)
        label = DAILY_LABEL[language] if len(days) == 7 else ", ".join(names[day] for day in days)
        parts.append(f"{label} {_clock(window.start_minute)}-{_clock(window.end_minute)}")
    return "; ".join(parts)


def service_condition_text(capability: str, schedule_rule: str, language: Language) -> str | None:
    """Formuliert ein vorhandenes festes Zeitfenster als lesbare Leistungsbedingung.

    Liefert ``None``, wenn die kuratierte Regel kein festes Fenster bezeichnet
    (zum Beispiel ``mobile_alternative_stands``). Solche Regeln werden nicht
    geraten, und es entsteht keine zweite maßgebliche Zeitquelle.
    """
    windows = SCHEDULE_WINDOWS.get(schedule_rule)
    label = CAPABILITY_LABELS.get(capability, {}).get(language)
    if not windows or not label:
        return None
    return f"{label}: {_window_text(windows, language)}"


def condition_capability(value: str) -> str | None:
    """Liest aus einer Bedingung zurück, welche Capability sie beschreibt."""
    head = transliterated(value.split(":", 1)[0]).strip()
    for capability, labels in CAPABILITY_LABELS.items():
        if any(transliterated(label) == head for label in labels.values()):
            return capability
    return None
