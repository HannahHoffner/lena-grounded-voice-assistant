# Question-aware Formulator

## Status and acceptance contract

Implemented and offline-verified, 2026-10-22. The Formulator remains the normal generator of natural,
question-specific answers grounded in selected offers. It receives the current
question on the drinking-water path as on the other offer paths. The prompt
explicitly prioritizes relevant, evidenced details over generic offer summaries.
Existing selection, fact checks, retries and technical fallbacks remain intact.

## Scope

Correct the drinking-water question handoff and clarify the existing prompt;
verify the provider handoff, grounding and fallback behavior. No template-first
redesign, new offer selection, validator relaxation, dataset changes or new
thesis measurements. Live answer quality must subsequently be measured; offline
tests cannot establish an improved E2E success rate.

## Repository review

`QueryService._formulate_or_fallback`, `_drinking_water_response` and the toilet
path use the existing evidence builders, `_call_formulator` and provider.
`build_drinking_water_evidence` alone replaces the question with an empty string;
the service already passes the real question. `BlabladorProvider.formulate_answer`
serializes the evidence into the model context. Facts and `current_query` are
separate fields; the question never establishes offer facts. Prompt 19 contains
many fact/format rules but no explicit overall question-answering priority.

Reuse `FormulatorEvidence`, existing service/provider interfaces and tests in
`tests/test_drinking_fountains.py` and `tests/test_formulation.py`. Code working
tree was clean at review; thesis changes from earlier work are outside scope.
No applicable AGENTS files were found. Existing large modules remain cohesive;
this bounded change does not warrant extracting unrelated responsibilities.

## Dead-end analysis and approach

| Risk / alternative | Evidence and mitigation | Verification |
|---|---|---|
| Templates replace normal formulation | Rejected: contradicts requested question-specific generation | Keep service routing unchanged |
| User question becomes evidence | Keep it in `current_query`, outside offer facts; retain grounding rules | Inspect evidence; reject invented facts and realtime claims |
| Better prompt alone guarantees quality | Rejected: model behavior needs live evaluation | Report offline evidence and measurement gap explicitly |
| Changing factual selection by district | Question context must not change deterministic ranking | Existing district-invariance tests |

## File impact

| File | Action / purpose | Risk |
|---|---|---|
| `app/formulation.py` | Preserve water question; prompt 20 clarifies answer priority | Limited model behavior change; validators unchanged |
| `tests/test_drinking_fountains.py` | Evidence and real service handoff regression | Low |
| `tests/test_formulation.py` | Update observable prompt version | Low |
| `docs/architecture.md` | Document actual prompt and question handoff | Low |

## Milestones and validation

- [x] Inspect instructions, implementation, caller, provider and existing tests.
- [x] Write review and plan before source edits.
- [x] Implement the bounded correction.
- [x] Run `python -m pytest tests/test_drinking_fountains.py tests/test_formulation.py tests/test_api.py tests/test_live_evaluation.py`.
- [x] Review diff, syntax/whitespace and documentation using code-documentation skill.

No dependency, public schema or packaging changes. Recover by reversing only this
task's diff; no data migration. Keep old measurements tied to their recorded
commit and prompt 19; do not relabel them as prompt-20 evidence.

## Decision and progress log

- 2026-10-22: Retain the Formulator and factual validation; correct missing context
  rather than bypass generation. Live quality remains an open verification item.
- 2026-10-22: The first regression run returned 301 passed, one known strict
  xfail and one failure in the new test fixture (provider not configured). Added
  synthetic provider settings and mocked transport; no external requests.
- 2026-10-22: Corrected integration test passed. Rechecked the entire drinking
  fountain module and observable prompt version: 42 passed in 16.84 seconds.
  The other three modules had already passed in the initial run (one known
  strict xfail). Existing Starlette deprecation warning remains.
- 2026-10-22: Applied code-documentation workflow to the final architecture diff;
  updated the existing documentation, with no public API/schema changes.

## Final verification summary

The real service -> evidence -> provider serialization -> response parsing ->
grounding -> QueryResponse path is exercised with mocked HTTP transport. The
question reaches the provider, a supported response is retained as `blablador`,
and no Formulator fallback is recorded. Existing invented-name and realtime-claim
rejections and district-invariance tests pass. AST parsing of all three changed
Python files and `git diff --check` pass.

Self-review against REVIEW_TEMPLATE: all changes map to the acceptance contract;
no new routes, duplicate implementations, dependencies, validator relaxation or
unrelated user-file changes. Existing large modules were not split for this
small correction. Documentation describes prompt instructions rather than
claiming measured model quality. The complete live evaluation has not been
rerun, and the previous thesis results still describe commit 3d0b80b / prompt 19.
At completion of the implementation turn these edits were uncommitted and did
not constitute a new evaluation baseline.

## Follow-up: authorized live evaluation

User requested testing on 2026-10-22. Run the four existing synthetic stages once
each with unchanged catalog limits, model, data and validators. First rerun the
four affected offline test modules on the final source, then commit the reviewed
Formulator change locally so every report identifies a clean software revision.
Store reports outside the repository; do not alter source files during a live
run. Negative gates remain negative; later stages are diagnostic runs rather
than evidence that the full gate chain passed. Compare terminal fallbacks,
recovered retries and actual content mismatches with 3d0b80b. No repeated runs
until success and no thesis result relabeling.

- [x] Final combined offline checks: 302 passed, one known strict xfail,
  one existing Starlette warning; 75.72 seconds. JUnit report saved externally.
- [ ] Clean local commit containing the reviewed change.
- [ ] Interpreter, selector/formulator, E2E and stability runs.
- [ ] Verify run identity and completeness; inspect generated answers/rejections.
- [ ] Write an external report with the comparison and limitations.

External run directory:
`C:/Users/User/AppData/Local/LENA/evaluations/20261022-formulator20-121834Z`.
Post-commit results are recorded there to keep the measured revision clean.
