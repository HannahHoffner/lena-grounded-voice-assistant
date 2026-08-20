from __future__ import annotations

import asyncio
import argparse
import json
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.candidates import CandidateSelector
from app.config import Settings
from app.drinking_fountain_releases import (
    DrinkingFountainReleaseError,
    DrinkingFountainReleasePaths,
    import_drinking_fountain_snapshot_as_pending,
    load_drinking_fountain_runtime,
    load_packaged_drinking_fountain_release,
    verify_drinking_fountain_release_path,
)
from app.drinking_fountain_source import (
    DrinkingFountainSourceError,
    diff_drinking_fountain_records,
    normalize_drinking_fountain_kml,
)
from app.drinking_fountain_sync import diff_live_source, fetch_drinking_fountains, run_command
from app.formulation import (
    FORMULATOR_CONTRACT_VERSION,
    ClaimType,
    FactType,
    FormulatedSentence,
    FormulatorError,
    FormulatorResponse,
    build_drinking_water_evidence,
)
from app.grounding import validate_formulation
from app.infrastructure import (
    CoordinatesStatus,
    FeeStatus,
    FountainExclusionReason,
    InstallationType,
    OperationStatus,
    PotableWaterStatus,
    SeasonalStatus,
    DrinkingFountainRecordCollection,
)
from app.infrastructure_results import select_drinking_water_results
from app.interpreter import (
    AcuteRiskStatus,
    ExplicitFacts,
    InputLanguage,
    Need,
    QueryInterpretation,
    ScopeStatus,
)
from app.kb_loader import load_active_knowledge_base
from app.main import create_app
from app.models import Language, QueryRequest
from app.providers.llm import InterpreterError
from app.resources import packaged_bootstrap_data_root
from app.service import QueryService


FETCHED_AT = datetime(2026, 8, 2, 12, 23, 18, tzinfo=timezone.utc)


def _bootstrap_root() -> Path:
    return packaged_bootstrap_data_root() / "drinking_fountains"


def _release_path() -> Path:
    pointer = json.loads((_bootstrap_root() / "active_release.json").read_text(encoding="utf-8"))
    return _bootstrap_root() / "releases" / pointer["release_id"]


def _source_files() -> tuple[bytes, bytes, bytes]:
    release = _release_path()
    return (
        (release / "snapshot.kml").read_bytes(),
        (release / "municipality_boundary.geojson").read_bytes(),
        (release / "source_evidence.json").read_bytes(),
    )


def _collection(kml: bytes | None = None):
    source, boundary, evidence = _source_files()
    return normalize_drinking_fountain_kml(
        source if kml is None else kml,
        boundary,
        evidence,
        retrieved_at=FETCHED_AT,
        content_type="text/xml; charset=utf-8",
        source_last_modified=None,
        boundary_last_modified="Thu, 13 Jul 2023 11:40:26 GMT",
    )


def _settings(tmp_path: Path, **changes: object) -> Settings:
    settings = Settings(
        app_root=tmp_path,
        kb_path=packaged_bootstrap_data_root() / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=30,
        blablador_max_context_chars=50_000,
        data_dir=tmp_path / "data",
        runtime_dir=tmp_path / "runtime",
        bootstrap_data_dir=packaged_bootstrap_data_root(),
        interaction_logging_enabled=False,
        wfs_auto_sync=False,
        toilet_auto_sync=False,
        drinking_fountain_auto_sync=False,
    )
    return replace(settings, **changes)


def _interpretation(need: Need = Need.DRINKING_WATER, *, district: str | None = None):
    return QueryInterpretation(
        contract_version="4",
        need=need,
        explicit_service_requests=[],
        scope_status=ScopeStatus.IN_SCOPE,
        input_language=InputLanguage.DE,
        explicit_facts=ExplicitFacts(
            age=None,
            age_group="unknown",
            gender="unknown",
            drug_use="unknown",
            no_social_benefit_entitlement="unknown",
            district=district,
            requested_day=None,
            requested_time=None,
        ),
        uncertain_hints=[],
        potentially_missing_information=[],
        clarification_may_be_needed=False,
        acute_risk_status=AcuteRiskStatus.NOT_DETECTED,
    )


