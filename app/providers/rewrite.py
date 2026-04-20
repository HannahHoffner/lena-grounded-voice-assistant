from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
import re

import httpx

from ..kb import KnowledgeBase
from ..models import KnowledgeAnswer, Language, RetrievedPage
from ..retrieval import RetrievalEngine, content_lines, extract_relevant_passages, query_tokens_for_search, tokenize


UNKNOWN_TEXT = {
    Language.DE: "Dazu habe ich in der Wissensbasis keine verlaessliche Information gefunden.",
    Language.EN: "I could not find reliable information about that in the knowledge base.",
    Language.PL: "Nie znalazlem wiarygodnej informacji na ten temat w bazie wiedzy.",
    Language.RO: "Nu am gasit informatii sigure despre asta in baza de cunostinte.",
    Language.RU: "Я не нашёл надёжной информации об этом в базе знаний.",
}

CLARIFY_TEXT = {
    Language.DE: "Koennen Sie kurz sagen, welche Art von Hilfe Sie brauchen?",
    Language.EN: "Can you briefly say what kind of help you need?",
    Language.PL: "Czy mozesz krotko powiedziec, jakiej pomocy potrzebujesz?",
    Language.RO: "Poti spune pe scurt de ce tip de ajutor ai nevoie?",
    Language.RU: "Можете коротко сказать, какая помощь вам нужна?",
}

WEAK_PREFIX = {
    Language.DE: "Ich habe nur einen aehnlichen Treffer gefunden: ",
    Language.EN: "I only found a close match in the knowledge base: ",
    Language.PL: "Znalazlem tylko podobny wpis w bazie wiedzy: ",
    Language.RO: "Am gasit doar o potrivire apropiata in baza de cunostinte: ",
    Language.RU: "Я нашёл только близкое совпадение в базе знаний: ",
}

