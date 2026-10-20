from __future__ import annotations

import csv
import io
import json
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.infrastructure import (
    FeeStatus,
    ToiletSourceError,
    diff_toilet_records,
    normalize_toilet_csv,
)
from app.infrastructure_results import select_public_toilets, toilet_card, toilet_map_data
from app.formulation import (
    ClaimType,
    FactType,
    FormulatedSentence,
    FormulatorError,
    FormulatorResponse,
    FORMULATOR_CONTRACT_VERSION,
    build_public_toilet_evidence,
)
from app.grounding import validate_formulation
from app.interpreter import QueryInterpretation
from app.kb_loader import load_active_knowledge_base
from app.models import Language, QueryRequest
from app.providers.llm import InterpreterError, ProviderAnswer
from app.safety import SafetyTextKind, safety_text
from app.service import QueryService
from app.resources import packaged_bootstrap_data_root
from app.release_storage import canonical_json_bytes, sha256_bytes
from app.spatial import distance_from_hbf
from app.toilet_releases import (
    ToiletReleaseError,
    ToiletReleasePaths,
    create_pending_toilet_release,
    load_toilet_runtime,
    promote_toilet_release,
    rollback_toilet_release,
    verify_toilet_release,
)
from app.toilet_sync import fetch_toilets, run_command


FETCHED_AT = datetime(2026, 8, 2, 5, 55, 52, tzinfo=timezone.utc)


def _snapshot() -> bytes:
    root = packaged_bootstrap_data_root() / "toilets"
    pointer = json.loads((root / "active_release.json").read_text(encoding="utf-8"))
    return (root / "releases" / pointer["release_id"] / "snapshot.csv").read_bytes()


def _collection(content: bytes | None = None):
    return normalize_toilet_csv(
        _snapshot() if content is None else content,
        fetched_at=FETCHED_AT,
        content_type="text/csv; charset=utf-8",
        source_last_modified="Wed, 14 Jan 2026 06:44:49 GMT",
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
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
        wfs_auto_sync=False,
        toilet_auto_sync=False,
    )


@pytest.mark.parametrize("language", list(Language))
def test_toilet_card_map_and_readout_share_localized_fields(language: Language) -> None:
    records = select_public_toilets(tuple(_collection().records)).map_results
    mapped = toilet_map_data(records, language)
    assert mapped is not None
    for record, destination in zip(records, mapped.destinations, strict=True):
        card = toilet_card(record, language)
        assert destination.opening_hours == card.opening_hours_raw
        assert destination.facilities == card.facilities
        assert destination.fee_raw == card.fee_raw
        assert destination.spoken_text == card.spoken_text
        for value in [*card.opening_hours_raw, *card.facilities, card.fee_raw]:
            assert value in card.spoken_text


