from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from .kb import KnowledgeBase
from .models import Language, PageMetadata, RetrievedPage


TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "bei",
    "bin",
    "bitte",
    "brauche",
    "brauchen",
    "can",
    "de",
    "der",
    "des",
    "die",
    "do",
    "du",
    "ein",
    "eine",
    "einen",
    "einer",
    "en",
    "es",
    "for",
    "get",
    "gibt",
    "hab",
    "habe",
    "haben",
    "hast",
    "hat",
    "have",
    "heute",
    "how",
    "i",
    "ich",
    "im",
    "in",
    "info",
    "informationen",
    "is",
    "kann",
    "kannst",
    "kde",
    "kurz",
    "mam",
    "mi",
    "mit",
    "na",
    "need",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "the",
    "to",
    "uber",
    "ueber",
    "und",
    "wann",
    "warum",
    "was",
    "wer",
    "what",
    "when",
    "where",
    "wie",
    "wo",
    "you",
}
GENERIC_QUERY_TOKENS = {
    "beratung",
    "brauch",
    "brauche",
    "hilfe",
    "information",
    "informationen",
    "service",
    "services",
    "support",
}
GENERIC_ALIAS_TERMS = {
    "hilfe",
    "leipzig",
    "leipziger",
    "service",
}
GERMAN_EQUIVALENTS = str.maketrans(
    {
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
    }
)
QUERY_EXPANSION_RULES: tuple[tuple[set[str], tuple[str, ...]], ...] = (
    ({"essen", "food", "jedzenie", "mancare", "еда"}, ("tafel", "lebensmittel", "lebensmittelausgabe", "mahlzeit", "mittagstisch", "fruehstueck", "suppe")),
    ({"kleidung", "clothes", "clothing", "ubrania", "haine", "одежда"}, ("kleiderkammer", "kleidung", "kleiderspenden")),
    ({"arzt", "doctor", "medical", "medizin", "medic", "lekarz", "doctor", "врач"}, ("gesundheit", "sprechstunde", "arzt", "medizin")),
    ({"schulden", "debt", "debts", "zadluzenie", "datorii", "долг"}, ("schuldnerberatung", "schulden", "beratung")),
    ({"unterkunft", "shelter", "sleep", "sleeping", "overnight", "nocleg", "adapost", "ночлег"}, ("notunterkunft", "uebernachtung", "notunterbringung", "wohnungslosigkeit")),
    ({"sucht", "drugs", "drug", "methadone", "substitution", "addiction", "uzaleznienie", "dependenta", "наркотики"}, ("sucht", "drogen", "methadon", "substitution", "schadensminimierung", "konsum")),
)
PHRASE_EXPANSION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ohne krankenversicherung", ("arzt", "medizin", "sprechstunde", "krankenversicherung")),
    ("without insurance", ("arzt", "medizin", "sprechstunde", "krankenversicherung")),
    ("sans assurance", ("arzt", "medizin", "sprechstunde", "krankenversicherung")),
)
DOCUMENT_HINTS = {"broschuere", "jahresbericht", "bericht"}
LOCATION_QUERY_TOKENS = {"adresse", "ort", "platz", "naehe", "nahe", "closest", "close", "location"}
HOURS_QUERY_TOKENS = {"offen", "open", "oeffnungszeiten", "hours", "today", "heute", "sonntag", "sunday"}
CATEGORY_QUERY_HINTS = {
    "food": {"essen", "food", "tafel", "lebensmittel", "mittagstisch", "mahlzeit", "fruehstueck", "suppe"},
    "housing": {"unterkunft", "shelter", "uebernachtung", "notunterkunft", "wohnungslosigkeit"},
    "medical": {"arzt", "medical", "medizin", "sprechstunde", "gesundheit"},
    "addiction": {"sucht", "drug", "drugs", "methadon", "substitution", "konsum"},
    "clothing": {"kleidung", "clothing", "kleiderkammer", "kleiderspenden"},
}
RELATED_CATEGORIES = {
    "food": {"food", "social", "housing"},
    "housing": {"housing", "social"},
    "medical": {"medical", "social"},
    "addiction": {"addiction", "social", "housing"},
    "clothing": {"clothing", "social", "housing"},
}


def normalize_text(text: str) -> str:
    normalized = text.casefold().translate(GERMAN_EQUIVALENTS)
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [token for token in TOKEN_RE.findall(normalized) if token not in STOPWORDS and len(token) > 1]


def query_tokens_for_search(text: str, language: Language | None = None) -> list[str]:
    del language
    normalized = normalize_text(text)
    tokens = tokenize(text)
    expanded = list(tokens)
    token_set = set(tokens)

    for triggers, additions in QUERY_EXPANSION_RULES:
        if token_set & triggers:
            for addition in additions:
                if addition not in token_set:
                    expanded.append(addition)
    for phrase, additions in PHRASE_EXPANSION_RULES:
        if phrase in normalized:
            for addition in additions:
                if addition not in token_set:
                    expanded.append(addition)
    unique_tokens = _unique(expanded)
    specific_tokens = [token for token in unique_tokens if token not in GENERIC_QUERY_TOKENS]
    if specific_tokens:
        return specific_tokens
    return unique_tokens


