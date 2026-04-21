from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.scraper.pipeline import promote_dataset, run_pipeline


def test_scraper_publishes_valid_dataset(tmp_path) -> None:
    source_html = tmp_path / "source.html"
    source_html.write_text(
        "<html><head><title>Sample Help</title></head><body><h1>Sample Help</h1><p>Food and shower support.</p></body></html>",
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "sample-help",
                    "title": "Sample Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "en",
                    "tags": ["food", "shower"],
                }
            ]
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "published"
    raw_root = tmp_path / "raw"
    reports_root = tmp_path / "reports"

    manifest = asyncio.run(
        run_pipeline(source_registry=source_registry, output_root=output_root, raw_root=raw_root, reports_root=reports_root)
    )

    assert manifest.page_count == 1
    assert (output_root / "index" / "manifest.json").exists()
    assert (output_root / "pages" / "sample-help.md").exists()
    page_markdown = (output_root / "pages" / "sample-help.md").read_text(encoding="utf-8")
    assert page_markdown.startswith("---\n")
    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    assert pages[0]["category"] == "general"
    assert pages[0]["description"]
    assert pages[0]["aliases"]
    assert pages[0]["service_type"] == "general"
    assert pages[0]["source_snapshot_path"]
    assert pages[0]["source_content_hash"]
    assert pages[0]["source_last_seen"]
    assert pages[0]["review_status"] in {"published", "needs_review"}
    aliases = json.loads((output_root / "index" / "aliases.json").read_text(encoding="utf-8"))
    assert "sample" in aliases
    report_files = list(reports_root.iterdir())
    assert report_files
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert report["changed_count"] == 1
    assert report["unchanged_count"] == 0


