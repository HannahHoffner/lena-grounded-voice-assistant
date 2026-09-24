# Execution Plan: Stage two measures the application path, including its retry

## Status

- State: Implemented, re-run pending
- Owner: Claude
- Created / updated: 2026-09-24

## Objective and acceptance contract

The selector/formulator gate currently measures a behaviour no user ever
experiences. `_run_formulator_scenario` calls `provider.formulate_answer`
exactly once, while the application calls `QueryService._call_formulator` with
`FORMULATOR_MAX_ATTEMPTS = 2`: one bounded retry carrying the closed grounding
diagnosis as correction feedback. Both rejections measured on `429ab1b`
(`service_fact_missing`, `number_not_cited`) belong precisely to the class that
feedback addresses.

- [x] Stage two drives the same formulator path the application drives,
      including the single bounded retry and its closed diagnostic feedback.
- [x] Reuse the existing retry implementation; do not copy it into the runner,
      because a copy would diverge and would no longer measure the application.
- [x] Leave `app/service.py`, the validator, prompts, contracts, models,
      timeouts and curated data untouched.
- [x] Raise only the stage's formulator call budget from 10 to 20 and keep every
      declared budget internally consistent.
- [x] Keep the gate criterion itself unchanged: zero technical failures.
- [x] Record which measurement mode a run used, so results under the old and the
      new mode can never be silently compared.
- [x] Cover the changed budget, the retry path and the report field in tests.

## Scope

No application behaviour change, no prompt or contract version bump, no
validator change, no scenario catalogue change, no gate redefinition, no
end-to-end or stability change. This plan does not make the gate pass; it makes
the gate measure the right thing. The gate may still fail afterwards.

## Repository review

Clean tree at `429ab1b`. No applicable AGENTS files.

`run_selector_formulator_live_gate` builds only
`LimitedEvaluationProvider(provider_factory(settings), counter)` and hands it to
`_run_formulator_scenario`, which awaits `provider.formulate_answer` directly.

`_build_isolated_service(settings, scratch_dir, provider_factory, counter)`
already exists for the end-to-end stage. It creates a `QueryService` on an
isolated runtime root and assigns the counted provider to `service.blablador`,
returning both. Stage two can reuse it unchanged, which keeps `app/service.py`
untouched and guarantees the measured path is the application path.

`QueryService._call_formulator(formulator_method, *, evidence, budget,
interaction)` holds the retry. It needs an `LLMRequestBudget(total_seconds,
clock)` and a `QueryInteraction`; both are constructible in the runner.
`settings.llm_request_budget_seconds` defaults to 45.0.

The stage declaration in `app/resources/bootstrap/evaluation/live_scenarios.json`
carries `minimum_calls.formulator = 10`, `maximum_calls.formulator = 10`,
`live_limits.max_provider_calls = 16` and `max_formulator_calls = 10`.
`LiveScenarioCatalog` validates `live_limits.max_provider_calls ==
maximum_calls.total` and `minimum_calls <= maximum_calls` per component, so the
totals must move together. The catalogue also requires exactly six selector and
ten formulator scenarios; that stays.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Copying the retry into the runner | Would drift from the application and measure a replica | Reuse `_build_isolated_service` and `_call_formulator` |
| Touching `app/service.py` | The application is deliberately frozen | The existing helper makes any change there unnecessary |
| Raising only one budget field | `LiveScenarioCatalog` refuses an inconsistent stage | Move `maximum_calls`, `max_provider_calls` and `max_formulator_calls` together |
| Silently comparing old and new runs | Two different measurement modes would look alike | Record the mode in the manifest and report it |
| Treating this as a way to pass | Would be gate shopping | Gate criterion unchanged; the run may still fail |
| Session writes into the real runtime | Evaluation must not touch app state | `_build_isolated_service` already isolates the runtime root |

## Recommended approach / alternatives rejected

Build the isolated service once per stage-two run with the existing helper. Pass
it into `_run_formulator_scenario` and await
`service._call_formulator(service.blablador.formulate_answer, evidence=evidence,
budget=LLMRequestBudget(settings.llm_request_budget_seconds, clock),
interaction=QueryInteraction())`. A fresh budget per scenario keeps scenarios
independent, matching one user request.

Raise `maximum_calls.formulator` to 20, `live_limits.max_provider_calls` to 26
and `max_formulator_calls` to 20. `minimum_calls.formulator` stays 10: a run in
which no scenario needs a retry is the good case, not a violation. Raise
`maximum_provider_wait_seconds` and `max_total_runtime_seconds` to cover the
added calls.

Add a manifest field naming the measurement mode so no report can be mistaken
for the other mode.

Rejected: extracting the retry into a shared helper in `app/service.py`
(unnecessary, and touches the frozen application); reimplementing the retry in
the runner; relaxing the gate to tolerate one rejection; tuning prompt 18
against the observed scenarios.

## File impact

| File | Action / purpose |
|---|---|
| app/live_evaluation_runner.py | Stage two uses the isolated service and the retry path |
| app/live_evaluation_plan.py | Manifest records the measurement mode |
| app/resources/bootstrap/evaluation/live_scenarios.json | Formulator budget 10 to 20 and dependent totals |
| tests/test_live_evaluation.py | Budget consistency, retry path, manifest field |
| docs/live-provider-evaluation.md | Document the changed measurement and its consequence |
| This plan | Review and evidence |

## Milestones

1. [x] Inspect the runner, the existing helper, the retry and the stage budget.
2. [x] Implement and verify narrow changes incrementally.
3. [x] Full local suite, compileall, pip check, complete diff review.
4. [ ] Re-run all three stages on the new commit and record the results.

## Validation plan

| Check | Command / expected result |
|---|---|
| Focused | python -m pytest tests/test_live_evaluation.py |
| Complete | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Providerless plan | python -m app.multilingual_review live-dry-run --stage selector-formulator |
| Live | interpreter, then selector-formulator, on the new commit |

## Rollback and recovery

No migrations, no deletions. Roll back this patch alone if required; existing run
reports stay untouched and keep their original measurement mode.

## Progress / decision log

- Plan written before source edits, on a clean tree at `429ab1b`.
- The commit changes with this patch, so the evaluation object moves again and
  every stage must be re-run, the interpreter included.
- The gate criterion is deliberately not touched.

## Discoveries and final verification summary

**Local result: 995 passed, 1 xfailed** (before: 993 collected; three tests
added). `compileall` clean, `pip check` clean, provider-free dry run confirms the
raised budget.

Implementation notes:

- `_build_isolated_service` was reusable unchanged, so `app/service.py` was not
  touched at all. The measured retry is literally the application's.
- Stage two had no scratch directory of its own; it now creates one like the
  later stages and releases it in a `finally`, so evaluation sessions never
  reach the application runtime root.
- `test_selector_formulator_runner_persists_redacted_grounding_diagnostics`
  keeps passing unchanged: a provider that always fails now consumes two calls
  per scenario, which the raised budget covers, and still reaches the failure
  limit after three scenarios.

The gate criterion was deliberately not touched. This change does not make the
gate pass; whether it passes is an open empirical question for the next run.
