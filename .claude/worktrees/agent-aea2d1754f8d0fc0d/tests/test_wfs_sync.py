from __future__ import annotations

import copy
import asyncio
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.kb_loader import load_knowledge_base
from app.wfs_sync import (
    LICENSE,
    WfsSyncError,
    canonical_payload,
    diff_canonical,
    sync_wfs,
    validate_feature_collection,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "wfs" / "current.geojson"
CANONICAL_PATH = ROOT / "data" / "canonical" / "offers.json"


def make_settings(root: Path, kb_path: Path) -> Settings:
    return Settings(
        app_root=root,
        kb_path=kb_path,
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=1,
        blablador_max_context_chars=50000,
    )


def raw_payload() -> dict:
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def test_promoted_wfs_snapshot_is_complete_and_loadable() -> None:
    raw = raw_payload()
    features = validate_feature_collection(raw)
    kb = load_knowledge_base(CANONICAL_PATH)

    assert len(features) == 30
    assert len(kb.offers) == 30
    assert kb.source_kind == "wfs"
    assert len({offer.id for offer in kb.offers}) == 30
    assert all(offer.geometry and offer.geometry["crs"].endswith("25833") for offer in kb.offers)
    assert kb.metadata["license"]["identifier"] == "dl-de/by-2-0"


def test_normalization_preserves_raw_fields_and_contact_arrays() -> None:
    canonical = canonical_payload(raw_payload(), make_settings(ROOT, CANONICAL_PATH))
    offer = canonical["offers"][0]

    assert offer["raw_properties"]["lnr"] is not None
    assert offer["raw_text"]
    assert isinstance(offer["phone_numbers"], list)
    assert isinstance(offer["emails"], list)
    assert canonical["license"] == {**LICENSE, "dataset_url": canonical["license"]["dataset_url"]}


def test_schema_change_is_blocked() -> None:
    raw = raw_payload()
    changed = copy.deepcopy(raw)
    changed["features"][0]["properties"]["unexpected_field"] = "value"

    with pytest.raises(WfsSyncError, match="schema changed"):
        validate_feature_collection(changed)


def test_diff_reports_changed_fields_without_raw_duplication() -> None:
    current = canonical_payload(raw_payload(), make_settings(ROOT, CANONICAL_PATH))
    previous = copy.deepcopy(current)
    previous["offers"][0]["address"] = "Old address"
    previous["source"]["content_hash"] = "old-hash"

    report = diff_canonical(previous, current)

    assert report["modified"]
    assert report["modified"][0]["changed_fields"] == ["address"]


def test_sync_promotes_atomically_and_then_detects_no_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = raw_payload()
    settings = make_settings(tmp_path, tmp_path / "data" / "canonical" / "offers.json")

    async def fake_fetch(_: Settings) -> dict:
        return copy.deepcopy(payload)

    monkeypatch.setattr("app.wfs_sync.fetch_wfs", fake_fetch)
    first = asyncio.run(sync_wfs(settings, promote=True))
    second = asyncio.run(sync_wfs(settings, promote=False))

    assert first.changed is True
    assert first.promoted is True
    assert second.changed is False
    assert settings.kb_path.is_file()
    assert load_knowledge_base(settings.kb_path).source_kind == "wfs"
