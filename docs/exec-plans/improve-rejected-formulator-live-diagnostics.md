# Rejected formulator output diagnostics and model comparison

## Status

- State: Verified
- Owner: Codex
- Created: 2026-09-22
- Last updated: 2026-09-22

## Objective

Make schema-valid but rejected synthetic formulator responses locally inspectable
in controlled live-evaluation reports, while keeping the user-facing fallback,
validators and content-free `redacted-errors.jsonl` unchanged. Compare the same
stage on `alias-large` before changing code.

## Acceptance contract

- [x] Verify whether Zotero changed `thesis/bibliography.bib` without editing thesis.
- [x] Run the authorized selector/formulator comparison on clean commit `ccc6a12`
  with all effective stage models verified as `alias-large`.
- [x] Preserve a schema-valid rejected formulator response only in the ignored,
  synthetic `stage-results.jsonl` record.
- [x] Keep `redacted-errors.jsonl`, application logs, API responses and normal
  interaction logs content-free.
- [x] Add regression tests and update the existing live-evaluation documentation.
- [x] Do not edit any thesis file, loosen validation, change defaults or commit.

## Scope

### In scope

- Optional in-memory attachment of a parsed rejected `FormulatorResponse` to
  `FormulatorError` after grounding/contract validation fails.
- Persistence of that response in the synthetic stage-2 result only.
- Tests and the existing technical live-evaluation guide.
- Recorded comparison of Fast and Large on the same versioned scenario stage.

### Out of scope

- Thesis edits, validator/prompt changes, model-default changes or timeout changes.
- Storage of raw HTTP responses, prompts, headers, keys or real user data.
- Re-running downstream gates after a failed selector/formulator gate.

## Repository review

### Current behavior

`BlabladorProvider.formulate_answer()` parses a strict `FormulatorResponse` and
then calls `validate_formulation()`. On rejection, `FormulatorError` retains only
the broad code and closed grounding diagnostic. `_run_formulator_scenario()`
therefore writes `structured_output=null`; the precise schema-valid model response
is lost. The content-free diagnostic is safe but insufficient to distinguish a
model citation mistake from an overly strict validator without another live call.

The reports are generated only from the versioned synthetic catalog in an ignored
runtime directory. Successful model text is already stored in `stage-results.jsonl`.
`redacted-errors.jsonl` deliberately stores only allowlisted codes.

### Relevant architecture and data flow

Provider HTTP response -> strict JSON parser -> `FormulatorResponse` -> grounding
validator -> `ProviderAnswer` or `FormulatorError` -> stage-2 runner -> atomic local
report store. The ordinary `QueryService` catches the same error but must never
persist or expose the diagnostic response.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| `FormulatorResponse` / `FormulatorError` | `app/formulation.py` | carry the already parsed response in memory |
| Provider validation boundary | `app/providers/llm.py` | attach response only after strict parsing succeeds |
| Stage-2 result | `app/live_evaluation_runner.py` | persist exact structured rejection in local synthetic report |
| Content-free error report | `app/live_evaluation_runtime.py` | preserve unchanged |
| Runner/report tests | `tests/test_live_evaluation.py` | prove inclusion and redaction boundary |
| Existing guide | `docs/live-provider-evaluation.md` | document purpose, scope and handling |

### Existing tests and commands

- `python -m pytest tests/test_live_evaluation.py tests/test_formulation.py`
- `python -m pytest`
- `python -m compileall -q app tests`
- `python -m pip check`
- `git diff --check`

### Working tree considerations

The code repository was clean before this plan. Live reports are ignored. The thesis
repository contains the previously requested five `.tex` changes; they are preserved.
`bibliography.bib` has no status/diff and its Git blob equals `HEAD`.

## Dead-end analysis

| Potential dead end | Evidence | Impact | Mitigation | Verification |
|---|---|---|---|---|
| Persist only another coarse code | Existing codes identify rules but not returned sentence/citations | root cause remains ambiguous | retain parsed rejected response in synthetic stage result | test exact snapshot |
| Put model text in `redacted-errors.jsonl` | File is designed to be safely shareable and allowlisted | breaks redaction boundary | keep that file unchanged | equality test |
| Store raw HTTP body | May contain provider metadata and unparsed content | excessive data and secret risk | capture only validated `FormulatorResponse` | schema-valid test double |
| Log diagnostics in normal runtime | Real requests may contain personal data | privacy regression | runner alone serializes optional payload | API/log tests and source review |
| Switch permanently to Large | Same-stage run produced two 30 s timeouts | latency regression and gate still fails | report comparison only; no default change | manifest and summary |
| Raise timeouts until Large passes | Masks unsuitable latency and weakens kiosk responsiveness | no principled bound | retain current limits | observed duration table |

