# Execution plan: final technical quality gate

## Status and objective

Review completed, 2026-09-21. Owner: Codex. Establish evidence-based readiness for
manual evaluation against the supplied thesis matrix; correct demonstrated
defects locally without expanding the prototype. No manual evaluation, live
provider/source calls, thesis edits, Git history changes, or new dependencies.

## Acceptance contract

- Inspect executable paths, packaged data, configuration, tests and documentation.
- Preserve curated runtime authority, domain rules, public interfaces and unrelated files.
- Trace every supplied requirement to code and meaningful tests, recording uncertainty.
- Reset must not expose previous users' visible content or accept late callbacks.
- Repeat safe automated, static, distribution/install and startup checks after changes.
- Deliver a readiness report including remaining thesis corrections and exact evidence.

## Post-review decisions (2026-09-21)

The responsible user resolved the only domain-rule ambiguity without changing
the intended implementation:

- **1B:** Hilfebus may appear at any time as a telephone/referral contact. It
  shows the documented daily 18:00--23:00 times but never asserts current
  reachability.
- **2B:** Without an explicit time, strict Europe/Berlin current-time filtering
  applies to food and drinking-water service paths only. Other domain paths are
  governed by their documented rule, not a universal opening-hours filter.
- **3B:** Outside a verified stand window, the Hilfebus is a clearly non-spatial
  referral card, never a regular location/marker. Sunday 20:00--21:00 remains
  the verified food/water Hbf stand.
- **4A:** The responsible person confirms that the current data state may be
  used for evaluation. This is recorded as an owner decision, not an invented
  institutional approval.
- **5A -> 5B -> 5C:** prepare synthetic manual checks first, then a separately
  authorized live-provider run, then any real-input work only after its own
  privacy/operations authorization. This review will not make external calls
  or conduct manual evaluation.

Current code already implements 1B--3B. The only required behavioral work is a
regression test that proves the all-times referral boundary; documentation and
the external quality-gate report must replace the former "decision required"
wording. Do not alter thesis source.

## Repository review and baseline

Clean branch `maintenance/repository-cleanup`, HEAD `62773fe` on entry. Ignored
local environment, runtime data, caches and build artifacts exist and are retained.
FastAPI factory / CLI serve packaged static JavaScript; LENAService orchestrates
curated release-bound retrieval and optional configured provider clients. JSON
sessions and optional JSONL interaction logs live outside package resources.
The normal free-text path requires an interpreter; providerless startup remains
available but is not a functional normal-query mode.

Baseline: Python 3.14.3, 846 pytest tests passed in 248.69 s (one Starlette/httpx
deprecation warning); compileall and pip check passed. Node is absent from PATH;
existing Playwright-bundled Node 24.15.0 ran 9 frontend tests and both script syntax
checks successfully. Pytest includes wheel/sdist build, clean install and
outside-checkout TestClient startup. No lint/type tool is configured.

## Approach and existing structures

Reuse current frontend state and cancellation mechanisms, test VM transport/DOM
doubles, existing pytest fixtures and release validators. Inspect before each
additional correction. Keep backend business rules unless a defect is demonstrated.
Document descriptive thesis mismatches instead of changing sound code to match them.

| Risk / dead end | Evidence | Mitigation / verification |
| --- | --- | --- |
| Old requests restore a reset session | Query response has no lifecycle guard | Invalidate requests; test late success/failure and new request overlap |
| Microphone or STT outlives reset | Async recorder/recognition callbacks | Cancel explicitly and test deferred callbacks/grants |
| Overcorrecting thesis prose | Mixed historical/current claims | Consult only relevant original sections; report exact replacement |
| Hidden productive calls | Optional provider and sync clients | Disable env files/live smoke; use mocks and packaged data |
| Deleting research evidence | Historic plans and runtime artifacts | Retain unless proved obsolete; no cleanup quota |

## Alternatives rejected

No frontend framework, session redesign, new persistence layer, dependency, or
module-wide rewrite: lifecycle tokens and existing abort/cleanup functions suffice.
No broad refactoring of large domain modules during a final quality gate.

## File impact

