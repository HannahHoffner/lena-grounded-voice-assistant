# Execution Plan: Scharni marker and sleeping-bag routing

## Status

- State: Complete
- Owner: Codex
- Created: 2026-09-24
- Last updated: 2026-09-24

## Objective

Show Scharni at its current curated address on the map and route a request for
a sleeping bag to the curated Hilfebus supply/referral path instead of treating
it as a request for overnight accommodation.

## Acceptance contract

- [x] Scharni keeps the curated Georg-Schumann-Str. 268 address and receives a
  map marker backed by separately recorded coordinate provenance.
- [x] The obsolete WFS geometry for Scharnhorststr. 27 is never restored.
- [x] A sleeping-bag-only interpretation is `general_help` plus `clothing` and
  makes Hilfebus a mandatory referral; it does not open the sleep-place dialog.
- [x] An explicit combined request for accommodation and clothing remains a
  sleep request.
- [x] Hilfebus remains nonspatial outside its documented Sunday food/water stand.
- [x] Tests cover curation, mapping, interpreter contract, selector and API flow.

## Scope

### In scope

- Curated Scharni geometry and source metadata.
- Interpreter guidance and bounded correction of a contradictory
  `sleep + clothing-only` result.
- Focused data, unit, integration and documentation updates.

### Out of scope

- Re-geocoding other offers, changing the old WFS snapshot, adding a geocoder,
  changing models/timeouts, live-provider calls, or thesis edits.
- Treating the Hilfebus office address as a mobile service location.

## Repository review

### Current behavior

Scharni's current address is a curated override, while `geometry` is explicitly
set to `null` and `coordinates_status` is
`not_verified_after_address_change`. Tests therefore require no Scharni marker.
The old WFS geometry belongs to the former address and cannot be reused.

The interpreter offers `clothing` but does not mention sleeping bags. A model
can consequently classify the lexical stem “Schlaf” as `need=sleep`, which
activates the accommodation dialogue. Candidate selection already makes offer
21 (Hilfebus) a mandatory, nonspatial referral for
`need=general_help, explicit_service_requests=[clothing]`; its curated service
text explicitly includes blankets and sleeping bags.

### Relevant architecture and data flow

`BlabladorProvider.interpret_query` validates the structured interpreter result;
`QueryService._process_core` reconciles semantically conflicting fields before
`CandidateSelector.select`. Runtime offers are projected from the immutable WFS
record plus `app/resources/bootstrap/curation/social_offers.json` overrides.
`maps.build_map_data` accepts valid CRS84 point geometry and omits the mobile
Hilfebus office location by design.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Semantic field reconciliation | `app/service.py` | Extend next to toilet/service reconciliation |
| Curated runtime overrides/provenance | `app/curation.py`, curated JSON | Add geometry and open-geodata source type/status |
| Map projection | `app/maps.py` | Preserve; no parallel marker logic |
| General-help Hilfebus priority | `app/candidates.py` | Reuse unchanged |
| Existing test helpers | `tests/test_curation.py`, `tests/test_candidates.py`, `tests/test_api.py` | Extend |

### Existing tests and commands

- Baseline focused tests pass; current Scharni test asserts `geometry is None`.
- `python -m pytest tests/test_interpreter.py tests/test_candidates.py tests/test_curation.py tests/test_api.py -q`
- Full suite: `python -m pytest`

### Working tree considerations

The repository was clean at commit `326efd2` before the plan. Runtime live-run
reports are ignored and are not modified. The thesis repository remains out of
scope.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Restore old WFS point | It belongs to Scharnhorststr. 27 | Wrong destination | Use a new address-matched point with separate provenance | Assert current address, CRS84 point and changed coordinates |
| Put Hilfebus office on map | Mobile service has changing stands | Misleading destination | Preserve `uses_stand_location_instead_of_office` | Existing and new no-marker tests |
| Map every “sleep” token to accommodation | Sleeping bag is a material item | Wrong questions/offers | Contract example plus bounded field reconciliation | API test with deliberately contradictory provider output |
| Collapse mixed accommodation + clothing | User may need both | Loses intended function | Correct only clothing-only explicit service | Negative regression test |
| Add new sleeping-bag service/category | Existing clothing capability already represents it | Unnecessary schema paths | Reuse `clothing` and cite exact service evidence | Candidate/API assertions |

## Recommended approach

