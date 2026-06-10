from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.kb import KnowledgeBase
from app.maintenance import (
    ChangeProposal,
    FieldEvidence,
    ManualOverride,
    PromotionBlockedError,
    ServiceEntry,
    build_maintenance_report,
    validate_publishable_dataset,
    write_maintenance_report,
)
from app.models import Language
from app.retrieval import RetrievalEngine


def test_service_entry_requires_evidence_for_reviewed_sensitive_fields() -> None:
    with pytest.raises(ValidationError):
        ServiceEntry(
            service_id="ruecke",
            name="Ruecke",
            category="housing",
            service_type="overnight_shelter",
            description="Notunterkunft.",
            address="Rueckmarsdorfer Str. 5-7, 04179 Leipzig",
            review_status="reviewed",
        )

    entry = ServiceEntry(
        service_id="ruecke",
        name="Ruecke",
        category="housing",
        service_type="overnight_shelter",
        description="Notunterkunft.",
        address="Rueckmarsdorfer Str. 5-7, 04179 Leipzig",
        review_status="reviewed",
        field_evidence={
            "address": [
                FieldEvidence(
                    field_name="address",
                    source_url="https://example.test/ruecke.pdf",
                    evidence_text="Rueckmarsdorfer Str. 5-7, 04179 Leipzig",
                )
            ],
            "description": [
                FieldEvidence(
                    field_name="description",
                    source_url="https://example.test/ruecke.pdf",
                    evidence_text="Notunterkunft fuer wohnungslose Maenner.",
                )
            ],
            "category": [
                FieldEvidence(
                    field_name="category",
                    source_url="https://example.test/ruecke.pdf",
                    evidence_text="Notunterkunft",
                )
            ],
            "service_type": [
                FieldEvidence(
                    field_name="service_type",
                    source_url="https://example.test/ruecke.pdf",
                    evidence_text="Notunterkunft",
                )
            ],
        },
    )
    assert entry.review_status == "reviewed"


def test_change_proposal_requires_evidence_for_sensitive_fields() -> None:
    with pytest.raises(ValidationError):
        ChangeProposal(
            proposal_id="proposal-1",
            source_id="source-1",
            affected_service_ids=["service-1"],
            proposed_changes={"opening_hours": ["Montag 10:00 bis 12:00 Uhr"]},
        )

    proposal = ChangeProposal(
        proposal_id="proposal-1",
        source_id="source-1",
        affected_service_ids=["service-1"],
        proposed_changes={"opening_hours": ["Montag 10:00 bis 12:00 Uhr"]},
        evidence=[
            FieldEvidence(
                field_name="opening_hours",
                source_url="https://example.test/source",
                evidence_text="Montag 10:00 bis 12:00 Uhr",
            )
        ],
    )
    assert proposal.proposed_changes["opening_hours"]


def test_promotion_validation_blocks_unreviewed_or_untraceable_pages(tmp_path: Path) -> None:
    published = _write_dataset(
        tmp_path,
        [
            {
                "page_id": "needs-review",
                "title": "Needs Review",
                "review_status": "needs_review",
                "validation_issues": ["low_signal_description"],
            }
        ],
    )

    with pytest.raises(PromotionBlockedError) as exc_info:
        validate_publishable_dataset(published)

    assert "needs-review" in str(exc_info.value)
    assert "review_status=needs_review" in str(exc_info.value)


def test_maintenance_report_writes_json_html_and_csv(tmp_path: Path) -> None:
    candidate = _write_dataset(
        tmp_path / "candidate",
        [
            {
                "page_id": "service-1",
                "title": "Service 1",
                "category": "housing",
                "source_url": "https://example.test/service-1",
            }
        ],
    )
    sources = tmp_path / "sources.json"
    sources.write_text(
        json.dumps(
            [
                {
                    "source_id": "service-1",
                    "title": "Service 1",
                    "url": "https://example.test/service-1",
                    "language": "de",
                    "category": "housing",
                }
            ]
        ),
        encoding="utf-8",
    )

    report = build_maintenance_report(
        source_registry_path=sources,
        candidate_root=candidate,
        maintenance_root=tmp_path / "maintenance",
    )
    artifacts = write_maintenance_report(report, tmp_path / "maintenance" / "reports")

    assert report.source_count == 1
    assert report.page_count == 1
    assert Path(artifacts["json"]).exists()
    assert Path(artifacts["html"]).exists()
    assert Path(artifacts["csv"]).exists()