class _ToiletInterpreter:
    async def interpret_query(self, **_kwargs):
        return QueryInterpretation.model_validate(
            {
                "contract_version": "4",
                "need": "toilet",
                "explicit_service_requests": [],
                "scope_status": "in_scope",
                "input_language": "de",
                "explicit_facts": {
                    "age": None,
                    "age_group": "unknown",
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

    def context_fits(self, _evidence):
        return False


def _toilet_client(tmp_path: Path) -> TestClient:
    app = __import__("app.main", fromlist=["create_app"]).create_app(_settings(tmp_path))
    app.state.service.blablador = _ToiletInterpreter()
    return TestClient(app)


def _toilet_service(settings: Settings, kb) -> QueryService:
    service = QueryService(settings, kb)
    service.blablador = _ToiletInterpreter()
    return service


def test_auto_promotion_cannot_be_enabled_in_prototype(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="TOILET_AUTO_PROMOTE"):
        Settings(
            app_root=tmp_path,
            kb_path=tmp_path / "unused.json",
            rewrite_provider="template",
            blablador_base_url=None,
            blablador_api_key=None,
            blablador_model=None,
            blablador_timeout_seconds=1,
            blablador_max_context_chars=1_000,
            toilet_auto_promote=True,
        )


def _rewrite_csv(mutator) -> bytes:
    text = _snapshot().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    fields = list(reader.fieldnames or [])
    mutator(fields, rows)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def test_official_bootstrap_schema_and_field_mapping() -> None:
    collection = _collection()
    assert len(collection.records) == 21
    assert collection.source.sha256 == "fce215d4e7bd928bd44963b0adb7e0b73f4e042d123e940dc96e8cdddc2b13f4"
    assert len({record.id for record in collection.records}) == 21
    assert all(record.id == f"toilet:{record.source_id}" for record in collection.records)
    assert {record.source_reference_id for record in collection.records} == {"leipzig-public-toilets-csv"}
    assert {record.fee_status for record in collection.records} == {FeeStatus.FREE, FeeStatus.PAID}
    assert all(abs(distance_from_hbf(record.latitude, record.longitude)) >= 0 for record in collection.records)


def test_additional_column_is_ignored_by_runtime_positive_list() -> None:
    content = _rewrite_csv(lambda fields, rows: (fields.append("NeueSpalte"), [row.update(NeueSpalte="x") for row in rows]))
    record = _collection(content).records[0]
    assert "NeueSpalte" not in record.model_dump()


def test_source_markup_remains_plain_card_data_for_dom_text_sinks() -> None:
    payload = '<img src=x onerror="alert(1)">'
    content = _rewrite_csv(lambda _fields, rows: rows[0].update(Ort=payload))
    record = _collection(content).records[0]
    assert toilet_card(record, Language.DE).name == payload


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "toilet_source_empty"),
        (b"<html>error</html>", "toilet_source_not_csv"),
        (b"\xef\xbb\xbfID,Ort\n0001,X\n", "toilet_schema_changed"),
    ],
)
def test_invalid_source_shapes_are_rejected(content: bytes, code: str) -> None:
    with pytest.raises(ToiletSourceError, match=code):
        _collection(content)


def test_missing_required_value_and_duplicate_id_are_rejected() -> None:
    missing = _rewrite_csv(lambda _fields, rows: rows[0].update(Betreiber=""))
    duplicate = _rewrite_csv(lambda _fields, rows: rows[1].update(ID=rows[0]["ID"]))
    with pytest.raises(ToiletSourceError, match="toilet_record_invalid"):
        _collection(missing)
    with pytest.raises(ToiletSourceError, match="toilet_duplicate_id"):
        _collection(duplicate)


@pytest.mark.parametrize("missing_column", ["Entgelt", "Servicenummer", "lat", "utm_north"])
def test_truncated_csv_row_is_a_controlled_source_error(missing_column: str) -> None:
    rows = list(csv.reader(io.StringIO(_snapshot().decode("utf-8-sig"))))
    rows[1] = rows[1][:rows[0].index(missing_column)]
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)

    with pytest.raises(ToiletSourceError, match="toilet_record_invalid"):
        _collection(b"\xef\xbb\xbf" + output.getvalue().encode("utf-8"))


def test_unknown_fee_is_preserved_without_inference() -> None:
    content = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt="vor Ort erfragen"))
    record = _collection(content).records[0]
    assert record.fee_status == FeeStatus.UNKNOWN
    assert record.fee_cents is None
    assert record.fee_raw == "vor Ort erfragen"

    blank = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt=""))
    blank_record = _collection(blank).records[0]
    assert blank_record.fee_status == FeeStatus.UNKNOWN
    assert blank_record.fee_cents is None


def test_invalid_or_inconsistent_geometry_is_retained_but_not_ranked() -> None:
    content = _rewrite_csv(lambda _fields, rows: rows[0].update(lat="0"))
    collection = _collection(content)
    record = collection.records[0]
    assert record.coordinates_status.value == "invalid"
    assert record.latitude is None
    assert record.id not in select_public_toilets(tuple(collection.records)).map_marker_ids