class _WaterInterpreter:
    async def interpret_query(self, **kwargs):
        district = "Connewitz" if "connewitz" in kwargs["query"].casefold() else None
        return _interpretation(district=district)

    def context_fits(self, _evidence):
        return False


def _decision(settings: Settings):
    kb = load_active_knowledge_base(settings)
    return kb, CandidateSelector().select(_interpretation(), kb.offers, now=FETCHED_AT)


def test_official_bootstrap_is_reproducible_and_scope_is_explicit() -> None:
    release = load_packaged_drinking_fountain_release()
    collection = _collection()
    assert release.collection == collection
    assert release.manifest.source_sha256 == "f7cef59936f4a8d5dbf801e4022670c396ffc8567a5163b4caaf39aa1d36adac"
    assert release.manifest.boundary_sha256 == "8914ae40b8e806d4d6210c9cab97f5d9f51a685a93670b23ff46a3ddf57452b1"
    assert len(collection.records) == 35
    assert sum(record.installation_type == InstallationType.FIXED for record in collection.records) == 30
    assert sum(record.installation_type == InstallationType.MOBILE for record in collection.records) == 5
    assert sum(record.runtime_eligible for record in collection.records) == 21
    assert sum(record.exclusion_reason == FountainExclusionReason.OUTSIDE_LEIPZIG for record in collection.records) == 9
    assert collection.source.publisher == "Leipziger Wasserwerke"
    assert collection.source.license_status == "not_explicitly_specified"
    assert collection.source.usage_scope == "reviewed_prototype_source"
    assert collection.page_evidence.completeness_claimed is False


def test_runtime_records_use_namespaced_stable_ids_and_no_inferred_addresses() -> None:
    records = _collection().records
    assert len({record.id for record in records}) == len(records)
    assert all(record.id == f"drinking_fountain:{record.source_id}" for record in records)
    assert not {"1", "2", "3", "4"}.intersection(record.id for record in records)
    eligible = [record for record in records if record.runtime_eligible]
    assert all(record.address is None for record in eligible)
    assert all(record.municipality == "Leipzig" for record in eligible)
    assert all(record.cost_status == FeeStatus.FREE and record.cost_amount == 0 for record in eligible)
    assert all(record.potable_water_status == PotableWaterStatus.VERIFIED for record in eligible)
    assert all(record.operation_status == OperationStatus.UNKNOWN for record in eligible)
    assert all(record.seasonal_status == SeasonalStatus.APRIL_TO_OCTOBER for record in eligible)


def test_normalized_collection_rejects_cross_source_identity_mix() -> None:
    payload = _collection().model_dump(mode="json")
    payload["source"]["kml_url"] = "https://example.invalid/other.kml"
    with pytest.raises(ValueError, match="record source URLs differ"):
        DrinkingFountainRecordCollection.model_validate(payload)


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "drinking_fountain_source_not_kml"),
        (b"<html>error</html>", "drinking_fountain_source_not_kml"),
        (b"<kml xmlns='http://www.opengis.net/kml/2.2'><Document><name>Other</name></Document></kml>", "drinking_fountain_source_identity_mismatch"),
    ],
)
def test_invalid_or_wrong_source_is_rejected(content: bytes, code: str) -> None:
    with pytest.raises(DrinkingFountainSourceError, match=code):
        _collection(content)


def test_invalid_and_duplicate_geometry_are_retained_but_excluded() -> None:
    source, _, _ = _source_files()
    coordinate_values = re.findall(rb"<coordinates>([^<]+)</coordinates>", source)
    invalid = source.replace(coordinate_values[0], b"not-a-coordinate", 1)
    invalid_record = next(record for record in _collection(invalid).records if record.geometry_status == CoordinatesStatus.INVALID)
    assert invalid_record.runtime_eligible is False
    assert invalid_record.exclusion_reason == FountainExclusionReason.INVALID_GEOMETRY

    duplicate = source.replace(coordinate_values[1], coordinate_values[0], 1)
    duplicates = [record for record in _collection(duplicate).records if record.geometry_status == CoordinatesStatus.DUPLICATE]
    assert len(duplicates) == 2
    assert all(record.exclusion_reason == FountainExclusionReason.DUPLICATE_LOCATION for record in duplicates)


