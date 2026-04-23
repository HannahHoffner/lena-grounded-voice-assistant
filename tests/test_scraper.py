from __future__ import annotations

import asyncio
import json
import sqlite3

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
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=raw_root,
            reports_root=reports_root,
            canonical_db_path=tmp_path / "canonical" / "kb.sqlite3",
        )
    )

    assert manifest.page_count == 1
    assert (output_root / "index" / "manifest.json").exists()
    assert (output_root / "pages" / "sample-help.md").exists()
    assert (output_root / "index" / "entities.jsonl").exists()
    assert (output_root / "index" / "alias_index.json").exists()
    assert (output_root / "index" / "runtime_snapshot.sqlite").exists()
    assert (output_root / "index" / "field_indexes" / "aliases.json").exists()
    page_markdown = (output_root / "pages" / "sample-help.md").read_text(encoding="utf-8")
    assert page_markdown.startswith("---\n")
    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    assert pages[0]["category"] == "general"
    assert pages[0]["description"]
    assert pages[0]["aliases"]
    assert pages[0]["service_type"] == "general"
    assert pages[0]["entity_kind"] == "service_location"
    assert pages[0]["source_snapshot_path"]
    assert pages[0]["source_content_hash"]
    assert pages[0]["source_last_seen"]
    assert pages[0]["source_document_refs"]
    assert pages[0]["review_status"] in {"published", "needs_review"}
    assert pages[0]["normalized_address"] is None
    assert pages[0]["latitude"] is None
    assert pages[0]["longitude"] is None
    assert pages[0]["geo_status"] == "missing_address"
    aliases = json.loads((output_root / "index" / "aliases.json").read_text(encoding="utf-8"))
    assert "sample" in aliases
    report_files = list(reports_root.iterdir())
    assert report_files
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert report["changed_count"] == 1
    assert report["unchanged_count"] == 0


def test_scraper_applies_geo_overrides_and_persists_entity_geo(tmp_path) -> None:
    source_html = tmp_path / "oase.html"
    source_html.write_text(
        """
        <html><body>
        <h1>Leipziger Oase</h1>
        <p>Adresse</p>
        <p>Nuernberger Strasse 31, 04103 Leipzig</p>
        <p>Montag bis Freitag 08:00 bis 16:00 Uhr</p>
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
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "housing",
                    "publisher": "Diakonie Leipzig",
                    "tags": ["oase", "tageseinrichtung", "wohnungslos"],
                }
            ]
        ),
        encoding="utf-8",
    )
    geo_overrides = tmp_path / "geo_overrides.json"
    geo_overrides.write_text(
        json.dumps(
            {
                "by_entity_id": {
                    "leipziger-oase": {
                        "latitude": 51.3349456,
                        "longitude": 12.3840015,
                        "geo_status": "ready",
                        "geo_source": "manual",
                        "geo_confidence": 1.0,
                        "geo_precision": "exact",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    canonical_db = tmp_path / "canonical" / "kb.sqlite3"
    output_root = tmp_path / "published"
    asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=canonical_db,
            geo_overrides_path=geo_overrides,
        )
    )

    page = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))[0]
    assert page["latitude"] == 51.3349456
    assert page["longitude"] == 12.3840015
    assert page["geo_status"] == "ready"
    assert page["geo_source"] == "manual"
    assert page["geo_precision"] == "exact"

    with sqlite3.connect(canonical_db) as connection:
        row = connection.execute(
            "SELECT latitude, longitude, geo_status, geo_source FROM entity_geo WHERE entity_id = ?",
            ("leipziger-oase",),
        ).fetchone()
    assert row == (51.3349456, 12.3840015, "ready", "manual")


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
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
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
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
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


def test_source_registry_v2_seed_url_and_policy_fields_are_accepted(tmp_path) -> None:
    source_html = tmp_path / "source.html"
    source_html.write_text("<html><body><h1>Sample Help</h1><p>Food support.</p></body></html>", encoding="utf-8")
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "sample-help-v2",
                    "title": "Sample Help V2",
                    "seed_url": source_html.resolve().as_uri(),
                    "language": "en",
                    "source_type": "html",
                    "trust_tier": 1,
                    "allowed_domains": ["example.org"],
                    "include_patterns": ["help"],
                    "exclude_patterns": ["jobs"],
                    "crawl_depth": 1,
                    "follow_pdf_links": True,
                    "entity_expectation": "service_location",
                    "schedule_class": "daily",
                    "priority": 10,
                    "tags": ["food"],
                }
            ]
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "published"
    manifest = asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    assert manifest.page_count == 1
    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    assert pages[0]["source_trust_tier"] == 1


def test_crawl_depth_discovers_and_ingests_internal_child_pages(tmp_path) -> None:
    child_html = tmp_path / "child-help.html"
    child_html.write_text(
        "<html><body><h1>Child Help</h1><p>Adresse</p><p>Musterstrasse 10, 04109 Leipzig</p></body></html>",
        encoding="utf-8",
    )
    source_html = tmp_path / "source.html"
    source_html.write_text(
        f"""
        <html><body>
        <h1>Root Help</h1>
        <p>Overview page.</p>
        <a href="{child_html.resolve().as_uri()}">Weitere Hilfe</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "root-help",
                    "title": "Root Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "crawl_depth": 1,
                    "include_patterns": ["hilfe", "help"],
                    "tags": ["hilfe", "beratung"],
                }
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    manifest = asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    assert manifest.page_count >= 2
    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    titles = {page["title"] for page in pages}
    assert "Root Help" in titles
    assert "Child Help" in titles
    child_page = next(page for page in pages if page["title"] == "Child Help")
    assert child_page["source_url"] == child_html.resolve().as_uri()
    assert child_page["page_id"].startswith("root-help-crawl-1-child-help")

    report_files = list((tmp_path / "reports").iterdir())
    report = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert report["discovered_document_count"] >= 1


