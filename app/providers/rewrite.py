from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import re

import httpx

from ..kb import KnowledgeBase
from ..models import (
    ConversationContext,
    KnowledgeAnswer,
    LLMKnowledgeAnswer,
    Language,
    MapData,
    MapOrigin,
    PageMetadata,
    RetrievedPage,
    TemporalContext,
)
from ..retrieval import (
    HOURS_QUERY_TOKENS,
    LOCATION_QUERY_TOKENS,
    RetrievalEngine,
    WINTER_QUERY_TERMS,
    extract_relevant_passages,
    normalize_text,
    query_tokens_for_search,
    tokenize,
)
from ..symbols import toilet_map_destinations


UNKNOWN_TEXT = {
    Language.DE: "Das weiß ich nicht sicher. Ich habe dazu keine sichere Information. Bitte frage nach Essen, Schlafen, Kleidung, Medizin, Beratung, Hygiene, Dokumenten oder Wasser.",
    Language.EN: "I do not know that for sure. I do not have safe information about that. You can ask about food, sleeping places, clothing, medical help, counselling, hygiene, documents or water.",
    Language.PL: "Nie wiem tego na pewno. Nie mam bezpiecznej informacji na ten temat. Mozesz zapytac o jedzenie, nocleg, ubrania, pomoc medyczna, porady, higiene, dokumenty albo wode.",
    Language.RO: "Nu stiu sigur. Nu am o informatie sigura despre asta. Poti intreba despre mancare, dormit, haine, ajutor medical, consiliere, igiena, documente sau apa.",
    Language.RU: "Ya ne znayu eto tochno. U menya net nadezhnoy informatsii ob etom. Vy mozhete sprosit pro edu, nochleg, odezhdu, meditsinskuyu pomoshch, konsultatsiyu, gigienu, dokumenty ili vodu.",
}
OVERVIEW_DETAIL_OFFER = {
    Language.DE: "Wenn Sie möchten, nenne ich Ihnen die genauen Standorte und Uhrzeiten.",
    Language.EN: "If you want, I can give you the exact locations and opening hours.",
    Language.PL: "Jesli chcesz, moge podac dokladne miejsca i godziny otwarcia.",
    Language.RO: "Daca vrei, pot spune locatiile exacte si programul.",
    Language.RU: "Esli hotite, ya mogu nazvat tochnye adresy i chasy raboty.",
}
OVERVIEW_HOURS_VARY = {
    Language.DE: "Die Zeiten unterscheiden sich je nach Standort.",
    Language.EN: "The times vary by location.",
    Language.PL: "Godziny roznia sie w zaleznosci od miejsca.",
    Language.RO: "Programul difera in functie de locatie.",
    Language.RU: "Vremya raboty zavisit ot mesta.",
}
OVERVIEW_REGISTRATION = {
    Language.DE: "Eine Anmeldung ist vorher nötig.",
    Language.EN: "Registration is needed in advance.",
    Language.PL: "Wczesniejsza rejestracja jest potrzebna.",
    Language.RO: "Este necesara o inregistrare inainte.",
    Language.RU: "Nuzhna predvaritelnaya registratsiya.",
}

CLARIFY_TEXT = {
    Language.DE: "Welche Hilfe brauchen Sie genau?",
    Language.EN: "What kind of help do you need?",
    Language.PL: "Jakiej pomocy dokladnie potrzebujesz?",
    Language.RO: "De ce tip de ajutor ai nevoie exact?",
    Language.RU: "ÐœÐ¾Ð¶ÐµÑ‚Ðµ ÐºÐ¾Ñ€Ð¾Ñ‚ÐºÐ¾ ÑÐºÐ°Ð·Ð°Ñ‚ÑŒ, ÐºÐ°ÐºÐ°Ñ Ð¿Ð¾Ð¼Ð¾Ñ‰ÑŒ Ð²Ð°Ð¼ Ð½ÑƒÐ¶Ð½Ð°?",
}

WEAK_PREFIX = {
    Language.DE: "Das passt vielleicht: ",
    Language.EN: "This may help: ",
    Language.PL: "To moze pomoc: ",
    Language.RO: "Asta poate ajuta: ",
    Language.RU: "Eto mozhet pomoch: ",
}

OUT_OF_SCOPE_TEXT = {
    Language.DE: "Dabei kann ich dir nicht helfen. Ich beantworte nur Fragen zu Hilfsangeboten in Leipzig. Bitte frage nach Essen, Schlafen, Kleidung, Medizin, Beratung, Hygiene, Dokumenten oder Wasser.",
    Language.EN: "I cannot help with that. I only answer questions about local help services in Leipzig. You can ask about food, sleeping places, clothing, medical help, counselling, hygiene, documents or water.",
    Language.PL: "Nie moge w tym pomoc. Odpowiadam tylko na pytania o pomoc w Lipsku. Mozesz zapytac o jedzenie, nocleg, ubrania, pomoc medyczna, porady, higiene, dokumenty albo wode.",
    Language.RO: "Nu pot ajuta cu asta. Raspund doar la intrebari despre ajutor local in Leipzig. Poti intreba despre mancare, dormit, haine, ajutor medical, consiliere, igiena, documente sau apa.",
    Language.RU: "Ya ne mogu s etim pomoch. Ya otvechayu tolko na voprosy o pomoshchi v Leyptsige. Vy mozhete sprosit pro edu, nochleg, odezhdu, meditsinskuyu pomoshch, konsultatsiyu, gigienu, dokumenty ili vodu.",
}
SELF_DESCRIPTION_TEXT = {
    Language.DE: "Ich bin LENA, der Leipzig Empowerment and Navigation Assistant. Ich helfe mit lokalen Informationen zu Hilfsangeboten in Leipzig, zum Beispiel zu Orten, Adressen, Öffnungszeiten und passenden Anlaufstellen.",
    Language.EN: "I am LENA, the Leipzig Empowerment and Navigation Assistant. I help with local information about support services in Leipzig, for example places, addresses, opening hours, and suitable services.",
    Language.PL: "Jestem LENA, Leipzig Empowerment and Navigation Assistant. Pomagam lokalnymi informacjami o uslugach wsparcia w Lipsku, na przyklad o miejscach, adresach, godzinach otwarcia i odpowiednich punktach pomocy.",
    Language.RO: "Sunt LENA, Leipzig Empowerment and Navigation Assistant. Ajut cu informatii locale despre servicii de sprijin din Leipzig, de exemplu despre locuri, adrese, program si puncte potrivite de ajutor.",
    Language.RU: "Ya LENA, Leipzig Empowerment and Navigation Assistant. Ya pomogayu s mestnoy informatsiyey o sluzhbakh podderzhki v Leyptsige, naprimer o mestakh, adresakh, chasakh raboty i podkhodyashchikh punktakh pomoshchi.",
}
CRISIS_TEXT = {
    Language.DE: "Das klingt nach einer akuten Gefahr. Bitte ruf sofort den Notruf 112 an. Wenn Gewalt oder Gefahr durch andere Menschen besteht, ruf die Polizei 110. Wenn du am Bahnhof bist: Geh zu Mitarbeitenden, zur Bahnhofsmission oder zu einem Arzt. Bleib nicht allein.",
    Language.EN: "This sounds like immediate danger. Please call emergency services now: 112. If there is violence or danger from another person, call the police: 110. If you are at the station, go to staff, Bahnhofsmission or a doctor. Do not stay alone.",
    Language.PL: "To brzmi jak bezposrednie zagrozenie. Zadzwon teraz pod numer alarmowy 112. Jesli grozi ci przemoc albo inna osoba jest zagrozeniem, zadzwon na policje: 110. Jesli jestes na dworcu, idz do pracownikow, do Bahnhofsmission albo do lekarza. Nie zostawaj sam.",
    Language.RO: "Pare un pericol imediat. Suna acum la urgenta: 112. Daca exista violenta sau pericol de la alta persoana, suna la politie: 110. Daca esti la gara, mergi la personal, la Bahnhofsmission sau la un medic. Nu ramane singur.",
    Language.RU: "Eto pokhozhe na neposredstvennuyu opasnost. Pozvonite seychas v sluzhbu pomoshchi: 112. Esli est nasilie ili opasnost ot drugogo cheloveka, pozvonite v politsiyu: 110. Esli vy na vokzale, obratites k sotrudnikam, v Bahnhofsmission ili k vrachu. Ne ostavaytes odni.",
}
SELF_DESCRIPTION_PATTERNS = (
    "wer bist du",
    "was bist du",
    "was ist lena",
    "wofuer bist du da",
    "wofur bist du da",
    "was kannst du",
    "wie kannst du helfen",
    "who are you",
    "what are you for",
    "what is lena",
    "what can you help with",
    "what can you do",
    "how can you help me",
    "kim jestes",
    "co to jest lena",
    "w czym mozesz pomoc",
    "cine esti",
    "ce este lena",
    "cum ma poti ajuta",
    "ÐºÑ‚Ð¾ Ñ‚Ñ‹",
    "Ñ‡Ñ‚Ð¾ Ñ‚Ð°ÐºÐ¾Ðµ lena",
    "Ñ‡ÐµÐ¼ Ñ‚Ñ‹ Ð¼Ð¾Ð¶ÐµÑˆÑŒ Ð¿Ð¾Ð¼Ð¾Ñ‡ÑŒ",
)
DOMAIN_TERMS = {
    "adresse",
    "address",
    "anlaufstelle",
    "bahnhof",
    "beratung",
    "dusche",
    "duschen",
    "essen",
    "food",
    "hauptbahnhof",
    "hilfe",
    "hours",
    "housing",
    "leipzig",
    "location",
    "medical",
    "medizin",
    "obdach",
    "oeffnungszeiten",
    "open",
    "place",
    "service",
    "services",
    "shower",
    "shelter",
    "support",
    "toilet",
    "toilette",
    "toiletten",
    "unterkunft",
    "wc",
    "wohnungslos",
}
OUT_OF_SCOPE_TOKENS = {
    "astronomy",
    "bitcoin",
    "capital",
    "code",
    "computer",
    "film",
    "football",
    "game",
    "javascript",
    "joke",
    "linux",
    "math",
    "mathe",
    "movie",
    "opinion",
    "orbit",
    "hauptstadt",
    "politik",
    "politics",
    "president",
    "programming",
    "python",
    "recipe",
    "science",
    "sport",
    "stocks",
    "telescope",
    "translate",
    "translation",
    "weather",
    "wetter",
    "witz",
}
OUT_OF_SCOPE_PATTERNS = (
    "what do you think",
    "was denkst du",
    "was haeltst du von",
    "was haltst du von",
    "deine meinung",
    "your opinion",
    "capital of",
    "how do telescopes work",
    "wie funktionieren teleskope",
    "write code",
    "schreib code",
    "write a poem",
    "tell me a joke",
    "erzaehl mir einen witz",
)
CRISIS_SERVICE_QUERY_HINTS = ("telefonseelsorge", "seelsorge", "notfallkontakte", "notdienste", "notdienst")
CRISIS_DIRECT_PATTERNS = (
    "ich bringe mich um",
    "ich will sterben",
    "ich moechte sterben",
    "ich mochte sterben",
    "ich will mich umbringen",
    "ich will mich toeten",
    "ich will mich toten",
    "ich will mir etwas antun",
    "ich tue mir etwas an",
    "ich will mich verletzen",
    "ich verletze mich",
    "ich will jemanden verletzen",
    "ich bringe jemanden um",
    "ich werde angegriffen",
    "jemand greift mich",
    "jemand greift mich an",
    "ich bin in gefahr",
    "akute gefahr",
    "akuter notfall",
    "medizinischer notfall",
    "ich habe eine ueberdosis",
    "ich habe eine uberdosis",
    "ich habe eine vergiftung",
    "jemand ist bewusstlos",
    "ich bin bewusstlos",
    "starke blutung",
    "schwere verletzung",
    "ich kann nicht atmen",
    "ich bekomme keine luft",
    "ich habe atemnot",
    "ich habe starke brustschmerzen",
    "ich habe brustschmerz",
    "ich blute stark",
    "ich erfriere",
    "ich bin unterkuehlt",
    "ich bin unterkuhlt",
    "i want to die",
    "i want to kill myself",
    "i will kill myself",
    "i want to hurt myself",
    "i will hurt myself",
    "i will hurt someone",
    "i want to hurt someone",
    "i want to kill someone",
    "i am being attacked",
    "someone is attacking me",
    "i am in danger",
    "immediate danger",
    "medical emergency",
    "i took an overdose",
    "i overdosed",
    "i have an overdose",
    "i have poisoning",
    "someone is unconscious",
    "severe bleeding",
    "serious injury",
    "i can't breathe",
    "i cant breathe",
    "i cannot breathe",
    "i have shortness of breath",
    "i have chest pain",
    "i am bleeding badly",
    "i am freezing",
    "i have hypothermia",
    "kill myself",
    "hurt myself",
    "chce umrzec",
    "zabije sie",
    "mam przedawkowanie",
    "vreau sa mor",
    "nu pot sa respir",
    "am luat o supradoza",
    "Ñ Ñ…Ð¾Ñ‡Ñƒ ÑƒÐ¼ÐµÑ€ÐµÑ‚ÑŒ",
    "Ñ Ñ…Ð¾Ñ‡Ñƒ ÑƒÐ±Ð¸Ñ‚ÑŒ ÑÐµÐ±Ñ",
    "Ñ Ð½Ðµ Ð¼Ð¾Ð³Ñƒ Ð´Ñ‹ÑˆÐ°Ñ‚ÑŒ",
    "Ñƒ Ð¼ÐµÐ½Ñ Ð¿ÐµÑ€ÐµÐ´Ð¾Ð·Ð¸Ñ€Ð¾Ð²ÐºÐ°",
)
CRISIS_DIRECT_TOKENS = {
    "attack",
    "attacke",
    "angegriffen",
    "angriff",
    "atemnot",
    "bedroht",
    "bewusstlos",
    "bleeding",
    "brustschmerz",
    "brustschmerzen",
    "emergency",
    "erfriere",
    "gewalt",
    "greift",
    "hypothermia",
    "notfall",
    "poisoning",
    "vergiftung",
    "verletzung",
    "violence",
    "unconscious",
    "overdose",
    "selbstmord",
    "suicide",
    "suizid",
    "ueberdosis",
    "uberdosis",
}

