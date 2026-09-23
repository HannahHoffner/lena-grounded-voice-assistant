# Execution Plan: Grounding review corrections

## Status

- State: Complete
- Owner: Codex
- Created / updated: 2026-09-23

## Objective and acceptance contract

Correct the locally reproduced false acceptances without restoring sentence-local
citation requirements. Keep general evidenced referral-service descriptions valid.
Reject contradictory age relations, changed service schedules, negated positive
service claims, and personal bed promises. An unrelated unknown-status clause must
not exempt a current service promise. Distinguish absence of lexical assessment
from positive evidence. Record content-free E2E stage errors per turn.

## Scope

Only grounding, conflicting formulation guidance, synthetic diagnostic reports,
regression tests and matching technical documentation. No thesis edits, live
calls, models, timeouts, dependencies, data changes, manual evaluation or cleanup.
This remains bounded lexical validation, not general natural-language entailment.

## Repository review

Clean maintenance/repository-cleanup at caa9532. Previous independently verified
baseline: 945 passed, 1 xfailed. QueryService uses formulation evidence, atomic
grounding, at most one corrective retry, then templates. Reuse existing fact
types, language vocabularies, service-condition projections and diagnostics.
Current checks lose age comparison direction and time order, do not compare
service weekdays, and treat no recognized concept as SUPPORTED. Unknown markers
exempt entire sentences. E2E reports retain only a technical boolean.
No applicable AGENTS files found. pyproject uses pytest/setuptools; no configured
lint/type checker. Packaging tests build/install and start without providers.

## Dead-end analysis and alternatives

| Risk / rejected approach | Mitigation / verification |
|---|---|
| Endless lexical additions pretend to prove arbitrary truth | Explicit NOT_CHECKED result and documented residual limits; reject unassessed service-only sentences |
| Scenario-specific rules | Domain constraints only; multilingual parameterized tests |
| Digit sets lose relations | Compare recognized age bounds and ordered schedule values |
| Conditions cited but hidden from reader | Require visible complete condition for personal receipt statements |
| Retry/fallback changed accidentally | Preserve service flow; run integration/full tests |
| Sensitive E2E diagnostics | Closed allowlist of existing stage error codes; no text or exception dumps |
| Large existing modules | Keep wiring local; extract cohesive relational checks into one bounded helper, no framework |

## File impact

| File | Change / risk |
|---|---|
| app/grounding_claims.py | Concept assessment and scoped promise rules; medium |
| app/grounding_constraints.py | Bounded age/schedule/polarity helpers; medium |
| app/grounding.py | Wire constraints into actual validation; medium |
| app/formulation.py | Resolve referral policy contradiction, accurate retry guidance; low |
| app/live_evaluation_runner.py | Closed per-turn stage diagnostics; low |
| tests/test_grounding*.py, tests/test_formulation.py | Regression and positive controls |
| tests/test_live_evaluation.py | Mocked diagnostic privacy/turn attribution |
| docs/architecture.md, docs/data-flow.md, docs/live-provider-evaluation.md | Actual guarantees, prompt version and limitations |

## Milestones and validation

- [x] Inspect repository, review execution path and prior counterexamples.
- [x] Persist plan before source edits.
- [x] Implement corrections and regression tests.
- [x] Run targeted pytest, then python -m pytest.
- [x] Run python -m compileall -q app, python -m pip check.
- [x] Verify wheel/install/provider-free startup through tests/test_packaging.py.
- [x] Review complete diff and git diff --check.
- [x] Apply code-documentation checklist to existing docs and update this plan.

## Rollback and recovery

Only local source/test/doc edits; no migrations or deletions. Review/reverse this
patch if necessary, preserving any subsequent user edits. No Git history changes.

## Decisions, discoveries and progress

- 2026-09-23: Review complete; user authorized corrections. Model/timeouts stay.
- Confirmed stale REFERRAL_WORDING policy contradicts prompt17's allowed service descriptions.
- Bounded checks cannot prove arbitrary wording true; do not claim comprehensive prevention.
- Implemented a separate NOT_CHECKED assessment instead of treating zero lexical
  matches as SUPPORTED. SERVICE sentences without an assessed service/target need
  a literal service value; ACTION/FACT paths retain their existing boundaries.
