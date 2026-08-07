# Work package 8A: provider isolation and release-fallback review

## Status

- State: Complete
- Owner: Codex
- Created: 2026-08-02
- Last updated: 2026-08-02

## Objective

Harden WP8A tests and local/template smokes against accidental external LLM,
STT, and TTS calls, require a three-part opt-in for the existing multilingual
live smoke, fail closed after invalid interpreter output, and ensure that a
toilet fallback can only use a fully verified release which was explicitly
activated for the configured source. WP8B remains out of scope.

## Acceptance contract

- [x] Pytest never reads checkout `.env` or `.env.local` accidentally and uses
  explicit test settings where runtime configuration matters.
- [x] In-process tests fail immediately on an unmocked non-loopback network
  connection, including LLM, STT, TTS and Edge TTS transports.
- [x] Packaging, clean-install and template smokes explicitly select the
  template/provider-free path.
- [x] The live-smoke command requires the named subcommand, `--confirm-live`,
  and `LENA_ALLOW_LIVE_SMOKE=true` before settings/provider initialization.
- [x] Invalid interpreter output produces a localized technical fallback with
  no selector, formulator, candidate cards, map markers or legacy retrieval.
- [x] Toilet interpreter contract fixtures cover DE/EN/PL/RO/RU, colloquial,
  district, free, accessible, correction and injection cases without weakening
  strict parsing.
- [x] Toilet runtime fallback accepts only manifest/hash-valid releases bound
  to the configured source and recorded by activation pointers; pending and
  arbitrary unactivated release directories are never candidates.
- [x] WP8A ordering, card limits, map breadth, fees, availability and district
  non-ranking remain unchanged.
- [x] No thesis/presentation file and no WP8B functionality is changed.
- [x] No external provider call occurs during implementation or verification.

## Scope

### In scope

- Settings/test isolation, transport-level test guard and provider-free smokes.
- Existing multilingual live-smoke authorization.
- Interpreter failure handling and redacted interpreter error observability.
- Toilet source-identity verification in the existing release path.
- Focused contracts, regressions, packaging verification and bounded docs.

### Out of scope

- Drinking fountains, geolocation, district ranking and routes.
- New deterministic query interpretation or relaxed model-output parsing.
- Final safety policy, deployment, real live smokes or provider compatibility
  experiments.
- Changes to thesis or presentation files.

## Repository review

### Current behavior

- `app.config.load_settings()` unconditionally reads checkout `.env` and then
  `.env.local`. A smoke using `create_app()` without explicit `Settings` can
  therefore inherit the locally configured Blablador credentials and model.
- `QueryService.__init__()` creates `BlabladorProvider` whenever those loaded
  values make `Settings.blablador_configured` true.
- The existing `app.multilingual_review live-smoke` gate requires the named
  command and `--confirm-live`, but not an independent environment opt-in; it
  calls `load_settings()` only after the flag check.
- Pytest has no central `conftest.py`. Most tests construct `Settings`
  explicitly, but some call `load_settings()` or `create_app()` directly. No
  suite-wide transport guard prevents an accidental external connection.
- Interpreter parsing is deliberately strict: pure JSON, exact Pydantic schema,
  forbidden internal IDs and redacted error codes. Raw model output is not
  persisted.
- On a normal-query `InterpreterError`, `QueryService` currently builds a
  lexical fallback interpretation. For a toilet phrase this reaches the
  deterministic infrastructure path and returns cards while skipping the same
  provider only at formulation time.
- Toilet loading considers only active, last-verified and previous-verified
  activation pointers, then the packaged bootstrap; it never enumerates release
  directories or pending releases. Every candidate is manifest/file/hash and
  snapshot-reproduction validated. The configured source URL is not yet checked
  when a pointer or packaged release is loaded.
- The three stored WP8A smoke interactions contain redacted route/fallback
  metadata only. They show `public_toilets`, fallback, and
  `formulator_skipped_provider`; neither raw output nor the interpreter error
  subclass was persisted, so the exact contract defect is not reconstructable.

### Relevant architecture and data flow

`create_app()` -> `load_settings()` when settings are omitted ->
`load_active_knowledge_base()` -> `QueryService()` -> optional
`BlabladorProvider` -> `interpret_query()` -> strict contract validation ->
candidate/infrastructure branch -> optional selector/formulator.

Toilet runtime loading is `load_toilet_runtime()` -> active pointer ->
last-verified pointer -> previous-verified pointer -> packaged pointer. Each
pointer binds a release ID and manifest hash; `verify_toilet_release_path()`
also verifies exact file inventory, sizes, hashes, raw-source hash, normalized
hash and reproducibility.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| Explicit immutable settings | `app/config.py::Settings` | Preserve for all unit/API tests |
| Existing live-smoke command | `app/multilingual_review.py` | Extend its single gate; no parallel CLI |
| Strict interpreter errors | `app/providers/llm.py::InterpreterError` | Preserve codes and parser strictness |
| Localized application texts | `app/resources/bootstrap/i18n/application_texts.json` | Add one versioned technical fallback key |
| Activation pointers | `app/toilet_releases.py::ToiletActivePointer` | Keep as sole local fallback allowlist |
| Release verifier | `app/toilet_releases.py::verify_toilet_release_path` | Add source-identity check at runtime boundary |
| Existing public-toilet tests | `tests/test_public_toilets.py` | Extend fixtures and failure/fallback cases |