def test_active_manual_ranking_override_changes_retrieval_order(tmp_path: Path) -> None:
    published = _write_dataset(
        tmp_path / "published",
        [
            {"page_id": "shelter-a", "title": "Shelter A", "category": "housing"},
            {"page_id": "shelter-b", "title": "Shelter B", "category": "housing"},
        ],
    )
    overrides_path = tmp_path / "manual_overrides.json"
    overrides_path.write_text(
        json.dumps(
            [
                ManualOverride(
                    override_id="prefer-shelter-b",
                    target_type="service",
                    target_id="shelter-b",
                    type="ranking",
                    value={"priority_weight": 1.0},
                    reason="Staff prefer this intake path during the test.",
                    author="tester",
                    status="active",
                    reviewed_at=datetime.now(timezone.utc).isoformat(),
                    reviewer="tester",
                    public_visible=False,
                    priority_weight=1.0,
                ).model_dump(mode="json")
            ]
        ),
        encoding="utf-8",
    )

    kb = KnowledgeBase(published, overrides_path)
    results = RetrievalEngine(kb).retrieve("shelter", Language.EN, limit=2)

    assert results
    assert results[0].page_id == "shelter-b"


def _write_dataset(root: Path, pages: list[dict]) -> Path:
    published = root
    index = published / "index"
    pages_root = published / "pages"
    index.mkdir(parents=True, exist_ok=True)
    pages_root.mkdir(parents=True, exist_ok=True)
    records = []
    for raw in pages:
        page_id = raw["page_id"]
        record = {
            "page_id": page_id,
            "title": raw.get("title", page_id),
            "category": raw.get("category", "housing"),
            "service_type": raw.get("service_type", "overnight_shelter"),
            "language": raw.get("language", "de"),
            "source_url": raw.get("source_url", f"https://example.test/{page_id}"),
            "source_urls": [raw.get("source_url", f"https://example.test/{page_id}")],
            "source_document_refs": [f"raw/{page_id}.html"],
            "source_snapshot_path": f"raw/{page_id}.html",
            "source_content_hash": "hash",
            "source_last_seen": "2026-06-10T08:00:00+00:00",
            "last_updated": "2026-06-10",
            "publisher": "Test",
            "address": raw.get("address", "Teststrasse 1, 04109 Leipzig"),
            "opening_hours": raw.get("opening_hours", ["Montag 10:00 bis 12:00 Uhr"]),
            "description": raw.get("description", "Shelter support."),
            "target_groups": raw.get("target_groups", ["homeless"]),
            "gender_access": None,
            "walk_in": None,
            "requires_registration": None,
            "languages": [],
            "phone": None,
            "email": None,
            "tags": ["shelter", "housing"],
            "aliases": [page_id.replace("-", " "), "shelter"],
            "summary": raw.get("summary", "Shelter support."),
            "file_path": f"{page_id}.md",
            "review_status": raw.get("review_status", "published"),
            "validation_issues": raw.get("validation_issues", []),
        }
        records.append(record)
        (pages_root / f"{page_id}.md").write_text(
            f"---\ntitle: \"{record['title']}\"\n---\n# {record['title']}\n\nShelter support.\n",
            encoding="utf-8",
        )
    manifest = {
        "kb_version": "test",
        "generated_at": "2026-06-10T08:00:00Z",
        "source_count": len(records),
        "page_count": len(records),
    }
    (index / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (index / "pages.json").write_text(json.dumps(records), encoding="utf-8")
    (index / "aliases.json").write_text(json.dumps({"shelter": [item["page_id"] for item in records]}), encoding="utf-8")
    return published