TOPIC_LABELS = {
    "food": {
        Language.DE: "Essen",
        Language.EN: "food",
        Language.PL: "jedzenie",
        Language.RO: "mancare",
        Language.RU: "еда",
    },
    "shelter": {
        Language.DE: "Unterkunft",
        Language.EN: "shelter",
        Language.PL: "nocleg",
        Language.RO: "adapost",
        Language.RU: "ночлег",
    },
    "clothing": {
        Language.DE: "Kleidung",
        Language.EN: "clothing",
        Language.PL: "ubrania",
        Language.RO: "haine",
        Language.RU: "одежда",
    },
    "medical": {
        Language.DE: "medizinische Hilfe",
        Language.EN: "medical help",
        Language.PL: "pomoc medyczna",
        Language.RO: "ajutor medical",
        Language.RU: "медицинская помощь",
    },
    "addiction": {
        Language.DE: "Sucht",
        Language.EN: "addiction support",
        Language.PL: "pomoc przy uzaleznieniu",
        Language.RO: "sprijin pentru dependenta",
        Language.RU: "помощь при зависимости",
    },
    "debt": {
        Language.DE: "Schulden",
        Language.EN: "debt advice",
        Language.PL: "dlugi",
        Language.RO: "datorii",
        Language.RU: "долги",
    },
    "counseling": {
        Language.DE: "Beratung",
        Language.EN: "counseling",
        Language.PL: "poradnictwo",
        Language.RO: "consiliere",
        Language.RU: "консультация",
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
ATTRIBUTE_QUERY_TOKENS = {"adresse", "email", "kontakt", "mail", "oeffnungszeiten", "offen", "telefon", "uhr", "zeit"}
NOTICE_HINTS = ("ferien", "wartezeiten", "hinweisen", "stand:", "druck:", "impressum")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
SPACE_RE = re.compile(r"\s+")


class BaseRewriteProvider(ABC):
    name = "base"
    model_name: str | None = None
    uses_llm = False

    @abstractmethod
    async def answer(self, transcript: str, language: Language, kb: KnowledgeBase) -> KnowledgeAnswer:
        raise NotImplementedError


def _ground_query(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    minimum_match_threshold: float,
    clarification_gap_threshold: float,
) -> tuple[list[RetrievedPage], KnowledgeAnswer | None]:
    retrieval = RetrievalEngine(kb)
    retrieved = retrieval.retrieve(transcript, language)
    if not retrieved:
        return [], KnowledgeAnswer(answer_text=UNKNOWN_TEXT[language], status="unknown")

    if retrieval.should_clarify(retrieved, transcript, clarification_gap_threshold):
        question = _build_clarification_question(language, kb, retrieved)
        return retrieved, KnowledgeAnswer(
            answer_text=question,
            status="clarification_needed",
            clarification_needed=True,
            clarification_question=question,
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

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
) -> KnowledgeAnswer:
    if not retrieved or retrieved[0].score < minimum_match_threshold:
        return KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    page = kb.get_page(retrieved[0].page_id)
    search_tokens = set(query_tokens_for_search(transcript, language))
    markdown = kb.get_page_markdown(page.page_id)
    passages = extract_relevant_passages(transcript, markdown, query_tokens=search_tokens)
    snippet = _select_snippet(transcript, language, page.title, markdown, passages, page.summary)
    if not snippet:
        return KnowledgeAnswer(
            answer_text=UNKNOWN_TEXT[language],
            status="unknown",
            retrieved_page_ids=[item.page_id for item in retrieved],
        )

    weak = retrieved[0].score < weak_match_threshold
    answer_text = snippet
    if weak:
        answer_text = f"{WEAK_PREFIX[language]}{page.title}. {snippet}"

    return KnowledgeAnswer(
        answer_text=answer_text,
        status="weak_match" if weak else "ok",
        weak_match=weak,
        retrieved_page_ids=[item.page_id for item in retrieved],
    )


def _build_retrieved_context(
    transcript: str,
    language: Language,
    kb: KnowledgeBase,
    retrieved: list[RetrievedPage],
    limit: int = 3,
) -> str:
    search_tokens = set(query_tokens_for_search(transcript, language))
    sections: list[str] = []
    for item in _select_context_pages(retrieved, limit=limit):
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
                    f"SOURCE_URL: {page.source_url}",
                    f"LAST_UPDATED: {page.last_updated}",
                    f"TAGS: {', '.join(page.tags)}",
                    f"SUMMARY: {_clean_answer_text(page.summary)}",
                    "RELEVANT_PASSAGES:",
                    *[f"- {passage}" for passage in relevant_passages],
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


def _select_context_pages(retrieved: list[RetrievedPage], limit: int = 3) -> list[RetrievedPage]:
    if not retrieved:
        return []
    if len(retrieved) == 1:
        return retrieved[:1]

    top_score = retrieved[0].score
    selected = [retrieved[0]]
    for item in retrieved[1:limit]:
        if item.score >= top_score * 0.45:
            selected.append(item)
    return selected[:limit]


def _select_snippet(
    transcript: str,
    language: Language,
    page_title: str,
    markdown: str,
    passages: list[str],
    summary: str,
) -> str:
    search_tokens = set(query_tokens_for_search(transcript, language))
    attribute_query = bool(search_tokens & ATTRIBUTE_QUERY_TOKENS)
    intro_candidates = content_lines(markdown)[:6]
    ordered_candidates = passages + intro_candidates if attribute_query else intro_candidates + passages
    ordered_candidates.append(summary)

    for candidate in ordered_candidates:
        cleaned = _clean_answer_text(candidate)
        if not cleaned or _looks_like_notice(cleaned):
            continue
        candidate_tokens = set(tokenize(cleaned))
        if search_tokens and not attribute_query and not candidate_tokens & search_tokens:
            continue
        if not attribute_query and _looks_too_detailed(cleaned):
            continue
        if "ausgabestellen" in cleaned.casefold():
            return _distribution_points_answer(page_title, language)
        if len(tokenize(cleaned)) < 3:
            continue
        return cleaned

    return _title_only_answer(page_title, language)


def _clean_answer_text(text: str) -> str:
    cleaned = LINK_RE.sub(r"\1", text or "")
    cleaned = cleaned.replace("•", " ").replace("·", " ").replace("\uf0b7", " ")
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


def _looks_like_notice(text: str) -> bool:
    lowered = text.casefold()
    if any(hint in lowered for hint in NOTICE_HINTS):
        return True
    return text.count("(") >= 2 and sum(char.isdigit() for char in text) > 4


def _looks_too_detailed(text: str) -> bool:
    digit_ratio = sum(char.isdigit() for char in text) / max(len(text), 1)
    return digit_ratio > 0.12 or len(text) > 320


def _title_only_answer(page_title: str, language: Language) -> str:
    if language == Language.DE:
        return f"In der Wissensbasis gibt es Informationen zu {page_title}."
    if language == Language.EN:
        return f"The knowledge base has information about {page_title}."
    if language == Language.PL:
        return f"W bazie wiedzy sa informacje o {page_title}."
    if language == Language.RO:
        return f"In baza de cunostinte exista informatii despre {page_title}."
    return f"В базе знаний есть информация о {page_title}."


def _distribution_points_answer(page_title: str, language: Language) -> str:
    if language == Language.DE:
        return f"{page_title} hat mehrere Ausgabestellen."
    if language == Language.EN:
        return f"{page_title} has several distribution points."
    if language == Language.PL:
        return f"{page_title} ma kilka punktow wydawania."
    if language == Language.RO:
        return f"{page_title} are mai multe puncte de distribuire."
    return f"У {page_title} есть несколько пунктов выдачи."


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
        return f"Koennen Sie kurz sagen, ob es um {', '.join(labels[:-1]) + ' oder ' + labels[-1] if len(labels) > 1 else labels[0]} geht?"
    if language == Language.EN:
        return f"Can you briefly say whether you need {', '.join(labels[:-1]) + ' or ' + labels[-1] if len(labels) > 1 else labels[0]}?"
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

    async def answer(self, transcript: str, language: Language, kb: KnowledgeBase) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
        )
        if early_answer:
            return early_answer
        return _fallback_answer(
            transcript,
            language,
            kb,
            retrieved,
            minimum_match_threshold=self.minimum_match_threshold,
            weak_match_threshold=self.weak_match_threshold,
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
                "Write short, natural sentences that sound clear when spoken aloud.",
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
            "- Write short, natural sentences that sound clear when spoken aloud.\n"
            "- Prefer the highest-scoring retrieved page. Only use lower-scoring pages if they add clearly relevant detail.\n"
            "- Answer in one or two short sentences unless the question clearly needs more.\n\n"
            f"Respond in language: {language.value}.\nReturn JSON only."
        )

    async def answer(self, transcript: str, language: Language, kb: KnowledgeBase) -> KnowledgeAnswer:
        retrieved, early_answer = _ground_query(
            transcript,
            language,
            kb,
            minimum_match_threshold=self.minimum_match_threshold,
            clarification_gap_threshold=self.clarification_gap_threshold,
        )
        if early_answer:
            return early_answer

        retrieved_page_ids = [item.page_id for item in retrieved]
        context = _build_retrieved_context(transcript, language, kb, retrieved)
        schema = KnowledgeAnswer.model_json_schema()
        system_prompt = self._load_system_prompt(language)
        user_prompt = "\n".join(
            [
                "User request:",
                transcript,
                "",
                "Retrieved knowledge base pages:",
                context,
                "",
                "Answer only from the retrieved pages above.",
                "Prefer the highest-scoring page unless another retrieved page adds directly relevant detail.",
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
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
            )

        answer.retrieved_page_ids = retrieved_page_ids
        answer.answer_text = _clean_answer_text(answer.answer_text)
        weak = retrieved[0].score < self.weak_match_threshold

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
            return answer

        if not answer.answer_text:
            return _fallback_answer(
                transcript,
                language,
                kb,
                retrieved,
                minimum_match_threshold=self.minimum_match_threshold,
                weak_match_threshold=self.weak_match_threshold,
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