### Existing tests and commands

- `tests/test_interpreter.py`, `tests/test_provider_timeouts.py`
- `tests/test_public_toilets.py`, `tests/test_result_ordering.py`
- `tests/test_packaging.py`, `tests/test_api.py`, `tests/test_observability.py`
- `python -m pytest -q`
- `python -m compileall -q app tests`
- `python -m build`
- `git diff --check`

### Working tree considerations

The branch is `maintenance/repository-cleanup` at
`9673668fbd2619dbec3ff57c5cdb0f69c400d6b0`. All uncommitted WP1-WP8A files
belong to the user and must be preserved. No reset, checkout, cleanup or branch
change is permitted.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Mock only `BlabladorProvider._post` | STT/TTS and future transports bypass it | External calls remain possible | Block non-loopback socket connections suite-wide | Deliberately attempt an HTTP transport and assert immediate failure |
| Detect pytest inside production code | Couples runtime behavior to a test runner | Normal startup could be disabled or bypassable | Put `.env` and network isolation in pytest configuration/fixtures | Regular explicit app settings still initialize provider in a unit test |
| Relax JSON parsing for real-model output | Three failures are not reconstructable | Weakens contract and can accept injected content | Keep strict parser; use schema-valid test doubles only | Existing and new negative parser tests |
| Lexical toilet recovery after invalid LLM output | Current service lines 511-530 | Unverified interpretation still selects records | Return technical fallback before all candidate paths | API test asserts no cards/map/selector/formulator |
| Scan release directories for “last good” | Directories include unactivated valid releases | Could activate unreviewed source silently | Only activation pointers and packaged pointer remain candidates | Fixture with arbitrary valid unactivated release is ignored |
| Compare only release hashes | Internally valid release may identify another URL | Cross-source fallback possible | Verify configured source identity as well as all existing hashes | Mismatched-source active/fallback tests |

## Recommended approach

Add one central pytest isolation fixture which suppresses checkout env-file
loading and rejects non-loopback sockets while leaving mocked transports and
local TestClient behavior intact. Make subprocess smokes explicitly sanitize
provider variables and choose template speech settings. Extend the existing
live-smoke preflight with the environment confirmation before `load_settings()`.
Fail closed on real interpreter errors, persist only the stable redacted error
code, and add a single localized technical fallback resource. Add source URL
identity validation to the existing pointer-based toilet loader without adding
a release registry or alternate knowledge base.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| Add another smoke command/module | Duplicates the established live-smoke safety path |
| Disable providers globally in `create_app()` | Would break deliberate regular runtime configuration |
| Rely only on `.invalid` test URLs | DNS/network can still be attempted and local `.env` can still leak |
| Use an arbitrary previous directory by timestamp | Not evidence of prior activation/review |
| Add toilet keywords as primary interpreter | Explicitly outside scope and weakens multilingual architecture |

## File impact

| File | Action | Reason | Expected size/risk |
|---|---|---|---|
| `tests/conftest.py` | Create | Central env/network isolation | Small, test-only |
| `app/multilingual_review.py` | Modify | Third live-smoke consent gate | Small |
| `app/service.py` | Modify | Fail closed after interpreter error | Small, active path |
| `app/models.py` | Modify | Redacted interpreter error trace field | Small schema change |
| `app/interactions.py` | Modify | Persist redacted interpreter error code | Small schema bump |
| `app/main.py` | Modify | Copy redacted field to interaction log | Small |
| `app/toilet_releases.py` | Modify | Enforce source identity for pointer fallbacks | Medium, release path |
| `app/resources/bootstrap/i18n/application_texts.json` | Modify | Five localized technical fallback strings | Data-only |
| `tests/test_provider_isolation.py` | Create | Env, transport, live-smoke gate tests | Medium |
| `tests/test_interpreter.py` | Modify | Five-language toilet contract fixtures | Medium |
| `tests/test_public_toilets.py` | Modify | Failure and safe release fallback cases | Medium |
| `tests/test_api.py` / `tests/test_observability.py` | Modify if needed | API/log regression | Small |
| `tests/test_packaging.py` | Modify | Explicit provider-free subprocess smoke | Small |
| `docs/setup.md`, `docs/testing.md` | Modify | Document gate and provider-free test boundary | Small |
| This plan | Update | Living evidence and final review | Small |

## Milestones

### Milestone 1: Review and design

- [x] Inspect applicable instructions and worktree.
- [x] Trace settings, provider creation, HTTP transport and live-smoke command.
- [x] Inspect redacted records from the three calls without reading raw prompts.
- [x] Trace toilet activation and fallback pointers.
- [x] Complete dead-end analysis and reuse decisions.