def test_coordinate_change_is_a_material_record_diff_but_retrieval_time_is_not() -> None:
    previous = _collection()
    changed_record = previous.records[0].model_copy(update={"latitude": previous.records[0].latitude + 0.001})
    changed = previous.model_copy(update={"records": [changed_record, *previous.records[1:]]})
    assert diff_drinking_fountain_records(previous, changed)["modified"] == [changed_record.id]
    later = previous.model_copy(update={
        "records": [record.model_copy(update={"retrieved_at": datetime(2026, 8, 3, tzinfo=timezone.utc)}) for record in previous.records]
    })
    assert diff_drinking_fountain_records(previous, later) == {"added": [], "removed": [], "modified": []}


def test_manifest_and_every_release_file_are_hash_verified(tmp_path: Path) -> None:
    copied = tmp_path / _release_path().name
    shutil.copytree(_release_path(), copied)
    verified = verify_drinking_fountain_release_path(copied, expected_id=copied.name)
    assert verified.collection.records
    snapshot = copied / "snapshot.kml"
    snapshot.write_bytes(snapshot.read_bytes() + b"\n")
    with pytest.raises(DrinkingFountainReleaseError, match="drinking_fountain_release_invalid"):
        verify_drinking_fountain_release_path(copied, expected_id=copied.name)


def _copy_local_release(settings: Settings) -> tuple[Path, bytes]:
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    target = paths.releases / _release_path().name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_release_path(), target)
    pointer = (_bootstrap_root() / "active_release.json").read_bytes()
    return target, pointer


