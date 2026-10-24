"""Historischer lexikalischer Retrievalbaseline (kein aktiver Anfragepfad).

Der produktive Anfragepfad wählt Kandidaten über ``candidates.py`` aus der
kuratierten Runtime. ``retrieve``/``select_card_offers`` bleiben als
Forschungs- und Regressionsbaseline erhalten und werden ausschließlich von
``tests/test_retrieval.py`` verwendet (Audit C-01/C-02). Die früher hier
definierte, aktiv genutzte Normalisierung liegt in ``text_normalization.py``
und wird für Kompatibilität re-exportiert.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Category, OfferRecord
from .text_normalization import normalize_text  # noqa: F401  (re-export, Baseline-Kompatibilität)


CATEGORY_TERMS: dict[Category, set[str]] = {
    Category.FOOD: {
        "essen", "lebensmittel", "mahlzeit", "fruhstuck", "mittagessen", "imbiss", "suppe",
        "getranke", "hunger", "brotchen", "food", "eat", "meal", "breakfast", "lunch", "hungry",
        "jedzenie", "zywnosc", "posilek", "glodny", "sniadanie", "mancare", "alimente", "foame",
        "masa", "еда", "пища", "голод", "завтрак", "обед",
    },
    Category.SLEEP: {
        "schlafen", "schlafplatz", "ubernachten", "ubernachtung", "ubernachtungsplatz", "notschlafstelle",
        "notunterbringung", "unterkunft", "wohnungslos", "obdachlos", "sleep", "overnight", "stay",
        "shelter", "accommodation", "homeless", "spanie", "nocleg", "przenocowac", "schronienie",
        "bezdomny", "dormit", "innopta", "adapost", "cazare", "fara adapost", "сон", "ночлег",
        "переночевать", "приют", "бездомный", "спать",
    },
    Category.MEDICAL: {
        "medizin", "medizinisch", "medizinische", "arzt", "arztlich", "arztliche", "behandlung", "sprechstunde", "gesundheit", "wunde",
        "medical", "doctor", "health", "treatment", "clinic", "medyczna", "lekarz", "zdrowie", "leczenie",
        "medicala", "medic", "sanatate", "tratament", "медицина", "врач", "здоровье", "лечение",
    },
    Category.ADVICE: {
        "beratung", "unterstutzung", "vermittlung", "amter", "behorden", "sozialberatung", "hilfe",
        "advice", "support", "counselling", "counseling", "authority", "authorities", "porada", "wsparcie",
        "doradztwo", "urzad", "consiliere", "sprijin", "autoritati", "консультация", "поддержка", "совет",
        "ведомство",
    },
    Category.TOILET: {
        "toilette", "toiletten", "wc", "klo", "public toilet", "toilet", "restroom",
        "toaleta", "toalety", "toaletă", "toalete", "туалет", "туалеты",
    },
}

SOURCE_CATEGORY_MARKERS: dict[Category, set[str]] = {
    Category.FOOD: {"verteilung von lebensmitteln"},
    Category.SLEEP: {"ubernachtungshaus"},
    Category.MEDICAL: {"medizinische versorgung"},
    Category.ADVICE: {"sozialberatung", "soziale wohnhilfen", "streetwork erwachsene"},
    Category.TOILET: set(),
}

STOPWORDS = {
    "ich", "du", "der", "die", "das", "ein", "eine", "und", "oder", "wo", "wie", "kann", "mir", "fur",
    "i", "you", "the", "a", "an", "and", "or", "where", "how", "can", "me", "for", "to", "get",
    "ja", "ty", "i", "lub", "gdzie", "jak", "dla", "eu", "tu", "si", "sau", "unde", "cum", "pentru",
    "я", "ты", "и", "или", "где", "как", "для", "мне",
}

DOMAIN_ANCHORS = {
    "leipzig", "lipsk", "hilfeangebot", "anlaufstelle", "streetwork", "sozial", "wohnungsnot", "sucht",
    "support service", "help service", "serviciu de ajutor", "услуга помощи",
}

TARGET_TERMS = {
    "women": {"frau", "frauen", "woman", "women", "kobieta", "kobiety", "femeie", "femei", "женщина", "женщины"},
    "men": {"mann", "manner", "man", "men", "mezczyzna", "mezczyzni", "barbat", "barbati", "мужчина", "мужчины"},
    "drug": {"droge", "drogen", "drogenkonsum", "drogengebrauch", "drug", "drugs", "narkotyki", "droguri", "наркотики"},
}


def _contains_term(text: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    if " " in normalized_term:
        return f" {normalized_term} " in f" {text} "
    return any(
        token == normalized_term or (len(normalized_term) >= 5 and token.startswith(normalized_term))
        for token in text.split()
    )


def _matching_terms(text: str, terms: set[str]) -> set[str]:
    return {normalize_text(term) for term in terms if _contains_term(text, term)}


def detect_categories(query: str) -> list[Category]:
    normalized = normalize_text(query)
    scored: list[tuple[int, Category]] = []
    for category, terms in CATEGORY_TERMS.items():
        matches = _matching_terms(normalized, terms)
        if matches:
            scored.append((len(matches), category))
    scored.sort(key=lambda item: (-item[0], list(Category).index(item[1])))
    return [category for _, category in scored]


def detect_target(query: str) -> str | None:
    normalized = normalize_text(query)
    for target, terms in TARGET_TERMS.items():
        if _matching_terms(normalized, terms):
            return target
    return None


def is_vague_query(query: str) -> bool:
    normalized = normalize_text(query)
    tokens = {token for token in normalized.split() if token not in STOPWORDS}
    vague_tokens = {
        "hilfe", "help", "support", "pomoc", "ajutor", "помощь", "bitte", "please", "prosze", "va rog",
        "пожалуйста", "brauche", "need", "potrzebuje", "am nevoie", "нужна", "нужен",
    }
    return bool(tokens) and len(tokens) <= 4 and tokens <= vague_tokens


def has_domain_signal(query: str) -> bool:
    normalized = normalize_text(query)
    return bool(detect_categories(query)) or bool(_matching_terms(normalized, DOMAIN_ANCHORS))


@dataclass(frozen=True)
class RankedOffer:
    offer: OfferRecord
    score: int
    strong_match: bool
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalOutcome:
    results: list[RankedOffer]
    selected_category: Category | None
    strong_match: bool
    in_scope: bool
    full_context_recommended: bool


def _offer_texts(offer: OfferRecord) -> tuple[str, str, str, str, str]:
    return (
        normalize_text(
            " ".join([offer.name, *offer.organization_aliases, *offer.offer_aliases, *offer.search_phrases])
        ),
        normalize_text(f"{offer.source_category} {offer.offer_type or ''} {' '.join(offer.needs)} {offer.short_description}"),
        normalize_text(" ".join(offer.services)),
        normalize_text(" ".join([*offer.opening_hours_raw, *offer.notes])),
        normalize_text(offer.raw_text),
    )


def _score_offer(offer: OfferRecord, query: str, category: Category | None) -> RankedOffer | None:
    name, classification, services, secondary, raw = _offer_texts(offer)
    score = 0
    strong = False
    matched: set[str] = set()

    if category:
        terms = CATEGORY_TERMS[category]
        marker_matches = _matching_terms(classification, SOURCE_CATEGORY_MARKERS[category])
        core_matches = _matching_terms(f"{name} {classification}", terms)
        service_matches = _matching_terms(services, terms)
        secondary_matches = _matching_terms(secondary, terms)
        raw_matches = _matching_terms(raw, terms)
        if marker_matches:
            score += 85 + 5 * len(marker_matches)
            strong = True
        if core_matches:
            score += 50 + 3 * len(core_matches)
            strong = True
        if service_matches:
            score += 35 + 2 * len(service_matches)
            strong = True
        if secondary_matches:
            score += 12 + len(secondary_matches)
        if raw_matches:
            score += min(8, len(raw_matches))
        matched.update(marker_matches | core_matches | service_matches | secondary_matches | raw_matches)

    normalized_query = normalize_text(query)
    query_tokens = {token for token in normalized_query.split() if len(token) >= 3 and token not in STOPWORDS}
    if normalized_query and len(normalized_query) >= 4:
        if _contains_term(name, normalized_query):
            score += 30
            strong = True
        elif _contains_term(raw, normalized_query):
            score += 10
    for token in query_tokens:
        if token in name.split():
            score += 12
            strong = True
            matched.add(token)
        if token in classification.split():
            score += 8
            matched.add(token)
        if token in services.split():
            score += 6
            strong = True
            matched.add(token)
        if token in secondary.split():
            score += 3
            matched.add(token)
        elif token in raw.split():
            score += 1
            matched.add(token)

    target = detect_target(query)
    if target:
        target_text = normalize_text(f"{offer.name} {offer.short_description} {' '.join(offer.services)}")
        target_matches = _matching_terms(target_text, TARGET_TERMS[target])
        if target_matches:
            score += 25
            strong = True
            matched.update(target_matches)

    if score <= 0:
        return None
    return RankedOffer(offer=offer, score=score, strong_match=strong, matched_terms=tuple(sorted(matched)))


def retrieve(
    offers: list[OfferRecord],
    query: str,
    category: Category | None = None,
    *,
    limit: int = 8,
) -> RetrievalOutcome:
    """Rankt Angebote anhand von Kategorie, Fachbegriffen und Zielgruppe.

    Args:
        offers: Vollständige aktive Angebotsliste.
        query: Normalisierte oder rohe Nutzerfrage.
        category: Optionale, explizit im UI ausgewählte Kategorie.
        limit: Maximale Zahl intern zurückgegebener Treffer.

    Returns:
        Ranking samt Scope-, Stärke- und Fallbackentscheidung.
    """
    detected = detect_categories(query)
    selected_category = category or (detected[0] if detected else None)
    ranked = [
        result
        for offer in offers
        if (result := _score_offer(offer, query, selected_category)) is not None
    ]
    ranked.sort(key=lambda item: (-item.score, item.offer.source_index))
    ranked = ranked[:limit]
    strong_match = any(item.strong_match for item in ranked)
    in_scope = bool(category or detected or ranked or has_domain_signal(query))
    full_context_recommended = bool(in_scope and query and not strong_match and not is_vague_query(query))
    return RetrievalOutcome(
        results=ranked,
        selected_category=selected_category,
        strong_match=strong_match,
        in_scope=in_scope,
        full_context_recommended=full_context_recommended,
    )


def _facet_strength(offer: OfferRecord, facet: str) -> int:
    terms = TARGET_TERMS[facet]
    if _matching_terms(normalize_text(offer.name), terms):
        return 2
    if _matching_terms(normalize_text(f"{offer.short_description} {' '.join(offer.services)}"), terms):
        return 1
    return 0


def _has_facet(offer: OfferRecord, facet: str) -> bool:
    return _facet_strength(offer, facet) > 0


def select_card_offers(outcome: RetrievalOutcome, query: str, *, limit: int = 4) -> list[OfferRecord]:
    """Wählt sichtbare Karten aus und wahrt die Schlafplatz-Zielgruppenregel."""
    ranked = outcome.results
    if outcome.selected_category != Category.SLEEP:
        return [item.offer for item in ranked[:limit]]

    target = detect_target(query)
    hilfebus = next((item.offer for item in ranked if "hilfebus" in normalize_text(item.offer.name)), None)
    if target:
        direct = [item.offer for item in ranked if _has_facet(item.offer, target) and item.offer is not hilfebus]
        direct.sort(key=lambda offer: -_facet_strength(offer, target))
        if hilfebus and len(direct) < limit:
            direct.append(hilfebus)
        return direct[:limit]

    selected: list[OfferRecord] = []
    for facet in ("men", "women", "drug"):
        facet_matches = [
            item.offer
            for item in ranked
            if item.offer not in selected and _has_facet(item.offer, facet) and item.offer is not hilfebus
        ]
        facet_matches.sort(key=lambda offer: -_facet_strength(offer, facet))
        match = facet_matches[0] if facet_matches else None
        if match:
            selected.append(match)
    if hilfebus and len(selected) < limit:
        selected.append(hilfebus)
    for item in ranked:
        if len(selected) >= limit:
            break
        if item.offer not in selected:
            selected.append(item.offer)
    return selected[:limit]
