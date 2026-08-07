# Work package 8A: public toilets and shared spatial result ordering

## Scope and constraints

- Implement only the official Leipzig public-toilet source, its separately promoted releases, the runtime projection, deterministic toilet result ordering, shared Hauptbahnhof distance logic, food day/time/stand ordering, API/card/map/formulator integration, health output, and tests.
- Do not add drinking fountains, user geolocation, general district ranking, route calculation, final safety policy, production deployment, or live LLM/STT/TTS tests.
- Preserve all pre-existing worktree changes. Do not edit thesis or presentation files.
- Do not auto-promote fetched source data. A verified packaged bootstrap remains available at cold start.

## Review-first findings

- The official CSV resource was fetched read-only on 2026-08-02. It is UTF-8 with BOM, comma-delimited, and contains 21 unique records with the exact header `ID,Betreiber,Ort,Ortsteil,Oeffnungszeiten,Ausstattung,Entgelt,Servicenummer,lat,long,utm_east,utm_north`.
- The downloaded resource had SHA-256 `fce215d4e7bd928bd44963b0adb7e0b73f4e042d123e940dc96e8cdddc2b13f4`, content type `text/csv`, and size 4,737 bytes. Resource metadata names Stadt Leipzig as attribution and Datenlizenz Deutschland – Namensnennung – Version 2.0 as license.
- The dataset page does not spell out the CRS. All 21 UTM pairs transform as EPSG:25833 to the published latitude/longitude pairs with only rounding-level differences, so the normalizer will preserve both representations, validate the cross-check, and use the published geographic pair for runtime display/ranking.
- Current map distance and UTM conversion are private to `app/maps.py`; they must move to a single shared spatial module so social and infrastructure results cannot diverge.
- The current `KnowledgeBase`, API cards, map destinations, Evidence contract, and frontend assume social offers. Public toilets therefore require explicit record types and positive-list projections rather than conversion into social `OfferRecord` objects.
- Existing WFS release code is source-specific and uses private helpers. The toilet release remains operationally separate; only genuinely generic hashing/atomic-write helpers will be shared.
- The interpreter already exposes the `toilet` need and the formulator domain policy already names toilets. The current CandidateSelector treats that need as unsupported; a dedicated deterministic infrastructure branch must run before social candidate selection.
- Existing food stand handling is presentation-only and incomplete. Day/time eligibility and actual stand location must be resolved before distance ordering with an injectable Europe/Berlin clock.

## Source field mapping

| CSV field | Runtime field | Rule |
|---|---|---|
| `ID` | `source_id`, namespaced `id=toilet:<ID>` | required, trimmed, unique, stable |
| `Betreiber` | `operator_name` | required source text |
| `Ort` | `display_name` | required source text; not translated |
| `Ortsteil` | `district` | retained for display only; not used for general ranking/filtering in 8A |
| `Oeffnungszeiten` | `opening_hours_raw`, `availability_status` | exact source text; `geschlossen` is not eligible, `ganztägig` is source-proven only |
| `Ausstattung` | `facilities` | comma-separated source assertions with controlled normalized feature values |
| `Entgelt` | `fee_status`, `fee_cents`, `fee_raw` | `kostenfrei`→free/0; `50 Cent (...)`→paid/50; unknown text→unknown/null without guessing |
| `Servicenummer` | `service_phone` | `-`→null; otherwise exact source token |
| `lat` | `latitude` | required finite Leipzig-range geographic coordinate |
| `long` | `longitude` | required finite Leipzig-range geographic coordinate |
| `utm_east` | `source_easting` | required finite EPSG:25833 coordinate |
| `utm_north` | `source_northing` | required finite EPSG:25833 coordinate; pair cross-validated against lat/long |

Unknown additional CSV columns remain only in the immutable snapshot and do not
enter the Runtime-Positivliste. Missing required columns and duplicate IDs block
the import. Individual invalid coordinates remain with explicit status and raw
values but cannot be ranked or mapped; predominant geometry loss blocks release
creation.

## Implementation plan

- [x] Add schema-validated infrastructure/source/release/runtime models and shared atomic/hash helpers.
- [x] Add strict CSV fetch/validate/normalize/diff and a separate toilet release store with fetch, validate, diff, promote, rollback, and status CLI operations.
- [x] Package and verify a bootstrap release made from the reviewed official snapshot; keep automatic promotion disabled.
- [x] Extend Settings, runtime loading, health, and the KB fingerprint with independently versioned toilet source state without weakening the social curation boundary.
- [x] Move Hauptbahnhof, haversine, coordinate validation, and EPSG:25833 conversion into one shared spatial module and adapt social maps.
- [x] Implement deterministic toilet eligibility/ranking and shared food day/time/actual-stand ordering using an injectable Europe/Berlin clock.
- [x] Extend API cards, explicit spoken/card/marker result IDs, maps, formulator Evidence/grounding, localized templates/resources, and accessible frontend rendering for public toilets.
- [x] Add focused source/release/runtime/ranking/food/formulator/map/frontend/health/session tests and security regressions.
- [x] Run focused and full verification, package/sdist/clean-install checks, template smoke, syntax checks, and `git diff --check`.
- [x] Review the complete WP8A diff against this scope using the review-first template; update this plan with outcomes and remaining limits.

## Review outcome and remaining limits

- The official snapshot contains 21 unique records. All coordinate pairs are
  internally consistent; 20 records are `ganztägig` and rankable, one source
  record is `geschlossen` and remains provenance-only.
- The manifest now binds full source metadata, raw source hash, normalized
  content hash, validation status and every release file. Verification
  re-normalizes the snapshot and compares the complete positive-list result.
- The runtime fallback order is active release, last verified release, previous
  verified release, then packaged bootstrap. A fetch only stages a change.
- Current food stand-distance support is limited to already verified structured
  stand rules. A mobile record without a verified actual point gets neither
  office-distance ranking nor office marker; no missing stand is invented.
- General district ranking, routes, geolocation, drinking fountains and final
  safety policy remain outside 8A.
- JavaScript syntax checking was unavailable because Node.js is not installed;
  frontend contract, DOM-sink and packaging tests passed instead.
- During an early smoke attempt, repository `.env` configuration caused three
  unintended Blablador interpreter calls containing only synthetic toilet
  questions in German, English and Polish. No user/session/log data and no
  offer records were transmitted; all later verification used explicit
  template/test-double settings.

## Verification and stop conditions

- No real LLM, STT, or TTS call is permitted. Source-network access is limited to the official public CSV/metadata needed for the bootstrap and source tests use doubles.
- Promotion remains an explicit CLI action; fetch/diff never changes the active pointer.
- If source identity, mandatory columns, coordinate consistency, fee semantics, license/attribution, or packaged fallback cannot be validated, stop before activation and report the blocker.
- Completion requires that social exclusions 1–4 remain absent from all runtime/LLM paths and that a toilet source failure cannot erase or contaminate the social knowledge base.
