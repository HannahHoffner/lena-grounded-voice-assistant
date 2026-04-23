from __future__ import annotations

import asyncio

from ..config import load_settings
from .pipeline import run_pipeline


async def main() -> None:
    settings = load_settings()
    manifest = await run_pipeline(
        source_registry=settings.source_registry,
        output_root=settings.scraper_published_root,
        raw_root=settings.scraper_raw_root,
        reports_root=settings.scraper_reports_root,
        canonical_db_path=settings.canonical_kb_path,
        intake_root=settings.scraper_intake_root,
        build_qc_enabled=settings.build_qc_enabled,
        build_qc_provider=settings.build_qc_provider,
        build_qc_model=settings.build_qc_model,
        build_qc_base_url=settings.build_qc_base_url,
        build_qc_api_key=settings.build_qc_api_key,
        geo_overrides_path=settings.geo_overrides_path,
        build_geocoding_enabled=settings.build_geocoding_enabled,
        build_geocoder_url=settings.build_geocoder_url,
    )
    print(f"Published KB version {manifest.kb_version} with {manifest.page_count} pages.")


if __name__ == "__main__":
    asyncio.run(main())
