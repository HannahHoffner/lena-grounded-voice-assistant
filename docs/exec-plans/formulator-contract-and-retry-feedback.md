# Execution Plan: Formulator contract and bounded retry feedback

## Status

- State: Complete
- Owner: Codex
- Created: 2026-09-23
- Last updated: 2026-09-23

## Objective

Implement only the minimal package explicitly approved after the read-only review:
align prompt terminology, explain citation requirements, and give the existing
second attempt a closed grounding diagnostic without relaxing validation.

## Acceptance contract

- [x] Remove contradictory referral-service permission; consolidate prompt rules.
- [x] Explain target citations despite descriptions and complete phone values.
- [x] Forward only a closed diagnostic, never rejected text, to the existing retry.
- [x] Preserve two-attempt limit, fast model, 30-second stage/45-second global defaults.
- [x] Preserve grounding, atomic fallback, data, output schema, privacy and all languages.
- [x] Focused regressions, complete safe Python suite, build/install/startup and diff review.
- [x] Document limitations and propose, but do not run, a bounded live comparison.

## Scope

In scope: prompt, optional provider retry argument, shared orchestration, tests,
existing technical documentation. Out of scope: thesis, live calls, manual evaluation,
validator changes, phone rendering/data migration, extra LLM stages and dependencies.

## Repository review

### Current behavior and architecture

Curated selected offers become FormulatorEvidence; BlabladorProvider.formulate_answer
requests JSON, validates schema and grounding atomically. QueryService._call_formulator
repeats once with identical input after retryable errors; all three offer/infrastructure
paths share it. Timeout/HTTP errors bypass retry. Final failure uses existing templates.
The prompt permits referral services in one place but forbids the corresponding claim
types elsewhere. Target detection checks fact types, not full entailment. Phone values
include labels and constraints. Recorded old rejected texts are unavailable.

### Existing structures to reuse

| Structure | Path | Reuse decision |
|---|---|---|
| GroundingDiagnosticCode | app/formulation.py | Closed optional feedback; no new error taxonomy |
| FormulatorError | app/formulation.py | Existing diagnostic, not rejected_response, is forwarded |
| Shared two-attempt loop | app/service.py | Extend in place for social/water/toilet paths |
| Provider JSON messages | app/providers/llm.py | Fixed trusted correction instruction on retry |
| Network-isolated pytest | tests/conftest.py | Preserve safe synthetic execution |

### Existing tests and commands

tests/test_formulation.py, test_api.py, test_live_evaluation.py and test_packaging.py
cover contracts, bounded retry, diagnostic isolation, wheel/sdist/install/startup.
Commands: python -m pytest; python -m compileall -q app; python -m pip check.
Packaging tests run python -m build, rebuild sdist and install/start outside checkout.
No configured lint/type tooling in pyproject.toml; do not introduce any.

### Working tree considerations

Clean maintenance/repository-cleanup at 082c20e; diagnostic change committed.
No applicable AGENTS files found. Preserve all unrelated files and Git history.

## Dead-end analysis

| Potential dead end | Evidence/impact | Mitigation and verification |
|---|---|---|
| Scenario-specific prompt fixes | Lost old outputs cannot prove exact cause | Generic rule classes, five-language regressions |
| Relax target checks | Contrary gender can pass with a wrong-value typed fact | No validator changes; explicit known-limitation tests |
| Digits-only phones | Values contain operational restrictions | Preserve full fact and exact-copy validation |
| Retry outside shared loop | Would miss water/toilets and alter call budget | Use existing loop, test exhausted budget and failures |
| Echo rejected response | Could elevate injected text or leak content | Only enum plus fixed instructions, never raw error text |
| Prompt-only success claims | Mocks cannot measure compliance | Separate local proof from future authorized live run |

## Recommended approach and alternatives rejected

Use the existing diagnostic enum as optional retry argument; map demonstrated rule
classes to short static guidance, with generic guidance for other enum members.
No new envelope/schema, stage, stored state or authoritative fact representation.
Parser failures without grounding diagnostics retain existing retry behavior.
Reject deterministic phone insertion, new fields, semantic planning and timeout/model
changes for this package: they expand the approved scope or lack comparative evidence.

## File impact

| File | Action | Reason / risk |
|---|---|---|
| app/formulation.py | Modify | Prompt version and closed correction instructions; low |
| app/providers/llm.py | Modify | Optional typed feedback on existing interface; low |
| app/service.py | Modify | Forward diagnostic only on retry; low |
| tests/test_formulation.py, tests/test_api.py | Modify | Contract, integration, privacy and limits |
| docs/live-provider-evaluation.md | Modify | Accurate limitations and comparison evidence |
| docs/architecture.md, docs/data-flow.md | Modify | Current prompt version and shared retry contract |
| This plan | Create/update | Review and verification record |

Existing source modules already exceed 400 lines. Splitting them merely for this
small addition would add indirection; keep the cohesive existing responsibilities.

