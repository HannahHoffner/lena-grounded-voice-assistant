from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..models import SourceDefinition
from ..retrieval import normalize_text


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    seed_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    trust_tier INTEGER NOT NULL,
    allowed_domains_json TEXT NOT NULL,
    include_patterns_json TEXT NOT NULL,
    exclude_patterns_json TEXT NOT NULL,
    crawl_depth INTEGER NOT NULL,
    follow_pdf_links INTEGER NOT NULL,
    entity_expectation TEXT,
    schedule_class TEXT NOT NULL,
    priority INTEGER NOT NULL,
    publisher TEXT,
    language TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    mime_type TEXT,
    raw_hash TEXT NOT NULL,
    normalized_hash TEXT NOT NULL,
    etag TEXT,
    last_modified TEXT,
    fetched_at TEXT NOT NULL,
    http_status INTEGER,
    discovered_from TEXT,
    raw_path TEXT,
    content_excerpt TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_kind TEXT NOT NULL,
    canonical_title TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_entity_id TEXT,
    organization TEXT,
    district TEXT,
    source_id TEXT NOT NULL,
    entity_signature TEXT,
    merged_into TEXT,
    superseded_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id TEXT NOT NULL,
    alias_text TEXT NOT NULL,
    language TEXT,
    alias_type TEXT NOT NULL,
    normalized_form TEXT NOT NULL,
    PRIMARY KEY (entity_id, normalized_form),
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    normalized_value TEXT,
    display_value TEXT,
    source_document_id INTEGER NOT NULL,
    evidence_span TEXT,
    confidence REAL,
    extractor TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    supersedes_claim_id TEXT,
    conflict_group_id TEXT,
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY(source_document_id) REFERENCES documents(document_id)
);