def content_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw_line in strip_frontmatter(markdown).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# ") or line.startswith("- Source:") or line.startswith("- Generated:"):
            continue
        cleaned = line.lstrip("- ").strip()
        if _is_low_signal_line(cleaned):
            continue
        lines.append(cleaned)
    return lines


def strip_frontmatter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    parts = markdown.split("\n---\n", 1)
    if len(parts) == 2:
        return parts[1]
    return markdown


def extract_relevant_passages(
    query: str,
    markdown: str,
    limit: int = 2,
    query_tokens: set[str] | None = None,
) -> list[str]:
    lines = content_lines(markdown)
    if not lines:
        return []

    search_tokens = query_tokens or set(tokenize(query))
    if not search_tokens:
        return lines[:limit]

    ranked: list[tuple[float, int, str]] = []
    query_counts = Counter(search_tokens)
    for index, line in enumerate(lines):
        window = [line]
        total_length = len(line)
        for next_index in range(index + 1, min(len(lines), index + 3)):
            if total_length >= 260:
                break
            next_line = lines[next_index]
            if _is_low_signal_line(next_line):
                continue
            window.append(next_line)
            total_length += len(next_line)

        passage = " ".join(window).strip()
        passage_tokens = tokenize(passage)
        score = _score_tokens(query_counts, passage_tokens)
        overlap_tokens = search_tokens & set(passage_tokens)
        if not overlap_tokens:
            continue
        score += sum(min(len(token), 10) for token in overlap_tokens) * 0.01
        ranked.append((score, index, passage))

    if not ranked:
        return lines[:limit]

    ranked.sort(key=lambda item: (-item[0], item[1]))
    passages: list[str] = []
    for _, _, passage in ranked:
        if passage not in passages:
            passages.append(passage)
        if len(passages) == limit:
            break
    return passages


