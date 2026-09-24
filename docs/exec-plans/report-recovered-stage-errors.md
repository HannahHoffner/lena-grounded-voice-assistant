# Execution Plan: Report whether a stage error was recovered

## Status

- State: Implemented, re-run pending
- Owner: Claude
- Created / updated: 2026-09-24

## Objective and acceptance contract

The end-to-end report cannot distinguish two different outcomes that it records
identically. `QueryService._call_formulator` sets
`interaction.formulator_error_code` on the first rejected attempt and never
clears it, so a rejected first call followed by a successful retry looks exactly
like a rejected call that ended in the template fallback. The runner's own
comment already names this ("A recovered retry can still leave an error code");
the report simply does not carry the distinction.

- [x] Record per stage error whether the application still produced its regular
      answer or fell back.
- [x] Derive it from the existing interaction flags, not from new application
      state.
- [x] **Leave `technically_valid` and both gate criteria exactly as they are.**
      This plan measures; it does not change what counts as a failure.
- [x] Leave the application, validator, prompts, contracts, models, timeouts and
      curated data untouched.
- [x] Keep the report closed: booleans and known codes only, never free text.
- [x] Cover the recovered and the fallback case in tests.

## Scope

Measurement only. No gate change, no budget change, no scenario change, no
application change. Deciding whether the failure definition should change is a
separate decision, to be taken **after** this measurement exists, so that it can
rest on data rather than on the fact that the current definition blocks a stage.

## Repository review

Clean tree at `66706bd`.

`_run_e2e_scenario` iterates the turns, and for each of `interpreter`,
`selector`, `formulator` appends a `stage_errors` entry when
`interaction.<stage>_error_code` is set. `technically_valid` is the negation of
"any of the three codes is set".

`app/service.py` shows the discriminator already exists. On a recovered retry
`_formulate_or_fallback` returns early with `provider="blablador"` and
`formulator_fallback_used` untouched (`False`); only the final failure falls
through to `interaction.formulator_fallback_used = bool(...)` and returns
`provider="template"`. `selector_fallback_used` behaves analogously. The
interpreter has no retry and fails closed, so an interpreter error is never
recovered.

`QueryInteraction` therefore already carries `formulator_fallback_used`,
`selector_fallback_used` and `fallback_used`; `QueryResponse.provider` carries
`"blablador"` or `"template"`.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Silently changing the failure count | Would be a criterion change disguised as reporting | `technically_valid` untouched; asserted by test |
| Inferring recovery from the error code alone | The code stays set after recovery | Use the stage's fallback flag |
| Claiming interpreter recovery | The interpreter fails closed, it has no retry | Interpreter entries are never marked recovered |
| Free text in the report | Reports must stay closed and redacted | Booleans plus the existing closed provider value |
| Reading the new field as a gate result | Would confuse measurement with criterion | Documented explicitly in the evaluation doc |

## Recommended approach / alternatives rejected

Add two closed fields to each `stage_errors` entry: `fallback_used` (that
stage's flag) and `recovered` (error code set and that stage's fallback not
used). Add the turn's `answer_provider` from `QueryResponse.provider` so the
recovered case is independently visible.

Rejected: changing `technically_valid` now; adding a new interaction field to
`app/service.py`; deriving recovery from durations or call counts.

## File impact

| File | Action / purpose |
|---|---|
| app/live_evaluation_runner.py | Record `fallback_used`, `recovered`, `answer_provider` |
| tests/test_live_evaluation.py | Recovered and fallback case; `technically_valid` unchanged |
| docs/live-provider-evaluation.md | Explain the fields and that no criterion changed |
| This plan | Review and evidence |

## Milestones

1. [x] Confirm the discriminator exists and where.
2. [x] Implement and verify narrow changes incrementally.
3. [x] Full local suite, compileall, pip check, complete diff review.
4. [ ] Re-run end-to-end and report how many errors were recovered.

## Validation plan

| Check | Command / expected result |
|---|---|
| Focused | python -m pytest tests/test_live_evaluation.py |
| Complete | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Live | end-to-end on the new commit; gate expected to stay unpassed |

## Rollback and recovery

Reporting-only change; roll back this patch alone if required. Existing reports
stay untouched and simply lack the new fields.

## Progress / decision log

- Plan written before source edits, on a clean tree at `66706bd`.
- The gate criterion is deliberately untouched, so this run cannot pass a gate
  that the previous one failed.

## Discoveries and final verification summary

**Local result: 998 passed, 1 xfailed** (before: 995 + 1; three tests added, two
existing expectations extended). `compileall` and `pip check` clean.

Implementation note: `recovered` had to be tightened during implementation. The
first version derived it from the stage fallback flag alone, which produced
`recovered = true` together with `answer_provider = "template"` in an existing
test double. A stage that did not fall back but whose answer still came from the
template has recovered nothing, so `recovered` now also requires
`response.provider != "template"`.

`test_recovery_reporting_does_not_change_the_failure_criterion` pins the point
of this change: a recovered retry is reported as recovered and still counted as
a technical failure.
