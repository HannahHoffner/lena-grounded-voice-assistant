from __future__ import annotations

from pathlib import Path

import pytest

from app.kb_loader import load_knowledge_base
from app.models import Category
from app.retrieval import retrieve, select_card_offers


KB = load_knowledge_base(Path(__file__).resolve().parents[1] / "data" / "canonical" / "offers.json")


@pytest.mark.parametrize(
    ("category", "expected_fragment"),
    [
        (Category.FOOD, "Lebensmittel"),
        (Category.SLEEP, "Übernachtung"),
        (Category.MEDICAL, "UVO"),
        (Category.ADVICE, "CABL"),
    ],
)
def test_category_retrieval_returns_relevant_offers(category: Category, expected_fragment: str) -> None:
    outcome = retrieve(KB.offers, "", category)

    assert outcome.results
    assert outcome.strong_match is True
    assert any(expected_fragment.casefold() in item.offer.raw_text.casefold() for item in outcome.results[:4])


@pytest.mark.parametrize(
    ("query", "category"),
    [
        ("Where can I get food?", Category.FOOD),
        ("Wo kann ich übernachten?", Category.SLEEP),
        ("Potrzebuję lekarza", Category.MEDICAL),
        ("Am nevoie de un loc de dormit", Category.SLEEP),
        ("Мне нужна консультация", Category.ADVICE),
    ],
)
def test_multilingual_intent_terms_map_to_source_categories(query: str, category: Category) -> None:
    outcome = retrieve(KB.offers, query)

    assert outcome.selected_category == category
    assert outcome.results


def test_broad_sleep_results_are_diverse() -> None:
    outcome = retrieve(KB.offers, "", Category.SLEEP)
    cards = select_card_offers(outcome, "")
    text = "\n".join(offer.raw_text for offer in cards)

    assert len(cards) == 4
    assert "wohnungslose Männer" in text
    assert "wohnungslose Frauen" in text
    assert "drogenkonsumierende" in text


def test_explicit_womens_sleep_query_ranks_named_womens_offer_first() -> None:
    query = "Ich brauche einen Schlafplatz für Frauen"
    cards = select_card_offers(retrieve(KB.offers, query), query)

    assert cards
    assert "Frauen" in cards[0].name


def test_ranking_is_stable() -> None:
    first = [item.offer.id for item in retrieve(KB.offers, "medical help").results]
    second = [item.offer.id for item in retrieve(KB.offers, "medical help").results]

    assert first == second
    assert KB.by_id()[first[0]].name.startswith("UVO")
