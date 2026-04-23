from __future__ import annotations

from abc import ABC, abstractmethod
import json
from datetime import UTC, datetime
from pathlib import Path
import re

import httpx

from ..kb import KnowledgeBase
from ..models import ConversationContext, KnowledgeAnswer, LLMKnowledgeAnswer, Language, PageMetadata, RetrievedPage
from ..retrieval import (
    HOURS_QUERY_TOKENS,
    LOCATION_QUERY_TOKENS,
    RetrievalEngine,
    extract_relevant_passages,
    normalize_text,
    query_tokens_for_search,
    tokenize,
)


UNKNOWN_TEXT = {
    Language.DE: "Dazu finde ich in meiner Wissensbasis keine verlaessliche Information. Ich kann bei Hilfsangeboten in Leipzig helfen, zum Beispiel mit Orten, Adressen und Oeffnungszeiten.",
    Language.EN: "I could not find reliable information about that in my knowledge base. I can help with support services in Leipzig, for example places, addresses, and opening hours.",
    Language.PL: "Nie znalazlem wiarygodnej informacji na ten temat w mojej bazie wiedzy. Moge pomagac przy uslugach wsparcia w Lipsku, na przyklad z miejscami, adresami i godzinami otwarcia.",
    Language.RO: "Nu am gasit informatii sigure despre asta in baza mea de cunostinte. Pot ajuta cu servicii de sprijin din Leipzig, de exemplu cu locuri, adrese si program.",
    Language.RU: "Ð¯ Ð½Ðµ Ð½Ð°ÑˆÑ‘Ð» Ð½Ð°Ð´Ñ‘Ð¶Ð½Ð¾Ð¹ Ð¸Ð½Ñ„Ð¾Ñ€Ð¼Ð°Ñ†Ð¸Ð¸ Ð¾Ð± ÑÑ‚Ð¾Ð¼ Ð² Ð±Ð°Ð·Ðµ Ð·Ð½Ð°Ð½Ð¸Ð¹.",
}
OVERVIEW_DETAIL_OFFER = {
    Language.DE: "Wenn Sie moechten, nenne ich Ihnen die genauen Standorte und Uhrzeiten.",
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
    Language.DE: "Eine Anmeldung ist vorher noetig.",
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
    Language.DE: "Ich habe nur einen aehnlichen Treffer gefunden: ",
    Language.EN: "I only found a close match: ",
    Language.PL: "Znalazlem tylko podobny wpis: ",
    Language.RO: "Am gasit doar un rezultat apropiat: ",
    Language.RU: "Ð¯ Ð½Ð°ÑˆÑ‘Ð» Ñ‚Ð¾Ð»ÑŒÐºÐ¾ Ð±Ð»Ð¸Ð·ÐºÐ¾Ðµ ÑÐ¾Ð²Ð¿Ð°Ð´ÐµÐ½Ð¸Ðµ Ð² Ð±Ð°Ð·Ðµ Ð·Ð½Ð°Ð½Ð¸Ð¹: ",
}