TOPIC_LABELS = {
    "food": {
        Language.DE: "Essen",
        Language.EN: "food",
        Language.PL: "jedzenie",
        Language.RO: "mancare",
        Language.RU: "ÐµÐ´Ð°",
    },
    "shelter": {
        Language.DE: "Unterkunft",
        Language.EN: "shelter",
        Language.PL: "nocleg",
        Language.RO: "adapost",
        Language.RU: "Ð½Ð¾Ñ‡Ð»ÐµÐ³",
    },
    "clothing": {
        Language.DE: "Kleidung",
        Language.EN: "clothing",
        Language.PL: "ubrania",
        Language.RO: "haine",
        Language.RU: "Ð¾Ð´ÐµÐ¶Ð´Ð°",
    },
    "medical": {
        Language.DE: "medizinische Hilfe",
        Language.EN: "medical help",
        Language.PL: "pomoc medyczna",
        Language.RO: "ajutor medical",
        Language.RU: "Ð¼ÐµÐ´Ð¸Ñ†Ð¸Ð½ÑÐºÐ°Ñ Ð¿Ð¾Ð¼Ð¾Ñ‰ÑŒ",
    },
    "addiction": {
        Language.DE: "Sucht",
        Language.EN: "addiction support",
        Language.PL: "pomoc przy uzaleznieniu",
        Language.RO: "sprijin pentru dependenta",
        Language.RU: "Ð¿Ð¾Ð¼Ð¾Ñ‰ÑŒ Ð¿Ñ€Ð¸ Ð·Ð°Ð²Ð¸ÑÐ¸Ð¼Ð¾ÑÑ‚Ð¸",
    },
    "debt": {
        Language.DE: "Schulden",
        Language.EN: "debt advice",
        Language.PL: "dlugi",
        Language.RO: "datorii",
        Language.RU: "Ð´Ð¾Ð»Ð³Ð¸",
    },
    "counseling": {
        Language.DE: "Beratung",
        Language.EN: "counseling",
        Language.PL: "poradnictwo",
        Language.RO: "consiliere",
        Language.RU: "ÐºÐ¾Ð½ÑÑƒÐ»ÑŒÑ‚Ð°Ñ†Ð¸Ñ",
    },
}
TOPIC_KEYWORDS = {
    "food": {"essen", "tafel", "lebensmittel", "mahlzeit", "food"},
    "shelter": {"unterkunft", "uebernachtung", "notunterkunft", "notunterbringung", "wohnungslosigkeit"},
    "clothing": {"kleidung", "kleiderkammer", "kleiderspenden"},
    "medical": {"gesundheit", "arzt", "medizin", "sprechstunde", "krankenversicherung"},
    "addiction": {"sucht", "drogen", "methadon", "substitution", "schadensminimierung", "konsum"},
    "debt": {"schulden", "schuldnerberatung", "mietrecht"},
    "counseling": {"beratung", "notlagen", "hilfe"},
}
ATTRIBUTE_QUERY_TOKENS = {
    "adresse",
    "appointment",
    "dusche",
    "duschen",
    "duschgelegenheit",
    "email",
    "kontakt",
    "koerperpflege",
    "mail",
    "oeffnungszeiten",
    "offen",
    "telefon",
    "termin",
    "uhr",
    "waeschepflege",
    "waschen",
    "zeit",
}
MULTI_OPTION_QUERY_HINTS = {"essen", "food", "unterkunft", "shelter", "kleidung", "clothing", "another", "andere", "alternative"}
TODAY_QUERY_HINTS = {"today", "heute"}
APPOINTMENT_QUERY_TOKENS = {"termin", "appointment", "anmeldung", "registration"}
LOCATION_REQUIRED_TOKENS = {
    "adresse",
    "address",
    "brunnen",
    "drinking",
    "fountain",
    "location",
    "naehe",
    "nahe",
    "nearest",
    "naechste",
    "naechster",
    "nächste",
    "nächster",
    "standort",
    "toilet",
    "toilette",
    "toiletten",
    "trinkbrunnen",
    "trinkwasser",
    "trinkwasserbrunnen",
    "wasser",
    "water",
    "wc",
}
NO_CONCRETE_LOCATION_TEXT = {
    Language.DE: "Dazu habe ich keinen sicheren konkreten Standort. Bitte frage nach einem anderen Hilfsangebot in Leipzig.",
    Language.EN: "I do not have a safe concrete location for this. I can only name places that are available in my local information.",
    Language.PL: "Nie mam do tego bezpiecznego konkretnego miejsca. Mogę podać tylko miejsca z moich lokalnych informacji.",
    Language.RO: "Nu am un loc concret sigur pentru asta. Pot numi doar locuri care apar in informatiile mele locale.",
    Language.RU: "U menya net nadezhnogo konkretnogo mesta dlya etogo. Ya mogu nazvat tolko mesta iz moey lokalnoy informatsii.",
}
NO_CONCRETE_WATER_LOCATION_TEXT = {
    Language.DE: "Ich habe dazu keinen sicheren konkreten Trinkwasser-Standort. Ich kann nur Orte nennen, die in meinen Informationen mit Standort stehen.",
    Language.EN: "I do not have a safe concrete drinking-water location for this. I can only name places that are available in my local information.",
    Language.PL: "Nie mam bezpiecznego konkretnego miejsca z woda pitna. Mogę podać tylko miejsca z moich lokalnych informacji.",
    Language.RO: "Nu am un loc concret sigur pentru apa potabila. Pot numi doar locuri care apar in informatiile mele locale.",
    Language.RU: "U menya net nadezhnogo konkretnogo mesta s pityevoy vodoy. Ya mogu nazvat tolko mesta iz moey lokalnoy informatsii.",
}
TOILET_QUERY_TOKENS = {
    "bathroom",
    "klo",
    "klos",
    "public",
    "restroom",
    "toilet",
    "toilets",
    "toilette",
    "toiletten",
    "wc",
}
TOILET_QUERY_PATTERNS = (
    "aufs klo",
    "auf klo",
    "auf toilette",
    "auf die toilette",
    "city toilette",
    "city-toilette",
    "sanitaeranlage",
    "sanitaranlage",
    "sanitaere anlage",
    "sanitare anlage",
)
FREE_TOILET_QUERY_TOKENS = {
    "bezahlen",
    "free",
    "gratis",
    "kostenfrei",
    "kostenlos",
    "umsonst",
}
FREE_TOILET_QUERY_PATTERNS = (
    "ohne geld",
    "nichts bezahlen",
    "kostet nichts",
    "kostenfreie toilette",
    "kostenlose toilette",
)
DEFAULT_MAP_ORIGIN = MapOrigin(
    id="leipzig_hbf",
    label="Leipzig Hauptbahnhof",
    address="Willy-Brandt-Platz 5, 04109 Leipzig",
    latitude=51.3465518,
    longitude=12.3830858,
)
TOILET_RESPONSE_TEXT = {
    Language.DE: "Ich kenne öffentliche City-Toiletten in Leipzig. Viele sind ganztägig geöffnet und kosten meist 50 Cent. Mit Euroschlüssel sind sie kostenlos. Kostenfrei ist der Standort Lene-Voigt-Park. Die Karte zeigt die Standorte.",
    Language.EN: "I know public city toilets in Leipzig. Many are open all day and usually cost 50 cents. They are free with a Euro key. Lene-Voigt-Park is free. The map shows the locations.",
    Language.PL: "Znam publiczne toalety miejskie w Lipsku. Wiele jest otwartych caly dzien i zwykle kosztuje 50 centow. Z kluczem Euro sa bezplatne. Lene-Voigt-Park jest bezplatny. Mapa pokazuje miejsca.",
    Language.RO: "Cunosc toalete publice in Leipzig. Multe sunt deschise toata ziua si costa de obicei 50 de centi. Sunt gratuite cu cheia Euro. Lene-Voigt-Park este gratuit. Harta arata locurile.",
    Language.RU: "Ya znayu obshchestvennye gorodskie tualety v Leyptsige. Mnogie otkryty ves den i obychno stoyat 50 tsentov. S Euro key oni besplatnye. Lene-Voigt-Park besplatnyy. Karta pokazyvaet mesta.",
}
FREE_TOILET_RESPONSE_TEXT = {
    Language.DE: "Kostenfrei ist die öffentliche Toilette im Lene-Voigt-Park. Sie ist ganztägig geöffnet. Adresse: Lene-Voigt-Park, Reudnitz-Thonberg, Leipzig. Andere City-Toiletten kosten meist 50 Cent; mit Euroschlüssel sind sie kostenlos.",
    Language.EN: "The public toilet at Lene-Voigt-Park is free. It is open all day. Address: Lene-Voigt-Park, Reudnitz-Thonberg, Leipzig. Other city toilets usually cost 50 cents; they are free with a Euro key.",
    Language.PL: "Publiczna toaleta w Lene-Voigt-Park jest bezplatna. Jest otwarta caly dzien. Adres: Lene-Voigt-Park, Reudnitz-Thonberg, Leipzig. Inne toalety miejskie zwykle kosztuja 50 centow; z kluczem Euro sa bezplatne.",
    Language.RO: "Toaleta publica din Lene-Voigt-Park este gratuita. Este deschisa toata ziua. Adresa: Lene-Voigt-Park, Reudnitz-Thonberg, Leipzig. Alte toalete publice costa de obicei 50 de centi; cu cheia Euro sunt gratuite.",
    Language.RU: "Obshchestvennyy tualet v Lene-Voigt-Park besplatnyy. On otkryt ves den. Adres: Lene-Voigt-Park, Reudnitz-Thonberg, Leipzig. Drugie gorodskie tualety obychno stoyat 50 tsentov; s Euro key oni besplatnye.",
}
LOCATION_REQUIRED_PATTERNS = (
    "wo ist",
    "wo finde ich",
    "wo bekomme ich",
    "wo kann",
    "wo kann ich",
    "in der naehe",
    "in der nahe",
    "in der nähe",
    "where can i",
    "where is",
    "near me",
)
CONCRETE_HELP_QUERY_TOKENS = {
    "arzt",
    "beratung",
    "clothing",
    "counselling",
    "counseling",
    "documents",
    "dokumente",
    "dusche",
    "duschen",
    "essen",
    "food",
    "hygiene",
    "kleidung",
    "klo",
    "klos",
    "medical",
    "medizin",
    "schlafen",
    "sleeping",
    "toilet",
    "toilette",
    "toiletten",
    "unterkunft",
    "water",
    "wasser",
    "wc",
}
DAY_QUERY_TOKENS = {
    "montag",
    "dienstag",
    "mittwoch",
    "donnerstag",
    "freitag",
    "samstag",
    "samstags",
    "sonntag",
    "sonntags",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}