## Milestones

1. [x] Review and design: read-only review and renewed call-site/status inspection.
2. [x] Implement bounded changes and focused tests.
3. [x] Verify targeted/full tests, packaging/startup, compileall, pip check, final diff.
4. [x] Apply code-documentation checklist to existing documentation and review it.

## Validation plan

| Check | Command/method | Expected result |
|---|---|---|
| Baseline | python -m pytest tests/test_formulation.py tests/test_api.py tests/test_live_evaluation.py | Existing tests pass |
| Focused | Same command after edits | New regressions and existing tests pass |
| Complete/build/install/startup | python -m pytest | All tests pass, including packaging and safe startup |
| Syntax/dependencies | python -m compileall -q app; python -m pip check | No errors |
| Scope | git diff --check; full git diff and status | Only approved files; no validator/config/thesis changes |
| Prompt cost | Compare characters/words against HEAD | Avoid unbounded prompt growth; not a token measurement |

## Rollback and recovery

No data migration or deletion. Revert only this patch if requested, preserving later
user changes. No commits, reset, stash or push. Generated test/build artifacts stay
in existing ignored/temporary locations.

## Progress log

- 2026-09-23: Plan created after explicit approval and renewed inspection.
- Baseline targeted suite: 173 passed, one existing Starlette/httpx deprecation
  warning, 40.41 seconds. No baseline failures.
- Implemented prompt 16, optional closed retry argument and shared forwarding.
  No output/evidence schema or grounding/configuration changes.
- First targeted verification: 214 passed, 2 explicitly expected known-limitation
  failures, one existing warning, 40.20 seconds. Added further negative retry
  and three-class API fallback coverage before starting the full suite.
- python -m compileall -q app passed; python -m pip check reported no broken requirements.
- Invoked code-documentation: updated existing evaluation/architecture/data-flow
  documentation, corrected the Large comparison, documented limits and next-run scope.
- Reviewed full source/test/documentation diff; git diff --check passed.
- Final python -m pytest: 907 passed, 2 xfailed, one existing Starlette/httpx
  deprecation warning, 308.06 seconds. Includes all seven packaging tests:
  wheel/sdist construction, package inventory, sdist rebuild, clean wheel install
  and provider-free TestClient startup/health/query/static-resource checks outside
  the checkout. No live provider or manual evaluation was performed.
- Additional node --test tests/frontend.test.cjs, node --check app/static/app.js
  and node --check app/static/dialogue.js could not run: node is not on PATH
  and checked conventional installations are absent (same known environment gap
  as earlier quality reviews). No new tooling installed; frontend unchanged.
- Final thesis worktree status is clean. No files deleted, staged or committed.

## Decision log

- Reuse diagnostic enum rather than adding arbitrary text feedback or a new schema.
- Keep all validators unchanged; known limitations must not become claimed guarantees.

## Discoveries

- Confirmed: all provider wrappers accept keyword forwarding; production provider has
  one formulation method; all three runtime callers use the shared bounded loop.
- Open: live compliance/latency effect, exact old rejected response contents.
- Prompt size: 8,418 characters / 1,227 whitespace-separated words versus 8,428 /
  1,228 previously. Retry guidance adds at most 472 characters plus one newline.
  No tokenizer measurement or live latency inference.
- Two NEW strict xfail tests express desired but currently unsupported target
  semantics; all existing tests remain active. They are not fixes or passes.
- Isolated stage 2 bypasses QueryService retry: a future stage-2 comparison measures
  the initial prompt, not live feedback efficacy. Existing documented E2E-runner
  limitations remain outside this package; do not bypass its call-budget concerns.
- Complexity: architecture stable, prompt slightly smaller, implementation slightly
  larger for closed feedback; no dependencies, new stages or duplicate factual stores.

## Final verification summary

| Verification | Result |
|---|---|
| Baseline targeted suite | 173 passed |
| First focused suite | 214 passed, 2 known-limit xfails |
| Final complete Python suite | 907 passed, 2 known-limit xfails, no unexpected failures |
| Build/install/safe startup | Passed within tests/test_packaging.py |
| compileall / pip check / git diff --check | Passed |
| Lint/type checks | Not configured; no new tooling added |
| Node frontend runtime/syntax checks | Blocked by missing Node; Python frontend checks passed |
| Scope and self-review | Only 3 production files, 2 test files, 3 existing docs and this plan |
| Live/manual evaluation | Not performed |

Acceptance package complete; architecture stable, code complexity slightly increased
for bounded diagnostic feedback, no weakening of validation. The two semantic
target limitations remain; general prevention of all three failure classes is not
established. A separately authorized stage-2 diagnostic run is justified, but does
not itself exercise application retries. No blanket manual-evaluation readiness
claim is made from these mock/local results. A clean versioned state is still
required before the existing live runner will accept a new run.