OUT_OF_SCOPE_TEXT = {
    Language.DE: "Dabei kann ich nicht helfen. Ich bin fuer Hilfsangebote und praktische Informationen in Leipzig da, zum Beispiel Essen, Unterkunft, Duschen, Beratung, Adressen und Oeffnungszeiten.",
    Language.EN: "I cannot help with that. I am here for support services and practical information in Leipzig, for example food, shelter, showers, advice, addresses, and opening hours.",
    Language.PL: "Nie moge w tym pomoc. Jestem tutaj do spraw uslug wsparcia i praktycznych informacji w Lipsku, na przyklad jedzenia, noclegu, prysznicow, porad, adresow i godzin otwarcia.",
    Language.RO: "Nu pot ajuta cu asta. Sunt aici pentru servicii de sprijin si informatii practice din Leipzig, de exemplu mancare, adapost, dusuri, consiliere, adrese si program.",
    Language.RU: "Ya ne mogu pomoch s etim. Ya zdes dlya uslug podderzhki i prakticheskoy informatsii v Leyptsige, naprimer pro edu, nochleg, dush, konsultatsii, adresy i chasy raboty.",
}
SELF_DESCRIPTION_TEXT = {
    Language.DE: "Ich bin LENA, der Leipzig Empowerment and Navigation Assistant. Ich helfe mit lokalen Informationen zu Hilfsangeboten in Leipzig, zum Beispiel zu Orten, Adressen, Oeffnungszeiten und passenden Anlaufstellen.",
    Language.EN: "I am LENA, the Leipzig Empowerment and Navigation Assistant. I help with local information about support services in Leipzig, for example places, addresses, opening hours, and suitable services.",
    Language.PL: "Jestem LENA, Leipzig Empowerment and Navigation Assistant. Pomagam lokalnymi informacjami o uslugach wsparcia w Lipsku, na przyklad o miejscach, adresach, godzinach otwarcia i odpowiednich punktach pomocy.",
    Language.RO: "Sunt LENA, Leipzig Empowerment and Navigation Assistant. Ajut cu informatii locale despre servicii de sprijin din Leipzig, de exemplu despre locuri, adrese, program si puncte potrivite de ajutor.",
    Language.RU: "Ya LENA, Leipzig Empowerment and Navigation Assistant. Ya pomogayu s mestnoy informatsiyey o sluzhbakh podderzhki v Leyptsige, naprimer o mestakh, adresakh, chasakh raboty i podkhodyashchikh punktakh pomoshchi.",
}
CRISIS_TEXT = {
    Language.DE: "Ich kann keine medizinische oder seelische Notfallberatung geben. Wenn Sie jetzt in Gefahr sind oder dringend Hilfe brauchen, rufen Sie bitte 112. Bei akuter Bedrohung oder Gewalt rufen Sie 110. Wenn Sie mit jemandem sprechen muessen, erreichen Sie die TelefonSeelsorge unter 0800 1110 111.",
    Language.EN: "I cannot provide medical or mental health emergency advice. If you are in danger now or need urgent help, please call 112 in Germany. If there is immediate threat or violence, call 110. If you need to talk to someone, you can reach TelefonSeelsorge at 0800 1110 111.",
    Language.PL: "Nie moge udzielac porad medycznych ani psychologicznych w naglym wypadku. Jesli jestes teraz w niebezpieczenstwie albo pilnie potrzebujesz pomocy, zadzwon w Niemczech pod 112. Przy bezposrednim zagrozeniu lub przemocy zadzwon pod 110. Jesli chcesz z kims porozmawiac, mozesz zadzwonic do TelefonSeelsorge pod 0800 1110 111.",
    Language.RO: "Nu pot oferi sfaturi medicale sau psihologice pentru urgente. Daca esti acum in pericol sau ai nevoie urgenta de ajutor, suna in Germania la 112. Daca exista amenintare imediata sau violenta, suna la 110. Daca ai nevoie sa vorbesti cu cineva, poti suna la TelefonSeelsorge la 0800 1110 111.",
    Language.RU: "Ya ne mogu davat meditsinskie ili psikhologicheskie sovety dlya ekstrennykh sluchaev. Esli vy seychas v opasnosti ili vam nuzhna srochnaya pomoshch v Germanii, pozhaluysta, zvonite 112. Pri neposredstvennoy ugroze ili nasilii zvonite 110. Esli vam nuzhno s kem-to pogovorit, mozhno pozvonit v TelefonSeelsorge po nomeru 0800 1110 111.",
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
    "unterkunft",
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
    "movie",
    "opinion",
    "orbit",
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
    "ich will sterben",
    "ich moechte sterben",
    "ich mochte sterben",
    "ich will mich umbringen",
    "ich will mich toeten",
    "ich will mich toten",
    "ich tue mir etwas an",
    "ich verletze mich",
    "ich habe eine ueberdosis",
    "ich habe eine uberdosis",
    "ich kann nicht atmen",
    "ich habe starke brustschmerzen",
    "ich blute stark",
    "i want to die",
    "i want to kill myself",
    "i want to hurt myself",
    "i took an overdose",
    "i overdosed",
    "i can't breathe",
    "i cant breathe",
    "i have chest pain",
    "i am bleeding badly",
    "i am being attacked",
    "i am in danger",
    "kill myself",
    "hurt myself",
    "emergency number",
    "notfallnummer",
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
    "110",
    "112",
    "attack",
    "attacke",
    "bedroht",
    "bleeding",
    "brustschmerzen",
    "emergency",
    "gewalt",
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
    "food": {"essen", "tafel", "lebensmittel", "mahlzeit"},
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


class BaseRewriteProvider(ABC):
    name = "base"
    model_name: str | None = None
    uses_llm = False
    last_answer_source = "unknown"

    @abstractmethod
    async def answer(
        self,
        transcript: str,
        language: Language,
        kb: KnowledgeBase,
        conversation_context: ConversationContext | None = None,
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
    if service_lookup and not (direct_pattern or direct_tokens):
        return False
    return direct_pattern or direct_tokens


def _is_out_of_scope_query(transcript: str) -> bool:
    normalized = normalize_text(transcript)
    tokens = set(tokenize(transcript))
    if _has_domain_signal(transcript):
        return False
    return any(pattern in normalized for pattern in OUT_OF_SCOPE_PATTERNS) or bool(tokens & OUT_OF_SCOPE_TOKENS)


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
) -> tuple[list[RetrievedPage], KnowledgeAnswer | None]:
    guarded = _guarded_response(transcript, language, kb)
    if guarded:
        return [], guarded
    retrieval = RetrievalEngine(kb)
    resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
    retrieved = retrieval.retrieve(
        resolved_transcript,
        language,
        limit=8,
        preferred_page_ids=conversation_context.preferred_page_ids if conversation_context else None,
        excluded_page_ids=conversation_context.excluded_page_ids if conversation_context else None,
    )
    if not retrieved:
        if _is_out_of_scope_query(transcript):
            return [], _out_of_scope_answer(language)
        return [], KnowledgeAnswer(answer_text=UNKNOWN_TEXT[language], status="unknown")

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
) -> KnowledgeAnswer:
    if not retrieved or retrieved[0].score < minimum_match_threshold:
        return KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    snippet = _build_structured_answer(transcript, language, kb, retrieved, conversation_context=conversation_context)
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
        sentences = ["Es gibt verschiedene Anlaufstellen fuer Essen und Lebensmittel in Leipzig."]
        if tafels:
            sentences.append("Bei der Tafel Leipzig gibt es mehrere Ausgabestellen fuer Lebensmittel.")
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
        elif secondary_page.description:
            detail_parts.append(f"offering {secondary_page.description.rstrip('.')}")
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
        options.append(_format_page_option(page, transcript, language))
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
        "food_distribution": "eine Ausgabestelle fuer Essen und Lebensmittel",
        "overnight_shelter": "ein Uebernachtungshaus",
        "medical_consultation": "eine medizinische Sprechstunde",
        "counseling": "eine Beratungsstelle",
        "station_support": "ein Hilfsangebot am Bahnhof",
        "streetwork": "ein Streetwork-Angebot",
        "streetwork_food_outreach": "ein Streetwork-Angebot mit Essen und Beratung",
        "service_catalog": "eine Uebersichtsseite",
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