CREATE TABLE IF NOT EXISTS entity_versions (
    entity_id TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, version_hash),
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    reason TEXT NOT NULL,
    decision TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS entity_geo (
    entity_id TEXT PRIMARY KEY,
    normalized_address TEXT,
    latitude REAL,
    longitude REAL,
    geo_status TEXT NOT NULL,
    geo_source TEXT,
    geo_confidence REAL,
    geo_precision TEXT,
    geo_matched_label TEXT,
    geo_matched_address TEXT,
    geocoded_at TEXT NOT NULL,
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);
"""


CLAIM_FIELDS: tuple[str, ...] = (
    "canonical_title",
    "title",
    "category",
    "service_type",
    "description",
    "summary",
    "address",
    "district",
    "opening_hours",
    "opening_hours_normalized",
    "target_groups",
    "eligibility",
    "gender_access",
    "appointment_required",
    "requires_registration",
    "languages",
    "phone",
    "email",
    "status",
    "source_url",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _claim_value(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, (list, dict)):
        rendered = _json_dumps(value)
        return rendered, rendered
    rendered = str(value)
    return normalize_text(rendered), rendered


class CanonicalStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self.connection.close()

    def upsert_source(self, source: SourceDefinition) -> None:
        self.connection.execute(
            """
            INSERT INTO sources (
                source_id, title, seed_url, source_type, trust_tier, allowed_domains_json,
                include_patterns_json, exclude_patterns_json, crawl_depth, follow_pdf_links,
                entity_expectation, schedule_class, priority, publisher, language, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                title=excluded.title,
                seed_url=excluded.seed_url,
                source_type=excluded.source_type,
                trust_tier=excluded.trust_tier,
                allowed_domains_json=excluded.allowed_domains_json,
                include_patterns_json=excluded.include_patterns_json,
                exclude_patterns_json=excluded.exclude_patterns_json,
                crawl_depth=excluded.crawl_depth,
                follow_pdf_links=excluded.follow_pdf_links,
                entity_expectation=excluded.entity_expectation,
                schedule_class=excluded.schedule_class,
                priority=excluded.priority,
                publisher=excluded.publisher,
                language=excluded.language,
                updated_at=excluded.updated_at
            """,
            (
                source.source_id,
                source.title,
                source.url,
                source.source_type,
                source.trust_tier,
                _json_dumps(source.allowed_domains),
                _json_dumps(source.include_patterns),
                _json_dumps(source.exclude_patterns),
                source.crawl_depth,
                int(source.follow_pdf_links),
                source.entity_expectation,
                source.schedule_class,
                source.priority,
                source.publisher,
                source.language,
                _now_iso(),
            ),
        )
        self.connection.commit()

    def insert_document(
        self,
        *,
        source_id: str,
        source_url: str,
        canonical_url: str,
        mime_type: str | None,
        raw_hash: str,
        normalized_hash: str,
        http_status: int | None,
        raw_path: str | None,
        content_excerpt: str,
        discovered_from: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO documents (
                source_id, source_url, canonical_url, mime_type, raw_hash, normalized_hash,
                etag, last_modified, fetched_at, http_status, discovered_from, raw_path, content_excerpt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                source_url,
                canonical_url,
                mime_type,
                raw_hash,
                normalized_hash,
                etag,
                last_modified,
                _now_iso(),
                http_status,
                discovered_from,
                raw_path,
                content_excerpt[:1000],
            ),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def upsert_entity(self, record: dict[str, Any], source: SourceDefinition) -> None:
        existing = self.connection.execute(
            "SELECT created_at FROM entities WHERE entity_id = ?",
            (record["page_id"],),
        ).fetchone()
        created_at = existing["created_at"] if existing else _now_iso()
        self.connection.execute(
            """
            INSERT INTO entities (
                entity_id, entity_kind, canonical_title, status, parent_entity_id, organization,
                district, source_id, entity_signature, merged_into, superseded_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                entity_kind=excluded.entity_kind,
                canonical_title=excluded.canonical_title,
                status=excluded.status,
                parent_entity_id=excluded.parent_entity_id,
                organization=excluded.organization,
                district=excluded.district,
                source_id=excluded.source_id,
                entity_signature=excluded.entity_signature,
                merged_into=excluded.merged_into,
                superseded_by=excluded.superseded_by,
                updated_at=excluded.updated_at
            """,
            (
                record["page_id"],
                record.get("entity_kind", "service_location"),
                record.get("canonical_title") or record["title"],
                record.get("status", "active"),
                record.get("parent_entity_id"),
                record.get("organization") or source.publisher,
                record.get("district"),
                source.source_id,
                record.get("entity_signature"),
                record.get("merged_into"),
                record.get("superseded_by"),
                created_at,
                _now_iso(),
            ),
        )
        self.connection.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (record["page_id"],))
        for alias in record.get("aliases", []):
            normalized = normalize_text(str(alias))
            if not normalized:
                continue
            self.connection.execute(
                """
                INSERT OR REPLACE INTO entity_aliases (entity_id, alias_text, language, alias_type, normalized_form)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record["page_id"], str(alias), record.get("language", source.language), "runtime", normalized),
            )
        self.connection.commit()

    def record_claims(self, record: dict[str, Any], document_id: int, extractor: str = "deterministic") -> None:
        observed_at = record.get("source_last_seen") or _now_iso()
        evidence_span = str(record.get("summary") or record.get("description") or "")[:500]
        for field_name in CLAIM_FIELDS:
            value = record.get(field_name)
            normalized_value, display_value = _claim_value(value)
            if display_value is None:
                continue
            claim_id = hashlib.sha256(
                f"{record['page_id']}|{field_name}|{document_id}|{display_value}".encode("utf-8")
            ).hexdigest()
            self.connection.execute(
                """
                INSERT OR REPLACE INTO claims (
                    claim_id, entity_id, field_name, normalized_value, display_value, source_document_id,
                    evidence_span, confidence, extractor, observed_at, supersedes_claim_id, conflict_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_id,
                    record["page_id"],
                    field_name,
                    normalized_value,
                    display_value,
                    document_id,
                    evidence_span,
                    record.get("confidence"),
                    extractor,
                    observed_at,
                    None,
                    None,
                ),
            )
        self.connection.commit()

    def record_entity_version(self, record: dict[str, Any]) -> None:
        payload_json = _json_dumps(record)
        version_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO entity_versions (entity_id, version_hash, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (record["page_id"], version_hash, payload_json, _now_iso()),
        )
        self.connection.commit()

    def record_review(self, record: dict[str, Any], reviewer: str = "pipeline") -> None:
        status = record.get("review_status", "published")
        reasons = record.get("validation_issues", [])
        self.connection.execute(
            """
            INSERT INTO reviews (entity_id, review_status, reviewer, reason, decision, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["page_id"],
                status,
                reviewer,
                ", ".join(reasons) if reasons else "auto_publish",
                "publish" if status == "published" else "manual_review",
                _now_iso(),
            ),
        )
        self.connection.commit()

    def get_entity_geo(self, entity_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT entity_id, normalized_address, latitude, longitude, geo_status, geo_source,
                   geo_confidence, geo_precision, geo_matched_label, geo_matched_address, geocoded_at
            FROM entity_geo
            WHERE entity_id = ?
            """,
            (entity_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def upsert_entity_geo(
        self,
        *,
        entity_id: str,
        normalized_address: str | None,
        latitude: float | None,
        longitude: float | None,
        geo_status: str,
        geo_source: str | None,
        geo_confidence: float | None,
        geo_precision: str | None,
        geo_matched_label: str | None,
        geo_matched_address: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO entity_geo (
                entity_id, normalized_address, latitude, longitude, geo_status, geo_source,
                geo_confidence, geo_precision, geo_matched_label, geo_matched_address, geocoded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                normalized_address=excluded.normalized_address,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                geo_status=excluded.geo_status,
                geo_source=excluded.geo_source,
                geo_confidence=excluded.geo_confidence,
                geo_precision=excluded.geo_precision,
                geo_matched_label=excluded.geo_matched_label,
                geo_matched_address=excluded.geo_matched_address,
                geocoded_at=excluded.geocoded_at
            """,
            (
                entity_id,
                normalized_address,
                latitude,
                longitude,
                geo_status,
                geo_source,
                geo_confidence,
                geo_precision,
                geo_matched_label,
                geo_matched_address,
                _now_iso(),
            ),
        )
        self.connection.commit()

    def mark_removed_entities(self, removed_entity_ids: list[str]) -> None:
        if not removed_entity_ids:
            return
        self.connection.executemany(
            "UPDATE entities SET status = 'removed', updated_at = ? WHERE entity_id = ?",
            [(_now_iso(), entity_id) for entity_id in removed_entity_ids],
        )
        self.connection.executemany(
            """
            INSERT INTO reviews (entity_id, review_status, reviewer, reason, decision, created_at)
            VALUES (?, 'needs_review', 'pipeline', 'removed_from_latest_snapshot', 'manual_review', ?)
            """,
            [(entity_id, _now_iso()) for entity_id in removed_entity_ids],
        )
        self.connection.commit()

    def latest_version_payload(self, entity_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT payload_json
            FROM entity_versions
            WHERE entity_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (entity_id,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])

    def document_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"]) if row else 0

    def entity_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM entities").fetchone()
        return int(row["count"]) if row else 0

    def backup_to(self, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target_path) as target_connection:
            self.connection.backup(target_connection)