NOTICE_HINTS = ("ferien", "wartezeiten", "hinweisen", "stand:", "druck:", "impressum")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
SPACE_RE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_LIKE_RE = re.compile(r"\+?\d[\d\s()./-]{5,}\d")
TIME_OR_LONG_NUMBER_RE = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{2,5}\b")
FORBIDDEN_REDIRECT_PATTERNS = (
    "app herunterladen",
    "laden sie die app herunter",
    "lade die app herunter",
    "nutzen sie die app",
    "nutze die app",
    "website besuchen",
    "auf der website nachsehen",
    "online suchen",
    "google maps",
    "im internet suchen",
    "die app zeigt",
    "der kuerzeste weg wird angezeigt",
    "der kurzeste weg wird angezeigt",
    "finden sie online",
    "finden sie in der app",
    "download the app",
    "use the app",
    "check the website",
    "search online",
    "use google maps",
    "the app will show",
    "find it online",
)


class BaseRewriteProvider(ABC):
    name = "base"
    model_name: str | None = None
    uses_llm = False
    last_answer_source = "unknown"
    last_resolved_transcript: str | None = None
    last_retrieved_page_ids: list[str] = []
    last_evidence_context: str = ""
    last_prompt_hash: str | None = None
    last_system_prompt_hash: str | None = None
    last_user_prompt_hash: str | None = None
    last_validation_error: str | None = None
    last_provider_error: str | None = None

    @abstractmethod
    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: KnowledgeBase,
        conversation_context: ConversationContext | None = None,
        temporal_context: TemporalContext | None = None,
    ) -> KnowledgeAnswer:
        raise NotImplementedError


def _known_response_page_ids(kb: KnowledgeBase, *page_ids: str) -> list[str]:
    available = {page.page_id for page in kb.dataset.pages}
    return [page_id for page_id in page_ids if page_id in available]


def _self_description_answer(language: Language) -> KnowledgeAnswer:
    return KnowledgeAnswer(
        answer_text=SELF_DESCRIPTION_TEXT[language],
        status="self_description",
        self_description=True,
    )


def _crisis_answer(language: Language, kb: KnowledgeBase) -> KnowledgeAnswer:
    return KnowledgeAnswer(
        answer_text=CRISIS_TEXT[language],
        status="crisis",
        crisis_mode=True,
        retrieved_page_ids=_known_response_page_ids(kb, "notfallkontakte", "telefonseelsorge-leipzig"),
    )


def _out_of_scope_answer(language: Language) -> KnowledgeAnswer:
    return KnowledgeAnswer(
        answer_text=OUT_OF_SCOPE_TEXT[language],
        status="out_of_scope",
        out_of_scope=True,
    )


def _no_concrete_location_answer(language: Language, transcript: str, retrieved: list[RetrievedPage] | None = None) -> KnowledgeAnswer:
    return KnowledgeAnswer(
        answer_text=NO_CONCRETE_WATER_LOCATION_TEXT[language] if _is_water_query(transcript) else NO_CONCRETE_LOCATION_TEXT[language],
        status="unknown",
        retrieved_page_ids=[item.page_id for item in retrieved or []],
    )