| Path | Action / intent | Risk |
| --- | --- | --- |
| app/static/app.js | Focused lifecycle/reset and playback correction | Medium; async regression tests |
| tests/frontend.test.cjs | Extend existing real-script regression harness | Low |
| README.md, docs/*.md | Correct verified operational descriptions | Low |
| docs/exec-plans/final-technical-quality-gate.md | Persist review decisions and checks | Low |
| ../LENA_TECHNICAL_QUALITY_GATE.md | Final evidence, traceability and findings | Outside application repository |

## Milestones / validation

- [x] Establish clean baseline and read applicable skills.
- [x] Inspect implementation/data/test/documentation; assurance limits recorded in report.
- [x] Implement bounded, regression-tested corrections.
- [x] Trace every matrix entry; verify consequential ambiguities in thesis.
- [x] Repeat pytest, compileall, pip check, Node tests/syntax; inspect complete diff.
- [x] Final readiness/report and documentation consistency review.

Use `LENA_ENV_FILE_MODE=disabled`, `LENA_ALLOW_LIVE_SMOKE=false` for checks.
Do not run production sync/live evaluation scripts. Existing packaging tests verify
isolated installation and startup; no new checking tools will be installed.

## Recovery

No data migrations or deletions planned. Changes are ordinary reviewable patches;
reverse only this task's hunks if necessary, preserving local runtime and user data.

## Progress / discoveries

- 2026-09-21: baseline complete. Inactivity only forgets UUID; Start does not cancel
  query/recording, so a late response can repopulate the previous user's screen.
  Existing nine JavaScript tests do not exercise that boundary.
- Frontend lifecycle fix: 15 JavaScript tests pass. Idle reset clears visible
  content/audio; late query/STT/microphone callbacks cannot restore it.
- Mixed water map projection stripped the namespace from fountain IDs before
  ordering. A failing regression proves incorrect social-first regrouping;
  complete-ID lookup now precedes social stand-suffix lookup.
- Evaluation preview still declared 700/300/900 tokens although all provider
  calls use min(shared limit, 4096). Corrected preview, legacy timeout and disabled
  env-file handling, and added actual token limits to run manifests.
- Demonstrated evaluation defect requires one small evaluation-only adapter:
  E2E/stability previously incremented estimated counts after each query, never
  enforcing per-call limits or counting formulation retries. LimitedEvaluationProvider
  now reserves actual calls and bounds in-flight waiting by the run deadline;
  production QueryService is unchanged. Removed only the superseded private
  counting helper after confirming its two callers and tests. Technical failures
  no longer automatically receive a successful technical gate. This limited
  additional structure is necessary to enforce the existing evaluation contract.
- Targeted backend set passed 91 tests; expanded evaluation tests passed 49.
- Local read-only health: 28 social offers, 21 toilet records / 20 eligible,
  35 fountain source records / 21 eligible; all four stored translation languages
  have 28 machine entries, no integrity errors. No live availability was checked.

## Final verification

Baseline 846 passed / 1 warning / 248.69 s; final 860 passed / 1 warning /
239.37 s. Full suites include wheel/sdist/rebuild, clean installation and
outside-checkout startup. An intermediate full run passed 859 tests before the
additional earlier-turn evaluation-error regression. Final frontend: 17 passed
(baseline 9); both JavaScript syntax checks passed with existing bundled Node.
Compileall, 54 application-module imports, pip check and git diff --check passed.
No new tools/dependencies, productive provider calls, manual evaluation, file
deletions, thesis edits, commits or pushes.

Further corrections: Hilfebus audio excludes office address and uses actual
stand fields; toilet map/card/audio share localized operational fields; review
template maximum counts include possible formulation retry. Repository docs
and evaluation prerequisites now describe the verified behavior. Full changed
code/test/docs diff and new documents reviewed.

Report: ../LENA_TECHNICAL_QUALITY_GATE.md, including all 41 TC and five AMB
entries with exact original matrix locations. Decision: not ready for final
thesis-bound manual evaluation until the temporal-contract ambiguity is
resolved, catalogue-required data review is recorded, and the corrected
code/data/configuration baseline is frozen. Domain rules were preserved;
no institutional approval or provider availability was inferred.

## Post-review implementation plan

- [x] Reinspect CandidateSelector, Hilfebus fallback/map paths and existing
  tests before changing overlapping files.
- [x] Persist the authorized 1B/2B/3B/4A/5A->5B->5C contract in this plan.
- [ ] Add a deterministic regression for telephone referral outside 18:00--23:00
  and ensure that it is not a direct location service.
- [ ] Update existing manual-evaluation/testing documentation and the external
  report; retain thesis only as a correction recommendation.
- [ ] Run focused candidate/dialogue tests, then full safe pytest and final
  diff/self-review.

### Dead-end check

Changing Hilfebus to disappear outside 18:00--23:00 would contradict the
authorized 1B decision and remove the intended non-spatial referral fallback.
Applying a global opening-hours filter would contradict 2B and unnecessarily
change medical/general-help behavior. A new configuration switch would create a
second domain contract without a need; existing CandidateSelector and service
paths are canonical and are retained.