def test_release_fallback_order_and_pending_is_never_runtime(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    release, pointer = _copy_local_release(settings)
    paths.pointer.parent.mkdir(parents=True, exist_ok=True)
    paths.pointer.write_bytes(pointer)
    assert load_drinking_fountain_runtime(settings).runtime_source == "active_release"

    paths.pointer.unlink()
    paths.verified_pointer.write_bytes(pointer)
    runtime = load_drinking_fountain_runtime(settings)
    assert runtime.runtime_source == "last_verified_release" and runtime.runtime_status == "degraded"

    paths.verified_pointer.unlink()
    paths.previous_pointer.write_bytes(pointer)
    assert load_drinking_fountain_runtime(settings).runtime_source == "previous_verified_release"

    paths.previous_pointer.unlink()
    pending = paths.pending / release.name
    pending.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(release, pending)
    assert load_drinking_fountain_runtime(settings).runtime_source == "packaged_bootstrap"


def test_corrupt_pointer_or_release_falls_back_only_to_verified_bootstrap(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    release, pointer = _copy_local_release(settings)
    paths.pointer.parent.mkdir(parents=True, exist_ok=True)
    paths.pointer.write_text("{broken", encoding="utf-8")
    runtime = load_drinking_fountain_runtime(settings)
    assert runtime.runtime_source == "packaged_bootstrap"
    assert runtime.runtime_status == "degraded"

    paths.pointer.write_bytes(pointer)
    (release / "snapshot.kml").write_bytes(b"broken")
    runtime = load_drinking_fountain_runtime(settings)
    assert runtime.runtime_source == "packaged_bootstrap"
    assert runtime.runtime_status == "degraded"


def test_missing_all_safe_releases_is_a_controlled_error(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    paths.pointer.parent.mkdir(parents=True, exist_ok=True)
    paths.pointer.write_text("{broken", encoding="utf-8")
    empty_bootstrap = tmp_path / "empty-bootstrap"
    empty_bootstrap.mkdir()
    monkeypatch.setattr(
        "app.drinking_fountain_releases.packaged_bootstrap_data_root",
        lambda: empty_bootstrap,
    )
    with pytest.raises(DrinkingFountainReleaseError, match="drinking_fountain_bound_release_unavailable"):
        load_drinking_fountain_runtime(settings)


def test_source_identity_mismatch_and_auto_promotion_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DRINKING_FOUNTAIN_AUTO_PROMOTE"):
        _settings(tmp_path, drinking_fountain_auto_promote=True)
    settings = _settings(tmp_path, drinking_fountain_source_url="https://example.invalid/other.kml")
    with pytest.raises(DrinkingFountainReleaseError, match="drinking_fountain_bound_release_unavailable"):
        load_drinking_fountain_runtime(settings)


def test_import_creates_pending_release_without_runtime_promotion(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    source, boundary, evidence = _source_files()
    pending = import_drinking_fountain_snapshot_as_pending(
        settings,
        source,
        boundary,
        evidence,
        retrieved_at=datetime(2026, 8, 2, 13, 0, tzinfo=timezone.utc),
        content_type="text/xml",
    )
    paths = DrinkingFountainReleasePaths.from_settings(settings)
    assert pending.path.parent == paths.pending
    assert not paths.pointer.exists()
    assert load_drinking_fountain_runtime(settings).runtime_source == "packaged_bootstrap"


def test_cli_fetch_diff_validate_and_explicit_activation(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    source, boundary, evidence = _source_files()

    async def downloaded(_settings):
        return source, "text/xml", None, boundary, "Thu, 13 Jul 2023 11:40:26 GMT"

    monkeypatch.setattr("app.drinking_fountain_sync._download", downloaded)
    fetched = asyncio.run(fetch_drinking_fountains(settings, stage=True))
    assert fetched.changed is False and fetched.pending_release_id is None
    assert asyncio.run(diff_live_source(settings))["added"] == []
    status = asyncio.run(run_command(settings, argparse.Namespace(command="status")))
    assert status["runtime_source"] == "packaged_bootstrap"

    pending = import_drinking_fountain_snapshot_as_pending(
        settings,
        source,
        boundary,
        evidence,
        retrieved_at=datetime(2026, 8, 2, 14, 0, tzinfo=timezone.utc),
        content_type="text/xml",
    )
    validated = asyncio.run(run_command(settings, argparse.Namespace(
        command="validate",
        release_id=pending.release_id,
        pending=True,
    )))
    assert validated["release_id"] == pending.release_id
    activated = asyncio.run(run_command(settings, argparse.Namespace(
        command="activate",
        release_id=pending.release_id,
    )))
    assert activated["release_id"] == pending.release_id
    runtime = load_drinking_fountain_runtime(settings)
    assert runtime.release_id == pending.release_id
    assert runtime.runtime_source == "active_release"

    second_pending = import_drinking_fountain_snapshot_as_pending(
        settings,
        source,
        boundary,
        evidence,
        retrieved_at=datetime(2026, 8, 3, 9, 0, tzinfo=timezone.utc),
        content_type="text/xml",
    )
    asyncio.run(run_command(settings, argparse.Namespace(
        command="activate",
        release_id=second_pending.release_id,
    )))
    assert load_drinking_fountain_runtime(settings).release_id == second_pending.release_id

    rolled_back = asyncio.run(run_command(settings, argparse.Namespace(
        command="rollback",
        release_id=pending.release_id,
    )))
    assert rolled_back["release_id"] == pending.release_id
    assert load_drinking_fountain_runtime(settings).release_id == pending.release_id


def test_water_selection_combines_only_positive_social_evidence_and_approved_fountains(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb, decision = _decision(settings)
    results = select_drinking_water_results(
        decision,
        kb.offers,
        kb.drinking_fountains,
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )
    social = [result.social_offer for result in results.eligible if result.social_offer]
    fountains = [result.fountain for result in results.eligible if result.fountain]
    assert social and all("drinking_water" in offer.capabilities for offer in social)
    assert len(fountains) == 21
    assert all(record.runtime_eligible for record in fountains)
    assert len(results.spoken_results) == len(results.card_results) == 3
    ranked_distances = [
        result.distance_meters
        for result in results.eligible
        if not result.mandatory and result.distance_meters is not None
    ]
    assert ranked_distances == sorted(
        result.distance_meters
        for result in results.eligible
        if not result.mandatory and result.distance_meters is not None
    )


def test_explicit_fountain_request_is_spatial_only_and_outside_season_uses_social_fallback(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb, decision = _decision(settings)
    summer = select_drinking_water_results(
        decision,
        kb.offers,
        kb.drinking_fountains,
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
        fountain_only=True,
    )
    assert summer.eligible and all(result.record_type == "drinking_fountain" for result in summer.eligible)
    winter = select_drinking_water_results(
        decision,
        kb.offers,
        kb.drinking_fountains,
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        fountain_only=True,
    )
    assert winter.eligible and all(result.record_type == "social_offer" for result in winter.eligible)


def test_unknown_season_or_inactive_status_never_becomes_a_direct_fountain_result(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb, decision = _decision(settings)
    source = kb.drinking_fountains[0]
    unknown_season = source.model_copy(update={
        "seasonal_status": SeasonalStatus.UNKNOWN,
        "season_start": None,
        "season_end": None,
    })
    inactive = source.model_copy(update={
        "id": f"{source.id}-inactive",
        "source_id": f"{source.source_id}-inactive",
        "operation_status": OperationStatus.INACTIVE,
    })
    results = select_drinking_water_results(
        decision,
        kb.offers,
        (unknown_season, inactive),
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
        fountain_only=True,
    )
    assert all(result.record_type == "social_offer" for result in results.eligible)


def test_equal_fountain_distances_use_stable_namespaced_id_as_tie_breaker(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb, decision = _decision(settings)
    source = kb.drinking_fountains[0]
    first = source.model_copy(update={"id": "drinking_fountain:a", "source_id": "a"})
    second = source.model_copy(update={"id": "drinking_fountain:b", "source_id": "b"})
    results = select_drinking_water_results(
        decision,
        kb.offers,
        (second, first),
        now=datetime(2026, 8, 2, tzinfo=timezone.utc),
        fountain_only=True,
    )
    assert [result.id for result in results.eligible] == [first.id, second.id]


def test_template_api_limits_cards_but_maps_every_seasonally_eligible_fountain(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)
    app.state.service = QueryService(
        settings,
        app.state.kb,
        clock=lambda: datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
    )
    app.state.service.blablador = _WaterInterpreter()
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Wo ist der nächste Trinkwasserbrunnen?", "language": "de"},
    ).json()
    assert body["status"] == "ok"
    assert len(body["cards"]) == 3
    assert all(card["record_type"] == "drinking_fountain" for card in body["cards"])
    assert len(body["map_marker_ids"]) == 21
    assert len(body["map_data"]["destinations"]) == 21
    assert all(item["record_type"] == "drinking_fountain" for item in body["map_data"]["destinations"])
    assert [card["id"] for card in body["cards"]] == [
        "drinking_fountain:katharinenstrasse",
        "drinking_fountain:em-brunnen",
        "drinking_fountain:kurt-masur-platz",
    ]
    assert "jetzt geöffnet" not in body["answer"].casefold()
    assert "funktioniert gerade" not in body["answer"].casefold()


def test_generic_water_request_excludes_hilfebus_outside_sunday_stand_time(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb = load_active_knowledge_base(settings)
    service = QueryService(
        settings,
        kb,
        clock=lambda: datetime(2026, 8, 14, 13, 32, tzinfo=ZoneInfo("Europe/Berlin")),
    )
    service.blablador = _WaterInterpreter()

    response = asyncio.run(
        service.query(QueryRequest(query="Ich habe Durst.", language=Language.DE))
    )

    assert "21" not in response.card_ids
    assert "21" not in response.spoken_result_ids
    assert not any(marker_id.startswith("21:") for marker_id in response.map_marker_ids)
    assert "Hilfebus" not in response.answer


def test_generic_water_request_uses_hilfebus_during_sunday_stand_time(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb = load_active_knowledge_base(settings)
    service = QueryService(
        settings,
        kb,
        clock=lambda: datetime(2026, 8, 16, 20, 30, tzinfo=ZoneInfo("Europe/Berlin")),
    )
    service.blablador = _WaterInterpreter()

    response = asyncio.run(
        service.query(QueryRequest(query="Ich habe Durst.", language=Language.DE))
    )

    assert response.card_ids[0] == "21"
    assert response.cards[0].address is None
    assert response.map_marker_ids[0] == "21:hbf-west"
    assert response.map_data is not None
    stand = response.map_data.destinations[0]
    assert "Westseite" in stand.address
    assert "20:00" in " ".join(stand.opening_hours)


@pytest.mark.parametrize(
    ("language", "plain", "with_district"),
    [
        (Language.DE, "Wo ist der nächste Trinkbrunnen?", "Wo ist der nächste Trinkbrunnen in Connewitz?"),
        (Language.EN, "Where is the nearest drinking fountain?", "Where is the nearest drinking fountain in Connewitz?"),
        (Language.PL, "Gdzie jest najbliższa fontanna z wodą pitną?", "Gdzie jest fontanna z wodą pitną w Connewitz?"),
        (Language.RO, "Unde este cea mai apropiată fântână cu apă potabilă?", "Unde este o fântână cu apă potabilă în Connewitz?"),
        (Language.RU, "Где ближайший питьевой фонтан?", "Где питьевой фонтан в Connewitz?"),
    ],
)
def test_district_never_changes_water_ranking_or_creates_a_district_claim(
    tmp_path: Path,
    language: Language,
    plain: str,
    with_district: str,
) -> None:
    settings = _settings(tmp_path / language.value)
    kb = load_active_knowledge_base(settings)
    service = QueryService(
        settings,
        kb,
        clock=lambda: datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
    )
    service.blablador = _WaterInterpreter()
    first = asyncio.run(service.query(QueryRequest(query=plain, language=language)))
    second = asyncio.run(service.query(QueryRequest(query=with_district, language=language)))
    assert first.card_ids == second.card_ids
    assert first.map_marker_ids == second.map_marker_ids
    assert "connewitz" not in second.answer.casefold()
    assert second.interaction.infrastructure_district_ranking_used is False
    assert second.interaction.selector_bypass_reason == "deterministic_spatial_ranking"


def _fact(evidence, kind: FactType):
    for fact in evidence.selected_offers[0].facts:
        if fact.fact_type == kind:
            return fact
    raise AssertionError(f"missing {kind}")


def test_fountain_evidence_is_minimal_and_grounded() -> None:
    release = load_packaged_drinking_fountain_release()
    record = next(record for record in release.collection.records if record.runtime_eligible)
    from app.infrastructure_results import DrinkingWaterResult, WaterReasonCode
    from app.candidate_contract import CandidateRole

    result = DrinkingWaterResult(
        id=record.id,
        record_type="drinking_fountain",
        mandatory=False,
        role=CandidateRole.DIRECT_SERVICE,
        distance_meters=605,
        reason_codes=(WaterReasonCode.PUBLIC_DRINKING_FOUNTAIN,),
        fountain=record,
    )
    evidence = build_drinking_water_evidence(
        query="Trinkbrunnen in Connewitz",
        language=Language.DE,
        results=[result],
    )
    payload = evidence.model_dump_json()
    assert evidence.current_query == ""
    assert "latitude" not in payload and "longitude" not in payload and "Connewitz" not in payload
    assert "outside_leipzig" not in payload and "mobile_schedule_not_verified" not in payload
    assert record.exclusion_reason is None
    name = _fact(evidence, FactType.DISPLAY_NAME)
    service = _fact(evidence, FactType.SERVICE)
    response = FormulatorResponse(
        contract_version=FORMULATOR_CONTRACT_VERSION,
        language=Language.DE,
        sentences=[FormulatedSentence(
            text=f"Bei {record.name} findest du einen Trinkwasserbrunnen.",
            claim_type=ClaimType.SERVICE,
            offer_id=record.id,
            fact_ids=[name.fact_id, service.fact_id],
        )],
        card_ids=[record.id],
    )
    assert validate_formulation(response, evidence).card_ids == [record.id]

    invented = response.model_copy(update={
        "sentences": [response.sentences[0].model_copy(update={"text": "Beim Fantasiebrunnen findest du Wasser."})]
    })
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(invented, evidence)

    realtime = response.model_copy(update={
        "sentences": [response.sentences[0].model_copy(update={"text": f"{record.name} funktioniert gerade."})]
    })
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(realtime, evidence)


def test_interpreter_error_fails_closed_and_formulator_failure_uses_only_template_results(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb = load_active_knowledge_base(settings)
    service = QueryService(settings, kb, clock=lambda: datetime(2026, 8, 2, tzinfo=timezone.utc))

    class InvalidInterpreter:
        async def interpret_query(self, **_kwargs):
            raise InterpreterError("interpreter_schema_error")

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der technische Fallback zusätzlich den deterministischen
    # Hilfebus-Kontakt statt eines reinen "versuche es erneut"-Hinweises.
    hilfebus_offer = next(offer for offer in kb.offers if "general_help_referral_first" in offer.priority_rules)
    service.blablador = InvalidInterpreter()
    failed = asyncio.run(service.query(QueryRequest(query="Trinkbrunnen", language=Language.DE)))
    assert failed.status == "error"
    assert [card.id for card in failed.cards] == [hilfebus_offer.id]
    assert failed.cards[0].address is None
    assert failed.map_data is None

    class InvalidFormulator:
        async def interpret_query(self, **_kwargs):
            return _interpretation()

        async def select_candidates(self, **_kwargs):
            raise AssertionError("spatial water path must bypass LLM selector")

        def context_fits(self, _evidence):
            return True

        async def formulate_answer(self, **_kwargs):
            raise FormulatorError("formulator_ungrounded_claim")

    service.blablador = InvalidFormulator()
    fallback = asyncio.run(service.query(QueryRequest(query="Trinkbrunnen", language=Language.DE)))
    assert fallback.provider == "template"
    assert len(fallback.cards) == 3 and len(fallback.map_marker_ids) == 21
    assert fallback.interaction.formulator_error_code == "formulator_ungrounded_claim"
    assert fallback.interaction.selector_used is False


def test_health_and_frontend_expose_only_redacted_fountain_state(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    health = client.get("/api/health").json()
    assert health["drinking_fountain_runtime_status"] == "ok"
    assert health["drinking_fountain_record_count"] == 35
    assert health["drinking_fountain_runtime_eligible_count"] == 21
    assert health["drinking_fountain_outside_leipzig_count"] == 9
    assert health["drinking_fountain_mobile_excluded_count"] == 5
    assert health["drinking_fountains"]["license_status"] == "not_explicitly_specified"
    assert not any("path" in key for key in health["drinking_fountains"])
    script = client.get("/static/app.js").text
    styles = client.get("/static/styles.css").text
    assert 'destination.record_type === "drinking_fountain"' in script
    assert "document.createElement(\"span\")" in script
    assert "drinking-fountain-symbol" in script and "drinking-fountain-marker" in styles
    assert "html: iconElement" in script


def test_kb_fingerprint_and_runtime_projection_include_only_approved_fountains(tmp_path: Path) -> None:
    kb = load_active_knowledge_base(_settings(tmp_path))
    assert len(kb.drinking_fountains) == 21
    assert all(record.runtime_eligible for record in kb.drinking_fountains)
    assert kb.metadata["drinking_fountains"]["record_count"] == 35
    assert kb.metadata["drinking_fountains"]["runtime_eligible_count"] == 21
    assert kb.runtime_kb_fingerprint