def _has_domain_signal(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    return "leipzig" in normalized or "hauptbahnhof" in normalized or bool(tokens & DOMAIN_TERMS)


def _is_self_description_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    return any(pattern in normalized for pattern in SELF_DESCRIPTION_PATTERNS)


def _is_crisis_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    service_lookup = any(hint in normalized for hint in CRISIS_SERVICE_QUERY_HINTS)
    direct_pattern = any(pattern in normalized for pattern in CRISIS_DIRECT_PATTERNS)
    direct_tokens = bool(tokens & CRISIS_DIRECT_TOKENS)
    informational = any(
        phrase in normalized
        for phrase in (
            "was ist der notruf",
            "was ist die notrufnummer",
            "what is the emergency number",
            "what is emergency services",
            "wie lautet der notruf",
        )
    )
    if service_lookup and not (direct_pattern or direct_tokens):
        return False
    if informational and not direct_pattern:
        return False
    return direct_pattern or direct_tokens


def _is_out_of_scope_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    if _has_domain_signal(transcript):
        return False
    return any(pattern in normalized for pattern in OUT_OF_SCOPE_PATTERNS) or bool(tokens & OUT_OF_SCOPE_TOKENS)


def _is_water_query(transcript: str) -> bool:
    tokens = set(tokenize(transcript))
    normalized = normalize_text(transcript)
    return bool(tokens & {"brunnen", "trinkbrunnen", "trinkwasser", "trinkwasserbrunnen", "wasser", "water", "drinking", "fountain"}) or "drinking water" in normalized or "water fountain" in normalized


def _is_toilet_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    return bool(tokens & TOILET_QUERY_TOKENS) or any(pattern in normalized for pattern in TOILET_QUERY_PATTERNS)


def _is_free_toilet_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    return _is_toilet_query(transcript) and (
        bool(tokens & FREE_TOILET_QUERY_TOKENS) or any(pattern in normalized for pattern in FREE_TOILET_QUERY_PATTERNS)
    )


def _toilet_answer(language: Language, transcript: str, kb: KnowledgeBase) -> KnowledgeAnswer:
    free_only = _is_free_toilet_query(transcript)
    destinations = toilet_map_destinations(free_only=free_only)
    map_data = MapData(
        origin=DEFAULT_MAP_ORIGIN,
        destinations=destinations,
        selected_destination_id=destinations[0].id if destinations else None,
    )
    return KnowledgeAnswer(
        answer_text=(FREE_TOILET_RESPONSE_TEXT if free_only else TOILET_RESPONSE_TEXT)[language],
        status="ok",
        retrieved_page_ids=_known_response_page_ids(kb, "oeffentliche-toiletten"),
        map_data=map_data if destinations else None,
    )


def _is_sleep_query(transcript: str) -> bool:
    tokens = set(tokenize(transcript))
    normalized = normalize_text(transcript)
    return bool(tokens & {"schlafen", "uebernachten", "ubernachten", "unterkunft", "notunterkunft", "sleep", "sleeping", "shelter", "overnight", "stay"}) or "sleep tonight" in normalized or "stay tonight" in normalized


def _sleep_target_group(transcript: str) -> str | None:
    tokens = set(tokenize(transcript))
    normalized = normalize_text(transcript)
    if tokens & {"frau", "frauen", "woman", "women", "kobieta", "femeie"}:
        return "women"
    if tokens & {"mann", "maenner", "manner", "men", "male", "barbat"}:
        return "men"
    if tokens & {"jugend", "jugendliche", "jugendlicher", "kind", "kinder", "young", "youth", "child", "teenager"}:
        return "young"
    if any(term in normalized for term in ("psychisch", "psychiatr", "seelisch")):
        return "psychiatric"
    if tokens & {"drogen", "droge", "sucht", "abhaengig", "abhängig", "addiction", "drugs"}:
        return "addiction"
    return None


def _sleep_clarification_answer(language: Language, kb: KnowledgeBase) -> KnowledgeAnswer:
    questions = {
        Language.DE: "Für wen wird ein Schlafplatz gebraucht? Männer, Frauen, junge Person oder Kind? Wenn Sie nicht sicher sind, sagen Sie: nicht sicher.",
        Language.EN: "Who needs a sleeping place? Men, women, young person or child? If you are not sure, say: not sure.",
        Language.PL: "Dla kogo jest potrzebny nocleg? Mężczyzna, kobieta, młoda osoba albo dziecko? Jeśli nie wiesz, powiedz: nie wiem.",
        Language.RO: "Pentru cine este nevoie de un loc de dormit? Bărbat, femeie, tânăr sau copil? Dacă nu ești sigur, spune: nu sunt sigur.",
        Language.RU: "Кому нужно место для ночлега? Мужчине, женщине, молодому человеку или ребенку? Если не знаете, скажите: не знаю.",
    }
    return KnowledgeAnswer(
        answer_text=questions[language],
        status="clarification_needed",
        clarification_needed=True,
        clarification_question=questions[language],
        retrieved_page_ids=_known_response_page_ids(
            kb,
            "wohnungsnotfallhilfe-pdf-uebernachtungshaus-maenner",
            "wohnungsnotfallhilfe-pdf-uebernachtungshaus-frauen-katalog",
            "wohnungsnotfallhilfe-pdf-jugendnotdienst",
            "wohnungsnotfallhilfe-pdf-kindernotdienst",
        ),
    )


def _is_location_required_query(transcript: str, language: Language) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(query_tokens_for_search(transcript, language)) | set(tokenize(transcript))
    if any(pattern in normalized for pattern in LOCATION_REQUIRED_PATTERNS):
        return True
    if tokens & LOCATION_REQUIRED_TOKENS:
        return True
    return bool(tokens & CONCRETE_HELP_QUERY_TOKENS and any(pattern in normalized for pattern in ("wo ", "where ", "near", "naehe", "nähe")))


def _is_address_detail_query(transcript: str, language: Language) -> bool:
    tokens = set(query_tokens_for_search(transcript, language)) | set(tokenize(transcript))
    return bool(tokens & {"adresse", "address"})


def _is_concrete_location_page(page: PageMetadata) -> bool:
    if page.service_type == "service_catalog" or page.entity_kind == "service_program":
        return False
    if page.latitude is not None and page.longitude is not None and _is_leipzig_coordinate(page.latitude, page.longitude):
        return True
    if page.address and _looks_like_leipzig_address(page.address):
        return True
    return False


def _is_leipzig_coordinate(latitude: float, longitude: float) -> bool:
    return 51.26 <= latitude <= 51.41 and 12.20 <= longitude <= 12.52


def _looks_like_leipzig_address(address: str) -> bool:
    normalized = normalize_text(address)
    if any(term in normalized for term in ("markkleeberg", "markranstadt", "markranstaedt", "borna")):
        return False
    if "leipzig" in normalized or re.search(r"\b04[123]\d{2}\b", normalized):
        return True
    street_words = ("strasse", "str", "platz", "ring", "weg", "gasse", "allee")
    return any(word in normalized for word in street_words) and bool(re.search(r"\d", normalized))


def _concrete_location_items(kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> list[RetrievedPage]:
    concrete = [item for item in retrieved if _is_concrete_location_page(kb.get_page(item.page_id))]
    concrete.sort(key=lambda item: (-item.score, item.page_id))
    return concrete


def _filter_sleep_items_by_target(kb: KnowledgeBase, items: list[RetrievedPage], target_group: str | None) -> list[RetrievedPage]:
    if not target_group:
        return items
    filtered: list[RetrievedPage] = []
    for item in items:
        page = kb.get_page(item.page_id)
        page_targets = set(page.target_groups)
        if target_group == "men" and (page.gender_access == "men" or "men" in page_targets):
            filtered.append(item)
        elif target_group == "women" and (page.gender_access == "women" or "women" in page_targets):
            filtered.append(item)
        elif target_group == "young" and page.service_type in {"youth_emergency_housing", "child_emergency_housing"}:
            filtered.append(item)
        elif target_group == "psychiatric" and (page.service_type == "protected_housing" or "psychisch" in normalize_text(page.title)):
            filtered.append(item)
        elif target_group == "addiction" and (page.category == "addiction" or "addiction" in page_targets or "sucht" in normalize_text(page.title)):
            filtered.append(item)
    if target_group in {"men", "women"}:
        overnight = [item for item in filtered if kb.get_page(item.page_id).service_type == "overnight_shelter"]
        if overnight:
            return overnight
    return filtered or items


def _contains_forbidden_redirect(answer_text: str) -> bool:
    normalized = normalize_text(answer_text)
    return any(pattern in normalized for pattern in FORBIDDEN_REDIRECT_PATTERNS)


def _guarded_response(transcript: str, language: Language, kb: KnowledgeBase) -> KnowledgeAnswer | None:
    if _is_crisis_query(transcript):
        return _crisis_answer(language, kb)
    if _is_self_description_query(transcript):
        return _self_description_answer(language)
    return None


def _ground_query(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    minimum_match_threshold: float,
    clarification_gap_threshold: float,
    weak_match_threshold: float,
    conversation_context: ConversationContext | None = None,
    temporal_context: TemporalContext | None = None,
) -> tuple[list[RetrievedPage], KnowledgeAnswer | None]:
    guarded = _guarded_response(transcript, language, kb)
    if guarded:
        return [], guarded
    if _is_toilet_query(transcript):
        return [], _toilet_answer(language, transcript, kb)
    if _is_out_of_scope_query(transcript):
        return [], _out_of_scope_answer(language)
    if _is_sleep_query(transcript) and _sleep_target_group(transcript) is None:
        return [], _sleep_clarification_answer(language, kb)
    retrieval = RetrievalEngine(kb)
    resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
    retrieved = retrieval.retrieve(
        resolved_transcript,
        language,
        limit=8,
        preferred_page_ids=conversation_context.preferred_page_ids if conversation_context else None,
        excluded_page_ids=conversation_context.excluded_page_ids if conversation_context else None,
        temporal_context=temporal_context,
    )
    if not retrieved:
        if _is_out_of_scope_query(transcript):
            return [], _out_of_scope_answer(language)
        return [], KnowledgeAnswer(answer_text=UNKNOWN_TEXT[language], status="unknown")

    if (
        _is_location_required_query(transcript, language)
        and not _is_address_detail_query(transcript, language)
        and not _concrete_location_items(kb, retrieved)
    ):
        return retrieved, _no_concrete_location_answer(language, transcript, retrieved)

    anchored_follow_up = bool(
        conversation_context
        and conversation_context.follow_up_mode == "referential"
        and conversation_context.preferred_page_ids
        and retrieved
        and retrieved[0].page_id in conversation_context.preferred_page_ids
    )
    if not anchored_follow_up and retrieval.should_clarify(retrieved, transcript, clarification_gap_threshold):
        question = _build_clarification_question(language, kb, retrieved)
        return retrieved, KnowledgeAnswer(
            answer_text=question,
            status="clarification_needed",
            clarification_needed=True,
            clarification_question=question,
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    if _is_out_of_scope_query(transcript) and retrieved[0].score < weak_match_threshold:
        return retrieved, _out_of_scope_answer(language)

    if retrieved[0].score < minimum_match_threshold:
        return retrieved, KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    return retrieved, None


def _fallback_answer(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    retrieved: list[RetrievedPage],
    minimum_match_threshold: float,
    weak_match_threshold: float,
    conversation_context: ConversationContext | None = None,
    temporal_context: TemporalContext | None = None,
) -> KnowledgeAnswer:
    if _is_location_required_query(transcript, language) and not _is_address_detail_query(transcript, language):
        concrete_items = _concrete_location_items(kb, retrieved)
        if _is_sleep_query(transcript):
            concrete_items = _filter_sleep_items_by_target(kb, concrete_items, _sleep_target_group(transcript))
        if not concrete_items:
            return _no_concrete_location_answer(language, transcript, retrieved)
        top_page = kb.get_page(retrieved[0].page_id) if retrieved else None
        if _is_water_query(transcript) or _is_sleep_query(transcript) or not top_page or not _is_concrete_location_page(top_page):
            answer_text = _build_concrete_location_answer(transcript, language, kb, concrete_items)
            return KnowledgeAnswer(
                answer_text=answer_text,
                status="weak_match" if concrete_items[0].score < weak_match_threshold else "ok",
                weak_match=concrete_items[0].score < weak_match_threshold,
                retrieved_page_ids=[item.page_id for item in concrete_items],
            )

    if not retrieved or retrieved[0].score < minimum_match_threshold:
        return KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    snippet = _build_structured_answer(transcript, language, kb, retrieved, conversation_context=conversation_context, temporal_context=temporal_context)
    if not snippet:
        return KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    weak = retrieved[0].score < weak_match_threshold
    answer_text = snippet
    if weak:
        page = kb.get_page(retrieved[0].page_id)
        answer_text = f"{WEAK_PREFIX[language]}{page.title}. {snippet}"

    return KnowledgeAnswer(
        answer_text=answer_text,
        status="weak_match" if weak else "ok",
        weak_match=weak,
        retrieved_page_ids=[item.page_id for item in retrieved],
    )


def _build_concrete_location_answer(transcript: str, language: Language, kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> str:
    concrete_items = _concrete_location_items(kb, retrieved)[:3]
    if not concrete_items:
        return (NO_CONCRETE_WATER_LOCATION_TEXT if _is_water_query(transcript) else NO_CONCRETE_LOCATION_TEXT)[language]

    parts: list[str] = []
    water_query = _is_water_query(transcript)
    sleep_query = _is_sleep_query(transcript)
    if sleep_query:
        concrete_items = _filter_sleep_items_by_target(kb, concrete_items, _sleep_target_group(transcript))[:3]
    if language == Language.DE:
        if water_query:
            parts.append("Ich kenne diese Trinkwasser-Orte:")
        elif sleep_query:
            parts.append("Ich kenne diese Schlaf-Orte:")
        else:
            parts.append("Ich kenne diese Orte:")
        for item in concrete_items:
            page = kb.get_page(item.page_id)
            detail = page.title
            if page.address:
                detail += f". Adresse: {page.address}"
            parts.append(detail + ".")
        return _clean_answer_text(" ".join(parts))

    if language == Language.EN:
        if water_query:
            parts.append("I know these drinking-water places:")
        elif sleep_query:
            parts.append("I know these shelter places:")
        else:
            parts.append("I know these places:")
        for item in concrete_items:
            page = kb.get_page(item.page_id)
            detail = page.title
            if page.address:
                detail += f". Address: {page.address}"
            parts.append(detail + ".")
        return _clean_answer_text(" ".join(parts))

    for item in concrete_items:
        page = kb.get_page(item.page_id)
        detail = page.title
        if page.address:
            detail += f". {page.address}"
        parts.append(detail + ".")
    return _clean_answer_text(" ".join(parts))


def _family_key(title: str) -> str:
    return title.split(" - ", 1)[0].strip()


def _location_label(page: PageMetadata) -> str:
    if " - " in page.title:
        return page.title.split(" - ", 1)[1].strip()
    return page.title


def _join_labels(labels: list[str], language: Language) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    connector = {
        Language.DE: " und ",
        Language.EN: " and ",
        Language.PL: " i ",
        Language.RO: " si ",
        Language.RU: " i ",
    }[language]
    if len(labels) == 2:
        return connector.join(labels)
    return ", ".join(labels[:-1]) + connector + labels[-1]


def _title_match_ratio(query_tokens: set[str], title: str) -> float:
    title_tokens = set(tokenize(title))
    if not query_tokens or not title_tokens:
        return 0.0
    return len(query_tokens & title_tokens) / max(min(len(query_tokens), len(title_tokens)), 1)


def _is_overview_query(transcript: str, language: Language, kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> bool:
    if len(retrieved) < 2:
        return False
    normalized = normalize_text(transcript)
    if any(hint in normalized for hint in TODAY_QUERY_HINTS):
        return False
    query_tokens = set(query_tokens_for_search(transcript, language))
    if not query_tokens:
        return False
    if query_tokens & ATTRIBUTE_QUERY_TOKENS:
        return False
    if query_tokens & LOCATION_QUERY_TOKENS:
        return False
    if query_tokens & HOURS_QUERY_TOKENS:
        return False
    if query_tokens & WINTER_QUERY_TERMS:
        return False

    family_counts: dict[str, list[PageMetadata]] = {}
    for item in retrieved[:6]:
        page = kb.get_page(item.page_id)
        family_counts.setdefault(_family_key(page.title), []).append(page)

    top_page = kb.get_page(retrieved[0].page_id)
    if _title_match_ratio(query_tokens, top_page.title) >= 0.6:
        return False

    top_family = family_counts.get(_family_key(top_page.title), [])
    if len(top_family) < 2:
        broad_categories = {"food", "housing", "clothing"}
        if top_page.category not in broad_categories:
            return False

    specific_location_tokens: set[str] = set()
    for page in top_family:
        if " - " in page.title:
            specific_location_tokens.update(tokenize(page.title.split(" - ", 1)[1]))
        specific_location_tokens.update(tokenize(page.address or ""))
    if query_tokens & specific_location_tokens:
        return False
    return True


def _has_useful_details(page: PageMetadata) -> bool:
    if page.review_status == "needs_review":
        return False
    return bool(page.address or page.opening_hours or "warme mahlzeit" in page.description.casefold())


def _food_family_overview(language: Language, grouped: dict[str, list[PageMetadata]], unique_pages: list[PageMetadata]) -> list[str]:
    tafels = grouped.get("Tafel Leipzig", [])
    tafel_locations: list[str] = []
    for page in tafels:
        label = _location_label(page)
        if label != "Tafel Leipzig" and label not in tafel_locations:
            tafel_locations.append(label)
        if len(tafel_locations) == 3:
            break

    secondary_page = next(
        (
            page
            for page in unique_pages
            if _family_key(page.title) != "Tafel Leipzig"
            and page.category in {"food", "social", "addiction"}
            and _has_useful_details(page)
        ),
        None,
    )

    if language == Language.DE:
        sentences = ["Es gibt verschiedene Anlaufstellen für Essen und Lebensmittel in Leipzig."]
        if tafels:
            sentences.append("Bei der Tafel Leipzig gibt es mehrere Ausgabestellen für Lebensmittel.")
            if any(page.requires_registration for page in tafels):
                sentences.append(OVERVIEW_REGISTRATION[language])
            if tafel_locations:
                sentences.append(f"Zum Beispiel in {_join_labels(tafel_locations, language)}.")
        if secondary_page:
            detail_parts = [f"Ausserdem gibt es {secondary_page.title}"]
            if secondary_page.address:
                detail_parts.append(f"in {secondary_page.address}")
            if secondary_page.opening_hours:
                detail_parts.append(f"mit Zeiten wie {'; '.join(secondary_page.opening_hours[:2])}")
            elif secondary_page.description:
                detail_parts.append(f"mit {secondary_page.description.rstrip('.')}")
            sentences.append(" ".join(detail_parts).strip() + ".")
        sentences.append(OVERVIEW_DETAIL_OFFER[language])
        return sentences

    sentences = ["There are several places in Leipzig where you can get food."]
    if tafels:
        sentences.append("Tafel Leipzig has several food distribution points.")
        if any(page.requires_registration for page in tafels):
            sentences.append(OVERVIEW_REGISTRATION[language])
        if tafel_locations:
            sentences.append(f"For example in {_join_labels(tafel_locations, language)}.")
    if secondary_page:
        detail_parts = [f"There is also {secondary_page.title}"]
        if secondary_page.address:
            detail_parts.append(f"at {secondary_page.address}")
        if secondary_page.opening_hours:
            detail_parts.append(f"with times such as {'; '.join(secondary_page.opening_hours[:2])}")
        else:
            service_label = _service_type_label(secondary_page, language)
            if service_label:
                detail_parts.append(f"as {service_label}")
        sentences.append(" ".join(detail_parts).strip() + ".")
    sentences.append(OVERVIEW_DETAIL_OFFER[language])
    return sentences


def _build_overview_answer(transcript: str, language: Language, kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> str:
    if not _is_overview_query(transcript, language, kb, retrieved):
        return ""

    grouped: dict[str, list[PageMetadata]] = {}
    for item in retrieved[:8]:
        page = kb.get_page(item.page_id)
        grouped.setdefault(_family_key(page.title), []).append(page)

    top_page = kb.get_page(retrieved[0].page_id)
    family_name = _family_key(top_page.title)
    family_pages = grouped.get(family_name, [top_page])
    query_tokens = set(query_tokens_for_search(transcript, language))
    food_query = bool(query_tokens & {"essen", "food", "tafel", "lebensmittel", "mahlzeit", "mittagstisch", "suppe", "fruehstueck"})
    unique_pages: list[PageMetadata] = []
    seen_families: set[str] = set()
    for item in retrieved:
        page = kb.get_page(item.page_id)
        page_family = _family_key(page.title)
        if page_family in seen_families:
            continue
        seen_families.add(page_family)
        unique_pages.append(page)
        if len(unique_pages) == 4:
            break
    location_labels = []
    for page in family_pages:
        label = _location_label(page)
        if label != family_name and label not in location_labels:
            location_labels.append(label)
        if len(location_labels) == 3:
            break

    if language == Language.DE:
        if top_page.category == "food" or food_query:
            sentences = _food_family_overview(language, grouped, unique_pages)
        else:
            sentences = [f"Bei {family_name} gibt es mehrere passende Angebote."]
            if any(page.requires_registration for page in family_pages):
                sentences.append(OVERVIEW_REGISTRATION[language])
            if location_labels:
                sentences.append(f"Zum Beispiel in {_join_labels(location_labels, language)}.")
            if any(page.opening_hours for page in family_pages):
                sentences.append(OVERVIEW_HOURS_VARY[language])
        return " ".join(sentences)

    if top_page.service_type == "food_distribution" or top_page.category == "food" or food_query:
        sentences = _food_family_overview(language, grouped, unique_pages)
    else:
        sentences = [f"{family_name} has several relevant support options."]
    if sentences and sentences[-1] == OVERVIEW_DETAIL_OFFER[language]:
        return " ".join(sentences)
    if any(page.requires_registration for page in family_pages):
        sentences.append(OVERVIEW_REGISTRATION[language])
    if location_labels:
        if language == Language.EN:
            sentences.append(f"For example in {_join_labels(location_labels, language)}.")
        elif language == Language.PL:
            sentences.append(f"Na przyklad w {_join_labels(location_labels, language)}.")
        elif language == Language.RO:
            sentences.append(f"De exemplu in {_join_labels(location_labels, language)}.")
        else:
            sentences.append(f"Naprimer v {_join_labels(location_labels, language)}.")
    if any(page.opening_hours for page in family_pages):
        sentences.append(OVERVIEW_HOURS_VARY[language])
    sentences.append(OVERVIEW_DETAIL_OFFER[language])
    return " ".join(sentences)


def _build_retrieved_context(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    retrieved: list[RetrievedPage],
    conversation_context: ConversationContext | None = None,
    limit: int = 3,
) -> str:
    search_tokens = set(query_tokens_for_search(transcript, language))
    sections: list[str] = []
    effective_limit = limit
    if conversation_context and (conversation_context.preferred_page_ids or conversation_context.follow_up_mode == "referential"):
        effective_limit = 1
    if conversation_context and conversation_context.history_summary:
        sections.append(f"RECENT_CONTEXT:\n{conversation_context.history_summary}")
    if conversation_context and conversation_context.follow_up_mode != "none":
        sections.append(f"FOLLOW_UP_MODE: {conversation_context.follow_up_mode}")
    for item in _select_context_pages(transcript, kb, retrieved, limit=effective_limit):
        page = kb.get_page(item.page_id)
        passages = extract_relevant_passages(
            transcript,
            kb.get_page_markdown(page.page_id),
            query_tokens=search_tokens,
        )
        relevant_passages = [_clean_answer_text(passage) for passage in passages if _clean_answer_text(passage)] or [page.summary]
        sections.append(
            "\n".join(
                [
                    f"PAGE_ID: {page.page_id}",
                     f"TITLE: {page.title}",
                     f"SCORE: {item.score}",
                     f"LANGUAGE: {page.language}",
                     f"CATEGORY: {page.category}",
                     f"SERVICE_TYPE: {page.service_type}",
                     f"PUBLISHER: {page.publisher or ''}",
                     f"TARGET_GROUPS: {', '.join(page.target_groups)}",
                     f"GENDER_ACCESS: {page.gender_access or ''}",
                     f"ADDRESS: {page.address or ''}",
                     f"OPENING_HOURS: {' | '.join(page.opening_hours)}",
                     f"PHONE: {page.phone or ''}",
                     f"EMAIL: {page.email or ''}",
                     f"REVIEW_STATUS: {page.review_status}",
                     f"ALIASES: {', '.join(page.aliases)}",
                     f"SOURCE_URL: {page.source_url}",
                     f"SOURCE_SNAPSHOT_PATH: {page.source_snapshot_path or ''}",
                     f"SOURCE_LAST_SEEN: {page.source_last_seen or ''}",
                     f"LAST_UPDATED: {page.last_updated}",
                     f"DESCRIPTION: {_clean_answer_text(page.description)}",
                    f"TAGS: {', '.join(page.tags)}",
                    f"SUMMARY: {_clean_answer_text(page.summary)}",
                    "RELEVANT_PASSAGES:",
                    *[f"- {passage}" for passage in relevant_passages],
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def _page_detail_priority(page: PageMetadata) -> tuple[int, int, int, int]:
    return (
        0 if page.service_type == "service_catalog" else 1,
        1 if page.address else 0,
        1 if page.opening_hours else 0,
        0 if page.review_status == "needs_review" else 1,
    )


def _best_family_page(transcript: str, kb: KnowledgeBase, family_items: list[RetrievedPage]) -> RetrievedPage:
    if len(family_items) == 1:
        return family_items[0]
    normalized_transcript = normalize_text(transcript)
    best_item = family_items[0]
    best_rank = (-1, float("-inf"))
    for item in family_items:
        page = kb.get_page(item.page_id)
        title_tokens = set(tokenize(page.title))
        query_tokens = set(query_tokens_for_search(transcript))
        anchored = 1 if query_tokens & title_tokens else 0
        exact_title = 1 if normalized_transcript and normalize_text(page.title) in normalized_transcript else 0
        rank = (
            exact_title,
            anchored,
            *_page_detail_priority(page),
            item.score,
        )
        if rank > best_rank:
            best_rank = rank
            best_item = item
    return best_item


def _dedupe_family_results(transcript: str, kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> list[RetrievedPage]:
    family_order: list[str] = []
    family_items: dict[str, list[RetrievedPage]] = {}
    for item in retrieved:
        family = _family_key(kb.get_page(item.page_id).title)
        if family not in family_items:
            family_order.append(family)
            family_items[family] = []
        family_items[family].append(item)
    deduped = [_best_family_page(transcript, kb, family_items[family]) for family in family_order]
    deduped.sort(key=lambda item: (-item.score, item.page_id))
    return deduped


def _select_context_pages(transcript: str, kb: KnowledgeBase, retrieved: list[RetrievedPage], limit: int = 3) -> list[RetrievedPage]:
    if not retrieved:
        return []
    deduped = _dedupe_family_results(transcript, kb, retrieved)
    if len(deduped) == 1:
        return deduped[:1]

    top_score = deduped[0].score
    selected = [deduped[0]]
    for item in deduped[1:limit]:
        if item.score >= top_score * 0.45:
            selected.append(item)
    return selected[:limit]


def _build_structured_answer(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    retrieved: list[RetrievedPage],
    conversation_context: ConversationContext | None = None,
    temporal_context: TemporalContext | None = None,
) -> str:
    del conversation_context
    if not retrieved:
        return ""

    overview_answer = _build_overview_answer(transcript, language, kb, retrieved)
    if overview_answer:
        return _clean_answer_text(overview_answer)

    pages = _select_answer_pages(transcript, kb, retrieved)
    options = []
    for item in pages:
        page = kb.get_page(item.page_id)
        options.append(_format_page_option(page, transcript, language, temporal_context=temporal_context))
    return " ".join(option for option in options if option).strip()


def _has_specific_page_anchor(transcript: str, page: PageMetadata) -> bool:
    raw_query_tokens = set(tokenize(transcript))
    page_tokens = set(tokenize(" ".join([page.title, " ".join(page.aliases), page.address or ""])))
    for token in raw_query_tokens & page_tokens:
        if len(token) < 4:
            continue
        if token in MULTI_OPTION_QUERY_HINTS or token in ATTRIBUTE_QUERY_TOKENS or token in LOCATION_QUERY_TOKENS:
            continue
        return True
    return False


def _select_answer_pages(transcript: str, kb: KnowledgeBase, retrieved: list[RetrievedPage], limit: int = 3) -> list[RetrievedPage]:
    if not retrieved:
        return []
    deduped = _dedupe_family_results(transcript, kb, retrieved)
    normalized_transcript = normalize_text(transcript)
    query_tokens = set(query_tokens_for_search(transcript))
    if query_tokens & WINTER_QUERY_TERMS:
        concrete = [item for item in deduped if _is_concrete_location_page(kb.get_page(item.page_id))]
        if concrete:
            return concrete[:limit]
    if any(hint in normalized_transcript for hint in TODAY_QUERY_HINTS):
        return deduped[:1]
    if _has_specific_page_anchor(transcript, kb.get_page(deduped[0].page_id)):
        return deduped[:1]
    if not (query_tokens & MULTI_OPTION_QUERY_HINTS) and len(query_tokens) > 1:
        return deduped[:1]

    top_score = deduped[0].score
    selected: list[RetrievedPage] = []
    for item in deduped[:limit]:
        if item.score >= top_score * 0.55:
            selected.append(item)
    return selected or deduped[:1]


def _service_type_label(page: PageMetadata, language: Language) -> str:
    labels_de = {
        "day_center": "eine Tageseinrichtung",
        "food_distribution": "eine Ausgabestelle für Essen und Lebensmittel",
        "overnight_shelter": "ein Übernachtungshaus",
        "medical_consultation": "eine medizinische Sprechstunde",
        "counseling": "eine Beratungsstelle",
        "station_support": "ein Hilfsangebot am Bahnhof",
        "streetwork": "ein Streetwork-Angebot",
        "streetwork_food_outreach": "ein Streetwork-Angebot mit Essen und Beratung",
        "service_catalog": "eine Übersichtsseite",
    }
    labels_en = {
        "day_center": "a day center",
        "food_distribution": "a food distribution point",
        "overnight_shelter": "an overnight shelter",
        "medical_consultation": "a medical consultation service",
        "counseling": "a counseling service",
        "station_support": "a station support service",
        "streetwork": "a street outreach service",
        "streetwork_food_outreach": "a street outreach service with food and advice",
        "service_catalog": "an overview page",
    }
    return (labels_de if language == Language.DE else labels_en).get(page.service_type, "")


def _format_page_option(page: PageMetadata, transcript: str, language: Language, temporal_context: TemporalContext | None = None) -> str:
    normalized_transcript = normalize_text(transcript)
    query_tokens = set(query_tokens_for_search(transcript, language))
    attribute_query = bool(query_tokens & ATTRIBUTE_QUERY_TOKENS)
    location_query = bool(query_tokens & LOCATION_QUERY_TOKENS)
    hours_query = bool(query_tokens & HOURS_QUERY_TOKENS)
    appointment_query = bool(query_tokens & APPOINTMENT_QUERY_TOKENS)
    intro = _place_intro(page, transcript, language)
    parts = [intro]
    include_address = location_query or not (hours_query or appointment_query)
    address_sentence = _address_sentence(page, include_address, language)
    if address_sentence and page.address and normalize_text(page.address) in normalize_text(intro):
        address_sentence = ""
    hours_sentence = _hours_sentence(
        page,
        normalized_transcript,
        query_tokens,
        hours_query or (attribute_query and not appointment_query and not location_query),
        language,
        temporal_context=temporal_context,
    )
    appointment_sentence = _appointment_sentence(page, appointment_query, language)
    if address_sentence:
        parts.append(address_sentence)
    if hours_sentence:
        parts.append(hours_sentence)
    if appointment_sentence:
        parts.append(appointment_sentence)
    service_label = _service_type_label(page, language)
    if service_label and (not page.description or language != Language.DE):
        if language == Language.DE:
            parts.append(f"Das ist {service_label}")
        else:
            parts.append(f"This is {service_label}")
    if language == Language.DE and page.description and not _description_redundant(page):
        parts.append(page.description.rstrip("."))
    return _clean_answer_text(". ".join(parts))


def _place_intro(page: PageMetadata, transcript: str, language: Language) -> str:
    normalized_transcript = normalize_text(transcript)
    query_tokens = set(query_tokens_for_search(transcript, language))
    location_query = bool(query_tokens & LOCATION_QUERY_TOKENS) or normalized_transcript.startswith("wo ist ") or normalized_transcript.startswith("where is ") or normalized_transcript.startswith("wo finde ")
    hours_query = bool(query_tokens & HOURS_QUERY_TOKENS)
    appointment_query = bool(query_tokens & APPOINTMENT_QUERY_TOKENS)
    need_label = _query_need_label(query_tokens, language)
    if language == Language.DE:
        if location_query and page.address:
            return f"{page.title} ist in {page.address}"
        if hours_query:
            return f"Zu {page.title} habe ich diese Information"
        if appointment_query:
            return f"Zu {page.title} habe ich diese Information"
        if need_label:
            return f"Für {need_label} können Sie zu {page.title} gehen"
        return f"{page.title} kann hier helfen"
    if location_query and page.address:
        return f"{page.title} is at {page.address}"
    if hours_query:
        return f"I have this information about {page.title}"
    if appointment_query:
        return f"I have this information about appointments for {page.title}"
    if need_label:
        return f"For {need_label}, you can go to {page.title}"
    return f"{page.title} can help here"


def _address_sentence(page: PageMetadata, include: bool, language: Language) -> str:
    if not include:
        return ""
    if page.address:
        if language == Language.DE:
            return f"Die Adresse ist {page.address}"
        return f"The address is {page.address}"
    if language == Language.DE:
        return "Ich habe dazu keine genaue Adresse"
    return "I do not have an exact address for that"


def _hours_sentence(
    page: PageMetadata,
    normalized_transcript: str,
    query_tokens: set[str],
    include: bool,
    language: Language,
    temporal_context: TemporalContext | None = None,
) -> str:
    if not include:
        return ""
    if page.opening_hours:
        day_specific_tokens = query_tokens & DAY_QUERY_TOKENS
        if day_specific_tokens:
            normalized_hours = normalize_text(" ".join(page.opening_hours))
            if not any(day_token in normalized_hours for day_token in day_specific_tokens):
                if language == Language.DE:
                    return "Für diesen Wochentag habe ich keine eigenen Öffnungszeiten"
                return "I do not have separate opening hours for that day"
        if any(hint in normalized_transcript for hint in TODAY_QUERY_HINTS):
            if temporal_context and not _opening_hours_supports_weekday(page.opening_hours, temporal_context):
                if language == Language.DE:
                    return f"Für heute ({temporal_context.date_iso}, {temporal_context.weekday_de}) habe ich keine sicheren Öffnungszeiten"
                return f"I do not have reliable opening hours for today ({temporal_context.date_iso}, {temporal_context.weekday_en})"
            today = temporal_context.date_iso if temporal_context else datetime.now(UTC).date().isoformat()
            weekday = f", {temporal_context.weekday_de}" if temporal_context and language == Language.DE else ""
            weekday = f", {temporal_context.weekday_en}" if temporal_context and language != Language.DE else weekday
            if language == Language.DE:
                return f"Für heute ({today}{weekday}) stehen diese Öffnungszeiten dort: {'; '.join(page.opening_hours)}"
            return f"For today ({today}{weekday}), these opening hours are listed: {'; '.join(page.opening_hours)}"
        if language == Language.DE:
            return f"Die Öffnungszeiten sind: {'; '.join(page.opening_hours)}"
        return f"The opening hours are: {'; '.join(page.opening_hours)}"
    if language == Language.DE:
        return "Ich habe keine klaren Öffnungszeiten"
    return "I do not have clear opening hours"


def _appointment_sentence(page: PageMetadata, appointment_query: bool, language: Language) -> str:
    if not appointment_query:
        return ""
    if page.requires_registration is True:
        if language == Language.DE:
            return "Eine Anmeldung ist vorher noetig"
        return "Registration is needed in advance"
    if page.requires_registration is False:
        if language == Language.DE:
            return "Eine Anmeldung ist dort nicht genannt"
        return "An appointment is not named as needed"
    if language == Language.DE:
        return "Ob ein Termin noetig ist, sehe ich dort nicht klar"
    return "I cannot clearly tell whether an appointment is needed"


WEEKDAY_ALIASES = (
    ("montag", "mo", "monday"),
    ("dienstag", "di", "tuesday"),
    ("mittwoch", "mi", "wednesday"),
    ("donnerstag", "do", "thursday"),
    ("freitag", "fr", "friday"),
    ("samstag", "sa", "saturday"),
    ("sonntag", "so", "sunday"),
)


def _opening_hours_supports_weekday(opening_hours: list[str], temporal_context: TemporalContext) -> bool:
    if not opening_hours:
        return False
    normalized_hours = normalize_text(" | ".join(opening_hours))
    weekday_index = temporal_context.weekday_index
    if any(_weekday_alias_present(normalized_hours, alias) for alias in WEEKDAY_ALIASES[weekday_index]):
        return True
    if weekday_index <= 4 and any(pattern in normalized_hours for pattern in ("montag bis freitag", "mo bis fr", "mo-fr", "mo - fr", "mo. bis fr")):
        return True
    if weekday_index >= 5 and any(pattern in normalized_hours for pattern in ("samstag, sonntag", "sa, so", "sa und so", "sa, so, feiertag")):
        return True
    return False


def _weekday_alias_present(normalized_hours: str, alias: str) -> bool:
    if len(alias) <= 2:
        return bool(re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", normalized_hours))
    return alias in normalized_hours


def _description_redundant(page: PageMetadata) -> bool:
    description_tokens = set(tokenize(page.description))
    service_tokens = set(tokenize(page.service_type.replace("_", " ")))
    return bool(description_tokens and service_tokens and service_tokens <= description_tokens)


def _query_need_label(query_tokens: set[str], language: Language) -> str | None:
    labels_de = {
        "food": "Essen",
        "hygiene": "Duschen oder Koerperpflege",
        "shelter": "eine Unterkunft",
        "clothing": "Kleidung",
        "medical": "medizinische Hilfe",
        "addiction": "Suchtberatung",
    }
    labels_en = {
        "food": "food",
        "hygiene": "showering or hygiene support",
        "shelter": "shelter",
        "clothing": "clothing",
        "medical": "medical help",
        "addiction": "addiction support",
    }
    for category, hints in TOPIC_KEYWORDS.items():
        if query_tokens & hints:
            return (labels_de if language == Language.DE else labels_en).get(category)
    if query_tokens & {"dusche", "duschen", "duschgelegenheit", "shower", "koerperpflege", "waeschepflege"}:
        return (labels_de if language == Language.DE else labels_en)["hygiene"]
    return None


def _clean_answer_text(text: str) -> str:
    cleaned = LINK_RE.sub(r"\1", text or "")
    cleaned = cleaned.replace("â€¢", " ").replace("Â·", " ").replace("\uf0b7", " ")
    cleaned = SPACE_RE.sub(" ", cleaned).strip(" -")
    if not cleaned or cleaned.startswith("[") and cleaned.endswith("]"):
        return ""
    if len(cleaned) < 4:
        return ""
    if cleaned.lower() in {"kontakt", "telefon", "telefon:", "mail", "e-mail"}:
        return ""
    if cleaned and cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _language_instruction(language: Language) -> str:
    names = {
        Language.DE: "German",
        Language.EN: "English",
        Language.PL: "Polish",
        Language.RO: "Romanian",
        Language.RU: "Russian",
    }
    requested = names[language]
    if language == Language.DE:
        return (
            "Answer in German. Use only facts from the retrieved service information. "
            "Use simple German. Keep names, addresses, organization names, and source titles unchanged."
        )
    return (
        f"Answer fully in {requested}. Translate German service descriptions into {requested}. "
        "Keep official names, organization names, addresses, street names, and source titles unchanged. "
        f"Do not copy German descriptive text into the {requested} answer unless it is an official name."
    )


def _simple_language_rules() -> list[str]:
    return [
        "Use simple language.",
        "Use short sentences.",
        "Put one idea in one sentence.",
        "Use direct words.",
        "Avoid technical words.",
        "Do not write internal system terms in answer_text.",
        "Forbidden answer_text words include: Wissensbasis, knowledge base, KB, retrieval, context, Kontext, provider, database.",
        "If information is missing, say it plainly.",
        "Prefer concrete next steps.",
    ]


def _no_external_redirection_rules() -> list[str]:
    return [
        "LENA is for users who may not have a smartphone, internet access, or digital skills.",
        "Do not answer by telling the user to download an app, use an app, search a website, check online, use Google Maps, or find the place themselves.",
        "If the user asks for a concrete place, address, water fountain, food place, sleeping place, clothing, hygiene, medical help, or counselling, answer with concrete retrieved locations.",
        "If no concrete retrieved location exists, say plainly that you do not have a safe concrete location for this.",
        "If map targets are available, mention the closest or most relevant places and let the frontend show the map.",
        "Source links may be included only as secondary evidence. They must not replace the answer.",
        "Never invent exact locations, distances, opening hours, or availability.",
    ]


def _temporal_context_block(temporal_context: TemporalContext | None) -> str:
    if not temporal_context:
        return "Temporal context: not available. Do not infer the current date."
    hints = ", ".join(temporal_context.season_hints) if temporal_context.season_hints else "none"
    return "\n".join(
        [
            "Temporal context computed by backend:",
            f"- now_iso: {temporal_context.now_iso}",
            f"- date_iso: {temporal_context.date_iso}",
            f"- weekday: {temporal_context.weekday_en} / {temporal_context.weekday_de}",
            f"- weekday_index_monday_0: {temporal_context.weekday_index}",
            f"- is_weekend: {temporal_context.is_weekend}",
            f"- season: {temporal_context.season}",
            f"- season_hints: {hints}",
        ]
    )


def _unsupported_sensitive_fact(answer_text: str, evidence_context: str) -> str | None:
    normalized_answer = normalize_text(answer_text)
    normalized_evidence = normalize_text(evidence_context)
    if not normalized_answer:
        return "empty_answer"

    for email in EMAIL_RE.findall(answer_text):
        if normalize_text(email) not in normalized_evidence:
            return f"unsupported_email:{email}"

    for phone in PHONE_LIKE_RE.findall(answer_text):
        compact = re.sub(r"\D+", "", phone)
        if compact and compact not in re.sub(r"\D+", "", evidence_context):
            return f"unsupported_phone_or_number:{phone.strip()}"

    for number in TIME_OR_LONG_NUMBER_RE.findall(answer_text):
        if normalize_text(number) not in normalized_evidence:
            return f"unsupported_number:{number}"

    return None


def _validate_location_answer(
    answer: KnowledgeAnswer,
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    retrieved: list[RetrievedPage],
) -> KnowledgeAnswer | None:
    if answer.status not in {"ok", "weak_match"}:
        return None
    if not _is_location_required_query(transcript, language):
        return None
    concrete_items = _concrete_location_items(kb, retrieved)
    if _contains_forbidden_redirect(answer.answer_text):
        if concrete_items:
            return _fallback_answer(
                transcript,
                language,
                kb,
                concrete_items,
                minimum_match_threshold=0.0,
                weak_match_threshold=0.18,
            )
        return _no_concrete_location_answer(language, transcript, retrieved)
    if not concrete_items:
        return _no_concrete_location_answer(language, transcript, retrieved)
    normalized_answer = normalize_text(answer.answer_text)
    if not any(
        normalize_text(kb.get_page(item.page_id).title) in normalized_answer
        or (kb.get_page(item.page_id).address and normalize_text(kb.get_page(item.page_id).address or "") in normalized_answer)
        for item in concrete_items
    ):
        return _fallback_answer(
            transcript,
            language,
            kb,
            concrete_items,
            minimum_match_threshold=0.0,
            weak_match_threshold=0.18,
        )
    return None


def _build_clarification_question(language: Language, kb: KnowledgeBase, retrieved: list[RetrievedPage]) -> str:
    topics: list[str] = []
    for item in retrieved:
        page = kb.get_page(item.page_id)
        normalized_tokens = set(query_tokens_for_search(" ".join([page.title, *page.tags, page.page_id])))
        for topic, keywords in TOPIC_KEYWORDS.items():
            if normalized_tokens & keywords and topic not in topics:
                topics.append(topic)

    if not topics:
        return CLARIFY_TEXT[language]

    labels = [TOPIC_LABELS[topic][language] for topic in topics[:4]]
    if language == Language.DE:
        joined = ", ".join(labels[:-1]) + " oder " + labels[-1] if len(labels) > 1 else labels[0]
        return f"Geht es um {joined}?"
    if language == Language.EN:
        joined = ", ".join(labels[:-1]) + " or " + labels[-1] if len(labels) > 1 else labels[0]
        return f"Do you need {joined}?"
    return CLARIFY_TEXT[language]


class TemplateRewriteProvider(BaseRewriteProvider):
    name = "template"

    def __init__(
        self,
        minimum_match_threshold: float,
        weak_match_threshold: float,
        clarification_gap_threshold: float,
    ) -> None:
        self.minimum_match_threshold = minimum_match_threshold
        self.weak_match_threshold = weak_match_threshold
        self.clarification_gap_threshold = clarification_gap_threshold

    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: KnowledgeBase,
        conversation_context: ConversationContext | None = None,
        temporal_context: TemporalContext | None = None,
    ) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
            temporal_context=temporal_context,
        )
        resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
        self.last_resolved_transcript = resolved_transcript
        self.last_retrieved_page_ids = [item.page_id for item in retrieved]
        self.last_evidence_context = _build_retrieved_context(resolved_transcript, language, kb, retrieved, conversation_context=conversation_context) if retrieved else ""
        self.last_prompt_hash = None
        self.last_system_prompt_hash = None
        self.last_user_prompt_hash = None
        self.last_validation_error = None
        self.last_provider_error = None
        if early_answer:
            self.last_answer_source = "guardrail"
            return early_answer
        self.last_answer_source = "template"
        return _fallback_answer(
            transcript,
            language,
            kb,
            retrieved,
            minimum_match_threshold=self.minimum_match_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
            temporal_context=temporal_context,
        )


class OllamaRewriteProvider(BaseRewriteProvider):
    name = "ollama"
    uses_llm = True

    def __init__(
        self,
        base_url: str,
        model: str,
        system_prompt_path: Path | None = None,
        ollama_timeout_seconds: float = 20.0,
        minimum_match_threshold: float = 0.08,
        weak_match_threshold: float = 0.18,
        clarification_gap_threshold: float = 0.03,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_name = model
        self.system_prompt_path = system_prompt_path
        self.ollama_timeout_seconds = ollama_timeout_seconds
        self.minimum_match_threshold = minimum_match_threshold
        self.weak_match_threshold = weak_match_threshold
        self.clarification_gap_threshold = clarification_gap_threshold

    def _load_system_prompt(self, language: Language) -> str:
        fallback = "\n".join(
            [
                "# Task",
                "You help users find local support services in Leipzig.",
                "",
                "# Rules",
                "Answer only from the retrieved service information.",
                "Do not invent facts.",
                "If the retrieved information does not clearly support the answer, return status unknown.",
                "If several pages may fit and the request is too vague, return status clarification_needed.",
                "If there is a closest match but support is weak, return status weak_match.",
                *_simple_language_rules(),
                *_no_external_redirection_rules(),
                "Answer entirely in the requested language.",
                "Translate German service descriptions into the requested language.",
                "Keep official names, organization names, addresses, street names, and source titles unchanged.",
                "Do not use German descriptive fragments in non-German answers unless they are official names.",
                "Write short, natural sentences that sound clear when spoken aloud.",
                "Keep important facts such as place name, address, opening hours, service type, and target group when they are supported by the retrieved information.",
                "Prefer the highest-scoring retrieved page. Only use lower-scoring pages if they add clearly relevant detail.",
                "Answer in one or two short sentences unless the question clearly needs more.",
                f"Respond in language: {language.value}.",
                "Return JSON only.",
            ]
        )
        if not self.system_prompt_path:
            return fallback
        try:
            content = self.system_prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            return fallback
        if not content:
            return fallback
        return (
            f"{content}\n"
            + "\n".join(f"- {rule}" for rule in _simple_language_rules())
            + "\n"
            + "\n".join(f"- {rule}" for rule in _no_external_redirection_rules())
            + "\n"
            "- Answer entirely in the requested language.\n"
            "- Translate German service descriptions into the requested language.\n"
            "- Keep official names, organization names, addresses, street names, and source titles unchanged.\n"
            "- Do not use German descriptive fragments in non-German answers unless they are official names.\n"
            "- Write short, natural sentences that sound clear when spoken aloud.\n"
            "- Keep important facts such as place name, address, opening hours, service type, and target group when they are supported by the retrieved information.\n"
            "- Prefer the highest-scoring retrieved page. Only use lower-scoring pages if they add clearly relevant detail.\n"
            "- Answer in one or two short sentences unless the question clearly needs more.\n\n"
            f"Respond in language: {language.value}.\nReturn JSON only."
        )

    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: KnowledgeBase,
        conversation_context: ConversationContext | None = None,
        temporal_context: TemporalContext | None = None,
    ) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
            temporal_context=temporal_context,
        )
        resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
        self.last_resolved_transcript = resolved_transcript
        self.last_retrieved_page_ids = [item.page_id for item in retrieved]
        self.last_evidence_context = _build_retrieved_context(resolved_transcript, language, kb, retrieved, conversation_context=conversation_context) if retrieved else ""
        self.last_prompt_hash = None
        self.last_system_prompt_hash = None
        self.last_user_prompt_hash = None
        self.last_validation_error = None
        self.last_provider_error = None
        if early_answer:
            self.last_answer_source = "guardrail"
            return early_answer

        query_tokens = set(query_tokens_for_search(transcript, language))
        detail_sensitive_follow_up = bool(
            conversation_context
            and conversation_context.follow_up_mode == "referential"
            and query_tokens & (LOCATION_QUERY_TOKENS | HOURS_QUERY_TOKENS | APPOINTMENT_QUERY_TOKENS | DAY_QUERY_TOKENS)
        )
        if detail_sensitive_follow_up:
            self.last_answer_source = "template_detail_guard"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
            )
        if _is_sleep_query(transcript) and _is_location_required_query(transcript, language):
            self.last_answer_source = "template_detail_guard"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )

        retrieved_page_ids = [item.page_id for item in retrieved]
        context = self.last_evidence_context
        overview_hint = _build_overview_answer(transcript, language, kb, retrieved)
        normalized_transcript = normalize_text(transcript)
        is_location_query = bool(query_tokens & LOCATION_QUERY_TOKENS) or normalized_transcript.startswith(("wo ist ", "where is ", "wo finde ", "gdzie jest ", "unde este "))
        is_day_specific_query = bool(query_tokens & DAY_QUERY_TOKENS)
        is_hours_query = bool(query_tokens & HOURS_QUERY_TOKENS)
        is_appointment_query = bool(query_tokens & APPOINTMENT_QUERY_TOKENS)
        follow_up_hint = ""
        if conversation_context and conversation_context.follow_up_mode == "referential":
            follow_up_hint = "This is a follow-up about the same place. Keep the answer anchored to the referenced place and avoid drifting to another page."
        elif conversation_context and conversation_context.follow_up_mode == "alternative":
            follow_up_hint = "This is a request for an alternative option. Do not repeat the same place if another retrieved page fits."
        elif conversation_context and conversation_context.follow_up_mode == "topic_shift":
            follow_up_hint = "This continues the same conversation with a related topic shift. Use only the currently retrieved pages for the new subtopic."
        schema = LLMKnowledgeAnswer.model_json_schema()
        system_prompt = self._load_system_prompt(language)
        user_prompt = "\n".join(
            [
                "User request:",
                transcript,
                "",
                f"Resolved request for retrieval: {resolved_transcript}",
                "",
                _temporal_context_block(temporal_context),
                "",
                "Retrieved service information:",
                context,
                "",
                f"Overview hint: {overview_hint}" if overview_hint else "",
                follow_up_hint,
                _language_instruction(language),
                "If several retrieved pages are locations of the same organisation, summarize them together instead of repeating one sentence per location.",
                "Answer only from the retrieved pages above.",
                "Always include the place name.",
                "Include the address and opening hours whenever they are available and directly useful.",
                *_simple_language_rules(),
                *_no_external_redirection_rules(),
                "Make the answer easy to understand for a stressed user and easy to speak aloud.",
                "If the user asks where a place is, answer with the place name and address. Do not add opening hours unless the user asked for them." if is_location_query else "",
                "If the user asks about opening hours, focus on the hours answer and do not add unrelated service details." if is_hours_query or is_day_specific_query else "",
                "If the user asks about appointments, answer only whether an appointment is required, not required, or not clearly stated." if is_appointment_query else "",
                "If several suitable places are retrieved, give 1 to 3 concrete options.",
                "Prefer the highest-scoring page unless another retrieved page adds directly relevant detail.",
                "Do not infer facts that are not explicitly supported by the retrieved pages.",
                "If a specific weekday is asked for, only say that the place is open on that day if that weekday is explicitly listed in OPENING_HOURS.",
                "Do not infer Sunday opening from Saturday hours or from public-holiday hours.",
                "If the retrieved information does not clearly say whether an appointment is needed, say that clearly instead of guessing." if is_appointment_query else "",
                "If today's opening status cannot be determined from retrieved opening hours, say that reliable opening information for today is not available instead of guessing.",
                "If the user asks about opening hours for a specific day and that day is not explicitly listed, say that no separate hours for that day are available." if is_day_specific_query or is_hours_query else "",
                "Seasonal advice must only use services or facts present in the retrieved pages.",
                "If the retrieved pages do not clearly support the answer, return status unknown.",
                "If support is weak, return status weak_match.",
                "Keep the answer concise, clear, and easy to speak aloud.",
            ]
        )
        payload = {
            "model": self.model,
            "format": schema,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        self.last_system_prompt_hash = _hash_text(system_prompt)
        self.last_user_prompt_hash = _hash_text(user_prompt)
        self.last_prompt_hash = _hash_text(system_prompt + "\n\n" + user_prompt)
        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
            content = body["message"]["content"].strip()
            parsed = json.loads(content)
            answer = KnowledgeAnswer.model_validate(parsed)
        except Exception:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "ollama_error"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
            )

        self.last_answer_source = "llm"
        answer.retrieved_page_ids = retrieved_page_ids
        answer.answer_text = _clean_answer_text(answer.answer_text)
        weak = retrieved[0].score < self.weak_match_threshold

        if answer.status in {"ok", "weak_match"}:
            location_replacement = _validate_location_answer(answer, transcript, language, kb, retrieved)
            if location_replacement:
                self.last_validation_error = "external_self_service_redirect_or_missing_concrete_location"
                self.last_answer_source = "validator_fallback"
                return location_replacement
            validation_error = _unsupported_sensitive_fact(answer.answer_text, context)
            if validation_error:
                self.last_validation_error = validation_error
                self.last_answer_source = "validator_fallback"
                return _fallback_answer(
                    transcript,
                    language,
                    kb,
                    retrieved,
                    minimum_match_threshold=self.minimum_match_threshold,
                    weak_match_threshold=self.weak_match_threshold,
                    conversation_context=conversation_context,
                )

        if answer.status == "self_description":
            answer.self_description = True
            return answer
        if answer.status == "out_of_scope":
            return _out_of_scope_answer(language)
        if answer.status == "crisis":
            return _crisis_answer(language, kb)

        if answer.status == "clarification_needed":
            if answer.clarification_question or answer.answer_text.endswith("?"):
                answer.clarification_needed = True
                if not answer.clarification_question:
                    answer.clarification_question = answer.answer_text or _build_clarification_question(language, kb, retrieved)
                answer.answer_text = answer.clarification_question
                return answer
            answer.status = "weak_match" if weak else "ok"
            answer.clarification_needed = False
            answer.clarification_question = None

        if answer.status == "unknown":
            if _is_location_required_query(transcript, language) and _concrete_location_items(kb, retrieved):
                self.last_answer_source = "validator_fallback"
                self.last_validation_error = "location_required_with_concrete_results"
                return _fallback_answer(
                    transcript,
                    language,
                    kb,
                    retrieved,
                    minimum_match_threshold=self.minimum_match_threshold,
                    weak_match_threshold=self.weak_match_threshold,
                    conversation_context=conversation_context,
                    temporal_context=temporal_context,
                )
            answer.answer_text = UNKNOWN_TEXT[language]
            if (
                answer.answer_text != UNKNOWN_TEXT[language]
                and not weak
                and retrieved
                and any(
                    marker in answer.answer_text
                    for marker in (
                        kb.get_page(retrieved[0].page_id).title,
                        kb.get_page(retrieved[0].page_id).address or "",
                        "08:00",
                        "09:30",
                        "10:30",
                    )
                )
            ):
                answer.status = "ok"
            return answer

        if not answer.answer_text:
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
            )

        if answer.status == "weak_match" or weak:
            if weak:
                answer.status = "weak_match"
                answer.weak_match = True
                if not answer.answer_text.startswith(WEAK_PREFIX[language]):
                    answer.answer_text = f"{WEAK_PREFIX[language]}{answer.answer_text}"
            else:
                answer.status = "ok"
                answer.weak_match = False
        return answer


class OpenAICompatibleRewriteProvider(OllamaRewriteProvider):
    name = "openai_compatible"
    uses_llm = True

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        model: str = "alias-large",
        provider_name: str = "openai_compatible",
        system_prompt_path: Path | None = None,
        timeout_seconds: float = 60.0,
        max_tokens: int = 800,
        temperature: float = 0.0,
        minimum_match_threshold: float = 0.08,
        weak_match_threshold: float = 0.18,
        clarification_gap_threshold: float = 0.03,
    ) -> None:
        self.name = provider_name
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.system_prompt_path = system_prompt_path
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.minimum_match_threshold = minimum_match_threshold
        self.weak_match_threshold = weak_match_threshold
        self.clarification_gap_threshold = clarification_gap_threshold

    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: KnowledgeBase,
        conversation_context: ConversationContext | None = None,
        temporal_context: TemporalContext | None = None,
    ) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
            temporal_context=temporal_context,
        )
        resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
        self.last_resolved_transcript = resolved_transcript
        self.last_retrieved_page_ids = [item.page_id for item in retrieved]
        self.last_evidence_context = _build_retrieved_context(resolved_transcript, language, kb, retrieved, conversation_context=conversation_context) if retrieved else ""
        self.last_prompt_hash = None
        self.last_system_prompt_hash = None
        self.last_user_prompt_hash = None
        self.last_validation_error = None
        self.last_provider_error = None
        if early_answer:
            self.last_answer_source = "guardrail"
            return early_answer

        if not self.base_url:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "missing_base_url"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        if not self.api_key:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "missing_api_key"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )

        query_tokens = set(query_tokens_for_search(transcript, language))
        detail_sensitive_follow_up = bool(
            conversation_context
            and conversation_context.follow_up_mode == "referential"
            and query_tokens & (LOCATION_QUERY_TOKENS | HOURS_QUERY_TOKENS | APPOINTMENT_QUERY_TOKENS | DAY_QUERY_TOKENS)
        )
        if detail_sensitive_follow_up:
            self.last_answer_source = "template_detail_guard"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        if _is_sleep_query(transcript) and _is_location_required_query(transcript, language):
            self.last_answer_source = "template_detail_guard"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )

        retrieved_page_ids = [item.page_id for item in retrieved]
        context = self.last_evidence_context
        overview_hint = _build_overview_answer(transcript, language, kb, retrieved)
        normalized_transcript = normalize_text(transcript)
        is_location_query = bool(query_tokens & LOCATION_QUERY_TOKENS) or normalized_transcript.startswith(("wo ist ", "where is ", "wo finde ", "gdzie jest ", "unde este "))
        is_day_specific_query = bool(query_tokens & DAY_QUERY_TOKENS)
        is_hours_query = bool(query_tokens & HOURS_QUERY_TOKENS)
        is_appointment_query = bool(query_tokens & APPOINTMENT_QUERY_TOKENS)
        follow_up_hint = ""
        if conversation_context and conversation_context.follow_up_mode == "referential":
            follow_up_hint = "This is a follow-up about the same place. Keep the answer anchored to the referenced place and avoid drifting to another page."
        elif conversation_context and conversation_context.follow_up_mode == "alternative":
            follow_up_hint = "This is a request for an alternative option. Do not repeat the same place if another retrieved page fits."
        elif conversation_context and conversation_context.follow_up_mode == "topic_shift":
            follow_up_hint = "This continues the same conversation with a related topic shift. Use only the currently retrieved pages for the new subtopic."
        schema = LLMKnowledgeAnswer.model_json_schema()
        system_prompt = self._load_system_prompt(language)
        user_prompt = "\n".join(
            [
                "User request:",
                transcript,
                "",
                f"Resolved request for retrieval: {resolved_transcript}",
                "",
                _temporal_context_block(temporal_context),
                "",
                "Retrieved service information:",
                context,
                "",
                f"Overview hint: {overview_hint}" if overview_hint else "",
                follow_up_hint,
                _language_instruction(language),
                "If several retrieved pages are locations of the same organisation, summarize them together instead of repeating one sentence per location.",
                "Answer only from the retrieved pages above.",
                "Always include the place name.",
                "Include the address and opening hours whenever they are available and directly useful.",
                *_simple_language_rules(),
                *_no_external_redirection_rules(),
                "Make the answer easy to understand for a stressed user and easy to speak aloud.",
                "If the user asks where a place is, answer with the place name and address. Do not add opening hours unless the user asked for them." if is_location_query else "",
                "If the user asks about opening hours, focus on the hours answer and do not add unrelated service details." if is_hours_query or is_day_specific_query else "",
                "If the user asks about appointments, answer only whether an appointment is required, not required, or not clearly stated." if is_appointment_query else "",
                "If several suitable places are retrieved, give 1 to 3 concrete options.",
                "Prefer the highest-scoring page unless another retrieved page adds directly relevant detail.",
                "Do not infer facts that are not explicitly supported by the retrieved pages.",
                "If a specific weekday is asked for, only say that the place is open on that day if that weekday is explicitly listed in OPENING_HOURS.",
                "Do not infer Sunday opening from Saturday hours or from public-holiday hours.",
                "If the retrieved information does not clearly say whether an appointment is needed, say that clearly instead of guessing." if is_appointment_query else "",
                "If today's opening status cannot be determined from retrieved opening hours, say that reliable opening information for today is not available instead of guessing.",
                "If the user asks about opening hours for a specific day and that day is not explicitly listed, say that no separate hours for that day are available." if is_day_specific_query or is_hours_query else "",
                "Seasonal advice must only use services or facts present in the retrieved pages.",
                "If the retrieved pages do not clearly support the answer, return status unknown.",
                "If support is weak, return status weak_match.",
                "Return exactly one JSON object matching this schema:",
                json.dumps(schema, ensure_ascii=False),
                "Keep the answer concise, clear, and easy to speak aloud.",
            ]
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        self.last_system_prompt_hash = _hash_text(system_prompt)
        self.last_user_prompt_hash = _hash_text(user_prompt)
        self.last_prompt_hash = _hash_text(system_prompt + "\n\n" + user_prompt)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                body = response.json()
            content = self._extract_chat_content(body)
            parsed = json.loads(content)
            answer = KnowledgeAnswer.model_validate(parsed)
        except json.JSONDecodeError:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "invalid_json"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        except httpx.TimeoutException:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "timeout"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        except httpx.HTTPStatusError as exc:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = f"http_{exc.response.status_code}"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        except (KeyError, IndexError, TypeError):
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "invalid_response"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        except httpx.HTTPError:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "connection_error"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )
        except Exception:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "schema_mismatch"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )

        self.last_answer_source = "llm"
        answer.retrieved_page_ids = retrieved_page_ids
        answer.answer_text = _clean_answer_text(answer.answer_text)
        weak = retrieved[0].score < self.weak_match_threshold

        if answer.status in {"ok", "weak_match"}:
            location_replacement = _validate_location_answer(answer, transcript, language, kb, retrieved)
            if location_replacement:
                self.last_validation_error = "external_self_service_redirect_or_missing_concrete_location"
                self.last_answer_source = "validator_fallback"
                return location_replacement
            validation_error = _unsupported_sensitive_fact(answer.answer_text, context)
            if validation_error:
                self.last_validation_error = validation_error
                self.last_answer_source = "validator_fallback"
                self.last_provider_error = "unsupported_sensitive_fact"
                return _fallback_answer(
                    transcript,
                    language,
                    kb,
                    retrieved,
                    minimum_match_threshold=self.minimum_match_threshold,
                    weak_match_threshold=self.weak_match_threshold,
                    conversation_context=conversation_context,
                    temporal_context=temporal_context,
                )

        if answer.status == "self_description":
            answer.self_description = True
            return answer
        if answer.status == "out_of_scope":
            return _out_of_scope_answer(language)
        if answer.status == "crisis":
            return _crisis_answer(language, kb)

        if answer.status == "clarification_needed":
            if answer.clarification_question or answer.answer_text.endswith("?"):
                answer.clarification_needed = True
                if not answer.clarification_question:
                    answer.clarification_question = answer.answer_text or _build_clarification_question(language, kb, retrieved)
                answer.answer_text = answer.clarification_question
                return answer
            answer.status = "weak_match" if weak else "ok"
            answer.clarification_needed = False
            answer.clarification_question = None

        if answer.status == "unknown":
            if _is_location_required_query(transcript, language) and _concrete_location_items(kb, retrieved):
                self.last_answer_source = "validator_fallback"
                self.last_validation_error = "location_required_with_concrete_results"
                return _fallback_answer(
                    transcript,
                    language,
                    kb,
                    retrieved,
                    minimum_match_threshold=self.minimum_match_threshold,
                    weak_match_threshold=self.weak_match_threshold,
                    conversation_context=conversation_context,
                    temporal_context=temporal_context,
                )
            answer.answer_text = UNKNOWN_TEXT[language]
            if (
                answer.answer_text != UNKNOWN_TEXT[language]
                and not weak
                and retrieved
                and any(
                    marker in answer.answer_text
                    for marker in (
                        kb.get_page(retrieved[0].page_id).title,
                        kb.get_page(retrieved[0].page_id).address or "",
                        "08:00",
                        "09:30",
                        "10:30",
                    )
                )
            ):
                answer.status = "ok"
            return answer

        if not answer.answer_text:
            self.last_answer_source = "template_fallback"
            self.last_provider_error = "empty_answer"
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
                conversation_context=conversation_context,
                temporal_context=temporal_context,
            )

        if answer.status == "weak_match" or weak:
            if weak:
                answer.status = "weak_match"
                answer.weak_match = True
                if not answer.answer_text.startswith(WEAK_PREFIX[language]):
                    answer.answer_text = f"{WEAK_PREFIX[language]}{answer.answer_text}"
            else:
                answer.status = "ok"
                answer.weak_match = False
        return answer

    @staticmethod
    def _extract_chat_content(body: dict) -> str:
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts).strip()
        raise TypeError("unexpected OpenAI-compatible response content")