def test_duplicate_geometry_is_retained_but_both_records_are_not_ranked() -> None:
    content = _rewrite_csv(
        lambda _fields, rows: rows[1].update(
            lat=rows[0]["lat"],
            long=rows[0]["long"],
            utm_east=rows[0]["utm_east"],
            utm_north=rows[0]["utm_north"],
        )
    )
    collection = _collection(content)
    assert collection.records[0].coordinates_status.value == "duplicate"
    assert collection.records[1].coordinates_status.value == "duplicate"
    marker_ids = select_public_toilets(tuple(collection.records)).map_marker_ids
    assert "toilet:0001" not in marker_ids
    assert "toilet:0002" not in marker_ids


@pytest.mark.parametrize(
    ("raw", "status", "cents"),
    [
        ("0", "free", 0),
        ("0,00 €", "free", 0),
        ("kostenlos", "free", 0),
        ("frei", "free", 0),
        ("0,50 €", "paid", 50),
        ("50 Cent", "paid", 50),
        ("1,00 €", "paid", 100),
        ("", "unknown", None),
        ("unbekannt", "unknown", None),
    ],
)
def test_fee_fail_safe_values(raw: str, status: str, cents: int | None) -> None:
    content = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt=raw))
    record = _collection(content).records[0]
    assert record.fee_status.value == status
    assert record.fee_cents == cents


def test_diff_detects_add_remove_fee_name_and_coordinate_changes() -> None:
    previous = _collection()
    changed = _rewrite_csv(
        lambda _fields, rows: (
            rows.pop(),
            rows[0].update(Entgelt="kostenfrei"),
            rows[1].update(Ort="Geänderter Ort"),
            rows[2].update(lat=rows[3]["lat"], long=rows[3]["long"], utm_east=rows[3]["utm_east"], utm_north=rows[3]["utm_north"]),
            rows.append({**rows[0], "ID": "0999"}),
        )
    )
    current = _collection(changed)
    diff = diff_toilet_records(previous, current)
    assert diff["added"] == ["toilet:0999"]
    assert "toilet:0021" in diff["removed"]
    assert {"toilet:0001", "toilet:0002", "toilet:0003"} <= set(diff["modified"])


def test_diff_ignores_dataset_hash_and_reports_only_changed_record() -> None:
    previous = _collection()
    unchanged = _collection(_rewrite_csv(lambda _fields, _rows: None))
    assert unchanged.source.sha256 != previous.source.sha256
    assert diff_toilet_records(previous, unchanged) == {"added": [], "removed": [], "modified": []}

    changed = _collection(_rewrite_csv(lambda _fields, rows: rows[0].update(Ort="Geänderter Ort")))
    assert diff_toilet_records(previous, changed) == {
        "added": [], "removed": [], "modified": ["toilet:0001"],
    }


def test_release_promotion_rollback_and_corruption_fallback(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    first_collection = _collection()
    first = create_pending_toilet_release(
        settings,
        _snapshot(),
        first_collection,
        base_release_id=None,
        created_at=FETCHED_AT,
    )
    promoted_first = promote_toilet_release(settings, first.release_id)
    assert load_toilet_runtime(settings).release_id == promoted_first.release_id

    modified_bytes = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt="kostenfrei"))
    modified = _collection(modified_bytes)
    second = create_pending_toilet_release(
        settings,
        modified_bytes,
        modified,
        base_release_id=first.release_id,
        created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )
    promoted_second = promote_toilet_release(settings, second.release_id)
    assert load_toilet_runtime(settings).release_id == promoted_second.release_id

    (promoted_second.path / "records.json").write_text("{}", encoding="utf-8")
    fallback = load_toilet_runtime(settings)
    assert fallback.release_id == promoted_first.release_id
    assert fallback.runtime_status == "degraded"
    assert fallback.runtime_source == "previous_verified_release"

    rollback_toilet_release(settings, promoted_first.release_id)
    assert verify_toilet_release(settings, promoted_first.release_id).release_id == promoted_first.release_id