- Polarity is conservative: unassessed negative paraphrases fall back; complete
  cited negative facts can be quoted. General entailment remains out of scope.
- Unknown-status exemption now requires an exact cited note, not clause splitting.
- Existing generic SERVICE_ROLE_MISMATCH feedback also contradicted the new role
  contract; corrected alongside REFERRAL_WORDING and REFERRAL_ROLE_MISMATCH.
- Corrected pre-existing happy-path fixtures that promised a bed or hid a temporal
  condition. Retry tests now expect contradiction when an uncited authoritative
  minimum-age restriction disproves the target statement; rejection is preserved.
- Self-review added controls for multiple permitted genders and clock times such
  as "ab 17:00", which must not become age bounds.
- Visible service conditions remain answer-wide per offer too: a following
  sentence can state the day/time. Added an integration regression for this
  explicit user requirement; foreign offers still cannot supply the condition.
- First full intermediate run: 971 passed, 1 xfailed, one existing Starlette
  deprecation warning, 238.48 s. Later targeted regression runs also pass.
- No files/artifacts deleted. Removed only the now-unused ASSURANCE_MARKERS
  constant after checking references; bed promises no longer require its words.
- Size review: existing grounding/claims/runner modules already exceed 400 lines.
  A single small relational helper is warranted; broad decomposition of unrelated
  validation and evaluation workflows would increase this patch's risk.
- Complexity increases modestly in local deterministic checks; no provider stage,
  abstraction framework, new dependency, model switch or additional retry.
- Documentation skill applied to architecture, data-flow and evaluation docs;
  corrected guarantees, prompt18 attribution and content-free stage diagnostics.

## Final verification summary

| Check | Result |
|---|---|
| `python -m pytest tests/test_grounding_constraints.py tests/test_grounding_claims.py tests/test_formulation.py -q` | Passed; known lexical xfail retained |
| Focused suite including `tests/test_live_evaluation.py` | Passed after updating the now-more-specific contradiction diagnostic |
| Final `python -m pytest` | 976 passed, 1 xfailed, 1 warning; 250.19 seconds |
| `python -m compileall -q app` | Passed |
| `python -m pip check` | No broken requirements |
| Wheel/sdist build, resource inventory, installation, startup outside checkout | Passed as part of `tests/test_packaging.py` in the full suite |
| `git diff --check` and full diff self-review (including new files) | Passed; only expected task files |
| Thesis `git status --short` | Clean |
| Lint / type checker | Not configured; no new tooling added |
| Live / manual evaluation | Not performed |

Intermediate full runs: 971/974/975 passed, each with the same one expected
failure and Starlette deprecation warning. One later run was deliberately
interrupted while correcting the last stale retry sentence and then restarted;
the final complete run above includes every source change. Early targeted
failures identified legitimate existing bread-service wording, a changed
diagnostic priority and outdated target-diagnostic assertions; these were
corrected and rerun, not skipped. One targeted command from the parent directory
found no tests and was rerun from `code`.

The 31 additional passing tests versus baseline include five-language age,
schedule and polarity cases, actual-validator bypass counterexamples, positive
controls, answer-wide visible conditions and mocked per-turn diagnostic privacy.
Existing provider retry/fallback, API, safety and packaging tests remain active.
The known xfail is `minor injuries` being misread as an age-group concept; the
single warning is the existing Starlette/httpx deprecation.

Self-review: no unrelated edits, migrations, dependencies, external provider
calls, new provider stages, changed budgets, deleted files, commits or thesis
edits. Public response/evidence schemas stay at versions 2/4; guidance is
versioned as prompt18. Ten tracked files modified, three new task files.

Residual limits: lexical checks do not prove arbitrary claims true. Unknown
content attached to recognized concepts, misleading claim labels, unrecognized
grammar and conservative false rejections remain possible. Complete temporal
comparison is deliberately conservative when several unrelated times occur in
one offer's text. These limits are explicit in architecture documentation.

Readiness: the bounded corrections are locally verified and ready for a newly
authorized controlled diagnostic rerun, not a claim of final manual-evaluation
readiness. Live acceptance rates and latency improvement remain unmeasured.
Use the existing scenarios, privacy controls and failure caps with unchanged
Fast model, dataset and timeouts; review isolated and E2E results before sign-off.
