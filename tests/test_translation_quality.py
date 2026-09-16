"""Verträge für Übersetzungsstatus, Runtime-Policy und Reviewartefakte."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.application_texts import APPLICATION_COPY_VERSION, LanguageTextInventory, application_text, application_text_summary, load_application_texts
from app.config import load_settings
from app.i18n import (
    TranslationCatalog,
    clone_store,
    load_translation_catalog,
    localize_offer_card,
    operational_facts_hash,
    source_translation_hash,
    translation_context,
    translation_store_write_path,
    validate_translation_fields,
    write_json,
)
from app.kb_loader import load_active_knowledge_base
from app.models import Language
from app.multilingual_review import build_review_template, load_scenario_catalog, main as review_main
from app.speech import EDGE_VOICES, LANGUAGE_HINTS, normalize_tts_text
from app.translate_offers import (
    TranslationError,
    _provider_payload,
    _parse_languages,
    _selected_offers,
    export_review,
    generate,
    import_review,
    migrate,
    status_or_validate,
)
from app.translation_contract import (
    FactualIntegrityStatus,
    LinguisticReviewStatus,
    ReviewRole,
    TranslationRecord,
    TranslationRuntimePolicy,
    TranslationFields,
)


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path):
    return replace(
        load_settings(),
        data_dir=tmp_path / "data",
        runtime_dir=tmp_path / "runtime",
        interaction_logging_enabled=False,
    )


def _runtime(tmp_path: Path):
    settings = _settings(tmp_path)
    kb = load_active_knowledge_base(settings)
    return settings, kb, load_translation_catalog(settings, kb)


def _valid_record(catalog: TranslationCatalog, language: Language = Language.EN):
    for entry in catalog.store.entries.values():
        record = entry.translations.get(language)
        if entry.active and record and record.factual_integrity_status == FactualIntegrityStatus.VALID:
            return entry.offer_id, record
    raise AssertionError("test inventory has no valid translation")


@pytest.mark.parametrize(
    "status",
    [
        LinguisticReviewStatus.MACHINE,
        LinguisticReviewStatus.REVIEW_PENDING,
        LinguisticReviewStatus.STALE,
    ],
)
def test_unreviewed_translation_statuses_reject_human_review_metadata(tmp_path: Path, status) -> None:
    _, _, catalog = _runtime(tmp_path)
    _, record = _valid_record(catalog)
    payload = record.model_dump(mode="python")
    payload.update(
        linguistic_review_status=status,
        reviewed_by_role=ReviewRole.AUTHOR,
        reviewed_at=datetime.now(UTC),
        review_scope="linguistic",
    )
    with pytest.raises(ValidationError):
        TranslationRecord.model_validate(payload)


@pytest.mark.parametrize("status", [LinguisticReviewStatus.REVIEWED, LinguisticReviewStatus.REJECTED])
def test_human_review_status_requires_complete_evidence(tmp_path: Path, status) -> None:
    _, _, catalog = _runtime(tmp_path)
    _, record = _valid_record(catalog)
    incomplete = record.model_dump(mode="python") | {"linguistic_review_status": status}
    with pytest.raises(ValidationError):
        TranslationRecord.model_validate(incomplete)
    complete = incomplete | {
        "reviewed_by_role": ReviewRole.NATIVE_SPEAKER,
        "reviewed_at": datetime.now(UTC),
        "review_scope": "language and direct address",
    }
    assert TranslationRecord.model_validate(complete).linguistic_review_status == status


def test_unknown_translation_status_is_rejected(tmp_path: Path) -> None:
    _, _, catalog = _runtime(tmp_path)
    _, record = _valid_record(catalog)
    with pytest.raises(ValidationError):
        TranslationRecord.model_validate(record.model_dump(mode="python") | {"linguistic_review_status": "approved"})


def test_translation_and_operational_hashes_have_separate_scope(tmp_path: Path) -> None:
    _, kb, _ = _runtime(tmp_path)
    offer = kb.by_id()["8"]
    changed_description = offer.model_copy(update={"short_description": offer.short_description + " geändert"})
    changed_services = offer.model_copy(update={"services": [*offer.services, "Neue Leistung"]})
    changed_address = offer.model_copy(update={"address": "Andere Straße 1, Leipzig"})
    assert source_translation_hash(changed_description) != source_translation_hash(offer)
    assert source_translation_hash(changed_services) != source_translation_hash(offer)
    assert source_translation_hash(changed_address) == source_translation_hash(offer)
    assert operational_facts_hash(changed_address) != operational_facts_hash(offer)
    original_context = translation_context(kb)
    changed_metadata = dict(kb.metadata)
    changed_metadata["curation"] = dict(changed_metadata["curation"]) | {"catalog_content_hash": "f" * 64}
    changed_context = translation_context(replace(kb, metadata=changed_metadata))
    assert original_context.curation_catalog_hash
    assert changed_context.curation_catalog_hash != original_context.curation_catalog_hash


def test_runtime_policies_never_use_invalid_or_unreviewed_content_as_reviewed(tmp_path: Path) -> None:
    _, kb, catalog = _runtime(tmp_path)
    offer_id, record = _valid_record(catalog)
    offer = kb.by_id()[offer_id]
    source = localize_offer_card(offer, Language.EN, catalog, TranslationRuntimePolicy.SOURCE_LANGUAGE_FALLBACK)
    reviewed_only = localize_offer_card(offer, Language.EN, catalog, TranslationRuntimePolicy.REVIEWED_ONLY)
    machine = localize_offer_card(offer, Language.EN, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE)
    assert source.short_description == reviewed_only.short_description == offer.short_description
    assert machine.name == offer.display_name or machine.name == offer.name

    store = clone_store(catalog.store)
    changed = store.entries[offer_id].translations[Language.EN]
    changed.linguistic_review_status = LinguisticReviewStatus.REVIEWED
    changed.reviewed_by_role = ReviewRole.AUTHOR
    changed.reviewed_at = datetime.now(UTC)
    changed.review_scope = "author language review"
    reviewed_catalog = TranslationCatalog(store=store, checked_at=catalog.checked_at)
    assert localize_offer_card(
        offer, Language.EN, reviewed_catalog, TranslationRuntimePolicy.REVIEWED_ONLY
    ).short_description == changed.fields.short_description

    changed.factual_integrity_status = FactualIntegrityStatus.INVALID
    assert localize_offer_card(
        offer, Language.EN, reviewed_catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
    ).short_description == offer.short_description
    changed.factual_integrity_status = FactualIntegrityStatus.VALID
    changed.linguistic_review_status = LinguisticReviewStatus.STALE
    changed.reviewed_by_role = None
    changed.reviewed_at = None
    changed.review_scope = None
    assert localize_offer_card(
        offer, Language.EN, reviewed_catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
    ).short_description == offer.short_description


def test_all_runtime_cards_preserve_names_and_operational_facts(tmp_path: Path) -> None:
    _, kb, catalog = _runtime(tmp_path)
    assert len(kb.offers) == 28
    assert {"1", "2", "3", "4"}.isdisjoint(kb.by_id())
    for offer in kb.offers:
        for language in Language:
            card = localize_offer_card(offer, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE)
            assert card.name == (offer.display_name or offer.name)
            assert card.address == offer.address
            assert card.phone_numbers == offer.phone_numbers
            assert card.standzeiten_raw == offer.standzeiten_raw
            # opening_hours_raw/notes sind seit Schema 3 übersetzbar; Länge
            # bleibt immer erhalten, Inhalt nur für Deutsch garantiert gleich.
            assert len(card.opening_hours_raw) == len(offer.opening_hours_raw)
            assert len(card.notes) == len(offer.notes)
            if language == Language.DE:
                assert card.opening_hours_raw == offer.opening_hours_raw
                assert card.notes == offer.notes
    scharni = localize_offer_card(
        kb.by_id()["8"], Language.EN, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
    )
    assert scharni.address == "Georg-Schumann-Str. 268, 04159 Leipzig"
    assert "Scharnhorststr. 27" not in json.dumps(scharni.model_dump(), ensure_ascii=False)
    helene = kb.by_id()["23"]
    helene_record = catalog.store.entries["23"].translations[Language.EN]
    helene_card = localize_offer_card(
        helene, Language.EN, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
    )
    assert helene_card.name == "Helene"
    assert helene_card.short_description == helene_record.fields.short_description
    assert helene_card.services == helene_record.fields.services
    assert "5,00 €" in json.dumps(helene_card.model_dump(), ensure_ascii=False)
    assert "2,50 €" in json.dumps(helene_card.model_dump(), ensure_ascii=False)

    oase = kb.by_id()["10"]
    for language in Language:
        oase_card = localize_offer_card(
            oase, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
        )
        assert oase_card.name == "Leipziger Oase"
        if language != Language.DE:
            record = catalog.store.entries["10"].translations[language]
            assert record.linguistic_review_status == LinguisticReviewStatus.MACHINE
            assert record.factual_integrity_status == FactualIntegrityStatus.VALID


def test_translation_integrity_is_positive_list_and_accepts_all_active_records(tmp_path: Path) -> None:
    _, kb, catalog = _runtime(tmp_path)
    invalid_records: list[tuple[str, str]] = []
    missing_records: list[str] = []
    for offer in kb.offers:
        entry = catalog.store.entries.get(offer.id)
        if entry is None:
            missing_records.append(offer.id)
            for language in (Language.EN, Language.PL, Language.RO, Language.RU):
                card = localize_offer_card(
                    offer, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
                )
                assert card.short_description == offer.short_description
                assert card.services == offer.services
            continue
        for language, record in entry.translations.items():
            assert set(record.fields.model_dump()) == {
                "short_description",
                "services",
                "opening_hours_raw",
                "notes",
            }
            if record.factual_integrity_status == FactualIntegrityStatus.VALID:
                assert validate_translation_fields(offer, record.fields, language) == ()
            else:
                invalid_records.append((offer.id, language.value))
    assert invalid_records == []
    assert missing_records == []
    summary = status_or_validate(_settings(tmp_path), validate_only=True)
    assert summary["valid"] is True
    assert summary["active_runtime_policy"] == "reviewed_or_machine"
    assert summary["integrity_error_count"] == len(catalog.integrity_errors) == 0


def test_regenerated_records_remain_machine_without_human_review_metadata(tmp_path: Path) -> None:
    """Jeder maschinell erzeugte Datensatz trägt keine menschliche

    Review-Freigabe und ist konsistent mit der ausgespielten Karte.
    """
    _, kb, catalog = _runtime(tmp_path)
    checked = 0
    for offer in kb.offers:
        entry = catalog.store.entries.get(offer.id)
        if entry is None:
            continue
        for language, record in entry.translations.items():
            if record.linguistic_review_status != LinguisticReviewStatus.MACHINE:
                continue
            checked += 1
            assert record.factual_integrity_status == FactualIntegrityStatus.VALID
            assert record.model_identifier != "not_recorded"
            assert record.reviewed_by_role is None
            assert record.reviewed_at is None
            assert record.review_scope is None
            card = localize_offer_card(offer, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE)
            assert card.short_description == record.fields.short_description
            assert card.services == record.fields.services
            assert card.opening_hours_raw == record.fields.opening_hours_raw
            assert card.notes == record.fields.notes
    assert checked > 0


def test_vkkj_cards_are_machine_translated_in_every_supported_target_language(tmp_path: Path) -> None:
    _, kb, catalog = _runtime(tmp_path)

    for offer_id in ("vkkj_notschlafstelle", "vkkj_jugendnotdienst"):
        offer = kb.by_id()[offer_id]
        entry = catalog.store.entries[offer_id]
        assert set(entry.translations) == {Language.EN, Language.PL, Language.RO, Language.RU}
        for language, record in entry.translations.items():
            assert record.linguistic_review_status == LinguisticReviewStatus.MACHINE
            assert record.factual_integrity_status == FactualIntegrityStatus.VALID
            assert record.reviewed_by_role is None
            assert record.reviewed_at is None
            card = localize_offer_card(
                offer, language, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE
            )
            assert card.short_description == record.fields.short_description
            assert card.services == record.fields.services
            assert card.opening_hours_raw == record.fields.opening_hours_raw
            assert card.notes == record.fields.notes


def test_translation_provider_payload_contains_only_public_positive_list(tmp_path: Path) -> None:
    settings, kb, _ = _runtime(tmp_path)
    payload = _provider_payload(settings, kb.by_id()["23"], Language.RO)
    assert set(payload) == {"model", "temperature", "max_tokens", "response_format", "messages"}
    assert [message["role"] for message in payload["messages"]] == ["system", "user"]
    user_payload = json.loads(payload["messages"][1]["content"])
    assert set(user_payload) == {
        "source_language",
        "target_language",
        "translatable_fields",
    }
    assert set(user_payload["translatable_fields"]) == {
        "short_description",
        "services",
        "opening_hours_raw",
        "notes",
    }
    assert "__LENA_P" in json.dumps(user_payload["translatable_fields"])
    offer = kb.by_id()["23"]
    serialized_fields = json.dumps(user_payload["translatable_fields"], ensure_ascii=False)
    assert "0,50" not in serialized_fields
    assert offer.address not in serialized_fields
    serialized = json.dumps(user_payload, ensure_ascii=False).casefold()
    for forbidden in (
        "raw_fields",
        "raw_properties",
        "curation_decision",
        "review_comment",
        "session",
        "interaction",
        "user_query",
    ):
        assert forbidden not in serialized


def test_translation_integrity_rejects_clear_target_script_mismatch(tmp_path: Path) -> None:
    _, kb, _ = _runtime(tmp_path)
    offer = kb.by_id()["5"]
    latin = TranslationFields(short_description="Only Latin text", services=offer.services)
    cyrillic = TranslationFields(short_description="Только русский текст", services=offer.services)
    assert "target_script_mismatch" in validate_translation_fields(offer, latin, Language.RU)
    assert "target_script_mismatch" in validate_translation_fields(offer, cyrillic, Language.EN)


def test_generate_dry_run_has_no_persistent_effect(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    before = list(tmp_path.rglob("*"))

    async def echo_masked_fields(_settings, payload):
        user_payload = json.loads(payload["messages"][1]["content"])
        return {
            "choices": [
                {"message": {"content": json.dumps(user_payload["translatable_fields"], ensure_ascii=False)}}
            ]
        }

    monkeypatch.setattr("app.translate_offers._post_blablador", echo_masked_fields)
    result = asyncio.run(
        generate(
            settings,
            provider="blablador",
            languages=[Language.EN],
            offer_ids="23",
            limit=1,
            force=True,
            dry_run=True,
        )
    )
    assert result["dry_run"] is True
    assert list(tmp_path.rglob("*")) == before
    assert not translation_store_write_path(settings).exists()


def test_targeted_generation_preserves_all_other_translation_records(tmp_path: Path, monkeypatch) -> None:
    settings, _, catalog = _runtime(tmp_path)
    before = catalog.store.model_dump(mode="json")["entries"]

    async def echo_masked_fields(_settings, payload):
        user_payload = json.loads(payload["messages"][1]["content"])
        return {
            "choices": [
                {"message": {"content": json.dumps(user_payload["translatable_fields"], ensure_ascii=False)}}
            ]
        }

    monkeypatch.setattr("app.translate_offers._post_blablador", echo_masked_fields)
    result = asyncio.run(
        generate(
            settings,
            provider="blablador",
            languages=[Language.EN],
            offer_ids="23",
            limit=1,
            force=True,
            dry_run=False,
        )
    )
    assert result == {
        "generated": 1,
        "failed": 0,
        "skipped_reviewed": 0,
        "dry_run": False,
        "failures": [],
    }
    after = json.loads(translation_store_write_path(settings).read_text(encoding="utf-8"))["entries"]
    for offer_id, entry in before.items():
        for language, record in entry["translations"].items():
            if (offer_id, language) != ("23", "en"):
                assert after[offer_id]["translations"][language] == record


def test_schema_two_migration_is_idempotent_and_packaged_copy_matches_checkout(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    assert migrate(settings, dry_run=True) == {
        "migrated": False,
        "dry_run": True,
        "schema_version": "3",
    }
    checkout = json.loads((ROOT / "data" / "i18n" / "offer_translations.json").read_text(encoding="utf-8"))
    packaged = json.loads(
        (ROOT / "app" / "resources" / "bootstrap" / "i18n" / "offer_translations.json").read_text(
            encoding="utf-8"
        )
    )
    assert checkout == packaged
    assert not any(
        record["linguistic_review_status"] == "reviewed"
        for entry in checkout["entries"].values()
        for record in entry["translations"].values()
    )


@pytest.mark.parametrize("schema", ["1", "2"])
@pytest.mark.parametrize("entries", [["unexpected"], {"5": {"translations": ["unexpected"]}}])
def test_malformed_legacy_translation_mappings_use_invalid_catalog_fallback(
    tmp_path: Path, schema: str, entries,
) -> None:
    settings, kb, _ = _runtime(tmp_path)
    path = tmp_path / "invalid-translations.json"
    path.write_text(json.dumps({"schema_version": schema, "entries": entries}), encoding="utf-8")

    catalog = load_translation_catalog(settings, kb, path=path)

    assert catalog.integrity_errors == ("translation_store_invalid",)
    assert catalog.store.entries == {}
    card = localize_offer_card(kb.offers[0], Language.EN, catalog, TranslationRuntimePolicy.REVIEWED_OR_MACHINE)
    assert card.short_description == kb.offers[0].short_description


def test_invalid_translation_encoding_uses_invalid_catalog_fallback(tmp_path: Path) -> None:
    settings, kb, _ = _runtime(tmp_path)
    path = tmp_path / "invalid-translations.json"
    path.write_bytes(b"\xff\xfe")

    catalog = load_translation_catalog(settings, kb, path=path)

    assert catalog.integrity_errors == ("translation_store_invalid",)
    assert catalog.store.entries == {}


def test_generate_changes_only_selected_language_and_offer(tmp_path: Path) -> None:
    settings, _, catalog = _runtime(tmp_path)
    original_polish = catalog.store.entries["5"].translations[Language.PL].model_dump(mode="json")
    result = asyncio.run(
        generate(
            settings,
            provider="copy",
            languages=[Language.EN],
            offer_ids="5",
            limit=1,
            force=True,
            dry_run=False,
        )
    )
    assert result["generated"] == 1
    stored = json.loads(translation_store_write_path(settings).read_text(encoding="utf-8"))
    assert stored["entries"]["5"]["translations"]["en"]["provider"] == "copy"
    assert stored["entries"]["5"]["translations"]["pl"] == original_polish


def test_cli_rejects_unknown_language_and_offer(tmp_path: Path) -> None:
    _, kb, _ = _runtime(tmp_path)
    with pytest.raises(TranslationError, match="translation_language_invalid"):
        _parse_languages("fr")
    with pytest.raises(TranslationError, match="translation_offer_unknown"):
        _selected_offers(kb, "unknown")


def test_atomic_json_write_preserves_previous_file_on_replace_error(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "translations.json"
    target.write_text('{"old": true}', encoding="utf-8")
    real_replace = Path.replace

    def failing_replace(path: Path, destination: Path):
        if path.name.startswith(".translations.json"):
            raise OSError("simulated atomic replace failure")
        return real_replace(path, destination)

    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        write_json(target, {"new": True})
    assert target.read_text(encoding="utf-8") == '{"old": true}'
    assert not (tmp_path / ".translations.json.tmp").exists()


def test_review_export_and_import_require_current_identity_and_human_metadata(tmp_path: Path) -> None:
    settings, _, catalog = _runtime(tmp_path)
    offer_id, _ = _valid_record(catalog)
    output = tmp_path / "review.json"
    export_review(settings, output=output, languages=[Language.EN])
    payload = json.loads(output.read_text(encoding="utf-8"))
    item = next(item for item in payload["items"] if item["offer_id"] == offer_id)
    item.update(
        review_decision="reviewed",
        reviewer_role="author_review",
        reviewed_at="2026-08-01T12:00:00Z",
        review_scope="language and factual token comparison",
    )
    payload["items"] = [item]
    output.write_text(json.dumps(payload), encoding="utf-8")
    assert import_review(settings, input_path=output)["imported"] == 1
    stored = json.loads(translation_store_write_path(settings).read_text(encoding="utf-8"))
    assert stored["entries"][offer_id]["translations"]["en"]["linguistic_review_status"] == "reviewed"

    item["translation_version"] = "obsolete"
    output.write_text(json.dumps(payload | {"items": [item]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="translation_review_target_stale"):
        import_review(settings, input_path=output)


def test_reviewed_translation_regenerates_only_after_its_source_goes_stale(tmp_path: Path) -> None:
    """Ein geprüfter Stand bleibt geschützt; nach einer Quelländerung ist er wieder erzeugbar."""
    settings, _, catalog = _runtime(tmp_path)
    offer_id, _ = _valid_record(catalog)
    output = tmp_path / "review.json"
    export_review(settings, output=output, languages=[Language.EN])
    payload = json.loads(output.read_text(encoding="utf-8"))
    item = next(item for item in payload["items"] if item["offer_id"] == offer_id)
    item.update(
        review_decision="reviewed",
        reviewer_role="author_review",
        reviewed_at="2026-08-01T12:00:00Z",
        review_scope="language and factual token comparison",
    )
    payload["items"] = [item]
    output.write_text(json.dumps(payload), encoding="utf-8")
    assert import_review(settings, input_path=output)["imported"] == 1

    # A still-valid reviewed translation stays protected, even with --force.
    still_valid = asyncio.run(
        generate(
            settings,
            provider="copy",
            languages=[Language.EN],
            offer_ids=offer_id,
            limit=None,
            force=True,
            dry_run=False,
        )
    )
    assert still_valid["generated"] == 0
    assert still_valid["skipped_reviewed"] == 1

    # Simulate the German source changing after the review: the stored record's
    # source_translation_hash no longer matches the offer, so the next catalog
    # load marks it stale while linguistic_review_status is still "reviewed".
    store_path = translation_store_write_path(settings)
    stored = json.loads(store_path.read_text(encoding="utf-8"))
    stored["entries"][offer_id]["translations"]["en"]["source_translation_hash"] = "0" * 64
    store_path.write_text(json.dumps(stored), encoding="utf-8")

    after_source_change = asyncio.run(
        generate(
            settings,
            provider="copy",
            languages=[Language.EN],
            offer_ids=offer_id,
            limit=None,
            force=False,
            dry_run=False,
        )
    )
    assert after_source_change["generated"] == 1
    assert after_source_change["skipped_reviewed"] == 0
    regenerated = json.loads(store_path.read_text(encoding="utf-8"))["entries"][offer_id]["translations"]["en"]
    assert regenerated["linguistic_review_status"] == "machine"
    assert regenerated["factual_integrity_status"] == "valid"


def test_application_resources_and_scenario_review_inventory_are_complete(tmp_path: Path) -> None:
    resources = load_application_texts()
    assert set(resources.languages) == set(Language)
    assert all(item.linguistic_review_status != LinguisticReviewStatus.REVIEWED for item in resources.languages.values())
    summary = application_text_summary()
    assert set(summary["areas"]) == {"ui", "dialogue", "fallback", "safety"}
    assert all(summary["areas"]["dialogue"][language.value]["missing"] == 0 for language in Language)

    scenarios = load_scenario_catalog()
    assert len(scenarios.scenarios) >= 16
    assert len(scenarios.review_raster) >= 11
    report = build_review_template(
        _settings(tmp_path), languages=list(Language), scenario_ids=None, repetitions=2
    )
    assert len(report["items"]) == len(scenarios.scenarios) * 5 * 2
    assert report["synthetic_data_only"] is True
    assert report["live_smoke_plan"]["maximum_provider_calls"] == len(report["items"]) * 3
    assert all(item["manual_review_status"] == "not_reviewed" for item in report["items"])


def test_result_copy_points_below_without_naming_cards_or_map() -> None:
    resources = load_application_texts()
    result_resource_ids = (
        "dialogue.answers.organization_service_conditional",
        "fallback.found",
        "fallback.toilet_more_markers",
        "fallback.water_more_markers",
    )
    forbidden_roots = {
        Language.DE: ("karte",),
        Language.EN: ("card", "map"),
        Language.PL: ("kart", "map"),
        Language.RO: ("card", "hart"),
        Language.RU: ("карт",),
    }
    below_markers = {
        Language.DE: "unten",
        Language.EN: "below",
        Language.PL: "poniżej",
        Language.RO: "mai jos",
        Language.RU: "ниже",
    }

    for language in Language:
        texts = resources.languages[language].texts
        for resource_id in result_resource_ids:
            visible_text = texts[resource_id].casefold()
            assert below_markers[language] in visible_text
            assert all(root not in visible_text for root in forbidden_roots[language])

    german_fallback = application_text(Language.DE, "fallback.found", names="Rücke, Scharni")
    assert german_fallback.endswith("Mehr Infos stehen unten.")
    assert "Karte" not in german_fallback


def test_unreviewed_application_resource_rejects_partial_review_metadata() -> None:
    with pytest.raises(ValidationError, match="unreviewed application copy must not carry review approval metadata"):
        LanguageTextInventory.model_validate(
            {
                "source_language": "de",
                "target_language": "en",
                "version": APPLICATION_COPY_VERSION,
                "linguistic_review_status": "machine",
                "source_origin": "machine_drafted",
                "reviewed_by_role": "author_review",
                "reviewed_at": None,
                "texts": {"ui.example": "Example"},
            }
        )


def test_live_smoke_requires_explicit_opt_in(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(sys, "argv", [
        "multilingual-review", "live-smoke", "--stage", "interpreter",
        "--expected-model", "alias-fast",
        "--expected-provider-domain", "provider.example",
        "--max-requests", "15", "--max-provider-calls", "15",
        "--max-interpreter-calls", "15", "--max-selector-calls", "0",
        "--max-formulator-calls", "0", "--max-total-runtime-seconds", "300",
        "--max-failures", "3",
    ])
    with pytest.raises(SystemExit, match="live_smoke_requires_explicit_confirmation"):
        review_main()
    assert not output.exists()


def test_stt_tts_contracts_cover_all_languages_and_emergency_number() -> None:
    assert set(LANGUAGE_HINTS) == set(EDGE_VOICES) == set(Language)
    for language in Language:
        rendered = normalize_tts_text("Rücke, Scharni, Jugendstreetwork, Hilfebus, 12:30, 112", language)
        assert "112" not in rendered
        assert "12:30" in rendered
