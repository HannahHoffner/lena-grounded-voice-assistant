"""Real catalog, marker-tile and session speech checks after manual evaluation."""

from dataclasses import replace
import re

import pytest

from app import card_texts
from app.card_texts import localize_card_text
from app.config import load_settings
from app.hilfebus import present_card
from app.i18n import load_translation_catalog, localize_offer_card
from app.infrastructure import TOILET_FACILITY_TRANSLATIONS, localize_toilet_text
from app.infrastructure_results import drinking_fountain_card
from app.kb_loader import load_active_knowledge_base
from app.models import Language
from app.maps import offer_stand_destinations
from app.translation_contract import TranslationRuntimePolicy
from app.translation_tokens import PROTECTED_TOKEN_RE
from app.interpreter import Need
from test_dialogue import client_with, interpretation

TARGETS = [Language.EN, Language.PL, Language.RO, Language.RU]
GERMAN_OPERATIONAL = re.compile(r"\b(?:Montag|Dienstag|Dienstags|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag|Uhr|Standzeiten?|Einsatzzeiten|Herr|Frau|unterwegs|wöchentlich)\b")


@pytest.fixture(scope="module")
def inventory(tmp_path_factory):
    root = tmp_path_factory.mktemp("card-inventory")
    settings = replace(load_settings(), data_dir=root/"data", runtime_dir=root/"runtime")
    kb = load_active_knowledge_base(settings)
    return kb, load_translation_catalog(settings, kb)


@pytest.mark.parametrize("language", list(Language))
def test_every_runtime_phone_and_stand_is_localized_without_changing_values(inventory, language):
    kb, catalog = inventory
    assert catalog.integrity_errors == ()
    for offer in kb.offers:
        card = localize_offer_card(offer, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE)
        assert (card.name, card.address) == (offer.display_name or offer.name, offer.address)
        for field in ("phone_numbers", "standzeiten_raw"):
            source = getattr(offer, field)
            target = getattr(card, field)
            assert len(source) == len(target)
            for raw, text in zip(source, target, strict=True):
                assert PROTECTED_TOKEN_RE.findall(raw) == PROTECTED_TOKEN_RE.findall(text)
                if language == Language.DE:
                    assert raw == text
                else:
                    assert not GERMAN_OPERATIONAL.search(text), (offer.id, language, text)
                    if field == "standzeiten_raw":
                        assert text != raw
                        for name in ("Goethestraße", "Schwanenteich", "Denkmal der Dresdner Eisenbahn", "Lindenauer Markt", "Hauptbahnhof", "Koehlerstr.", "CABL e. V.", "Brücke am Kohlweg", "Torgauer Platz", "Rabet", "Südvorstadt", "Dölitz DÖsen", "Lößnig", "Dittrichring", "Lennéanlage", "Nikolaistraße"):
                            if name in raw:
                                assert name in text
                    if field == "phone_numbers" and " (" in raw:
                        annotation = raw.split(" (", 1)[1].rstrip(")")
                        if annotation.startswith(("Herr ", "Frau ")):
                            assert annotation.split(" ",1)[1] in text
                        elif annotation not in {"Allgemein", "nur zu Einsatzzeiten des Busses"}:
                            assert annotation in text
        if offer.id != "21":
            assert all(value.removeprefix("> ") in card.spoken_text for value in card.phone_numbers + card.standzeiten_raw)


@pytest.mark.parametrize("language", TARGETS)
def test_bus_contact_speech_uses_localized_operating_condition_not_staff(inventory, language):
    kb, catalog = inventory
    bus = kb.by_id()["21"]
    card = present_card(localize_offer_card(bus, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE), bus, language)
    assert "0175 6758041" in " ".join(card.phone_numbers)
    assert "0175 6758041" not in card.spoken_text
    assert "0152 33661087" in card.spoken_text
    assert "Einsatzzeiten" not in card.spoken_text
    assert "Demmering" not in card.spoken_text
    assert card.address is None and not card.standzeiten_raw


