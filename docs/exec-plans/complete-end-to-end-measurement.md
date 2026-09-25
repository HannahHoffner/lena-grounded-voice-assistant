# Execution Plan: Complete the end-to-end measurement

## Status

- State: Reviewed
- Owner: Claude
- Created / updated: 2026-09-24

## Objective and acceptance contract

The end-to-end stage has never run to completion. Three attempts stopped after
8 to 12 of 27 scenarios, so the safety, injection, language-switch and
session-continuation flows have never been measured live at all. The stage
stops because `max_failures = 4` is consumed by ordinary technical rejections,
several of which the application recovered from.

Two findings drive this plan. First, the abort limit is **not** the gate
criterion: `contract_gate_passed` additionally requires `status == "completed"`
and all declared requests, so raising the stop can only make a run more
complete, never turn a failure into a pass. Second, the documentation states the
end-to-end stop is "4 kritische Fehler", but the implementation counts
`critical_content_error or not technically_valid`, so a safety-relevant error
and a routine rejection consume the same budget.

- [ ] Let the end-to-end stage measure all 27 scenarios under normal rejection
      rates.
- [ ] Stop immediately and distinguishably when safety-relevant critical content
      errors accumulate, at the documented threshold.
- [ ] Record the visible answer per turn so the recorded run supports the manual
      qualitative assessment.
- [ ] **Leave both gate criteria untouched.** Every rejection keeps counting; the
      gate still requires zero failures.
- [ ] Leave the application, validator, prompts, contracts, models, timeouts and
      curated data untouched.
- [ ] Keep the existing cost guards (provider calls, runtime) unchanged.
- [ ] Cover the separated critical stop and the recorded answers in tests.

## Scope

Coverage and reporting only. No application change, no gate change, no scenario
change, no provider-call or runtime budget change. This plan does not make any
gate pass; the end-to-end gate is expected to stay red.

## Repository review

Clean tree at `9b7f317`.

`AtomicRunCounter.record_failure` raises `EvaluationLimitReached` at
`limits.max_failures`. In `run_end_to_end_live_gate` it is called for
`result["critical_content_error"] or not result["technically_valid"]`, so both
kinds share one budget. `critical_content_errors` is already tracked as a local
in the same loop, so a separate stop needs no new counter state.

`contract_gate_passed` for the stage is `status == "completed" and
counts["requests"] == plan.request_count and counts["failures"] == 0`. Raising
`max_failures` therefore cannot produce a pass; it can only let `status` reach
`completed` and `requests` reach 34.

`_run_e2e_scenario` records `response_type` but not the visible answer. Stage two
already persists `structured_output.answer`, so recording answers here follows an
existing precedent rather than creating a new disclosure category. Inputs are
synthetic throughout.

Observed technical rejection rate across three partial runs: 4 of 12, 4 of 12 and
4 of 8 scenarios, roughly one third. Extrapolated to 27 scenarios that is about
nine rejections, above the current limit of four.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Reading this as gate relaxation | Would repeat the pattern the run plan warns about | Gate criterion untouched and asserted by test; a raised stop cannot create a pass |
| Weakening the safety stop | A raised general limit would delay stopping on critical errors | Separate immediate stop at the documented critical threshold |
| Removing the stop entirely | A systematically broken run would burn the full budget | Limit raised, not removed; provider-call and runtime guards unchanged |
| Guessing the new limit | An arbitrary value is not defensible | Derived from the observed rate, still below half the scenarios |
| Answers as a new disclosure category | Reports must stay bounded | Same content class stage two already stores; inputs are synthetic |

## Recommended approach / alternatives rejected

Raise the end-to-end `max_failures` from 4 to 14. That exceeds the extrapolated
nine rejections and still stops a run in which more than half the scenarios fail,
which would indicate a systematic problem rather than a measurable rate.

Add an immediate, separately named stop when `critical_content_errors` reaches
the documented threshold, so a safety-relevant accumulation still ends the run at
four and is distinguishable from the general limit in the report. Apply the same
separation to the stability stage at its documented threshold of three, without
changing its failure limit, because no stability run has been measured yet.

Record `answers` per scenario as a list of `{turn, text}` from the visible
`QueryResponse.answer`.

Rejected: removing the stop; lowering the gate; changing `technically_valid`;
raising the stability failure limit without evidence.

## File impact

| File | Action / purpose |
|---|---|
| app/live_evaluation_runner.py | Separate critical stop; record answers |
| app/resources/bootstrap/evaluation/live_scenarios.json | End-to-end `max_failures` 4 to 14 |
| tests/test_live_evaluation.py | Critical stop, raised limit, answers, gate unchanged |
| docs/live-provider-evaluation.md | Stop semantics and the new field |
| This plan | Review and evidence |

## Milestones

1. [x] Confirm the stop semantics, the gate criterion and the doc mismatch.
2. [ ] Implement and verify narrow changes incrementally.
3. [ ] Full local suite, compileall, pip check, complete diff review.
4. [ ] Re-run all stages; report the first complete end-to-end measurement.

## Validation plan

| Check | Command / expected result |
|---|---|
| Focused | python -m pytest tests/test_live_evaluation.py |
| Complete | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Live | interpreter, selector-formulator, end-to-end; end-to-end gate expected red but complete |

## Rollback and recovery

No migrations, no deletions. Roll back this patch alone if required; existing run
reports stay untouched.

## Progress / decision log

- Plan written before source edits, on a clean tree at `9b7f317`.
- The gate criterion stays untouched. The purpose is measurement coverage for the
  pending manual qualitative assessment, not a green gate.

## Discoveries and final verification summary

Pending implementation.
