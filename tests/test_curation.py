"""Vertrags- und Integrationsprüfungen der freigegebenen Kurationsschicht."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.candidate_contract import CandidateRole
from app.candidates import build_selection_context
from app.config import Settings
from app.curation import load_curation_catalog
from app.formulation import AnswerType, EvidenceFact, EvidenceOffer, FactType, FormulatorEvidence, build_formulator_evidence
from app.i18n import load_translation_catalog, localize_offer_card, offer_translation_hash
from app.interpreter import Need, QueryInterpretation, RequestedService, interpreter_alias_hints
from app.kb_loader import KnowledgeBaseError, load_active_knowledge_base, load_knowledge_base
from app.main import create_app
from app.maps import build_map_data
from app.models import ChatTurn, Language
from app.translation_contract import TranslationRuntimePolicy
from app.retrieval import retrieve
from app.service import QueryService
from app.sessions import ConversationSession


ROOT = Path(__file__).resolve().parents[1]
CURATION_PATH = ROOT / "app" / "resources" / "bootstrap" / "curation" / "social_offers.json"
SOURCE_PATH = ROOT / "data" / "wfs" / "releases" / "legacy-3b72f95a88f9" / "offers.json"
EXCLUDED_IDS = {"1", "2", "3", "4"}


def _interpretation(
    need: Need = Need.UNKNOWN,
    *,
    services: list[RequestedService] | None = None,
    in_scope: bool = False,
) -> QueryInterpretation:
    return QueryInterpretation.model_validate(
        {
            "contract_version": "4",
            "need": need.value,
            "explicit_service_requests": [item.value for item in services or []],
            "scope_status": "in_scope" if in_scope or need != Need.UNKNOWN else "out_of_scope",
            "input_language": "de",
            "explicit_facts": {
                "age": None,
                "gender": "unknown",
                "drug_use": "unknown",
                "no_social_benefit_entitlement": "unknown",
                "district": None,
                "requested_day": None,
                "requested_time": None,
            },
            "uncertain_hints": [],
            "potentially_missing_information": [],
            "clarification_may_be_needed": False,
            "acute_risk_status": "not_detected",
        }
    )


def curated_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_root=ROOT,
        kb_path=ROOT / "data" / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50_000,
        interaction_logging_enabled=False,
        bootstrap_data_dir=ROOT / "data",
        data_dir=ROOT / "data",
        runtime_dir=tmp_path / "runtime",
        curation_path=CURATION_PATH,
    )


class _CurationInterpreter:
    async def interpret_query(self, **kwargs):
        query = kwargs["query"].casefold()
        if any(word in query for word in ("schlafen", "übernachten", "notschlafstelle")):
            return _interpretation(Need.SLEEP, services=[RequestedService.OVERNIGHT_STAY])
        if "essen" in query:
            return _interpretation(Need.FOOD, services=[RequestedService.FOOD])
        if "hygiene" in query:
            return _interpretation(Need.GENERAL_HELP, services=[RequestedService.HYGIENE])
        if "aufenthalt" in query:
            return _interpretation(Need.GENERAL_HELP, services=[RequestedService.DAY_STAY])
        if "kontakt" in query:
            return _interpretation(Need.GENERAL_HELP, services=[RequestedService.CONTACT])
        if "beratung" in query:
            return _interpretation(Need.ADVICE, services=[RequestedService.COUNSELLING])
        return _interpretation(Need.GENERAL_HELP, in_scope=True)

    def context_fits(self, _evidence):
        return False


def _curation_client(tmp_path: Path) -> TestClient:
    app = create_app(curated_settings(tmp_path))
    app.state.service.blablador = _CurationInterpreter()
    return TestClient(app)


@pytest.fixture
def curated_kb(tmp_path: Path):
    return load_active_knowledge_base(curated_settings(tmp_path))


def test_catalog_models_organization_location_and_distinct_service_offers() -> None:
    catalog = load_curation_catalog(CURATION_PATH)
    offers = {offer.id: offer for offer in catalog.service_offers}
    organizations = {organization.id: organization for organization in catalog.organizations}

    assert organizations["alternative_i"].display_name == "A1"
    assert offers["6"].organization_id == offers["11"].organization_id == "alternative_i"
    assert offers["6"].location_id == offers["11"].location_id == "alternative_i_chopinstrasse"
    assert offers["6"].offer_type == "overnight_accommodation"
    assert offers["11"].offer_type == "contact_cafe_day_center"
    assert offers["6"].id != offers["11"].id


def test_organization_aliases_cover_all_related_offers(curated_kb) -> None:
    bindings = {
        binding.alias: set(binding.offer_ids)
        for binding in curated_kb.organization_aliases
    }

    assert bindings["Schoppi"] == bindings["A1"] == {"6", "11"}
    assert bindings["Mobile"] == bindings["Kübel"] == {"19.1", "19.2", "19.3"}


def test_timmitohelp_route_is_curated_without_overwriting_wfs_or_inventing_markers(curated_kb) -> None:
    route = [
        "Donnerstag ca. 16:00 Uhr: Dittrichring",
        "Donnerstag ca. 16:30 Uhr: Lennéanlage",
        "Donnerstag ca. 17:30 Uhr: Nikolaistraße",
    ]
    offer = curated_kb.by_id()["16"]
    source = load_knowledge_base(SOURCE_PATH).by_id()["16"]
    catalog = load_curation_catalog(CURATION_PATH)
    reference = next(item for item in catalog.source_references if item.id == "timmitohelp_tourplan_pdf")

    assert offer.standzeiten_raw == route
    assert offer.address is None and offer.geometry is None
    assert "Halte Ausschau nach dem bunten Team mit zwei Bollerwagen." in offer.notes
    assert offer.service_schedules == {
        "food": "thursday_16_19",
        "drinking_water": "thursday_16_19",
        "hygiene": "thursday_16_19",
        "clothing": "thursday_16_19",
    }
    assert build_map_data([offer], language=Language.DE, service="food") is None
    assert source.address == "Dittrichring 15, 04109 Leipzig"
    assert source.geometry is not None
    assert any("16:00" in note and "19:00" in note for note in source.notes)
    assert reference.content_hash == "64155c223575dc152f420f0ebdca7822d5d4b015740e7b34ab7557bbafdbf4d2"

    evidence = build_formulator_evidence(
        query="Wo ist TiMMi ToHelp am Donnerstag?",
        language=Language.DE,
        answer_type=AnswerType.GROUNDED_RESULT,
        need=Need.FOOD,
        offers=[offer],
        roles={offer.id: CandidateRole.DIRECT_SERVICE},
    )
    facts = evidence.selected_offers[0].facts
    assert [fact.value for fact in facts if fact.fact_type == FactType.STAND_TIME] == route
    assert any(
        fact.fact_type == FactType.NOTE and "zwei Bollerwagen" in fact.value
        for fact in facts
    )


def test_timmitohelp_machine_localizations_are_current_without_human_approval(curated_kb) -> None:
    catalog = load_translation_catalog(curated_settings(Path(".")), curated_kb)
    offer = curated_kb.by_id()["16"]

    assert catalog.integrity_errors == ()
    for language in (Language.EN, Language.PL, Language.RO, Language.RU):
        record = catalog.store.entries["16"].translations[language]
        card = localize_offer_card(
            offer,
            language,
            catalog,
            TranslationRuntimePolicy.REVIEWED_OR_MACHINE,
        )
        assert record.linguistic_review_status.value == "machine"
        assert record.reviewed_by_role is None and record.reviewed_at is None
        assert card.address is None
        assert card.standzeiten_raw == offer.standzeiten_raw
        assert card.notes == record.fields.notes


@pytest.mark.parametrize("query", ["Schoppi schlafen", "A1 übernachten", "Schoppi Notschlafstelle"])
def test_alternative_i_sleep_need_without_drug_fact_stays_conditional(tmp_path: Path, query: str) -> None:
    response = _curation_client(tmp_path).post(
        "/api/query", json={"query": query, "language": "de"}
    )
    assert response.status_code == 200
    assert [card["id"] for card in response.json()["cards"]] == ["6"]
    assert "Zugangsbedingungen" in response.json()["answer"]
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize(
    "query",
    ["Schoppi essen", "A1 Aufenthalt", "Schoppi Hygiene", "A1 Kontakt", "Schoppi Beratung"],
)
def test_alternative_i_day_need_without_drug_fact_stays_conditional(tmp_path: Path, query: str) -> None:
    client = _curation_client(tmp_path)
    # Eingefroren auf Montag 10:00, da Karte "11" nur bei geöffnetem Angebot
    # erwartet wird; ohne feste Uhr hängt der Testerfolg von der realen
    # Tageszeit ab (WP9C).
    client.app.state.service.clock = lambda: datetime(2026, 8, 3, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    response = client.post(
        "/api/query", json={"query": query, "language": "de"}
    )
    assert response.status_code == 200
    assert [card["id"] for card in response.json()["cards"]] == ["11"]
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("query", ["A1", "Schoppi", "Mobile", "Kübel", "Kübel Beratung"])
def test_ambiguous_organization_alias_never_selects_arbitrarily(tmp_path: Path, query: str) -> None:
    response = _curation_client(tmp_path).post(
        "/api/query", json={"query": query, "language": "de"}
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "no_results"
    assert payload["cards"] == []
    assert payload["clarification"]["type"] in {"organization_need", "organization_district"}


def test_mobile_location_phrase_can_identify_one_team(curated_kb) -> None:
    value = _interpretation(Need.ADVICE)
    value.explicit_facts.district = "Grünau"
    context = build_selection_context(
        query="Kübel in Grünau",
        interpretation=value,
        offers=curated_kb.offers,
        organization_aliases=curated_kb.organization_aliases,
        ui_category=None,
    )
    assert context.alias and context.alias.district_narrowed
    assert context.alias.offer_ids == ["19.2"]


def test_scharni_runtime_override_preserves_immutable_wfs_address(curated_kb) -> None:
    source = load_knowledge_base(SOURCE_PATH).by_id()["8"]
    runtime = curated_kb.by_id()["8"]

    assert source.address == "Scharnhorststr. 27, 04275 Leipzig"
    assert source.phone_numbers == ["0341 5852413"]
    assert source.raw_properties["adr"] == "Scharnhorststr. 27, 04275 Leipzig"
    assert runtime.address == "Georg-Schumann-Str. 268, 04159 Leipzig"
    assert runtime.name == "Scharni"
    assert runtime.phone_numbers == ["0341 420920-0"]
    assert runtime.emails == ["uebernachtungshaus@aww.info"]
    assert runtime.raw_properties == source.raw_properties
    assert "Scharnhorststr. 27" in runtime.raw_text
    assert runtime.geometry is None
    assert runtime.source_hash == source.source_hash
    assert offer_translation_hash(runtime) != offer_translation_hash(source)
    catalog = load_translation_catalog(curated_settings(Path.cwd()), curated_kb)
    localized = localize_offer_card(
        runtime,
        Language.EN,
        catalog,
        TranslationRuntimePolicy.REVIEWED_OR_MACHINE,
    )
    assert localized.services == ["Sleeping place", "Basic provision of food, clothing and hygiene", "Social support"]
    assert localized.name == "Scharni"


def test_hilfebus_runtime_notes_include_operating_hours_call_reminder(curated_kb) -> None:
    """Der Hilfebus ist nur zu seinen Einsatzzeiten telefonisch erreichbar; das muss als
    eigener, zitierbarer Hinweis in Karte und LLM-Evidence ankommen (nicht als
    access_rules-Code, der nur die deterministische Kandidatenauswahl steuert)."""
    source = load_knowledge_base(SOURCE_PATH).by_id()["21"]
    runtime = curated_kb.by_id()["21"]

    assert source.notes == ["Instagramkanal: #safeleipzig"]
    assert runtime.notes == [
        "Instagramkanal: #safeleipzig",
        "Rufe während der Einsatzzeiten (täglich 18:00–23:00 Uhr) direkt beim Hilfebus an.",
    ]
    assert runtime.access_rules == []

    evidence = build_formulator_evidence(
        query="Ich brauche Beratung",
        language=Language.DE,
        answer_type=AnswerType.GROUNDED_RESULT,
        need=Need.ADVICE,
        offers=[runtime],
        roles={"21": CandidateRole.DIRECT_SERVICE},
    )
    note_values = [
        fact.value
        for offer in evidence.selected_offers
        for fact in offer.facts
        if fact.fact_type == FactType.NOTE
    ]
    assert "Rufe während der Einsatzzeiten (täglich 18:00–23:00 Uhr) direkt beim Hilfebus an." in note_values


def test_card_translation_cannot_override_curated_identity_facts(curated_kb) -> None:
    """Name, Adresse, Kontakte und Standzeiten bleiben immer aus der

    Runtime-KB. opening_hours_raw/notes sind seit Schema 3 übersetzbar
    (Länge bleibt erhalten, exakte Uhrzeiten bleiben als geschützte Tokens
    unverändert), dürfen sich im Wortlaut aber vom deutschen Original
    unterscheiden.
    """
    runtime = curated_kb.by_id()["8"]
    catalog = load_translation_catalog(curated_settings(Path.cwd()), curated_kb)
    translated = localize_offer_card(
        runtime,
        Language.RO,
        catalog,
        TranslationRuntimePolicy.REVIEWED_OR_MACHINE,
    )

    assert translated.address == runtime.address
    assert translated.phone_numbers == runtime.phone_numbers
    assert translated.standzeiten_raw == runtime.standzeiten_raw
    assert len(translated.opening_hours_raw) == len(runtime.opening_hours_raw)
    assert translated.opening_hours_raw != runtime.opening_hours_raw
    time_re = re.compile(r"\b\d{1,2}:\d{2}\b")
    for line in runtime.opening_hours_raw:
        for token in time_re.findall(line):
            assert any(token in translated_line for translated_line in translated.opening_hours_raw)


def test_review_policy_and_provenance_are_explicit_without_invented_dates() -> None:
    catalog = load_curation_catalog(CURATION_PATH)
    policy = catalog.review_policy
    decisions = {decision.id: decision for decision in catalog.curation_decisions}
    sources = {source.id: source for source in catalog.source_references}

    assert policy.review_interval is None
    assert policy.review_policy_status == "not_yet_formally_defined"
    assert policy.review_required_before_final_evaluation is True
    assert policy.review_on_source_change is True
    assert policy.formal_approval_status == "not_granted"
    assert decisions["alternative_i_alias_model"].reviewed_at is None
    assert decisions["alternative_i_alias_model"].reviewed_by_role == "SAFE-Team des Suchtzentrums Leipzig"
    assert decisions["alternative_i_alias_model"].evidence_type == "formative Stakeholder-Konsultation"
    assert decisions["alternative_i_alias_model"].evidence_reference == "4Approachneu.tex"
    assert sources["scharni_website"].url is not None
    assert str(sources["scharni_website"].url) == "https://obdachlosenhaus.de/"
    assert sources["scharni_website"].retrieved_at is not None


def test_excluded_ids_are_absent_from_every_runtime_projection(curated_kb) -> None:
    normalized_source_ids = set(load_knowledge_base(SOURCE_PATH).by_id())
    runtime_ids = {offer.id for offer in curated_kb.offers}
    interpreter_aliases = interpreter_alias_hints(
        curated_kb.offers,
        curated_kb.organization_aliases,
    )
    formulator_ids = {
        build_formulator_evidence(
            query="Hilfe",
            language=Language.DE,
            answer_type=AnswerType.GROUNDED_RESULT,
            need=Need.GENERAL_HELP,
            offers=[offer],
            roles={offer.id: CandidateRole.DIRECT_SERVICE},
        ).selected_offers[0].offer_id
        for offer in curated_kb.offers
    }
    retrieval_ids = {item.offer.id for item in retrieve(curated_kb.offers, "Hilfe", limit=100).results}
    card_ids = {
        localize_offer_card(offer, Language.DE, {}, {}).id
        for offer in curated_kb.offers
    }
    map_data = build_map_data(curated_kb.offers, language=Language.DE, limit=100)
    map_ids = {
        destination.id.split(":", 1)[0]
        for destination in (map_data.destinations if map_data else [])
    }

    for consumer_ids in (runtime_ids, formulator_ids, retrieval_ids, card_ids, map_ids):
        assert consumer_ids.isdisjoint(EXCLUDED_IDS)
    assert {"vkkj_notschlafstelle", "vkkj_jugendnotdienst"} <= map_ids
    assert all(set(item.model_dump()) == {"alias", "alias_kind", "may_refer_to_multiple_services"} for item in interpreter_aliases)
    assert not any(hasattr(item, "offer_ids") for item in interpreter_aliases)
    assert EXCLUDED_IDS <= normalized_source_ids
    assert len(runtime_ids) == 28


def test_health_exposes_pending_review_policy_and_runtime_exclusions(tmp_path: Path) -> None:
    health = TestClient(create_app(curated_settings(tmp_path))).get("/api/health").json()
    assert health["offer_count"] == 28
    assert health["source_kind"] == "curated_wfs"
    assert health["curation"]["excluded_source_ids"] == ["1", "2", "3", "4"]
    assert len(health["curation"]["catalog_content_hash"]) == 64
    assert health["curation"]["review_policy"]["review_interval"] is None
    assert health["curation"]["review_policy"]["review_policy_status"] == "not_yet_formally_defined"
    assert health["curation"]["review_monitoring"]["review_due"] is None
    assert health["curation"]["review_monitoring"]["decisions_with_unknown_review_date"]
    assert health["curation"]["review_monitoring"]["review_required_before_final_evaluation"] is True
    assert health["curation"]["review_monitoring"]["source_review_status"] == "current"
    assert health["curation"]["approval_status"] == {
        "technical_validation_status": "validated",
        "prototype_review_status": "reviewed_for_prototype",
        "formal_approval_status": "not_granted",
        "production_approval_status": "not_granted",
    }
    assert health["curation"]["coordinates_status"] == {
        "8": "not_verified_after_address_change",
        "vkkj_notschlafstelle": "verified_from_official_source",
        "vkkj_jugendnotdienst": "verified_from_official_source",
    }
    assert health["official_offer_source"]["source_version"] == "vkkj-2026-08-25"
    translations = health["translations"]
    assert translations["active_runtime_policy"] == "reviewed_or_machine"
    assert set(translations["languages"]) == {"en", "pl", "ro", "ru"}
    assert all(values["reviewed"] == 0 for values in translations["languages"].values())


@pytest.mark.parametrize("configured_path", [None, CURATION_PATH])
def test_runtime_curation_cannot_be_disabled(
    tmp_path: Path,
    configured_path: Path | None,
) -> None:
    kb = load_active_knowledge_base(
        replace(curated_settings(tmp_path), curation_path=configured_path)
    )

    assert len(kb.offers) == 28
    assert {offer.id for offer in kb.offers}.isdisjoint(EXCLUDED_IDS)
    assert kb.source_kind == "curated_wfs"
    assert kb.runtime_kb_fingerprint


def test_query_service_rejects_a_runtime_not_marked_as_validated(
    tmp_path: Path,
    curated_kb,
) -> None:
    unvalidated = replace(curated_kb, runtime_validated=False)

    with pytest.raises(ValueError, match="validated curated runtime"):
        QueryService(curated_settings(tmp_path), unvalidated)


@pytest.mark.parametrize(
    ("relative_path", "content", "error_code"),
    [
        ("missing.json", None, "curation_catalog_missing"),
        ("invalid.json", "{}", "curation_catalog_invalid"),
        ("", None, "curation_catalog_missing"),
    ],
)
def test_invalid_explicit_curation_never_falls_back_to_unfiltered_source(
    tmp_path: Path,
    relative_path: str,
    content: str | None,
    error_code: str,
) -> None:
    path = tmp_path / relative_path
    if content is not None:
        path.write_text(content, encoding="utf-8")
    settings = replace(curated_settings(tmp_path), curation_path=path)

    with pytest.raises(KnowledgeBaseError) as raised:
        load_active_knowledge_base(settings)
    health = TestClient(create_app(settings)).get("/api/health").json()

    assert raised.value.code == error_code
    assert health["kb_loaded"] is False
    assert health["offer_count"] == 0
    assert health["runtime_kb_status"] == "error"
    assert health["error_code"] == error_code
    assert str(tmp_path) not in json.dumps(health)


def test_all_formulator_offer_payloads_use_exact_positive_field_sets(curated_kb) -> None:
    formulator = [
        build_formulator_evidence(
            query="Hilfe",
            language=Language.DE,
            answer_type=AnswerType.GROUNDED_RESULT,
            need=Need.GENERAL_HELP,
            offers=[offer],
            roles={offer.id: CandidateRole.DIRECT_SERVICE},
        ).model_dump(mode="json")
        for offer in curated_kb.offers
    ]

    evidence_fields = set(FormulatorEvidence.model_fields)
    offer_fields = set(EvidenceOffer.model_fields)
    fact_fields = set(EvidenceFact.model_fields)
    assert len(formulator) == 28
    assert all(set(item) == evidence_fields for item in formulator)
    assert all(set(item["selected_offers"][0]) == offer_fields for item in formulator)
    assert all(
        set(fact) == fact_fields
        for item in formulator
        for fact in item["selected_offers"][0]["facts"]
    )

    serialized = json.dumps(
        {"formulator": formulator},
        ensure_ascii=False,
    )
    for forbidden in (
        "Scharnhorststr. 27, 04275 Leipzig",
        "0341 5852413",
        '"ap1"',
        '"ap2"',
        "raw_fields",
        "raw_properties",
    ):
        assert forbidden not in serialized
    assert {
        item["selected_offers"][0]["offer_id"] for item in formulator
    }.isdisjoint(EXCLUDED_IDS)


def test_changed_runtime_fingerprint_blocks_stale_history_before_router(
    tmp_path: Path,
) -> None:
    app = create_app(curated_settings(tmp_path))
    captured: dict[str, object] = {}
    old = ConversationSession(
        session_id="old-runtime-session",
        language=Language.DE,
        created_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
        runtime_kb_fingerprint="old-runtime-fingerprint",
        turns=[
            ChatTurn(
                question="Scharni",
                answer="Scharnhorststr. 27 und Sozialamt-ID 1",
            )
        ],
    )
    app.state.service.sessions.save(old)

    class FakeProvider:
        async def interpret_query(self, **kwargs) -> QueryInterpretation:
            captured["history"] = kwargs["conversation_history"]
            return _interpretation()

    app.state.service.blablador = FakeProvider()
    response = TestClient(app).post(
        "/api/query",
        json={
            "query": "Eine ausreichend lange fachfremde Anfrage",
            "language": "de",
            "session_id": old.session_id,
        },
    ).json()

    assert captured["history"] == []
    assert response["session_id"] != old.session_id
    assert all("Scharnhorststr. 27" not in turn["answer"] for turn in response["history"])