@pytest.mark.parametrize("language", TARGETS)
@pytest.mark.parametrize("need,day,stand_id", [
    (Need.FOOD,"sunday","21:hbf-west"),
    (Need.FOOD,"tuesday","14:schwanenteich"),
])
def test_actual_marker_tiles_and_registered_speech_are_localized(tmp_path, language, need, day, stand_id):
    client, _ = client_with(tmp_path, [interpretation(need, facts={"requested_day":day})])
    response = client.post("/api/query",json={"query":"Hilfe bitte","language":language.value})
    assert response.status_code == 200
    body = response.json()
    destination = next(d for d in body["map_data"]["destinations"] if d["id"] == stand_id)
    for field in ("description", "opening_hours", "standzeiten_raw", "phone_numbers"):
        values = destination[field] if isinstance(destination[field],list) else [destination[field]]
        assert all(not GERMAN_OPERATIONAL.search(v) for v in values), (field,values)
    assert all(v.removeprefix("> ") in destination["spoken_text"] for v in destination["opening_hours"] + destination["standzeiten_raw"] + destination["phone_numbers"])
    session = client.app.state.service.sessions.get(body["session_id"])
    assert destination["spoken_text"] in session.speakable_texts
    if stand_id == "21:hbf-west":
        assert destination["address"] == "Westseite des Hauptbahnhofes, 04109 Leipzig"
        assert "0175 6758041" not in destination["spoken_text"]
    assert body["provider"] == "template"  # fixture uses no live Formulator


@pytest.mark.parametrize("language", TARGETS)
def test_medibus_stand_specific_prose_has_complete_display_translations(inventory, language):
    kb,_=inventory
    stand=offer_stand_destinations(kb.by_id()["25"],language,service="medical_care")[0]
    assert stand.id == "25:hbf-medibus"
    for text in [stand.description,*stand.opening_hours]:
        localized=localize_card_text(text,language)
        assert not GERMAN_OPERATIONAL.search(localized)
        assert "Hauptbahnhof" in localized
        assert PROTECTED_TOKEN_RE.findall(text) == PROTECTED_TOKEN_RE.findall(localized)


@pytest.mark.parametrize("language", list(Language))
def test_all_infrastructure_card_values_are_translated_with_source_identity(inventory, language):
    kb, _ = inventory
    assert kb.public_toilets and kb.drinking_fountains
    for toilet in kb.public_toilets:
        for value in toilet.facilities:
            translated = localize_toilet_text(value, TOILET_FACILITY_TRANSLATIONS, language)
            assert translated != value or language == Language.DE and value != "All Gender"
    for fountain in kb.drinking_fountains:
        card = drinking_fountain_card(fountain, language)
        assert card.name == fountain.name and card.address == fountain.address
        if card.location_description:
            assert card.location_description in card.spoken_text
        if language != Language.DE and fountain.location_description:
            assert not re.search(r"\b(?:Trinkbrunnen|folgenden|Zeiten|Uhr|Höhe)\b", card.location_description)


@pytest.mark.parametrize("policy", [TranslationRuntimePolicy.SOURCE_LANGUAGE_FALLBACK, TranslationRuntimePolicy.REVIEWED_ONLY])
def test_unreviewed_extra_prose_respects_existing_source_fallback_policy(inventory, policy):
    kb,catalog=inventory
    bus=kb.by_id()["21"]
    card=localize_offer_card(bus,Language.EN,catalog,policy)
    assert card.phone_numbers == bus.phone_numbers
    assert card.standzeiten_raw == bus.standzeiten_raw
    assert bus.phone_numbers[1] in card.spoken_text


def test_unknown_strings_and_names_are_never_partially_translated():
    for value in ["Sonntagstraße 7", "Frau Holle", "Telefonzeiten noch ungeklärt", "0341 12345 (Becky)"]:
        assert localize_card_text(value,Language.EN) == value


def test_bad_display_resource_cannot_change_phone_digits(monkeypatch):
    real=card_texts.application_text
    monkeypatch.setattr(card_texts,"application_text",lambda lang,key,**kw: "999" if key=="card.phone.operating_only" else real(lang,key,**kw))
    with pytest.raises(RuntimeError,match="card_translation_literal_mismatch"):
        localize_card_text("0152 33661087 (nur zu Einsatzzeiten des Busses)",Language.EN)
