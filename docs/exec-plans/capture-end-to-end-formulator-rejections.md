# Execution Plan: Capture rejected formulations in the end-to-end report

## Status

- State: Implemented, re-run pending
- Owner: Claude
- Created / updated: 2026-09-24

## Objective and acceptance contract

Three end-to-end scenarios (`e_food_time`, `e_water`, `e_hilfebus`) reproducibly
end in the template fallback because the formulation is rejected twice. The
report proves the rejection but not its cause: unlike stage two, the end-to-end
records carry no `rejected_structured_output`, because `QueryService.query()`
handles `FormulatorError` internally and returns a template response.

- [x] Record the rejected formulations of the end-to-end stage, including the
      retry attempt, so the cause can be named.
- [x] Capture them on the evaluation boundary that already intercepts every
      formulator call; do not change the application.
- [x] Keep the report closed and redacted: known codes plus the already
      schema-validated model response, exactly as stage two stores it.
- [x] Leave `technically_valid`, both gate criteria and every budget unchanged.
- [x] Attribute rejections to the scenario and turn that produced them.
- [x] Cover capture, attribution and redaction in tests.

## Scope

Reporting only. No application change, no gate change, no budget change, no
scenario change. This plan does not make any gate pass.

## Repository review

Clean tree at `4309b26`.

`BlabladorProvider.formulate_answer` validates and, on failure, raises
`FormulatorError` with `rejected_response` attached
(`app/providers/llm.py:402-407`). `QueryService._call_formulator` catches it,
retries once and finally lets `_formulate_or_fallback` swallow it, so the
end-to-end runner never sees the exception.

`LimitedEvaluationProvider` (`app/live_evaluation_runtime.py:93`) already wraps
every provider call for budget counting and is evaluation-only code. Its
`formulate_answer` sits between the provider and the service, which is exactly
where a rejection is still visible. Attaching the capture there needs no
application change and automatically covers the retry, because the retry is a
second call through the same boundary.

Stage two already persists `rejected_structured_output` and
`grounding_diagnostic_code`, so the redaction contract for this content exists
and is unchanged.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Changing the application to surface the error | The application is frozen | Capture on the existing evaluation boundary |
| Free provider text in the report | Reports must stay closed | Only closed codes and the schema-validated response, as in stage two |
| Rejections attributed to the wrong scenario | Would mislead the diagnosis | Drain the buffer at scenario start, record turn numbers |
| Silently changing failure counts | Would be a criterion change | `technically_valid` untouched; asserted by test |
| Unbounded report growth | Reports must stay small | At most two attempts per request, same size class as stage two |

## Recommended approach / alternatives rejected

Give `LimitedEvaluationProvider` an optional rejection buffer. Its
`formulate_answer` catches `FormulatorError`, appends a redacted record
(`error_code`, `grounding_diagnostic_code`, `rejected_structured_output`) and
re-raises unchanged, so application behaviour is untouched. `_run_e2e_scenario`
clears the buffer before a scenario, tags each captured record with its turn and
writes them as `formulator_rejections`.

Rejected: propagating the error through `QueryService`; adding an interaction
field; reconstructing the rejection from durations or call counts.

## File impact

| File | Action / purpose |
|---|---|
| app/live_evaluation_runtime.py | Optional rejection buffer on the evaluation boundary |
| app/live_evaluation_runner.py | Attribute and persist `formulator_rejections` |
| tests/test_live_evaluation.py | Capture, attribution, redaction, criterion unchanged |
| docs/live-provider-evaluation.md | Document the new field |
| This plan | Review and evidence |

## Milestones

1. [x] Confirm where the rejection is still visible.
2. [x] Implement and verify narrow changes incrementally.
3. [x] Full local suite, compileall, pip check, complete diff review.
4. [ ] Re-run end-to-end and name the cause of the three reproducible fallbacks.

## Validation plan

| Check | Command / expected result |
|---|---|
| Focused | python -m pytest tests/test_live_evaluation.py |
| Complete | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Live | end-to-end; gate expected to stay unpassed |

## Rollback and recovery

Reporting-only change; roll back this patch alone if required. Existing reports
stay untouched and simply lack the new field.

## Progress / decision log

- Plan written before source edits, on a clean tree at `4309b26`.
- The gate criterion stays untouched; this run cannot pass a gate the previous
  one failed.

## Discoveries and final verification summary

**Local result: 1000 passed, 1 xfailed** (before: 998 + 1; two tests added).
`compileall` and `pip check` clean.

Implementation note: the buffer had to be cleared per scenario and drained per
turn, otherwise a rejection would be attributed to whichever scenario happened
to read the buffer next. A test pins that a provider which rejects only the
first call per evidence packet never produces an `attempt == 2` entry.