Store a CRS84 centroid derived from the OpenStreetMap building polygon for
Georg-Schumann-Straße 268 (way 206151027), record its source and retrieval date,
and identify its status as verified open geodata. Add a precise multilingual-
neutral contract rule: a sleeping bag is a clothing/basic-supply item, not an
overnight stay. Reconcile only the contradictory structured combination
`need=sleep` with non-empty explicit services consisting solely of `clothing`.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Runtime geocoding | Adds network dependency, nondeterminism and privacy/availability risk |
| Reuse old point | Proven wrong address |
| Hard-code Hilfebus response for one German phrase | Language-specific scenario patch outside existing interpretation contract |
| Add another LLM stage | Adds latency and complexity without need |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `app/resources/bootstrap/curation/social_offers.json` | Modify | Geometry, provenance, decision metadata | Medium; authoritative data |
| `app/curation.py` | Modify | Allow explicit open-geodata provenance/status | Low |
| `app/interpreter.py` | Modify | Clarify sleeping-bag classification; bump prompt version | Low |
| `app/service.py` | Modify | Bounded semantic reconciliation | Low |
| `app/resources/bootstrap/evaluation/live_scenarios.json` | Modify | Remove obsolete Scharni no-marker expectation | Low |
| `app/resources/bootstrap/i18n/dynamic_scenarios.json` | Modify | Update map expectation | Low |
| `tests/test_curation.py` | Modify | Geometry/provenance regression | Low |
| `tests/test_candidates.py` | Modify | Hilfebus and combined-request routing | Low |
| `tests/test_interpreter.py` | Modify | Prompt contract regression | Low |
| `tests/test_api.py` | Modify | End-to-end local routing and marker | Medium |
| Existing architecture/data-flow/testing docs | Modify if needed | Match resulting contract | Low |

## Milestones

### Milestone 1: Review and design

- [x] Inspect all applicable instructions.
- [x] Trace the real execution path.
- [x] Confirm reuse decisions.
- [x] Complete dead-end analysis.

Evidence: focused baseline tests passed; official operator and Leipzig sources
confirm the address, while OpenStreetMap way 206151027 supplies the matching
building polygon used only for its centroid.

### Milestone 2: Implementation

- [x] Implement bounded changes.
- [x] Keep source files cohesive and preferably below 400 lines.
- [x] Update this plan with discoveries.

### Milestone 3: Verification

- [x] Run targeted tests.
- [x] Run lint/format/type checks.
- [x] Run integration/build checks where relevant.
- [x] Verify registration, imports, routes, configuration, and packaging.
- [x] Review final diff.

### Milestone 4: Documentation

- [x] Invoke `code-documentation`.
- [x] Review documentation changes.
- [x] Rerun affected checks.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Focused behavior | Targeted interpreter/candidate/curation/API pytest | Scharni marker and Hilfebus routing pass |
| Regression | `python -m pytest` | Suite passes with only documented xfail/warning |
| Static quality | `python -m compileall -q app`; `python -m pip check`; `git diff --check` | Pass |
| Build/runtime | Packaging/startup tests in full suite | Pass |

## Rollback and recovery

All edits are versioned data/code/test/doc changes. No release, migration,
external mutation or deletion occurs. Reverting the coherent diff restores the
previous intentional no-marker behavior and interpreter contract.

## Progress log

- 2026-09-24 — Plan created after tracing curation, map, interpreter, service,
  candidate and API paths.
- 2026-09-24 — Added address-matched Scharni geometry with separate provenance,
  clarified the interpreter contract and added bounded service reconciliation.
- 2026-09-24 — Rebound only active machine translations to the changed curation
  context after proving their source-translation and operational-facts hashes
  were unchanged; both packaged and mutable stores validate identically.
- 2026-09-24 — Focused interpreter, candidate, curation, API and translation
  tests passed. Documentation was aligned with the resulting contract.
- 2026-09-24 — Full suite passed with 992 tests and one documented xfail;
  compileall, pip check, package build, provider-free health smoke and diff
  validation also passed.

## Decision log

- Decision: Use address-matched open geodata rather than the old WFS point.
  - Context: The current official pages confirm the address but expose no point.
  - Options: old point, runtime geocoder, curated open-geodata centroid.
  - Choice: curated centroid with explicit provenance.
  - Consequences: deterministic correct marker; one small provenance enum extension.

## Discoveries

- The Hilfebus already has `clothing`, a service description naming sleeping
  bags, mandatory general-help priority, and intentional nonspatial behavior.
- A broad initial JSON patch matched TiMMi's identical `geometry: null` field.
  Diff review caught this before final verification; TiMMi was restored to
  `null`, and the Scharni-specific test now guards the intended record.
- The translation store binds entries to the complete curation-catalog hash.
  This geometry-only change therefore required a metadata rebind even though
  every active translation and operational-facts hash remained unchanged.

## Final verification summary

The requested behavior is implemented without a new dependency, runtime
geocoder, extra LLM call or Hilfebus location. The complete provider-free suite
passes (`992 passed, 1 xfailed`), both distributions build, `/api/health`
returns `200 ok`, translations validate for all four non-German languages, and
the final diff contains no whitespace errors. No live provider or productive
source call was made and the thesis repository was not modified.