def test_release_rejects_implausible_reduction_and_geometry_loss(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    previous = _collection()
    reduced_bytes = _rewrite_csv(lambda _fields, rows: rows.__delitem__(slice(10, None)))
    with pytest.raises(ToiletReleaseError, match="toilet_record_invalid"):
        create_pending_toilet_release(
            settings,
            reduced_bytes,
            _collection(reduced_bytes),
            base_release_id="20260802T055552Z-fce215d4e7bd",
            base_collection=previous,
            created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        )

    invalid_geometry = _rewrite_csv(
        lambda _fields, rows: [row.update(lat="0") for row in rows[:11]]
    )
    with pytest.raises(ToiletReleaseError, match="toilet_geometry_invalid"):
        create_pending_toilet_release(
            settings,
            invalid_geometry,
            _collection(invalid_geometry),
            base_release_id="20260802T055552Z-fce215d4e7bd",
            base_collection=previous,
            created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        )


def test_release_rejects_records_not_reproducible_from_snapshot(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pending = create_pending_toilet_release(
        settings,
        _snapshot(),
        _collection(),
        base_release_id=None,
        created_at=FETCHED_AT,
    )
    records_path = pending.path / "records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    records["records"][0]["display_name"] = "Manipulierter Name"
    records_bytes = canonical_json_bytes(records)
    records_path.write_bytes(records_bytes)
    manifest_path = pending.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["records.json"] = {
        "sha256": sha256_bytes(records_bytes),
        "size_bytes": len(records_bytes),
    }
    manifest["manifest_sha256"] = sha256_bytes(
        canonical_json_bytes({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ToiletReleaseError, match="toilet_release_invalid"):
        verify_toilet_release(settings, pending.release_id, pending=True)


def test_corrupt_pointer_uses_same_last_verified_release(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    pending = create_pending_toilet_release(
        settings,
        _snapshot(),
        _collection(),
        base_release_id=None,
        created_at=FETCHED_AT,
    )
    active = promote_toilet_release(settings, pending.release_id)
    ToiletReleasePaths.from_settings(settings).pointer.write_text("not-json", encoding="utf-8")
    runtime = load_toilet_runtime(settings)
    assert runtime.release_id == active.release_id
    assert runtime.runtime_source == "last_verified_release"
    assert runtime.runtime_status == "degraded"


def test_unactivated_valid_release_directory_is_never_a_runtime_fallback(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    changed = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt="kostenfrei"))
    pending = create_pending_toilet_release(
        settings,
        changed,
        _collection(changed),
        base_release_id=None,
        created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )
    paths = ToiletReleasePaths.from_settings(settings)
    paths.releases.mkdir(parents=True)
    unactivated = paths.releases / pending.release_id
    shutil.move(str(pending.path), unactivated)
    assert verify_toilet_release(settings, pending.release_id).release_id == pending.release_id

    runtime = load_toilet_runtime(settings)

    assert runtime.runtime_source == "packaged_bootstrap"
    assert runtime.release_id != pending.release_id


def test_release_source_identity_is_required_for_promotion_and_bootstrap_fallback(
    tmp_path: Path,
) -> None:
    settings = replace(
        _settings(tmp_path),
        toilet_source_url="https://different-source.invalid/public-toilets.csv",
    )
    pending = create_pending_toilet_release(
        settings,
        _snapshot(),
        _collection(),
        base_release_id=None,
        created_at=FETCHED_AT,
    )

    with pytest.raises(ToiletReleaseError, match="toilet_source_identity_mismatch"):
        promote_toilet_release(settings, pending.release_id)
    with pytest.raises(ToiletReleaseError, match="toilet_bound_release_unavailable"):
        load_toilet_runtime(settings)


def test_no_safe_toilet_fallback_is_a_controlled_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable():
        raise ToiletReleaseError("toilet_bound_release_unavailable")

    monkeypatch.setattr("app.toilet_releases._packaged_release", unavailable)

    with pytest.raises(ToiletReleaseError, match="toilet_bound_release_unavailable"):
        load_toilet_runtime(_settings(tmp_path))


def test_packaged_bootstrap_and_composite_runtime_fingerprint(tmp_path: Path) -> None:
    first = load_active_knowledge_base(_settings(tmp_path))
    assert len(first.offers) == 28
    assert len(first.public_toilets) == 21
    assert not {"1", "2", "3", "4"}.intersection(offer.id for offer in first.offers)
    assert not set(offer.id for offer in first.offers).intersection(record.id for record in first.public_toilets)
    assert first.metadata["public_toilets"]["runtime_source"] == "packaged_bootstrap"


def test_validate_command_verifies_packaged_bootstrap_without_local_pointer(tmp_path: Path) -> None:
    args = __import__("argparse").Namespace(command="validate", release_id=None, pending=False)
    result = __import__("asyncio").run(run_command(_settings(tmp_path), args))
    assert result["validation_status"] == "validated"
    assert result["record_count"] == 21


def test_toilet_release_change_changes_composite_fingerprint(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    before = load_active_knowledge_base(settings)
    changed = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt="kostenfrei"))
    pending = create_pending_toilet_release(
        settings,
        changed,
        _collection(changed),
        base_release_id=before.metadata["public_toilets"]["release_id"],
        base_collection=load_toilet_runtime(settings).collection,
        created_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )
    promote_toilet_release(settings, pending.release_id)
    after = load_active_knowledge_base(settings)
    assert after.release_id == before.release_id
    assert after.runtime_kb_fingerprint != before.runtime_kb_fingerprint


def test_toilet_release_failure_does_not_break_social_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)

    def fail(_settings):
        raise ToiletReleaseError("toilet_bound_release_unavailable")

    monkeypatch.setattr("app.kb_loader.load_toilet_runtime", fail)
    kb = load_active_knowledge_base(settings)
    assert len(kb.offers) == 28
    assert kb.public_toilets == ()
    assert kb.metadata["public_toilets"]["error_code"] == "toilet_bound_release_unavailable"


def test_deterministic_selection_excludes_closed_and_returns_all_markers() -> None:
    result = select_public_toilets(tuple(_collection().records))
    assert len(result.eligible) == 20
    assert len(result.spoken_results) == 3
    assert len(result.card_results) == 3
    assert len(result.map_results) == 20
    assert "toilet:0003" not in result.map_marker_ids
    assert result.eligible == tuple(sorted(result.eligible, key=lambda item: (distance_from_hbf(item.latitude, item.longitude), item.id)))


@pytest.mark.parametrize(("count", "expected"), [(1, 1), (2, 2), (3, 3), (8, 3)])
def test_spoken_and_card_limit_for_small_and_large_result_sets(count: int, expected: int) -> None:
    records = tuple(record for record in _collection().records if record.availability_status.value == "available")[:count]
    result = select_public_toilets(records)
    assert len(result.spoken_results) == expected
    assert len(result.card_results) == expected
    assert len(result.map_results) == count


@pytest.mark.parametrize(
    ("language", "query"),
    [
        ("de", "Wo ist eine Toilette?"),
        ("en", "Where is a public toilet?"),
        ("pl", "Gdzie jest toaleta?"),
        ("ro", "Unde este o toaletă?"),
        ("ru", "Где находится туалет?"),
    ],
)
def test_toilet_api_is_multilingual_deterministic_and_selector_free(
    tmp_path: Path,
    language: str,
    query: str,
) -> None:
    client = _toilet_client(tmp_path)
    body = client.post("/api/query", json={"query": query, "language": language}).json()
    assert body["status"] == "ok"
    assert len(body["spoken_result_ids"]) == 3
    assert body["card_ids"] == body["spoken_result_ids"]
    assert len(body["map_marker_ids"]) == 20
    assert all(card["record_type"] == "public_toilet" for card in body["cards"])
    assert all(card["operator_name"] for card in body["cards"])
    assert {card["source_attribution"] for card in body["cards"]} == {"Stadt Leipzig"}
    assert body["cards"][0]["fee_raw"] in body["answer"]
    assert all(item["record_type"] == "public_toilet" for item in body["map_data"]["destinations"])
    assert body["map_marker_ids"] == [item["id"] for item in body["map_data"]["destinations"]]
    assert "toilet:" not in body["answer"]


def test_district_words_do_not_change_toilet_ranking(tmp_path: Path) -> None:
    client = _toilet_client(tmp_path)
    plain = client.post("/api/query", json={"query": "Wo ist eine Toilette?", "language": "de"}).json()
    district = client.post("/api/query", json={"query": "Wo ist in Grünau eine Toilette?", "language": "de"}).json()
    assert district["spoken_result_ids"] == plain["spoken_result_ids"]
    assert "Grünau" not in district["answer"]


def test_template_fee_wording_is_fail_safe_for_free_and_unknown(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    base = load_active_knowledge_base(settings)
    source = select_public_toilets(base.public_toilets).spoken_results[0]

    free = source.model_copy(
        update={"fee_status": FeeStatus.FREE, "fee_cents": 0, "fee_currency": None, "fee_raw": "0"}
    )
    free_response = __import__("asyncio").run(
        _toilet_service(settings, replace(base, public_toilets=(free,))).query(
            QueryRequest(query="Wo ist eine Toilette?", language=Language.DE)
        )
    )
    assert "kostenlos" in free_response.answer
    assert free_response.map_marker_ids == [free.id]
    assert "Weitere passende Toiletten" not in free_response.answer

    unknown = source.model_copy(
        update={"fee_status": FeeStatus.UNKNOWN, "fee_cents": None, "fee_currency": None, "fee_raw": ""}
    )
    unknown_response = __import__("asyncio").run(
        _toilet_service(settings, replace(base, public_toilets=(unknown,))).query(
            QueryRequest(query="Wo ist eine Toilette?", language=Language.DE)
        )
    )
    assert "kostenlos" not in unknown_response.answer
    assert "Entgelt" not in unknown_response.answer


def test_health_exposes_redacted_toilet_release_state(tmp_path: Path) -> None:
    client = TestClient(__import__("app.main", fromlist=["create_app"]).create_app(_settings(tmp_path)))
    health = client.get("/api/health").json()["public_toilets"]
    assert health["runtime_status"] == "ok"
    assert health["source_status"] == "current"
    assert health["runtime_source"] == "packaged_bootstrap"
    assert health["record_count"] == 21
    assert health["eligible_record_count"] == 20
    assert health["valid_geometry_count"] == 21
    assert health["missing_geometry_count"] == 0
    assert health["fee_free_count"] + health["fee_paid_count"] + health["fee_unknown_count"] == 21
    assert health["source_change_pending"] is False
    assert health["auto_promote"] is False
    assert not any("\\" in str(value) or ":\\" in str(value) for value in health.values())


def test_fetch_identical_source_does_not_stage_or_promote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)

    async def download(_settings):
        return _snapshot(), "text/csv", "Wed, 14 Jan 2026 06:44:49 GMT"

    monkeypatch.setattr("app.toilet_sync._download", download)
    result = __import__("asyncio").run(fetch_toilets(settings))
    assert result.changed is False
    assert result.pending_release_id is None
    assert ToiletReleasePaths.from_settings(settings).pointer.exists() is False
    assert settings.toilet_auto_promote is False


def test_fetch_changed_source_stages_without_activation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    changed = _rewrite_csv(lambda _fields, rows: rows[0].update(Entgelt="kostenfrei"))

    async def download(_settings):
        return changed, "text/csv", "Thu, 15 Jan 2026 06:44:49 GMT"

    monkeypatch.setattr("app.toilet_sync._download", download)
    result = __import__("asyncio").run(fetch_toilets(settings))
    assert result.changed is True
    assert result.pending_release_id
    assert result.pending_release_id in [item.name for item in ToiletReleasePaths.from_settings(settings).pending.iterdir()]
    assert ToiletReleasePaths.from_settings(settings).pointer.exists() is False
    repeated = __import__("asyncio").run(fetch_toilets(settings))
    assert repeated.pending_release_id == result.pending_release_id
    assert len(list(ToiletReleasePaths.from_settings(settings).pending.iterdir())) == 1


def test_source_failure_does_not_replace_promoted_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(tmp_path)
    pending = create_pending_toilet_release(
        settings,
        _snapshot(),
        _collection(),
        base_release_id=None,
        created_at=FETCHED_AT,
    )
    active = promote_toilet_release(settings, pending.release_id)

    async def fail(_settings):
        raise ToiletReleaseError("toilet_source_timeout")

    monkeypatch.setattr("app.toilet_sync._download", fail)
    with pytest.raises(ToiletReleaseError, match="toilet_source_timeout"):
        __import__("asyncio").run(fetch_toilets(settings))
    assert load_toilet_runtime(settings).release_id == active.release_id


def test_toilet_evidence_is_a_positive_list_of_only_spoken_records() -> None:
    selected = select_public_toilets(tuple(_collection().records)).spoken_results
    evidence = build_public_toilet_evidence(
        query="Wo ist eine Toilette?",
        language=Language.DE,
        toilets=list(selected),
        distances={record.id: distance_from_hbf(record.latitude, record.longitude) for record in selected},
    )
    payload = evidence.model_dump(mode="json")
    assert [item["offer_id"] for item in payload["selected_offers"]] == [record.id for record in selected]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "raw_fields" not in serialized
    assert "raw_properties" not in serialized
    assert not {"1", "2", "3", "4"}.intersection(item["offer_id"] for item in payload["selected_offers"])
    assert all(item["mandatory"] for item in payload["selected_offers"])


def test_toilet_formulation_is_grounded_and_restores_card_order() -> None:
    selected = select_public_toilets(tuple(_collection().records)).spoken_results
    evidence = build_public_toilet_evidence(
        query="Wo ist eine Toilette?",
        language=Language.DE,
        toilets=list(selected),
        distances={record.id: distance_from_hbf(record.latitude, record.longitude) for record in selected},
    )
    first = evidence.selected_offers[0]
    name = next(fact for fact in first.facts if fact.fact_type == FactType.DISPLAY_NAME)
    service = next(fact for fact in first.facts if fact.fact_type == FactType.SERVICE)
    fee = next(fact for fact in first.facts if fact.fact_type == FactType.FEE)
    response = FormulatorResponse(
        contract_version=FORMULATOR_CONTRACT_VERSION,
        language=Language.DE,
        sentences=[
            FormulatedSentence(
                text=f"Gehe zuerst zur öffentlichen Toilette {name.value}; das Entgelt beträgt {fee.value}.",
                claim_type=ClaimType.ACTION,
                offer_id=first.offer_id,
                fact_ids=[name.fact_id, service.fact_id, fee.fact_id],
            )
        ],
        card_ids=[first.offer_id],
    )
    validated = validate_formulation(response, evidence)
    assert validated.card_ids == [record.id for record in selected]
    assert "toilet:" not in validated.answer

    without_fee = response.model_copy(
        update={
            "sentences": [
                FormulatedSentence(
                    text=f"Gehe zuerst zur öffentlichen Toilette {name.value}.",
                    claim_type=ClaimType.ACTION,
                    offer_id=first.offer_id,
                    fact_ids=[name.fact_id, service.fact_id],
                )
            ]
        }
    )
    with pytest.raises(FormulatorError, match="formulator_ungrounded_claim"):
        validate_formulation(without_fee, evidence)

    second = evidence.selected_offers[1]
    second_name = next(fact for fact in second.facts if fact.fact_type == FactType.DISPLAY_NAME)
    second_service = next(fact for fact in second.facts if fact.fact_type == FactType.SERVICE)
    second_fee = next(fact for fact in second.facts if fact.fact_type == FactType.FEE)
    wrong_primary = response.model_copy(
        update={
            "sentences": [
                FormulatedSentence(
                    text=(
                        f"Gehe zuerst zur öffentlichen Toilette {second_name.value}; "
                        f"das Entgelt beträgt {second_fee.value}."
                    ),
                    claim_type=ClaimType.ACTION,
                    offer_id=second.offer_id,
                    fact_ids=[second_name.fact_id, second_service.fact_id, second_fee.fact_id],
                )
            ]
        }
    )
    with pytest.raises(FormulatorError, match="formulator_contract_violation"):
        validate_formulation(wrong_primary, evidence)


def test_toilet_path_uses_interpreter_and_formulator_but_never_llm_selector(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = QueryService(settings, load_active_knowledge_base(settings))

    class Provider:
        async def interpret_query(self, **_kwargs):
            return QueryInterpretation.model_validate(
                {
                    "contract_version": "4",
                    "need": "toilet",
                    "explicit_service_requests": [],
                    "scope_status": "in_scope",
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

        async def select_candidates(self, **_kwargs):
            raise AssertionError("toilet path must not call LLM selector")

        def context_fits(self, _evidence):
            return True

        async def formulate_answer(self, *, evidence, **_kwargs):
            return ProviderAnswer(
                answer="Die nächsten öffentlichen Toiletten stehen in den Karten.",
                card_ids=[offer.offer_id for offer in evidence.selected_offers],
                answer_type=evidence.answer_type,
                sentence_count=1,
            )

    service.blablador = Provider()
    response = __import__("asyncio").run(service.query(QueryRequest(query="Toilette", language=Language.DE)))
    assert response.provider == "blablador"
    assert response.interaction.selector_used is False
    assert response.interaction.selector_bypass_reason == "deterministic_infrastructure"
    assert len(response.cards) == 3


@pytest.mark.parametrize("language", list(Language))
def test_invalid_interpreter_output_fails_closed_before_toilet_results(
    tmp_path: Path,
    language: Language,
) -> None:
    settings = replace(
        _settings(tmp_path),
        rewrite_provider="blablador",
        blablador_base_url="https://provider.invalid/v1",
        blablador_api_key="test-token",
        blablador_model="test-model",
        interaction_log_path=tmp_path / "runtime" / "logs" / "interactions.jsonl",
    )
    app = __import__("app.main", fromlist=["create_app"]).create_app(settings)
    provider = app.state.service.blablador
    calls = {"interpreter": 0, "selector": 0, "formulator": 0}

    async def invalid_interpretation(**_kwargs):
        calls["interpreter"] += 1
        raise InterpreterError("interpreter_schema_error")

    async def forbidden_selector(**_kwargs):
        calls["selector"] += 1
        raise AssertionError("selector_must_not_run")

    async def forbidden_formulator(**_kwargs):
        calls["formulator"] += 1
        raise AssertionError("formulator_must_not_run")

    provider.interpret_query = invalid_interpretation
    provider.select_candidates = forbidden_selector
    provider.formulate_answer = forbidden_formulator
    body = TestClient(app).post(
        "/api/query",
        json={"query": "Wo ist eine Toilette?", "language": language.value},
    ).json()

    # Seit der Untersuchung zu unbemerkten technischen Fallbacks (Zeile 5)
    # enthält der Text zusätzlich den deterministischen Hilfebus-Kontakt statt
    # eines reinen "versuche es erneut"-Hinweises, sofern die Wissensbasis ihn
    # liefert; der bedingte 112-Hinweis bleibt dabei erhalten.
    offer = next(offer for offer in app.state.kb.offers if "general_help_referral_first" in offer.priority_rules)
    phone = ", ".join(offer.phone_numbers) or "—"
    times = "; ".join(offer.opening_hours_raw or offer.standzeiten_raw) or "—"
    assert body["status"] == "error"
    assert body["provider"] == "template"
    assert body["answer"] == safety_text(language, SafetyTextKind.TECHNICAL_HILFEBUS, phone=phone, times=times)
    assert [card["id"] for card in body["cards"]] == [offer.id]
    assert body["card_ids"] == [offer.id]
    assert calls == {"interpreter": 1, "selector": 0, "formulator": 0}
    record = json.loads(settings.interaction_log_path.read_text(encoding="utf-8"))
    assert record["route"] == "interpreter_error"
    assert record["interpreter_error_code"] == "interpreter_schema_error"
    assert record["source_ids"] == [offer.id]


def test_missing_verified_toilets_never_falls_back_to_social_offers(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    kb = replace(load_active_knowledge_base(settings), public_toilets=())
    response = __import__("asyncio").run(
        _toilet_service(settings, kb).query(QueryRequest(query="Wo ist eine Toilette?", language=Language.DE))
    )
    assert response.status == "no_results"
    assert response.cards == []
    assert response.map_data is None
    assert "verifizierten Toiletteninformationen" in response.answer
