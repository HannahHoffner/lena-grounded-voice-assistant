"""Fixed, localized sentences around evidence values; no model paraphrasing.

Only outer Markdown list/quote markers are removed. Conditions, numbers,
negation, contacts and source language remain unchanged. Unstructured values
are quoted rather than interpreted as a new grammatical or factual claim.
"""

from __future__ import annotations

import re

from .models import Language

ANSWER_RENDERER_VERSION = "1"
_LANGUAGES = tuple(Language)
_PREFIX = re.compile(r"^\s*(?:>\s*(?=>|$)|>\s+(?=[^\d=\s])|[-*+]\s+(?=[^\d\s]))")

# Each row is a complete sentence, not a field label. These fixed translations
# still require human language review; arbitrary source prose is not translated.
_SENTENCES = {
    "intro": (
        "Hier findest du Angaben zu {name}.", "Here is information about {name}.",
        "Oto informacje o {name}.", "Iată informații despre {name}.", "Вот информация о {name}.",
    ),
    "service": (
        "Bei {name} gibt es {value}.", "At {name}, the services include {value}.",
        "W {name} oferta obejmuje {value}.", "La {name}, oferta include {value}.",
        "В {name} предлагается следующее: {value}.",
    ),
    "target_group": (
        "Das Angebot richtet sich an {value}.", "The service is intended for {value}.",
        "Oferta jest skierowana do następującej grupy: {value}.", "Oferta se adresează următorului grup: {value}.",
        "Услуга предназначена для следующей группы: {value}.",
    ),
    "opening_time": (
        "Die angegebenen Öffnungszeiten sind {value}.", "The listed opening hours are {value}.",
        "Podane godziny otwarcia to {value}.", "Programul indicat este {value}.",
        "Указаны следующие часы работы: {value}.",
    ),
    "stand_time": (
        "Die angegebenen Standzeiten sind {value}.", "The listed stop times are {value}.",
        "Podane godziny postoju to {value}.", "Orele de staționare indicate sunt {value}.",
        "Указаны следующие часы стоянки: {value}.",
    ),
    "address": (
        "Die Adresse ist {value}.", "The address is {value}.",
        "Adres to {value}.", "Adresa este {value}.", "Адрес — {value}.",
    ),
    "phone": (
        "Die Telefonnummer ist {value}.", "The phone number is {value}.",
        "Numer telefonu to {value}.", "Numărul de telefon este {value}.", "Номер телефона — {value}.",
    ),
    "email": (
        "Die E-Mail-Adresse ist {value}.", "The email address is {value}.",
        "Adres e-mail to {value}.", "Adresa de e-mail este {value}.", "Адрес электронной почты — {value}.",
    ),
    "url": (
        "Weitere Informationen findest du auf {value}.", "You can find more information at {value}.",
        "Więcej informacji znajdziesz na {value}.", "Găsești mai multe informații la {value}.",
        "Дополнительная информация есть на {value}.",
    ),
    "minimum_age": (
        "Das Mindestalter beträgt {value} Jahre.", "The minimum age is {value} years.",
        "Minimalny wiek wynosi {value} lat.", "Vârsta minimă este de {value} ani.",
        "Минимальный возраст — {value} лет.",
    ),
    "maximum_age": (
        "Für das Höchstalter ist die Angabe „{value}“ gespeichert.", "The recorded upper-age value is “{value}”.",
        "Zapisana górna granica wieku to „{value}”.", "Valoarea înregistrată pentru limita superioară de vârstă este „{value}”.",
        "Для верхней возрастной границы указано «{value}».",
    ),
    "eligible_gender": (
        "Die angegebene Zugangsgruppe ist „{value}“.", "The listed access group is “{value}”.",
        "Podana grupa uprawniona do dostępu to „{value}”.", "Grupul de acces indicat este „{value}”.",
        "Указана следующая группа доступа: «{value}».",
    ),
    "access": (
        "Für den Zugang gilt die Bedingung „{value}“.", "The access condition is “{value}”.",
        "Obowiązuje warunek dostępu „{value}”.", "Se aplică condiția de acces „{value}”.",
        "Действует условие доступа «{value}».",
    ),
    "service_condition": (
        "Bitte beachte die Bedingung „{value}“.", "Please note the condition “{value}”.",
        "Zwróć uwagę na warunek „{value}”.", "Te rugăm să ții cont de condiția „{value}”.",
        "Учти условие «{value}».",
    ),
    "note": (
        "Bitte beachte den Hinweis „{value}“.", "Please note the following: “{value}”.",
        "Zwróć uwagę na informację „{value}”.", "Te rugăm să ții cont de informația „{value}”.",
        "Учти следующую информацию: «{value}».",
    ),
    "description": (
        "Das Angebot wird so beschrieben: „{value}“.", "The service is described as follows: “{value}”.",
        "Ofertę opisano następująco: „{value}”.", "Oferta este descrisă astfel: „{value}”.",
        "Услуга описана так: «{value}».",
    ),
    "facility": (
        "Zur Ausstattung gehört laut Quelle „{value}“.", "The listed facilities include “{value}”.",
        "Podane wyposażenie obejmuje „{value}”.", "Dotările indicate includ „{value}”.",
        "Согласно источнику, оснащение включает «{value}».",
    ),
    "fee": (
        "Zu den Kosten ist „{value}“ angegeben.", "The listed cost information is “{value}”.",
        "Podana informacja o kosztach to „{value}”.", "Informația indicată despre costuri este „{value}”.",
        "О стоимости указано следующее: «{value}».",
    ),
    "fee_status": (
        "Für die Kosten gilt die Angabe „{value}“.", "The fee status is listed as “{value}”.",
        "Podany status opłat to „{value}”.", "Statutul taxei este indicat ca „{value}”.",
        "Статус оплаты указан как «{value}».",
    ),
    "district": (
        "Der angegebene Stadtteil ist {value}.", "The listed district is {value}.",
        "Podana dzielnica to {value}.", "Cartierul indicat este {value}.", "Указанный район — {value}.",
    ),
    "operator": (
        "Betreiber ist {value}.", "The operator is {value}.",
        "Operatorem jest {value}.", "Operatorul este {value}.", "Оператор — {value}.",
    ),
    "air_distance": (
        "Der Ort liegt {value} Luftlinie vom Hauptbahnhof entfernt.", "The place is {value} from the main station in a straight line.",
        "Miejsce jest oddalone o {value} w linii prostej od dworca głównego.", "Locul este la {value} în linie dreaptă de gara principală.",
        "Место находится в {value} по прямой от главного вокзала.",
    ),
    "location_description": (
        "Der Standort ist so beschrieben: „{value}“.", "The location is described as follows: “{value}”.",
        "Lokalizację opisano następująco: „{value}”.", "Amplasarea este descrisă astfel: „{value}”.",
        "Местоположение описано так: «{value}».",
    ),
    "potable_water_status": (
        "Zum Trinkwasser gilt die Angabe „{value}“.", "The drinking-water information is “{value}”.",
        "Podana informacja o wodzie pitnej to „{value}”.", "Informația indicată despre apa potabilă este „{value}”.",
        "О питьевой воде указано следующее: «{value}».",
    ),
    "seasonal_status": (
        "Für die Saison gilt die Angabe „{value}“.", "The listed season information is “{value}”.",
        "Podana informacja o sezonie to „{value}”.", "Informația indicată despre sezon este „{value}”.",
        "О сезоне указано следующее: «{value}».",
    ),
    "operation_status": (
        "Zum Betrieb ist „{value}“ angegeben.", "The recorded operation status is “{value}”.",
        "Podany status działania to „{value}”.", "Starea de funcționare înregistrată este „{value}”.",
        "О работе указано следующее: «{value}».",
    ),
    "source": (
        "Die angegebene Quelle ist {value}.", "The listed source is {value}.",
        "Podane źródło to {value}.", "Sursa indicată este {value}.", "Указанный источник — {value}.",
    ),
}


