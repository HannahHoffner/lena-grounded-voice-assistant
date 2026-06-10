from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.config import load_settings
from app.maintenance import build_maintenance_report, ensure_maintenance_workspace, write_maintenance_report
from app.scraper.pipeline import run_pipeline


async def _run(mode: str, *, report_only: bool = False) -> None:
    settings = load_settings()
    ensure_maintenance_workspace(settings.maintenance_root)
    if not report_only:
        manifest = await run_pipeline(
            source_registry=settings.source_registry,
            output_root=settings.scraper_published_root,
            raw_root=settings.scraper_raw_root,
            reports_root=settings.scraper_reports_root,
            canonical_db_path=settings.canonical_kb_path,
            intake_root=settings.scraper_intake_root,
            build_qc_enabled=settings.build_qc_enabled and mode in {"full", "integrity"},
            build_qc_provider=settings.build_qc_provider,
            build_qc_model=settings.build_qc_model,
            build_qc_base_url=settings.build_qc_base_url,
            build_qc_api_key=settings.build_qc_api_key,
            geo_overrides_path=settings.geo_overrides_path,
            build_geocoding_enabled=settings.build_geocoding_enabled,
            build_geocoder_url=settings.build_geocoder_url,
        )
        print(
            f"[{mode}] KB version {manifest.kb_version} published with "
            f"{manifest.page_count} pages and {manifest.document_count} documents."
        )
    report = build_maintenance_report(
        source_registry_path=settings.source_registry,
        candidate_root=settings.scraper_published_root,
        maintenance_root=settings.maintenance_root,
    )
    artifacts = write_maintenance_report(report, settings.maintenance_reports_root)
    print(
        "[maintenance] "
        f"{report.review_needed_count} entries need review, "
        f"{report.stale_count} stale entries, "
        f"{report.active_override_count} active overrides."
    )
    print(f"[maintenance] HTML report: {artifacts['html']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scheduled KB maintenance for LENA.")
    parser.add_argument(
        "--mode",
        choices=("incremental", "full", "integrity"),
        default="incremental",
        help="Maintenance mode. Full and integrity runs enable the optional QC pass if configured.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip fetching and only generate a maintenance report from the latest scraper candidate dataset.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.mode, report_only=args.report_only))


if __name__ == "__main__":
    main()