class RetrievalEngine:
    def __init__(self, kb: KnowledgeBase) -> None:
        self.kb = kb

    def retrieve(
        self,
        transcript: str,
        language: Language,
        limit: int = 3,
        preferred_page_ids: list[str] | None = None,
        excluded_page_ids: list[str] | None = None,
    ) -> list[RetrievedPage]:
        tokens = query_tokens_for_search(transcript, language)
        if not tokens:
            return []

        query_counts = Counter(tokens)
        query_token_set = set(tokens)
        normalized_query = normalize_text(transcript).strip()
        alias_hits = self._alias_hits(transcript, tokens)
        preferred_page_ids = preferred_page_ids or []
        excluded_page_ids = set(excluded_page_ids or [])
        ranked: list[tuple[float, PageMetadata]] = []
        location_query = bool(query_token_set & LOCATION_QUERY_TOKENS)
        hours_query = bool(query_token_set & HOURS_QUERY_TOKENS)
        query_category = _detect_query_category(query_token_set)

        for page in self.kb.dataset.pages:
            if page.page_id in excluded_page_ids:
                continue
            markdown = self.kb.get_page_markdown(page.page_id)
            score = 0.0
            score += self._field_score(query_counts, page.title, weight=3.2)
            score += self._field_score(query_counts, page.page_id.replace("-", " "), weight=2.8)
            score += self._field_score(query_counts, page.category, weight=0.9)
            score += self._field_score(query_counts, page.description, weight=1.4)
            score += self._field_score(query_counts, " ".join(page.tags), weight=2.2)
            score += self._field_score(query_counts, " ".join(page.aliases), weight=2.4)
            score += self._field_score(query_counts, page.address or "", weight=2.1)
            score += self._field_score(query_counts, " ".join(page.opening_hours), weight=1.8)
            score += self._field_score(query_counts, page.publisher or "", weight=0.35)
            score += self._field_score(query_counts, page.summary, weight=0.55)
            score += self._best_passage_score(query_counts, markdown) * 2.4
            score += alias_hits.get(page.page_id, 0.0)
            if page.language == language.value:
                score += 0.08
            if location_query and page.address:
                score += 0.12
            if hours_query and page.opening_hours:
                score += 0.14
            if page.page_id in preferred_page_ids:
                score += 0.28
            score += self._category_score(query_category, page)
            score += self._exact_match_boost(normalized_query, query_token_set, page)
            score -= self._document_penalty(page)
            if score > 0.04:
                ranked.append((score, page))

        ranked.sort(key=lambda item: (-item[0], item[1].page_id))
        return [RetrievedPage(page_id=page.page_id, title=page.title, score=round(score, 4)) for score, page in ranked[:limit]]

    def _field_score(self, query_counts: Counter[str], text: str, weight: float) -> float:
        return _score_tokens(query_counts, tokenize(text)) * weight

    def _best_passage_score(self, query_counts: Counter[str], markdown: str) -> float:
        best = 0.0
        lines = content_lines(markdown)
        for index, line in enumerate(lines):
            window = [line]
            for next_index in range(index + 1, min(len(lines), index + 3)):
                window.append(lines[next_index])
            score = _score_tokens(query_counts, tokenize(" ".join(window)))
            best = max(best, score)
        return best

    def _exact_match_boost(self, normalized_query: str, query_token_set: set[str], page: PageMetadata) -> float:
        normalized_title = normalize_text(page.title)
        normalized_page_id = normalize_text(page.page_id.replace("-", " "))
        title_tokens = set(tokenize(page.title))
        page_id_tokens = set(tokenize(page.page_id.replace("-", " ")))

        boost = 0.0
        if normalized_query and normalized_query == normalized_title:
            boost += 0.55
        if normalized_query and normalized_query == normalized_page_id:
            boost += 0.75
        if query_token_set and query_token_set <= title_tokens:
            boost += 0.18
        if query_token_set and query_token_set <= page_id_tokens:
            boost += 0.22
        return boost

    def _document_penalty(self, page: PageMetadata) -> float:
        normalized = normalize_text(f"{page.page_id} {page.title}")
        if any(hint in normalized for hint in DOCUMENT_HINTS):
            return 0.08
        return 0.0

    def _category_score(self, query_category: str | None, page: PageMetadata) -> float:
        if not query_category:
            return 0.0
        page_tokens = set(
            tokenize(
                " ".join(
                    [
                        page.title,
                        page.description,
                        page.summary,
                        page.category,
                        " ".join(page.tags),
                        " ".join(page.aliases),
                    ]
                )
            )
        )
        if page.category == query_category:
            return 0.65
        if page.category in RELATED_CATEGORIES.get(query_category, set()):
            if page_tokens & CATEGORY_QUERY_HINTS.get(query_category, set()):
                return 0.35
            return -0.55
        return -0.8

    def _alias_hits(self, transcript: str, tokens: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        token_set = set(tokens)
        normalized_transcript = normalize_text(transcript)
        for alias, page_ids in self.kb.dataset.aliases.items():
            normalized_alias = normalize_text(alias)
            if normalized_alias in GENERIC_ALIAS_TERMS:
                continue
            if len(normalized_alias) < 4 and " " not in normalized_alias:
                continue
            matched = normalized_alias in token_set or (" " in normalized_alias and normalized_alias in normalized_transcript)
            if not matched:
                continue
            page_count = max(len(page_ids), 1)
            bonus = (0.18 if " " in normalized_alias else 0.08) / page_count
            if normalized_alias == normalized_transcript:
                bonus += 0.08 / page_count
            for page_id in page_ids:
                scores[page_id] = scores.get(page_id, 0.0) + bonus
        return scores

    def should_clarify(self, results: list[RetrievedPage], transcript: str, threshold_gap: float) -> bool:
        if not results:
            return False

        query_tokens = tokenize(transcript)
        generic_query = _is_generic_query(query_tokens)
        top_score = results[0].score

        if generic_query and len(results) >= 2:
            return abs(results[0].score - results[1].score) < max(threshold_gap, 0.08) or top_score < 0.45
        if generic_query:
            return True
        if len(query_tokens) < 2 and top_score < 0.32:
            return True
        if len(results) >= 2:
            gap = abs(results[0].score - results[1].score)
            if gap < threshold_gap and top_score < 0.24:
                return True
            if len(query_tokens) <= 2 and gap < 0.06 and top_score < 0.5:
                return True
        return False


def _score_tokens(query_counts: Counter[str], text_tokens: list[str]) -> float:
    if not query_counts or not text_tokens:
        return 0.0

    text_counts = Counter(text_tokens)
    dot = sum(query_counts[token] * text_counts.get(token, 0) for token in query_counts)
    if not dot:
        return 0.0

    query_norm = math.sqrt(sum(value * value for value in query_counts.values()))
    text_norm = math.sqrt(sum(value * value for value in text_counts.values()))
    cosine = dot / (query_norm * text_norm) if query_norm and text_norm else 0.0
    overlap = len(set(query_counts) & set(text_counts)) / max(len(query_counts), 1)
    return cosine * 0.65 + overlap * 0.35


def _is_generic_query(tokens: list[str]) -> bool:
    if not tokens:
        return False
    informative_tokens = [token for token in tokens if token not in GENERIC_QUERY_TOKENS]
    return not informative_tokens or len(informative_tokens) == 1 and len(tokens) <= 2


def _detect_query_category(query_token_set: set[str]) -> str | None:
    for category, hints in CATEGORY_QUERY_HINTS.items():
        if query_token_set & hints:
            return category
    return None


def _is_low_signal_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith("[") and stripped.endswith("]"):
        return True
    if stripped.startswith("[") and "](" in stripped:
        return True
    if stripped.lower() in {"kontakt", "telefon:", "mail:", "e-mail:"}:
        return True
    return len(stripped) < 3


def _unique(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_tokens: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        unique_tokens.append(token)
    return unique_tokens
