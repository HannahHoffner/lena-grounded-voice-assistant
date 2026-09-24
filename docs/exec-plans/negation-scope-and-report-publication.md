# Execution Plan: Negation scope and diagnostic report publication

## Status

- State: Complete (offline verification; live confirmation remains pending)
- Owner: Codex
- Created / updated: 2026-09-24

## Objective and acceptance contract

- Replay the captured Romanian counselling answer successfully without allowing
  negated services to be supported by positive facts (or the reverse).
- Treat a verbatim cited audience qualifier as audience information, not as
  negation of the service. Apply the same bounded rule across five languages.
- Investigate the unexpected live-run abort without new provider calls; preserve
  all original diagnostic artifacts and distinguish evidence from inference.
- Make report-publication failures explicit and tolerate only a strictly bounded
  transient Windows replacement failure, without repeating a provider call.
- Preserve prompt18, Fast, timeouts, budgets, atomic validation and fallback.

## Scope

Grounding polarity, evaluation report persistence/diagnostics, regression tests
and matching technical docs. No thesis edits, new dependencies, data edits,
commits, cleanup, manual evaluation or live calls.

## Repository review

Clean maintenance/repository-cleanup at 7335883. Baseline: 976 passed, 1 known
xfail. No applicable AGENTS files found. pytest/setuptools are configured;
no lint/type checker is configured. Skills review-first-coding and
code-documentation and both review templates read before implementation.

`grounding._validate_sentence` excludes a whole cited value whenever
`grounding_constraints.has_negation` finds any negative marker. The live
Romanian SERVICE fact says counselling for people without regular healthcare;
`fara` incorrectly removes that positive service evidence.

Live run `run_1a3636eeae18436591d07feb9d7322f6` also retains
`.stage-results.jsonl.fd61fb24eeb544258bd7ee56742b8bd6.tmp`. Its final row contains
the successfully validated `f_ro_injection` response. The published file contains
only the preceding 13 rows. `_atomic_write` writes the temporary file then calls
`os.replace`. This local evidence locates the failure in report publication, not
the LLM answer; the historical OS exception/locking process is not recorded.

Reuse `grounding_constraints`, existing citation pools and lexical vocabularies;
reuse EvaluationReportStore and runner exception boundaries. Existing
`release_storage.atomic_write` removes temporary files on failure and provides
no replacement retries: substituting it would lose diagnostic recovery evidence
and change unrelated release semantics. Keep the correction local to the report
store. Existing report/error allowlists and mocked runner tests remain in use.

## Dead ends and alternatives rejected

| Approach / risk | Decision and verification |
|---|---|
| Remove all negation checks or ignore `fara` globally | Rejected: without a service still negates that service |
| Special-case CABL / Romanian scenario | Rejected: cited audience-qualifier rule with five-language controls |
| Interpret arbitrary negation scope using more NLP layers | Rejected: bounded exact evidence matching; unsupported variants remain conservative |
| Assume OneDrive caused the historical failure | Not proven; report publication is localized, specific OS cause stays uncertain |
| Retry provider calls after report errors | Rejected: only repeat atomic file replacement, with a strict limit |
| Replace atomic writes with direct writes / delete old artifacts | Rejected: preserve atomicity and historical evidence |

## File impact

| File | Action / reason / risk |
|---|---|
| app/grounding_constraints.py | Modify scoped evidence-qualified service text; medium |
| app/grounding.py | Use the same scoped text for polarity and service concepts; medium |
| app/live_evaluation_runtime.py | Bounded replacement retry and closed write-error metadata; low |
| app/live_evaluation_runner.py | Classify report-write failures at existing boundaries; low |
| tests/test_grounding_constraints.py | Actual recorded answer replay and multilingual negative/positive controls |
| tests/test_live_evaluation.py | Mock transient/permanent replace errors and privacy, preserve call counts |
| docs/architecture.md, docs/live-provider-evaluation.md | Correct scope guarantees and failure diagnosis |

## Milestones and validation plan

- [x] Review code, artifacts, instructions and existing tests; persist plan.
- [x] Implement scoped correction and regression tests; retain module responsibilities.
- [x] Run targeted grounding/formulation/live-evaluation pytest suite.
- [x] Run full `python -m pytest` (includes package/install/provider-free startup).
- [x] Run `python -m compileall -q app`, `python -m pip check`, `git diff --check`.
- [x] Review complete diff, original-report hashes and thesis Git status.
- [x] Apply code-documentation checklist and record results here.

## Rollback and recovery

Local source/test/doc edits only; no migrations, deletions or history changes.
Original run files, including its unpublished temporary snapshot, remain intact.
New failed report snapshots remain recoverable; do not promote them silently or
rewrite historical summary metrics.

## Progress / decisions / discoveries

- 2026-09-24: historical temporary report reveals successful injection result;
  exact filesystem exception remains unknown. No new live run authorized here.
- Exact line comparison confirms all 13 published rows are the prefix of the
  14-row temporary snapshot; its extra `f_ro_injection` row is technically valid.
  SHA256 hashes of all five historical files match their pre-change values.
- Self-review retained the original negation vocabulary: adding generic
  `without`/`ohne` would create new false rejections for free services or
  appointment-free access. The correction only scopes cited audience phrases.
  Unmatched paraphrases still depend on the existing lexical coverage.
- Do not split audience qualifiers at conjunctions: a source about people
  without food and sleeping accommodation must not prove either offered service.
- Two new fault-injection tests initially used platform-default text decoding;
  corrected their reads to UTF-8. Current focused suite passes. A read-only
  Python artifact comparison failed on PowerShell argument quoting; the native
  PowerShell line comparison succeeded without changing any artifacts.
- Complexity increases slightly (one local text-scoping helper and one closed
  report-error class), with no new layer, dependency or provider stage. Existing
  large grounding/runner modules retain their responsibilities; splitting them
  as part of this defect correction would create unrelated restructuring.
- code-documentation updated the existing architecture and live-evaluation
  guides, checked affected symbols/paths, and documented bounded coverage,
  publication retries and persistence limits. No setup/configuration change.

## Final verification summary

| Command / check | Result |
|---|---|
| `python -m pytest tests/test_grounding_constraints.py tests/test_grounding_claims.py tests/test_formulation.py tests/test_live_evaluation.py -q` | Passed; known xfail retained |
| `python -m pytest` | 989 passed, 1 xfailed, 1 warning in 297.99 s; baseline 976 passed |
| Packaging tests within full suite | Wheel/sdist build, resource inventory, clean installation and provider-free startup outside checkout passed |
| `python -m compileall -q app` | Passed |
| `python -m pip check` | No broken requirements |
| `git diff --check` | Passed; Git only reports configured LF/CRLF conversion notices |
| Historical artifact SHA256 and prefix comparison | Unchanged; 13-row prefix matches temporary 14-row snapshot |
| `git -C ../thesis status --short` | Clean; thesis untouched |

No configured lint/type-check commands were added. The existing xfail covers
the lexical `minor injuries` target-group limitation; the warning is the
existing Starlette/httpx deprecation. Final review found only the scoped four
source files, two tests, two existing docs and this new plan changed. No files
were removed, no commits created and no live calls made.

Local regression evidence is not a successful live rerun or proof of complete
natural-language entailment. A separately authorized bounded rerun on the
committed version remains necessary before claiming the live gate passes.