def test_domain_specific_discovery_filters_noise_and_deduplicates_urls(tmp_path) -> None:
    child_help = tmp_path / "help-service.html"
    child_help.write_text(
        "<html><body><h1>Beratungspunkt</h1><p>Musterstrasse 10, 04109 Leipzig</p><p>Montag 09:00-12:00 Uhr</p></body></html>",
        encoding="utf-8",
    )
    child_jobs = tmp_path / "jobs-service.html"
    child_jobs.write_text("<html><body><h1>Jobs</h1><p>Karriere</p></body></html>", encoding="utf-8")
    child_imprint = tmp_path / "impressum-hilfe.html"
    child_imprint.write_text("<html><body><h1>Impressum</h1></body></html>", encoding="utf-8")
    source_html = tmp_path / "source.html"
    source_html.write_text(
        f"""
        <html><body>
        <h1>Root Help</h1>
        <a href="{child_help.resolve().as_uri()}?utm_source=test#top">Service Hilfe</a>
        <a href="{child_help.resolve().as_uri()}#kontakt">Service Hilfe erneut</a>
        <a href="{child_jobs.resolve().as_uri()}">Service Jobs</a>
        <a href="{child_imprint.resolve().as_uri()}">Impressum Hilfe</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "root-help",
                    "title": "Root Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "crawl_depth": 1,
                    "include_patterns": ["hilfe", "service", "help"],
                    "exclude_patterns": ["jobs"],
                    "tags": ["hilfe", "beratung"],
                }
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    titles = {page["title"] for page in pages}
    assert "Beratungspunkt" in titles
    assert "Jobs" not in titles
    assert "Impressum" not in titles

    report = json.loads(next((tmp_path / "reports").iterdir()).read_text(encoding="utf-8"))
    assert report["discovered_document_urls"] == [child_help.resolve().as_uri()]


def test_discovered_contact_aggregation_page_is_ignored(tmp_path) -> None:
    contact_html = tmp_path / "beratung-kontakt.html"
    contact_html.write_text(
        """
        <html><body>
        <h1>Kontakt und Ansprechpartner</h1>
        <p>Telefon 0341 1111111</p>
        <p>Telefon 0341 2222222</p>
        <p>E-Mail kontakt@example.org</p>
        <p>E-Mail team@example.org</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_html = tmp_path / "source.html"
    source_html.write_text(
        f"""
        <html><body>
        <h1>Root Help</h1>
        <a href="{contact_html.resolve().as_uri()}">Kontakt Hilfe</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "root-help",
                    "title": "Root Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "crawl_depth": 1,
                    "include_patterns": ["kontakt", "hilfe"],
                    "tags": ["hilfe", "beratung"],
                }
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    manifest = asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    assert manifest.page_count == 1
    report = json.loads(next((tmp_path / "reports").iterdir()).read_text(encoding="utf-8"))
    decision = next(item for item in report["crawl_decisions"] if item["url"] == contact_html.resolve().as_uri())
    assert decision["policy"] == "ignore"
    assert "contact_aggregation" in decision["reasons"]


def test_discovery_skips_urls_already_registered_as_seed_sources(tmp_path) -> None:
    child_html = tmp_path / "child-help.html"
    child_html.write_text(
        "<html><body><h1>Child Help</h1><p>Musterstrasse 10, 04109 Leipzig</p></body></html>",
        encoding="utf-8",
    )
    source_html = tmp_path / "source.html"
    source_html.write_text(
        f"""
        <html><body>
        <h1>Root Help</h1>
        <a href="{child_html.resolve().as_uri()}">Weitere Hilfe</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "root-help",
                    "title": "Root Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "crawl_depth": 1,
                    "include_patterns": ["hilfe", "help"],
                    "tags": ["hilfe", "beratung"],
                },
                {
                    "source_id": "child-help-explicit",
                    "title": "Child Help",
                    "url": child_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "tags": ["hilfe"],
                },
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    manifest = asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    assert manifest.page_count == 2
    assert not any(page["page_id"].startswith("root-help-crawl-1-child-help") for page in pages)


def test_discovered_catalog_child_page_is_split_into_atomic_records_with_provenance(tmp_path) -> None:
    child_catalog = tmp_path / "angebote.html"
    child_catalog.write_text(
        """
        <html><body>
        <h1>Unsere Hilfen</h1>
        <h2>Standort Ost</h2>
        <p>Musterstrasse 10, 04109 Leipzig</p>
        <p>Montag 09:00-12:00 Uhr</p>
        <p>Telefon 0341 1234567</p>
        <h2>Standort West</h2>
        <p>Beispielweg 5, 04177 Leipzig</p>
        <p>Dienstag 10:00-14:00 Uhr</p>
        <p>Telefon 0341 7654321</p>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_html = tmp_path / "source.html"
    source_html.write_text(
        f"""
        <html><body>
        <h1>Root Help</h1>
        <a href="{child_catalog.resolve().as_uri()}">Unsere Angebote</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    source_registry = tmp_path / "sources.json"
    source_registry.write_text(
        json.dumps(
            [
                {
                    "source_id": "root-help",
                    "title": "Root Help",
                    "url": source_html.resolve().as_uri(),
                    "language": "de",
                    "category": "social",
                    "crawl_depth": 1,
                    "include_patterns": ["angebote", "hilfe", "standort"],
                    "tags": ["hilfe", "beratung"],
                }
            ]
        ),
        encoding="utf-8",
    )

    output_root = tmp_path / "published"
    asyncio.run(
        run_pipeline(
            source_registry=source_registry,
            output_root=output_root,
            raw_root=tmp_path / "raw",
            reports_root=tmp_path / "reports",
            canonical_db_path=tmp_path / "canonical.sqlite3",
        )
    )

    pages = json.loads((output_root / "index" / "pages.json").read_text(encoding="utf-8"))
    by_title = {page["title"]: page for page in pages}

    assert "Unsere Hilfen" in by_title
    assert by_title["Unsere Hilfen"]["service_type"] == "service_catalog"
    assert "Standort Ost" in by_title
    assert "Standort West" in by_title
    assert by_title["Standort Ost"]["address"] == "Musterstrasse 10, 04109 Leipzig"
    assert child_catalog.resolve().as_uri() in by_title["Standort Ost"]["source_urls"]
    assert source_html.resolve().as_uri() in by_title["Standort Ost"]["source_urls"]
    assert by_title["Standort Ost"]["source_document_refs"]
    assert "generic_catalog_split" in by_title["Standort Ost"]["validation_issues"]

    report = json.loads(next((tmp_path / "reports").iterdir()).read_text(encoding="utf-8"))
    decision = next(item for item in report["crawl_decisions"] if item["url"] == child_catalog.resolve().as_uri())
    assert decision["policy"] == "catalog"
