from __future__ import annotations

import hashlib
from pathlib import Path

from app.kb_loader import load_knowledge_base


ROOT = Path(__file__).resolve().parents[1]
KB_PATH = ROOT / "tests" / "fixtures" / "wissensbasis_hilfsangebote_leipzig.md"


def test_markdown_loads_as_exact_source_and_parses_all_offers() -> None:
    kb = load_knowledge_base(KB_PATH)

    assert len(kb.offers) == 30
    assert kb.source_hash == hashlib.sha256(KB_PATH.read_bytes()).hexdigest()
    assert all(offer.id and offer.name and offer.raw_text for offer in kb.offers)


def test_repeated_fields_accumulate_and_duplicate_names_remain_distinct() -> None:
    kb = load_knowledge_base(KB_PATH)

    assert len(kb.offers[0].phone_numbers) == 2
    assert len(kb.offers[29].emails) == 4
    duplicate_names = [offer for offer in kb.offers if offer.name == "Übernachtungshaus für wohnungslose Männer"]
    assert len(duplicate_names) == 2
    assert len({offer.id for offer in duplicate_names}) == 2
    assert len({offer.address for offer in duplicate_names}) == 2


def test_malformed_source_fragments_and_unknown_fields_are_preserved() -> None:
    kb = load_knowledge_base(KB_PATH)
    uvo = next(offer for offer in kb.offers if offer.source_index == 10)
    care_bags = next(offer for offer in kb.offers if offer.source_index == 26)

    assert "Notschl" in uvo.raw_text
    assert "UhrEinsatzgebiet" in care_bags.raw_text
    assert "Adresse laut Kopfzeile" in uvo.raw_fields
    assert uvo.header_address == "Taubestraße 2"


def test_stand_times_are_copied_from_explicit_markers() -> None:
    kb = load_knowledge_base(KB_PATH)
    hilfebus = next(offer for offer in kb.offers if "Hilfebus" in offer.name)

    assert hilfebus.standzeiten_raw
    assert any("Sonntag" in value for value in hilfebus.standzeiten_raw)
    assert all(value in hilfebus.raw_text for value in hilfebus.standzeiten_raw)
