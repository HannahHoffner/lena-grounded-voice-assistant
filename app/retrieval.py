from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from .kb import KnowledgeBase
from .models import Language, PageMetadata, RetrievedPage


TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
DETAIL_TOKEN_RE = re.compile(r"\b\d{1,5}[a-z]?\b", re.UNICODE)
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
    "work",
    "works",
    "wo",
    "you",
}
GENERIC_QUERY_TOKENS = {
    "beratung",
    "appointment",
    "brauch",
    "brauche",
    "help",
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
EXTRA_QUERY_EXPANSION_RULES: tuple[tuple[set[str], tuple[str, ...]], ...] = (
    (
        {
            "dus",
            "dusche",
            "duschen",
            "duschgelegenheit",
            "laundry",
            "pomytsya",
            "prysznic",
            "shower",
            "wash",
            "washing",
            "waesche",
            "waescheservice",
            "waschen",
        },
        ("dusche", "duschgelegenheit", "koerperpflege", "waeschepflege", "tageseinrichtung"),
    ),
    (
        {"termin", "appointment", "anmeldung", "registrierung", "registration"},
        ("termin", "anmeldung", "sprechstunde", "walk", "walkin"),
    ),
    ({"frau", "frauen", "woman", "women", "kobieta", "femeie"}, ("frauen", "frau", "uebernachtung", "notunterkunft")),
    ({"mann", "maenner", "manner", "men", "man", "barbat"}, ("maenner", "mann", "uebernachtung", "notunterkunft")),
    ({"naloxone", "naloxon", "overdose", "ueberdosis"}, ("naloxon", "schadensminimierung", "safe", "konsum")),
)
EXTRA_CATEGORY_QUERY_HINTS = {
    "hygiene": {
        "dusche",
        "duschen",
        "duschgelegenheit",
        "shower",
        "wash",
        "washing",
        "waesche",
        "waeschepflege",
        "waescheservice",
        "waschen",
        "toilette",
        "toiletten",
        "koerperpflege",
    },
}
EXTRA_RELATED_CATEGORIES = {
    "hygiene": {"hygiene", "social", "housing", "clothing"},
}


def normalize_text(text: str) -> str:
    normalized = text.casefold().translate(GERMAN_EQUIVALENTS)
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [token for token in TOKEN_RE.findall(normalized) if token not in STOPWORDS and len(token) > 1]


def detail_tokens(text: str) -> list[str]:
    normalized = normalize_text(text)
    return _unique(DETAIL_TOKEN_RE.findall(normalized))


def query_tokens_for_search(text: str, language: Language | None = None) -> list[str]:
    del language
    normalized = normalize_text(text)
    tokens = tokenize(text)
    expanded = list(tokens)
    token_set = set(tokens)

    for triggers, additions in QUERY_EXPANSION_RULES + EXTRA_QUERY_EXPANSION_RULES:
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
        detail_query_tokens = detail_tokens(transcript)
        detail_query_counts = Counter(detail_query_tokens)
        normalized_query = normalize_text(transcript).strip()
        alias_hits = self._alias_hits(transcript, tokens)
        preferred_page_ids = preferred_page_ids or []
        excluded_page_ids = set(excluded_page_ids or [])
        ranked: list[tuple[float, PageMetadata]] = []
        location_query = bool(query_token_set & LOCATION_QUERY_TOKENS)
        hours_query = bool(query_token_set & HOURS_QUERY_TOKENS)
        query_category = _detect_query_category(query_token_set)
        specific_place_query = _is_specific_place_query(query_token_set, detail_query_tokens, query_category)

        for page in self.kb.dataset.pages:
            if page.page_id in excluded_page_ids:
                continue
            markdown = self.kb.get_page_markdown(page.page_id)
            lexical_score = 0.0
            lexical_score += self._field_score(query_counts, page.title, weight=3.2)
            lexical_score += self._field_score(query_counts, page.page_id.replace("-", " "), weight=2.8)
            lexical_score += self._field_score(query_counts, page.category, weight=0.9)
            lexical_score += self._field_score(query_counts, page.service_type, weight=1.35)
            lexical_score += self._field_score(query_counts, page.description, weight=1.4)
            lexical_score += self._field_score(query_counts, " ".join(page.tags), weight=2.2)
            lexical_score += self._field_score(query_counts, " ".join(page.aliases), weight=2.4)
            lexical_score += self._field_score(query_counts, " ".join(page.target_groups), weight=1.7)
            lexical_score += self._field_score(query_counts, page.gender_access or "", weight=1.1)
            lexical_score += self._field_score(query_counts, " ".join(page.languages), weight=0.35)
            lexical_score += self._field_score(query_counts, page.address or "", weight=2.1)
            lexical_score += self._field_score(query_counts, " ".join(page.opening_hours), weight=1.8)
            lexical_score += self._field_score(query_counts, page.phone or "", weight=0.2)
            lexical_score += self._field_score(query_counts, page.email or "", weight=0.2)
            lexical_score += self._field_score(query_counts, page.publisher or "", weight=0.35)
            lexical_score += self._field_score(query_counts, page.summary, weight=0.55)
            lexical_score += self._detail_field_score(detail_query_counts, page.address or "", weight=2.6)
            lexical_score += self._detail_field_score(detail_query_counts, " ".join(page.opening_hours), weight=1.7)
            lexical_score += self._best_passage_score(query_counts, markdown) * 2.4
            lexical_score += alias_hits.get(page.page_id, 0.0)
            lexical_score += self._category_score(query_category, page)
            lexical_score += self._exact_match_boost(normalized_query, query_token_set, query_category, page)
            lexical_score += self._detail_match_boost(detail_query_tokens, page)

            has_match_signal = lexical_score > 0.02 or page.page_id in preferred_page_ids
            score = lexical_score
            if has_match_signal and page.language == language.value:
                score += 0.08
            if has_match_signal and location_query and page.address:
                score += 0.12
            if has_match_signal and hours_query and page.opening_hours:
                score += 0.14
            if page.page_id in preferred_page_ids:
                score += 0.6 if has_match_signal else 0.32
            score += self._concrete_page_score(
                page,
                location_query=location_query,
                hours_query=hours_query,
                specific_place_query=specific_place_query,
                detail_query_tokens=detail_query_tokens,
                has_match_signal=has_match_signal,
            )
            score -= self._document_penalty(page)
            score -= self._review_penalty(page)
            if score > 0.04:
                ranked.append((score, page))

        ranked.sort(key=lambda item: (-item[0], item[1].page_id))
        return [RetrievedPage(page_id=page.page_id, title=page.title, score=round(score, 4)) for score, page in ranked[:limit]]

    def _field_score(self, query_counts: Counter[str], text: str, weight: float) -> float:
        return _score_tokens(query_counts, tokenize(text)) * weight

    def _detail_field_score(self, query_counts: Counter[str], text: str, weight: float) -> float:
        return _score_tokens(query_counts, detail_tokens(text)) * weight

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

    def _exact_match_boost(
        self,
        normalized_query: str,
        query_token_set: set[str],
        query_category: str | None,
        page: PageMetadata,
    ) -> float:
        normalized_title = normalize_text(page.title)
        normalized_page_id = normalize_text(page.page_id.replace("-", " "))
        title_tokens = set(tokenize(page.title))
        page_id_tokens = set(tokenize(page.page_id.replace("-", " ")))
        page_match_tokens = set(tokenize(" ".join([page.title, page.page_id.replace("-", " "), " ".join(page.aliases), page.address or ""])))
        category_hints = CATEGORY_QUERY_HINTS.get(query_category, set()) | EXTRA_CATEGORY_QUERY_HINTS.get(query_category, set())
        raw_query_tokens = set(tokenize(normalized_query))
        specific_query_tokens = {
            token
            for token in raw_query_tokens
            if token not in GENERIC_QUERY_TOKENS and token not in category_hints
        }

        boost = 0.0
        if normalized_query and normalized_query == normalized_title:
            boost += 0.55
        if normalized_query and normalized_query == normalized_page_id:
            boost += 0.75
        if query_token_set and query_token_set <= title_tokens:
            boost += 0.18
        if query_token_set and query_token_set <= page_id_tokens:
            boost += 0.22
        if specific_query_tokens and specific_query_tokens <= page_match_tokens:
            boost += 1.35
        normalized_address = normalize_text(page.address or "")
        normalized_hours = normalize_text(" ".join(page.opening_hours))
        normalized_aliases = [normalize_text(alias) for alias in page.aliases]
        if normalized_query and normalized_address and normalized_query in normalized_address:
            boost += 1.25
        if normalized_query and normalized_hours and normalized_query in normalized_hours:
            boost += 0.9
        if normalized_query and any(normalized_query == alias for alias in normalized_aliases):
            boost += 0.55
        return boost

    def _detail_match_boost(self, detail_query_tokens: list[str], page: PageMetadata) -> float:
        if not detail_query_tokens:
            return 0.0
        page_detail_tokens = set(detail_tokens(" ".join([page.address or "", " ".join(page.opening_hours)])))
        if not page_detail_tokens:
            return -0.08
        overlap = set(detail_query_tokens) & page_detail_tokens
        if not overlap:
            return -0.18
        if set(detail_query_tokens) <= page_detail_tokens:
            return 0.95
        return 0.22 * len(overlap)

    def _concrete_page_score(
        self,
        page: PageMetadata,
        *,
        location_query: bool,
        hours_query: bool,
        specific_place_query: bool,
        detail_query_tokens: list[str],
        has_match_signal: bool,
    ) -> float:
        score = 0.0
        is_catalog = page.service_type == "service_catalog"
        if is_catalog:
            if has_match_signal and (specific_place_query or location_query or hours_query or detail_query_tokens):
                score -= 1.2
            else:
                score += 0.04
        else:
            if has_match_signal and specific_place_query:
                score += 0.22
            if has_match_signal and location_query and page.address:
                score += 0.2
            if has_match_signal and hours_query and page.opening_hours:
                score += 0.2
        if has_match_signal and location_query and not page.address:
            score -= 0.22
        if has_match_signal and hours_query and not page.opening_hours:
            score -= 0.18
        return score

    def _document_penalty(self, page: PageMetadata) -> float:
        normalized = normalize_text(f"{page.page_id} {page.title}")
        if any(hint in normalized for hint in DOCUMENT_HINTS):
            return 0.08
        return 0.0

    def _review_penalty(self, page: PageMetadata) -> float:
        if page.review_status == "needs_review":
            return 0.06 + min(len(page.validation_issues), 4) * 0.01
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
                        page.service_type,
                        " ".join(page.tags),
                        " ".join(page.aliases),
                        " ".join(page.target_groups),
                        page.gender_access or "",
                    ]
                )
            )
        )
        if page.category == query_category:
            return 0.65
        related_categories = RELATED_CATEGORIES.get(query_category, set()) | EXTRA_RELATED_CATEGORIES.get(query_category, set())
        category_hints = CATEGORY_QUERY_HINTS.get(query_category, set()) | EXTRA_CATEGORY_QUERY_HINTS.get(query_category, set())
        if page.category in related_categories:
            if page_tokens & category_hints:
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

        if generic_query and len(query_tokens) <= 1:
            return True
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
    return not informative_tokens


def _detect_query_category(query_token_set: set[str]) -> str | None:
    for category, hints in {**CATEGORY_QUERY_HINTS, **EXTRA_CATEGORY_QUERY_HINTS}.items():
        if query_token_set & hints:
            return category
    return None


def _is_specific_place_query(
    query_token_set: set[str],
    detail_query_tokens: list[str],
    query_category: str | None,
) -> bool:
    if detail_query_tokens:
        return True
    category_hints = CATEGORY_QUERY_HINTS.get(query_category, set()) | EXTRA_CATEGORY_QUERY_HINTS.get(query_category, set())
    specific_tokens = {
        token
        for token in query_token_set
        if token not in GENERIC_QUERY_TOKENS
        and token not in LOCATION_QUERY_TOKENS
        and token not in HOURS_QUERY_TOKENS
        and token not in category_hints
    }
    return bool(specific_tokens)


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