Evidence: repository review above; no source files changed before this plan.

### Milestone 2: Implementation

- [x] Add test/env/network and live-smoke guards.
- [x] Add fail-closed interpreter handling and redacted observability.
- [x] Enforce source identity in the existing toilet release chain.
- [x] Add focused contract and fallback tests.

Evidence: `tests/conftest.py`, `tests/test_provider_isolation.py`, five-language
interpreter fixtures and pointer/source fallback fixtures all pass.

### Milestone 3: Verification

- [x] Run focused settings/provider/network tests.
- [x] Run interpreter, toilet, map, ordering, API and observability regressions.
- [x] Run full suite, compileall, packaging, clean-install/template smoke and diff check.
- [x] Review the complete bounded diff against the review template.

Evidence: 560 tests pass; packaging module 7/7; explicit build succeeds;
compileall and `git diff --check` succeed; provider-free smoke returns three
cards and twenty markers.

### Milestone 4: Documentation

- [x] Apply the code-documentation checklist to existing setup/testing docs.
- [x] Review documentation accuracy and rerun affected checks.

Evidence: existing `docs/setup.md`, `docs/testing.md` and `docs/data-flow.md`
describe only implemented gates, failure behavior and fallback order; the full
suite passed after the documentation/resource update.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Isolation | `python -m pytest tests/test_provider_isolation.py -q` | `.env` ignored; external sockets blocked; regular explicit provider preserved |
| Interpreter | `python -m pytest tests/test_interpreter.py -q` | Strict multilingual toilet contract passes |
| Infrastructure | `python -m pytest tests/test_public_toilets.py tests/test_result_ordering.py -q` | WP8A and fallback guarantees pass |
| API/observability | `python -m pytest tests/test_api.py tests/test_observability.py -q` | Technical fallback and redacted code pass |
| Regression | `python -m pytest -q` | Entire suite passes without network |
| Static quality | `python -m compileall -q app tests`; `git diff --check` | No syntax or whitespace errors |
| Build/runtime | `python -m pytest tests/test_packaging.py -q`; `python -m build` | Wheel/sdist/rebuild/clean install and template smoke pass |

## Rollback and recovery

All changes are code/tests/resources and no migrations or provider writes are
performed. Recovery is limited to reverting only this plan's bounded hunks;
existing WP1-WP8A changes and runtime data must not be reset. Release tests use
temporary directories and never activate repository data.

## Progress log

- 2026-08-02 — Review completed; accidental-call chain, missing gates,
  fail-open interpreter fallback and source-identity gap confirmed.
- 2026-08-02 — Plan created before source modification.
- 2026-08-02 — Added session-wide pytest env/transport isolation and three-part
  live-smoke authorization.
- 2026-08-02 — Changed invalid interpreter responses to a localized fail-closed
  result and added redacted error-code persistence in interaction schema 9.
- 2026-08-02 — Bound all runtime toilet pointer fallbacks and the packaged
  bootstrap to the configured source identity.
- 2026-08-02 — Final focused, full, packaging, build, template-smoke and diff
  verification completed with zero external provider calls.

## Decision log

- Decision: Enforce network isolation in pytest rather than production startup.
  - Context: Tests need a hard transport boundary while deliberate runtime use
    must remain possible.
  - Choice: Test-only env suppression plus non-loopback socket rejection.
  - Consequences: Test doubles and local in-process HTTP remain usable; any
    forgotten external transport fails visibly.
- Decision: Exact cause of the three historical schema failures remains unknown.
  - Context: Only redacted interaction metadata exists; raw outputs were
    correctly not stored.
  - Choice: Do not infer JSON/schema details and do not reproduce live.
  - Consequences: Real model compatibility remains an explicit unresolved risk.

## Discoveries

- The three stored smoke rows prove provider failure and subsequent template
  formulation skip, but the then-current interaction schema has no interpreter
  error-code field.
- The local fallback chain is pointer-based already; the required hardening is
  source identity, not a new registry.
- A function-scoped network fixture would begin after session-scoped packaging
  fixtures. The implemented guard is therefore session-scoped and exports
  `LENA_ENV_FILE_MODE=disabled` to child processes as well.
- Application-copy version was advanced to 3 because the localized technical
  fallback is a new versioned resource; no language gained a human-review flag.

## Final verification summary

- Acceptance requirements: Satisfied within the bounded WP8A review scope.
- Tests: 560 passed; focused isolation/contract/fallback groups passed.
- Build: Wheel and sdist built; sdist-to-wheel and clean install passed in the
  seven packaging tests.
- Manual verification: Explicit template-only smoke passed; no live/provider
  test was run and the suite-wide transport guard observed no attempted call.
- Documentation: Code-documentation checklist completed against existing setup,
  testing and data-flow documents.
- Residual risks: The exact defect in each of the three historical Blablador
  outputs is not reconstructable because raw responses and the then-current
  interpreter code were correctly not persisted. Real model compatibility is
  not measurable without a separately authorized live run.
