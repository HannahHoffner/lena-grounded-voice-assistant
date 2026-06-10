from __future__ import annotations

import csv
import hashlib
import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from .models import PageMetadata


ReviewState = Literal["draft", "pending_review", "reviewed", "rejected", "published", "stale", "contradiction"]
ProposalState = Literal["draft", "pending_review", "accepted", "rejected", "superseded"]
OverrideType = Literal["ranking", "text", "warning", "temporary_closure", "intake_priority", "visibility"]
OverrideStatus = Literal["draft", "active", "expired", "rejected"]

SENSITIVE_FIELDS = {
    "address",
    "normalized_address",
    "latitude",
    "longitude",
    "opening_hours",
    "opening_hours_normalized",
    "phone",
    "email",
    "eligibility",
    "gender_access",
    "target_groups",
    "requires_registration",
    "appointment_required",
    "description",
    "service_type",
    "category",
    "status",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FieldEvidence(BaseModel):
    field_name: str
    source_id: str | None = None
    source_url: str
    snapshot_id: str | None = None
    snapshot_path: str | None = None
    evidence_text: str = Field(min_length=1)
    extracted_at: str = Field(default_factory=utc_now_iso)


class SourceSnapshot(BaseModel):
    snapshot_id: str
    source_id: str
    url: str
    fetched_at: str
    status_code: int | None = None
    final_url: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    raw_hash: str
    normalized_text_hash: str
    raw_snapshot_path: str
    extracted_text_path: str | None = None
    title: str | None = None
    source_type: str = "html"
    provenance: str = "scraper"


class ServiceEntry(BaseModel):
    service_id: str
    name: str
    organization: str | None = None
    category: str
    service_type: str
    description: str
    short_user_answer: str | None = None
    address: str | None = None
    coordinates: dict[str, float] | None = None
    opening_hours: list[str] = Field(default_factory=list)
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    target_groups: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    eligibility: str | None = None
    cost: str | None = None
    accessibility: str | None = None
    gender_specificity: str | None = None
    emergency_relevance: bool = False
    source_refs: list[str] = Field(default_factory=list)
    field_evidence: dict[str, list[FieldEvidence]] = Field(default_factory=dict)
    last_verified_at: str | None = None
    review_status: ReviewState = "draft"
    confidence: float | None = None
    public_notes: list[str] = Field(default_factory=list)
    internal_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sensitive_fields_need_evidence(self) -> "ServiceEntry":
        if self.review_status in {"published", "reviewed"}:
            for field_name in SENSITIVE_FIELDS:
                value = getattr(self, field_name, None)
                if value in (None, "", [], {}):
                    continue
                if field_name not in self.field_evidence:
                    raise ValueError(f"reviewed sensitive field lacks evidence: {field_name}")
        return self


class ManualOverride(BaseModel):
    override_id: str
    target_type: Literal["service", "category"]
    target_id: str
    type: OverrideType
    value: dict[str, Any] | str | int | float | bool
    reason: str = Field(min_length=1)
    author: str = Field(min_length=1)
    created_at: str = Field(default_factory=utc_now_iso)
    valid_from: str | None = None
    valid_until: str | None = None
    public_visible: bool = False
    priority_weight: float = 0.0
    status: OverrideStatus = "draft"
    reviewer: str | None = None
    reviewed_at: str | None = None

    def is_active(self, *, now: datetime | None = None) -> bool:
        if self.status != "active":
            return False
        current = now or datetime.now(UTC)
        if self.valid_from and _parse_datetime(self.valid_from) > current:
            return False
        if self.valid_until and _parse_datetime(self.valid_until) < current:
            return False
        return True


class ChangeProposal(BaseModel):
    proposal_id: str
    source_id: str
    source_snapshot_id: str | None = None
    affected_service_ids: list[str] = Field(default_factory=list)
    proposed_changes: dict[str, Any]
    diff: dict[str, Any] = Field(default_factory=dict)
    evidence: list[FieldEvidence] = Field(default_factory=list)
    llm_model: str | None = None
    prompt_hash: str | None = None
    source_snapshot_hash: str | None = None
    response_hash: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    status: ProposalState = "draft"
    reviewer: str | None = None
    review_notes: str | None = None

    @model_validator(mode="after")
    def _sensitive_changes_need_evidence(self) -> "ChangeProposal":
        changed_fields = set(self.proposed_changes)
        changed_fields.update(self.diff)
        evidence_fields = {item.field_name for item in self.evidence}
        missing = sorted((changed_fields & SENSITIVE_FIELDS) - evidence_fields)
        if missing:
            raise ValueError(f"sensitive proposal fields lack evidence: {', '.join(missing)}")
        return self


class KBRelease(BaseModel):
    release_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    included_entries: list[str] = Field(default_factory=list)
    included_overrides: list[str] = Field(default_factory=list)
    changelog: list[str] = Field(default_factory=list)
    reviewer: str
    validation_status: Literal["passed", "failed"]
    artifact_hashes: dict[str, str] = Field(default_factory=dict)


class SourceHealthItem(BaseModel):
    source_id: str
    title: str
    url: str
    status: Literal["ok", "changed", "failed", "stale", "needs_review", "unknown"]
    last_checked_at: str | None = None
    last_changed_at: str | None = None
    content_hash: str | None = None
    linked_page_ids: list[str] = Field(default_factory=list)
    review_needed: bool = False
    notes: list[str] = Field(default_factory=list)


class MaintenanceReport(BaseModel):
    generated_at: str = Field(default_factory=utc_now_iso)
    source_count: int
    page_count: int
    review_needed_count: int
    stale_count: int
    source_less_count: int
    active_override_count: int
    sources: list[SourceHealthItem]
    pages_needing_review: list[str] = Field(default_factory=list)
    stale_pages: list[str] = Field(default_factory=list)
    source_less_pages: list[str] = Field(default_factory=list)
    active_overrides: list[str] = Field(default_factory=list)
    category_counts: dict[str, int] = Field(default_factory=dict)


class PromotionBlockedError(RuntimeError):
    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("Published KB promotion blocked: " + "; ".join(issues))


def ensure_maintenance_workspace(root: Path) -> None:
    for relative in ("proposals", "curated", "review_logs", "releases", "reports", "snapshots"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    overrides_path = root / "manual_overrides.json"
    if not overrides_path.exists():
        overrides_path.write_text("[]\n", encoding="utf-8")


def load_manual_overrides(path: Path) -> list[ManualOverride]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    overrides: list[ManualOverride] = []
    for item in raw:
        try:
            overrides.append(ManualOverride.model_validate(item))
        except ValidationError:
            continue
    return overrides


def active_manual_overrides(path: Path, *, now: datetime | None = None) -> list[ManualOverride]:
    return [override for override in load_manual_overrides(path) if override.is_active(now=now)]


def validate_publishable_dataset(root: Path, *, allow_needs_review: bool = False) -> None:
    pages = _load_pages(root)
    issues: list[str] = []
    for page in pages:
        page_issues = _page_publish_issues(page, allow_needs_review=allow_needs_review)
        issues.extend(f"{page.page_id}: {issue}" for issue in page_issues)
    if issues:
        raise PromotionBlockedError(issues)


def _page_publish_issues(page: PageMetadata, *, allow_needs_review: bool) -> list[str]:
    issues: list[str] = []
    if page.review_status != "published" and not allow_needs_review:
        issues.append(f"review_status={page.review_status}")
    if page.status in {"removed", "deprecated", "merged"}:
        issues.append(f"status={page.status}")
    if page.status == "stale" or page.stale:
        issues.append("stale")
    if page.conflict_fields:
        issues.append("unresolved_conflicts=" + ",".join(page.conflict_fields))
    if not page.source_url and not page.source_urls:
        issues.append("missing_source_url")
    if not page.source_snapshot_path and not page.source_document_refs:
        issues.append("missing_source_snapshot")
    severe_validation = {
        "suspicious_address",
        "suspicious_opening_hours",
        "low_signal_description",
        "conflicting_claims",
        "imprint_address",
    }
    severe = sorted(severe_validation & set(page.validation_issues))
    if severe:
        issues.append("severe_validation=" + ",".join(severe))
    return issues


def build_maintenance_report(
    *,
    source_registry_path: Path,
    candidate_root: Path,
    maintenance_root: Path,
) -> MaintenanceReport:
    ensure_maintenance_workspace(maintenance_root)
    pages = _load_pages(candidate_root)
    sources = _load_source_registry(source_registry_path)
    overrides = active_manual_overrides(maintenance_root / "manual_overrides.json")
    pages_by_source: dict[str, list[PageMetadata]] = {}
    for page in pages:
        if page.source_url:
            pages_by_source.setdefault(page.source_url, []).append(page)
        for source_url in page.source_urls:
            pages_by_source.setdefault(source_url, []).append(page)

    source_items: list[SourceHealthItem] = []
    for source in sources:
        linked_pages = pages_by_source.get(str(source.get("url") or source.get("seed_url") or ""), [])
        page_ids = sorted({page.page_id for page in linked_pages})
        review_needed = any(_page_publish_issues(page, allow_needs_review=False) for page in linked_pages)
        source_items.append(
            SourceHealthItem(
                source_id=str(source.get("source_id") or ""),
                title=str(source.get("title") or source.get("source_id") or ""),
                url=str(source.get("url") or source.get("seed_url") or ""),
                status=_source_status(source, linked_pages, review_needed),
                last_checked_at=str(source.get("last_checked_at") or "") or _latest_source_seen(linked_pages),
                last_changed_at=str(source.get("last_changed_at") or "") or None,
                content_hash=str(source.get("current_hash") or "") or _latest_hash(linked_pages),
                linked_page_ids=page_ids,
                review_needed=review_needed,
                notes=[str(source.get("notes"))] if source.get("notes") else [],
            )
        )

    pages_needing_review = sorted(
        page.page_id for page in pages if _page_publish_issues(page, allow_needs_review=False)
    )
    stale_pages = sorted(page.page_id for page in pages if page.stale or page.status == "stale")
    source_less_pages = sorted(page.page_id for page in pages if not page.source_url and not page.source_urls)
    category_counts: dict[str, int] = {}
    for page in pages:
        category_counts[page.category] = category_counts.get(page.category, 0) + 1

    return MaintenanceReport(
        source_count=len(sources),
        page_count=len(pages),
        review_needed_count=len(pages_needing_review),
        stale_count=len(stale_pages),
        source_less_count=len(source_less_pages),
        active_override_count=len(overrides),
        sources=source_items,
        pages_needing_review=pages_needing_review,
        stale_pages=stale_pages,
        source_less_pages=source_less_pages,
        active_overrides=[override.override_id for override in overrides],
        category_counts=dict(sorted(category_counts.items())),
    )


def write_maintenance_report(report: MaintenanceReport, reports_root: Path) -> dict[str, str]:
    reports_root.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp_for_filename(report.generated_at)
    json_path = reports_root / f"maintenance-{stamp}.json"
    html_path = reports_root / f"maintenance-{stamp}.html"
    csv_path = reports_root / f"maintenance-{stamp}.csv"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    html_path.write_text(render_report_html(report), encoding="utf-8")
    write_report_csv(report, csv_path)
    return {
        "json": json_path.as_posix(),
        "html": html_path.as_posix(),
        "csv": csv_path.as_posix(),
    }


def render_report_html(report: MaintenanceReport) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item.source_id)}</td>"
        f"<td><a href=\"{html.escape(item.url)}\">{html.escape(item.title)}</a></td>"
        f"<td>{html.escape(item.status)}</td>"
        f"<td>{html.escape(item.last_checked_at or '')}</td>"
        f"<td>{html.escape(item.last_changed_at or '')}</td>"
        f"<td>{html.escape(', '.join(item.linked_page_ids))}</td>"
        f"<td>{'yes' if item.review_needed else 'no'}</td>"
        "</tr>"
        for item in report.sources
    )
    category_rows = "\n".join(
        f"<tr><td>{html.escape(category)}</td><td>{count}</td></tr>"
        for category, count in report.category_counts.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>LENA KB Maintenance Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #17202a; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #d7dee8; padding: .45rem .55rem; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    .summary {{ display: grid; grid-template-columns: repeat(5, minmax(8rem, 1fr)); gap: .75rem; }}
    .metric {{ border: 1px solid #d7dee8; padding: .75rem; }}
    .metric strong {{ display: block; font-size: 1.45rem; }}
  </style>
</head>
<body>
  <h1>LENA KB Maintenance Report</h1>
  <p>Generated: {html.escape(report.generated_at)}</p>
  <section class="summary">
    <div class="metric"><strong>{report.source_count}</strong>Sources</div>
    <div class="metric"><strong>{report.page_count}</strong>Entries</div>
    <div class="metric"><strong>{report.review_needed_count}</strong>Need review</div>
    <div class="metric"><strong>{report.stale_count}</strong>Stale</div>
    <div class="metric"><strong>{report.active_override_count}</strong>Active overrides</div>
  </section>
  <h2>Sources</h2>
  <table>
    <thead><tr><th>ID</th><th>Source</th><th>Status</th><th>Last checked</th><th>Last changed</th><th>Entries</th><th>Review</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <h2>Category Coverage</h2>
  <table>
    <thead><tr><th>Category</th><th>Entries</th></tr></thead>
    <tbody>{category_rows}</tbody>
  </table>
  <h2>Review Queue</h2>
  <p>{html.escape(', '.join(report.pages_needing_review) or 'No entries currently blocked by maintenance validation.')}</p>
</body>
</html>
"""


def write_report_csv(report: MaintenanceReport, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id",
                "title",
                "url",
                "status",
                "last_checked_at",
                "last_changed_at",
                "linked_page_ids",
                "review_needed",
                "notes",
            ],
        )
        writer.writeheader()
        for item in report.sources:
            writer.writerow(
                {
                    "source_id": item.source_id,
                    "title": item.title,
                    "url": item.url,
                    "status": item.status,
                    "last_checked_at": item.last_checked_at or "",
                    "last_changed_at": item.last_changed_at or "",
                    "linked_page_ids": ";".join(item.linked_page_ids),
                    "review_needed": "yes" if item.review_needed else "no",
                    "notes": "; ".join(item.notes),
                }
            )


def proposal_response_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _load_pages(root: Path) -> list[PageMetadata]:
    pages_path = root / "index" / "pages.json"
    entities_path = root / "index" / "entities.jsonl"
    if entities_path.exists():
        pages: list[PageMetadata] = []
        for line in entities_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                pages.append(PageMetadata.model_validate_json(line))
        if pages:
            return pages
    if not pages_path.exists():
        return []
    raw_pages = json.loads(pages_path.read_text(encoding="utf-8"))
    return [PageMetadata.model_validate(item) for item in raw_pages]


def _load_source_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _source_status(source: dict[str, Any], linked_pages: list[PageMetadata], review_needed: bool) -> Literal["ok", "changed", "failed", "stale", "needs_review", "unknown"]:
    raw_status = str(source.get("source_status") or "active")
    if raw_status in {"failed", "stale", "needs_review"}:
        return raw_status  # type: ignore[return-value]
    if review_needed:
        return "needs_review"
    if not linked_pages:
        return "unknown"
    if any(page.stale or page.status == "stale" for page in linked_pages):
        return "stale"
    return "ok"


def _latest_source_seen(pages: list[PageMetadata]) -> str | None:
    values = sorted(page.source_last_seen or page.last_verified or page.last_updated for page in pages if page.source_last_seen or page.last_verified or page.last_updated)
    return values[-1] if values else None


def _latest_hash(pages: list[PageMetadata]) -> str | None:
    values = sorted({page.source_content_hash for page in pages if page.source_content_hash})
    return values[-1] if values else None


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _timestamp_for_filename(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace(".", "").replace("+", "").replace("Z", "")[:15]