def display_value(value: str) -> str:
    """Drop outer source formatting without removing a condition or clause."""
    lines = []
    for line in value.splitlines():
        previous = None
        while previous != line:
            previous, line = line, _PREFIX.sub("", line)
        if line.strip():
            lines.append(line.strip())
    # Preserve line boundaries as readable pauses, never concatenate two words.
    return " / ".join(lines)


def _join(values: list[str], language: Language) -> str:
    if len(values) == 1:
        return values[0]
    conjunction = ("und", "and", "i", "și", "и")[_LANGUAGES.index(language)]
    return ", ".join(values[:-1]) + " " + conjunction + " " + values[-1]


def fact_sentences(name: str, facts: list[tuple[str, str]], language: Language) -> str:
    """Group same-type evidence into full sentences; keep every distinct value."""
    groups: dict[str, list[str]] = {}
    for kind, value in facts:
        values = groups.setdefault(kind, [])
        value = display_value(value)
        if value not in values:
            values.append(value)
    index = _LANGUAGES.index(language)
    sentences = []
    if "service" not in groups:
        sentences.append(_SENTENCES["intro"][index].format(name=name))
    order = (["service"] if "service" in groups else []) + [kind for kind in groups if kind != "service"]
    for kind in order:
        values = groups[kind]
        # Stop punctuation belongs to the sentence, not to a field label.
        value = _join(values, language)
        sentence = _SENTENCES[kind][index].format(name=name, value=value)
        if value.endswith((".", "!", "?")) and sentence.endswith(value + "."):
            sentence = sentence[:-1]
        sentences.append(sentence)
    return " ".join(sentences)