def _format_page_option(page: PageMetadata, transcript: str, language: Language) -> str:
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
    )
    appointment_sentence = _appointment_sentence(page, appointment_query, language)
    if address_sentence:
        parts.append(address_sentence)
    if hours_sentence:
        parts.append(hours_sentence)
    if appointment_sentence:
        parts.append(appointment_sentence)
    service_label = _service_type_label(page, language)
    if service_label and not page.description:
        if language == Language.DE:
            parts.append(f"Das ist {service_label}")
        else:
            parts.append(f"This is {service_label}")
    if page.description and not _description_redundant(page):
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
            return f"Bei {page.title} stehen diese Oeffnungszeiten"
        if appointment_query:
            return f"Zu {page.title} steht in der Wissensbasis"
        if need_label:
            return f"Fuer {need_label} koennen Sie zu {page.title} gehen"
        return f"{page.title} kann hier helfen"
    if location_query and page.address:
        return f"{page.title} is at {page.address}"
    if hours_query:
        return f"These are the listed hours for {page.title}"
    if appointment_query:
        return f"This is what the knowledge base says about appointments for {page.title}"
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
        return "Ich sehe in der Wissensbasis keine genaue Adresse"
    return "I do not see an exact address in the knowledge base"


def _hours_sentence(
    page: PageMetadata,
    normalized_transcript: str,
    query_tokens: set[str],
    include: bool,
    language: Language,
) -> str:
    if not include:
        return ""
    if page.opening_hours:
        day_specific_tokens = query_tokens & DAY_QUERY_TOKENS
        if day_specific_tokens:
            normalized_hours = normalize_text(" ".join(page.opening_hours))
            if not any(day_token in normalized_hours for day_token in day_specific_tokens):
                if language == Language.DE:
                    return "Fuer diesen Wochentag sehe ich in der Wissensbasis keine eigenen Oeffnungszeiten"
                return "I do not see separate opening hours for that day in the knowledge base"
        if any(hint in normalized_transcript for hint in TODAY_QUERY_HINTS):
            today = datetime.now(UTC).date().isoformat()
            if language == Language.DE:
                return f"Fuer heute ({today}) stehen diese Oeffnungszeiten dort: {'; '.join(page.opening_hours)}"
            return f"For today ({today}), these opening hours are listed: {'; '.join(page.opening_hours)}"
        if language == Language.DE:
            return f"Die Oeffnungszeiten sind: {'; '.join(page.opening_hours)}"
        return f"The opening hours are: {'; '.join(page.opening_hours)}"
    if language == Language.DE:
        return "Ich sehe in der Wissensbasis keine klaren Oeffnungszeiten"
    return "I do not see clear opening hours in the knowledge base"


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
        return "The knowledge base does not say that an appointment is needed"
    if language == Language.DE:
        return "Ob ein Termin noetig ist, sehe ich dort nicht klar"
    return "I cannot clearly tell from the knowledge base whether an appointment is needed"


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
    if len(cleaned) > 320:
        cleaned = cleaned[:317].rstrip() + "..."
    if cleaned and cleaned[-1] not in ".!?":
        cleaned = f"{cleaned}."
    return cleaned


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
    ) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
        )
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
                "You are a local knowledge-base assistant for Leipzig support services.",
                "",
                "# Rules",
                "Answer only from the provided local knowledge base.",
                "Do not invent facts.",
                "If the KB does not clearly support the answer, return status unknown.",
                "If several pages may fit and the request is too vague, return status clarification_needed.",
                "If there is a closest match but support is weak, return status weak_match.",
                "Use plain language.",
                "Write short, natural sentences that sound clear when spoken aloud.",
                "Avoid jargon. If a hard term is necessary, explain it briefly.",
                "Keep important facts such as place name, address, opening hours, service type, and target group when they are supported by the KB.",
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
            "- Use plain language.\n"
            "- Write short, natural sentences that sound clear when spoken aloud.\n"
            "- Avoid jargon. If a hard term is necessary, explain it briefly.\n"
            "- Keep important facts such as place name, address, opening hours, service type, and target group when they are supported by the KB.\n"
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
    ) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
            weak_match_threshold=self.weak_match_threshold,
            conversation_context=conversation_context,
        )
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

        retrieved_page_ids = [item.page_id for item in retrieved]
        resolved_transcript = conversation_context.resolved_transcript if conversation_context else transcript
        context = _build_retrieved_context(resolved_transcript, language, kb, retrieved, conversation_context=conversation_context)
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
                "Retrieved knowledge base pages:",
                context,
                "",
                f"Overview hint: {overview_hint}" if overview_hint else "",
                follow_up_hint,
                "If several retrieved pages are locations of the same organisation, summarize them together instead of repeating one sentence per location.",
                "Answer only from the retrieved pages above.",
                "Always include the place name.",
                "Include the address and opening hours whenever they are available and directly useful.",
                "Use plain language and short sentences.",
                "Avoid jargon. If you need a hard term, explain it briefly.",
                "Make the answer easy to understand for a stressed user and easy to speak aloud.",
                "If the user asks where a place is, answer with the place name and address. Do not add opening hours unless the user asked for them." if is_location_query else "",
                "If the user asks about opening hours, focus on the hours answer and do not add unrelated service details." if is_hours_query or is_day_specific_query else "",
                "If the user asks about appointments, answer only whether an appointment is required, not required, or not clearly stated in the knowledge base." if is_appointment_query else "",
                "If several suitable places are retrieved, give 1 to 3 concrete options.",
                "Prefer the highest-scoring page unless another retrieved page adds directly relevant detail.",
                "Do not infer facts that are not explicitly supported by the retrieved pages.",
                "If a specific weekday is asked for, only say that the place is open on that day if that weekday is explicitly listed in OPENING_HOURS.",
                "Do not infer Sunday opening from Saturday hours or from public-holiday hours.",
                "If the knowledge base does not clearly say whether an appointment is needed, say that clearly instead of guessing." if is_appointment_query else "",
                "If the user asks about opening hours for a specific day and that day is not explicitly listed, say that the knowledge base does not clearly list separate hours for that day." if is_day_specific_query or is_hours_query else "",
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

        if answer.status == "self_description":
            answer.self_description = True
            return answer
        if answer.status == "out_of_scope":
            answer.out_of_scope = True
            return answer
        if answer.status == "crisis":
            answer.crisis_mode = True
            if not answer.retrieved_page_ids:
                answer.retrieved_page_ids = _known_response_page_ids(kb, "notfallkontakte", "telefonseelsorge-leipzig")
            return answer

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
            answer.answer_text = answer.answer_text or UNKNOWN_TEXT[language]
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


def create_rewrite_provider(
    name: str,
    ollama_url: str,
    ollama_model: str,
    ollama_timeout_seconds: float,
    minimum_match_threshold: float,
    weak_match_threshold: float,
    clarification_gap_threshold: float,
    system_prompt_path: Path | None = None,
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
    return TemplateRewriteProvider(
        minimum_match_threshold=minimum_match_threshold,
        weak_match_threshold=weak_match_threshold,
        clarification_gap_threshold=clarification_gap_threshold,
    )