def test_promote_dataset_copies_workspace_to_runtime(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    runtime = tmp_path / "runtime"
    (workspace / "pages").mkdir(parents=True)
    (workspace / "index").mkdir(parents=True)
    (workspace / "pages" / "sample.md").write_text("# Sample", encoding="utf-8")
    manifest = {
        "kb_version": "test-version",
        "generated_at": "2026-04-19T12:00:00Z",
        "source_count": 1,
        "page_count": 1,
    }
    (workspace / "index" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (workspace / "index" / "pages.json").write_text("[]", encoding="utf-8")
    (workspace / "index" / "aliases.json").write_text("{}", encoding="utf-8")

    result = promote_dataset(workspace, runtime)

    assert result.kb_version == "test-version"
    assert (runtime / "pages" / "sample.md").exists()


def test_location_list_source_expands_into_atomic_pages(tmp_path) -> None:
    source_html = tmp_path / "tafel.html"
    source_html.write_text(
        """
        <html><body>
        <h1>Tafel Leipzig</h1>
        <p>Unsere Ausgabestellen</p>
        <p>Lindenau/ West</p>
        <p>Jordanstr. 5a, 04177 Leipzig</p>
        <p>An- oder Ummeldung: Mo-Fr 9:30 - 10:30 Uhr</p>
        <p>Lebensmittelausgabe: Mo-Fr 10:30 - 15:30 Uhr</p>
        <p>Telefon: 0163 88 68 226</p>
        <p>[.. Zur Ausgabestelle](https://tafel-leipzig.de/lindenau/)</p>
        <p>Markkleeberg</p>
        <p>Neue Strasse 2, 04416 Markkleeberg</p>
        <p>An- oder Ummeldung: Mi 10:00 - 11:00 Uhr</p>
        <p>Lebensmittelausgabe: Mi 11:00 - 13:30 Uhr</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "tafel-leipzig",
                    "title": "Tafel Leipzig",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "food",
                    "service_type": "food_distribution",
                    "tags": ["tafel", "lebensmittel", "essen", "ausgabestellen"],
                    "target_groups": ["food"],
                    "entity_mode": "location_list",
                }
            ]
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "published"
    manifest = asyncio.run(
        run_pipeline(source_registry=source_registry, output_root=output_root, raw_root=tmp_path / "raw", reports_root=tmp_path / "reports")
    )

    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    page_ids = {page["page_id"] for page in pages}
    assert manifest.page_count >= 3
    assert "tafel-leipzig" in page_ids
    assert "tafel-leipzig-lindenau-west" in page_ids
    assert "tafel-leipzig-markkleeberg" in page_ids

    parent = next(page for page in pages if page["page_id"] == "tafel-leipzig")
    assert parent["service_type"] == "service_catalog"
    assert parent["address"] is None
    assert parent["opening_hours"] == []
    assert parent["description"] == "Uebersichtsseite mit Ausgabestellen der Tafel Leipzig."

    lindenau = next(page for page in pages if page["page_id"] == "tafel-leipzig-lindenau-west")
    assert lindenau["address"] == "Jordanstr. 5a, 04177 Leipzig"
    assert lindenau["service_type"] == "food_distribution"
    assert lindenau["requires_registration"] is True
    assert lindenau["review_status"] == "published"


def test_source_specific_cleanups_fix_known_problem_records(tmp_path) -> None:
    oase_html = tmp_path / "oase.html"
    oase_html.write_text(
        """
        <html><body>
        <h1>Leipziger Oase</h1>
        <p>Die Leipziger Oase ist eine Tageseinrichtung fuer wohnungslose Menschen.</p>
        <p>Oeffnungszeiten</p>
        <p>Montag bis Freitag: 08:00 bis 16:00 Uhr</p>
        <p>Samstag (inkl. Feiertage) 09:00 bis 14:00 Uhr</p>
        <p>Kleiderkammer in der Nuernberger Strasse 37</p>
        <p>IBAN: DE28 3702 0500 0003 4650 50</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    cabl_html = tmp_path / "cabl.html"
    cabl_html.write_text(
        """
        <html><body>
        <h1>CABL Medizinische Sprechstunden fuer Wohnungslose</h1>
        <p>Medizinische Sprechstunden an mehreren Standorten.</p>
        <p>Tagestreff OASE, Nuernberger Strasse 31, 04103 Leipzig</p>
        <p>montags 15:00-16:00 Uhr</p>
        <p>Kontakt: 0341 246 766 55</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "leipziger-oase",
                    "title": "Leipziger Oase",
                    "url": oase_html.resolve().as_uri(),
                    "language": "de",
                    "category": "housing",
                    "publisher": "Diakonie Leipzig",
                    "tags": ["oase", "tageseinrichtung", "wohnungslos"],
                },
                {
                    "source_id": "cabl-uvo",
                    "title": "CABL Medizinische Sprechstunden fuer Wohnungslose",
                    "url": cabl_html.resolve().as_uri(),
                    "language": "de",
                    "category": "medical",
                    "publisher": "CABL e.V.",
                    "tags": ["medizin", "sprechstunde", "wohnungslosigkeit", "gesundheit"],
                },
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    asyncio.run(
        run_pipeline(source_registry=source_registry, output_root=output_root, raw_root=tmp_path / "raw", reports_root=tmp_path / "reports")
    )

    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    by_id = {page["page_id"]: page for page in pages}

    oase = by_id["leipziger-oase"]
    assert oase["service_type"] == "day_center"
    assert oase["address"] == "Nuernberger Strasse 31, 04103 Leipzig"
    assert oase["opening_hours"] == [
        "Montag bis Freitag 08:00 bis 16:00 Uhr",
        "Samstag und Feiertage 09:00 bis 14:00 Uhr",
    ]
    assert oase["phone"] == "0341 2682670"
    assert oase["target_groups"] == ["homeless"]

    cabl = by_id["cabl-uvo"]
    assert cabl["service_type"] == "medical_consultation"
    assert cabl["address"] is None
    assert cabl["opening_hours"] == []
    assert cabl["requires_registration"] is None
    assert "multi_location_service" in cabl["validation_issues"]
