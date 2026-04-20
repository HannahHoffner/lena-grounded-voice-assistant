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
    )
    print(f"Published KB version {manifest.kb_version} with {manifest.page_count} pages.")


if __name__ == "__main__":
    asyncio.run(main())