def build_entity_signature(record: dict[str, Any]) -> str:
    signature_parts = [
        normalize_text(str(record.get("canonical_title") or record.get("title") or "")),
        normalize_text(str(record.get("address") or "")),
        normalize_text(str(record.get("phone") or "")),
        normalize_text(str(record.get("organization") or record.get("publisher") or "")),
    ]
    signature = "|".join(part for part in signature_parts if part)
    if not signature:
        signature = normalize_text(str(record.get("page_id") or ""))
    return signature


def detect_conflict_fields(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        signature = record.get("entity_signature") or build_entity_signature(record)
        grouped.setdefault(signature, []).append(record)

    conflicts: dict[str, list[str]] = {}
    comparable_fields = ("address", "phone", "email", "opening_hours", "requires_registration")
    for group in grouped.values():
        if len(group) < 2:
            continue
        for field_name in comparable_fields:
            values = {
                _json_dumps(record.get(field_name))
                for record in group
                if record.get(field_name) not in (None, "", [])
            }
            if len(values) < 2:
                continue
            for record in group:
                conflicts.setdefault(record["page_id"], []).append(field_name)
    return {key: sorted(set(value)) for key, value in conflicts.items()}


def copy_runtime_sqlite(canonical_db_path: Path, output_root: Path) -> Path:
    target_path = output_root / "index" / "runtime_snapshot.sqlite"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(canonical_db_path, target_path)
    return target_path
