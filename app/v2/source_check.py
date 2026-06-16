from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .kb import V2KnowledgeBase


DEFAULT_SOURCE_URL = "https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung"


@dataclass(frozen=True, slots=True)
class SourceCheckResult:
    checked_at: str
    source_url: str
    http_status: int
    title: str
    raw_sha256: str
    text_sha256: str
    raw_snapshot_path: str
    text_snapshot_path: str
    report_path: str
    kb_path: str
    offer_count: int
    missing_evidence: list[str]
    non_authoritative_offers: list[str]
    needs_manual_review: bool
    changed_from_recorded_source_hash: bool | None


def run_source_check(
    *,
    app_root: Path,
    kb_path: Path | None = None,
    source_url: str = DEFAULT_SOURCE_URL,
    output_root: Path | None = None,
    timeout_seconds: float = 30.0,
) -> SourceCheckResult:
    kb_path = kb_path or app_root / "data" / "v2" / "curated_kb" / "offers.json"
    output_root = output_root or app_root / "data" / "v2" / "source_checks"
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    response = httpx.get(source_url, timeout=timeout_seconds, follow_redirects=True)
    raw = response.text
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    title = _clean_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    text = _clean_text(soup.get_text("\n", strip=True))
    raw_hash = _sha256(raw)
    text_hash = _sha256(text)

    raw_snapshot = output_root / f"{stamp}-source.html"
    text_snapshot = output_root / f"{stamp}-source.txt"
    raw_snapshot.write_text(raw, encoding="utf-8")
    text_snapshot.write_text(text, encoding="utf-8")

    kb = V2KnowledgeBase(kb_path)
    missing_evidence = _missing_evidence(kb)
    non_authoritative = _non_authoritative(kb, source_url)
    changed_from_recorded = None
    if kb.v2_dataset.source_hash:
        changed_from_recorded = kb.v2_dataset.source_hash not in {raw_hash, text_hash}

    report = {
        "checked_at": stamp,
        "source_url": source_url,
        "http_status": response.status_code,
        "title": title,
        "raw_sha256": raw_hash,
        "text_sha256": text_hash,
        "kb_path": str(kb_path),
        "kb_version": kb.v2_dataset.version,
        "offer_count": len(kb.v2_dataset.offers),
        "missing_evidence": missing_evidence,
        "non_authoritative_offers": non_authoritative,
        "changed_from_recorded_source_hash": changed_from_recorded,
        "manual_review_required": True,
        "note": "Runtime KB is not updated by this check. Review snapshots and report before publishing changes.",
    }
    report_path = output_root / f"{stamp}-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    markdown_path = output_root / f"{stamp}-report.md"
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")

    result = SourceCheckResult(
        checked_at=stamp,
        source_url=source_url,
        http_status=response.status_code,
        title=title,
        raw_sha256=raw_hash,
        text_sha256=text_hash,
        raw_snapshot_path=str(raw_snapshot),
        text_snapshot_path=str(text_snapshot),
        report_path=str(report_path),
        kb_path=str(kb_path),
        offer_count=len(kb.v2_dataset.offers),
        missing_evidence=missing_evidence,
        non_authoritative_offers=non_authoritative,
        needs_manual_review=True,
        changed_from_recorded_source_hash=changed_from_recorded,
    )
    result_path = output_root / f"{stamp}-result.json"
    result_path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def _missing_evidence(kb: V2KnowledgeBase) -> list[str]:
    missing: list[str] = []
    for offer in kb.v2_dataset.offers:
        if not offer.source_evidence:
            missing.append(offer.offer_id)
            continue
        fields = {item.field_name for item in offer.source_evidence}
        required = {"name", "category", "short_description", "source_url"}
        if required - fields - set(offer.field_evidence):
            missing.append(offer.offer_id)
    return missing


def _non_authoritative(kb: V2KnowledgeBase, source_url: str) -> list[str]:
    result: list[str] = []
    for offer in kb.v2_dataset.offers:
        direct = {offer.source_url, *offer.detail_source_urls}
        if source_url not in direct:
            result.append(offer.offer_id)
    return result


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# LENA v2 Source Check",
        "",
        f"- Checked at: `{report['checked_at']}`",
        f"- Source: {report['source_url']}",
        f"- HTTP status: `{report['http_status']}`",
        f"- Raw SHA256: `{report['raw_sha256']}`",
        f"- Text SHA256: `{report['text_sha256']}`",
        f"- KB version: `{report['kb_version']}`",
        f"- Offer count: `{report['offer_count']}`",
        f"- Changed from recorded source hash: `{report['changed_from_recorded_source_hash']}`",
        f"- Missing evidence: `{len(report['missing_evidence'])}`",
        f"- Non-authoritative offers: `{len(report['non_authoritative_offers'])}`",
        "",
        "Manual review is required before any runtime KB update.",
        "",
    ]
    if report["missing_evidence"]:
        lines.extend(["## Missing Evidence", "", *[f"- `{item}`" for item in report["missing_evidence"]], ""])
    if report["non_authoritative_offers"]:
        lines.extend(["## Non-Authoritative Offers", "", *[f"- `{item}`" for item in report["non_authoritative_offers"]], ""])
    return "\n".join(lines)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_text(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in value.splitlines() if line.strip())).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the one-source LENA v2 KB against the Leipzig source page.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--kb-path", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser


def main() -> None:
    app_root = Path(__file__).resolve().parents[2]
    args = build_parser().parse_args()
    result = run_source_check(
        app_root=app_root,
        kb_path=args.kb_path,
        source_url=args.source_url,
        output_root=args.output_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