## Recommended approach

Add an optional typed `rejected_response` field to the existing exception. Attach it
only around `validate_formulation()` after strict parsing. The stage-2 runner writes
its model dump as `rejected_structured_output`; accepted `structured_output` remains
null, and the redacted error file remains codes-only. Document that the field may
contain hallucinated synthetic text and is diagnostic evidence, not trusted data.

## Alternatives rejected

| Alternative | Reason rejected |
|---|---|
| New diagnostic provider/client | duplicates the production transport and parser |
| Save full request/evidence | unnecessary; versioned scenario, release and source reconstruct it |
| Relax validator based on codes alone | exact rejected text was unavailable |

## File impact

| File | Action | Reason | Risk |
|---|---|---|---|
| `app/formulation.py` | Modify | optional typed rejected response | low |
| `app/providers/llm.py` | Modify | attach after validation rejection | low |
| `app/live_evaluation_runner.py` | Modify | write synthetic rejected output | low |
| `tests/test_live_evaluation.py` | Modify | regression and redaction tests | low |
| `docs/live-provider-evaluation.md` | Modify | handling and interpretation | low |
| this plan | Create/update | persistent evidence | none |

## Milestones

### Milestone 1: Review and design

- [x] Inspect instructions, status, runtime path and report boundaries.
- [x] Verify bibliography identity and complete Large comparison.
- [x] Confirm reuse decisions and dead ends.

Evidence: Git blob `936ccb42...` equals HEAD; Large run
`run_d438bc21c7424178b85c2edbe66a118a` completed 16 scenarios with two timeouts.

### Milestone 2: Implementation

- [x] Implement bounded diagnostic attachment and persistence.
- [x] Add regression coverage.
- [x] Update discoveries.

Evidence: `FormulatorError.rejected_response`, provider attachment after strict
schema parsing, runner-only `rejected_structured_output`; focused tests passed.

### Milestone 3: Verification

- [x] Run targeted and full tests.
- [x] Run syntax/dependency/diff checks.
- [x] Review final diff.

Evidence: focused formulation/live tests passed; 861/861 full tests passed in
294.99 s with the existing Starlette warning; compileall, pip check and diff
check passed.

### Milestone 4: Documentation

- [x] Apply `code-documentation` checklist to the final diff.
- [x] Rerun affected checks.

Evidence: the existing guide documents field semantics, privacy boundary,
interpretation limits and the Fast/Large comparison. Focused tests were run
after the behavioral change and the full suite after documentation.

## Validation plan

| Check | Command or method | Expected result |
|---|---|---|
| Diagnostic capture | focused provider/runner tests | rejected parsed response present only in stage result |
| Redaction | report-store/runner tests | errors file remains code-only; no secrets |
| Regression | full pytest | all tests pass |
| Static | compileall, pip check, diff check | pass |

## Rollback and recovery

No migration or persistent runtime format requirement is introduced. The optional
field can be removed hunkwise; old reports remain readable. Live reports are retained.

## Progress log

- 2026-09-22 — Review completed; bibliography verified; Large comparison completed.
- 2026-09-22 — Diagnostic capture, tests and documentation completed; full suite and static checks passed.

## Decision log

- Decision: preserve parsed rejected response only in synthetic stage results.
  - Context: closed codes were safe but insufficient for diagnosis.
  - Choice: typed in-memory payload and local runner serialization.
  - Consequences: diagnostic reports are more useful but must remain local research artifacts.
- Decision: do not adopt Large or extend timeout.
  - Context: Large removed observed grounding failures but timed out twice at 30 seconds.
  - Consequences: model/default decision remains open pending a passing bounded gate.

## Discoveries

- Fast failed three of six attempted formulator cases by grounding and aborted.
- Large completed all ten formulator cases but timed out on `f_de_grounded` and
  `f_pl_grounded`; all eight returned responses were technically valid.
- Large averaged 15.16 s per formulator call versus Fast 5.08 s in its six attempted
  calls. This is descriptive for these runs, not a general benchmark.
- Existing historical plans correctly describe the earlier no-content policy; the
  current guide now documents the explicitly revised, synthetic-only boundary.

## Final verification summary

- Acceptance requirements: met.
- Tests: focused tests passed; 861/861 full suite passed, one existing warning.
- Static/build: compileall, pip check, packaging paths in full suite and diff check passed.
- Live comparison: Large gate failed with two 30-second timeouts; no downstream stage.
- Documentation: existing guide updated; no thesis file changed in this task.
- Residual risk: the three historical Fast responses cannot be reconstructed. A new
  Fast run using the enhanced report requires a clean, newly versioned code state.