class BlabladorRewriteProvider(OpenAICompatibleRewriteProvider):
    def __init__(
        self,
        api_key: str | None,
        base_url: str | None = None,
        model: str = "alias-large",
        system_prompt_path: Path | None = None,
        timeout_seconds: float = 60.0,
        max_tokens: int = 800,
        temperature: float = 0.0,
        minimum_match_threshold: float = 0.08,
        weak_match_threshold: float = 0.18,
        clarification_gap_threshold: float = 0.03,
    ) -> None:
        super().__init__(
            base_url=base_url or "https://api.blablador.fz-juelich.de/v1/",
            api_key=api_key,
            model=model,
            provider_name="blablador",
            system_prompt_path=system_prompt_path,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
            temperature=temperature,
            minimum_match_threshold=minimum_match_threshold,
            weak_match_threshold=weak_match_threshold,
            clarification_gap_threshold=clarification_gap_threshold,
        )


def create_rewrite_provider(
    name: str,
    ollama_url: str,
    ollama_model: str,
    ollama_timeout_seconds: float,
    minimum_match_threshold: float,
    weak_match_threshold: float,
    clarification_gap_threshold: float,
    system_prompt_path: Path | None = None,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str = "alias-large",
    llm_timeout_seconds: float = 60.0,
    llm_max_tokens: int = 800,
    llm_temperature: float = 0.0,
    llm_fallback_provider: str = "template",
) -> BaseRewriteProvider:
    if name == "ollama":
        return OllamaRewriteProvider(
            base_url=ollama_url,
            model=ollama_model,
            system_prompt_path=system_prompt_path,
            ollama_timeout_seconds=ollama_timeout_seconds,
            minimum_match_threshold=minimum_match_threshold,
            weak_match_threshold=weak_match_threshold,
            clarification_gap_threshold=clarification_gap_threshold,
        )
    if name == "blablador":
        return BlabladorRewriteProvider(
            base_url=llm_base_url,
            api_key=llm_api_key,
            model=llm_model,
            system_prompt_path=system_prompt_path,
            timeout_seconds=llm_timeout_seconds,
            max_tokens=llm_max_tokens,
            temperature=llm_temperature,
            minimum_match_threshold=minimum_match_threshold,
            weak_match_threshold=weak_match_threshold,
            clarification_gap_threshold=clarification_gap_threshold,
        )
    if name == "openai_compatible":
        return OpenAICompatibleRewriteProvider(
            base_url=llm_base_url,
            api_key=llm_api_key,
            model=llm_model,
            provider_name="openai_compatible",
            system_prompt_path=system_prompt_path,
            timeout_seconds=llm_timeout_seconds,
            max_tokens=llm_max_tokens,
            temperature=llm_temperature,
            minimum_match_threshold=minimum_match_threshold,
            weak_match_threshold=weak_match_threshold,
            clarification_gap_threshold=clarification_gap_threshold,
        )
    if llm_fallback_provider != "template" and name not in {"template", "ollama", "blablador", "openai_compatible"}:
        return create_rewrite_provider(
            llm_fallback_provider,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            ollama_timeout_seconds=ollama_timeout_seconds,
            minimum_match_threshold=minimum_match_threshold,
            weak_match_threshold=weak_match_threshold,
            clarification_gap_threshold=clarification_gap_threshold,
            system_prompt_path=system_prompt_path,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            llm_timeout_seconds=llm_timeout_seconds,
            llm_max_tokens=llm_max_tokens,
            llm_temperature=llm_temperature,
            llm_fallback_provider="template",
        )
    return TemplateRewriteProvider(
        minimum_match_threshold=minimum_match_threshold,
        weak_match_threshold=weak_match_threshold,
        clarification_gap_threshold=clarification_gap_threshold,
    )
