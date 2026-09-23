# Execution Plan: Answer-wide, offer-bound grounding

## Status

- State: Implemented
- Owner: Codex (Planung), Claude (Umsetzung)
- Created / updated: 2026-09-23

## Objective and acceptance contract

Implement the explicitly approved contract: references may support statements in
another sentence about the SAME offer; descriptions can establish target facts;
referral offers can describe their evidenced services without promising admission,
personal suitability or current availability.

- [x] Validate all references before pooling them by offer, never globally.
      `_resolve_references` runs before `_citation_pools` in app/grounding.py.
- [x] Check recognized service/target concepts against values, not just fact types.
      app/grounding_claims.py compares a closed multilingual stem vocabulary
      against cited values; detection is scoped to the answer language, support
      additionally to DE/EN because curated literals are not localized.
- [x] Accept localized descriptions as evidence, reject contradicted gender/age concepts.
      New `target_claim_contradicted` separates contradiction from undecidability.
- [x] Permit evidenced referral services and contact imperatives; keep policy/safety rules.
      The blanket role prohibition is gone; admission/suitability/current-availability
      guards now apply in every role.
- [x] Preserve service-specific schedule restrictions from existing curated data.
      `service_condition` facts project existing `service_schedules` windows; no
      second schedule store and no guessing for rules without a fixed window.
- [x] Keep phone/address/price/time checks, atomic rejection, bounded retry and defaults.
      Unchanged; operational tokens now read the offer's own citation pool.
- [x] Cover correct/incorrect examples in five languages, real captured failure shapes,
      cross-offer attacks, conditions, retry/fallback and packaging/startup.
- [x] Document the changed evaluation contract and residual semantic limitations.

## Scope

No live calls, thesis edits, model/timeout changes, new dependencies/frameworks,
selection redesign, history changes, deletions or telephone normalization. Do not
claim complete semantic entailment for unrestricted natural language. Runner limits
and existing historical results remain unchanged.

## Repository review

Clean maintenance/repository-cleanup at 6075f8d. No applicable AGENTS files found.
Existing flow: curated projection -> selected offers -> formulation evidence ->
provider JSON/schema -> grounding -> bounded retry -> atomic template fallback.
Current grounding validates each sentence's fact types separately. Roles are treated
as global prohibitions even for evidenced general descriptions. Description-only
target statements are rejected, but an unrelated typed gender fact can pass.
The isolated stage-2 fixture imposes referral roles; it does not run selection.

Reuse `FormulatorEvidence`, `EvidenceFact`, `FormulatorError`, closed diagnostics,
shared QueryService retry, existing exact-value checks and `result_time.SCHEDULE_WINDOWS`.
Do not add a second schedule database. Add only derived, service-bound schedule facts
for existing fixed windows; the authoritative data stays in the curated projection.

Existing tests: test_formulation.py, test_api.py, test_live_evaluation.py,
test_provider_timeouts.py, test_packaging.py. pytest blocks external application
transports and isolates state. Build/startup tests install a wheel outside checkout.
No configured lint/type checker; Node is known absent. Modules formulation/grounding
already exceed 400 lines; keep the new bounded lexical/value checks in one cohesive
helper, not a framework or an alternative validator.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Global fact pooling | Wrong offer could lend its phone or target group | Resolve ownership first; cross-offer negative tests |
| Any description means any target | Existing type-only checks do not prove values | Recognized concepts must be supported, typed restrictions remain authoritative |
| Role removal implies guaranteed help | Referral roles can bypass eligibility clarification | Preserve unsafe-claim guards; add multilingual promises tests |
| One opening time for all services | Hilfebus food and counselling differ | Derived service-bound conditions; unrelated time cannot satisfy food condition |
| Keyword inference from names | Names can contain target/service terms | Strip cited immutable names/operational literals before concept checks |
| Claiming full semantic proof | No NLI model/new LLM stage authorized | Explicit bounded supported vocabulary and documented unknown paraphrase limits |
| Passing only current scenario IDs | Would hide unrelated hallucinations | Generic concept maps and five-language/adversarial tests |

## Recommended approach / alternatives rejected

First resolve all fact IDs and pool citations by offer. Retain sentence-to-offer
binding and policy validation. Use bounded multilingual service/target concept
recognition against cited values, with structured gender/age restrictions acting
as contradiction guards. Never permit description by mere presence. Preserve exact
operational-token checks per sentence using its offer's citation pool.

General referral service descriptions are allowed, not automatic suitability or
availability. Existing fixed service windows become explicit schedule facts in the
evidence and must be stated when a relevant time-limited service is asserted.
Descriptions/prompt/retry guidance must agree. Bump evidence/prompt versions so future
reports cannot be mistaken for old criterion runs. Keep response schema unchanged.

Reject broader free-text semantic judging, extra provider stages, digits-only phone
matching, opportunistic current-scenario exceptions, changing failure caps and adding
new independent authoritative schedule facts.

## File impact

| File | Action / purpose |
|---|---|
| app/formulation.py | Evidence/prompt version, derived condition facts, aligned prompt and retry |
| app/grounding.py | Offer citation pools, value checks and revised role semantics |
| app/grounding_claims.py | Bounded multilingual concept/condition checks, reused schedule windows |
| tests/test_formulation.py and related contract tests | Update changed expectations, retain rejection tests |
| tests/test_grounding_claims.py | Focused answer-wide/cross-language/condition regressions |
| docs/architecture.md, docs/data-flow.md, docs/live-provider-evaluation.md | Changed contract and limits |
| This plan | Review and evidence |

## Milestones

1. [x] Inspect current code, instructions, source of schedule/target data and tests.
2. [x] Implement and verify narrow changes incrementally.
3. [x] Full local suite, compileall, pip check, packaging/startup, complete diff review.
4. [x] Apply code-documentation to existing docs and record limitations.

## Validation plan

| Check | Command / expected result |
|---|---|
| Baseline / focused | python -m pytest tests/test_formulation.py tests/test_api.py tests/test_live_evaluation.py |
| New counterexamples | python -m pytest tests/test_grounding_claims.py |
| Complete / packaging / safe startup | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Diff / scope | git diff --check; full diff; unchanged config/data/runner/thesis |

## Rollback and recovery

No migrations or deletion. Roll back only this patch if requested; do not reset user
changes. Historical local reports retain their original evidence/prompt versions.

## Progress / decision log

- Plan created before source edits, after approval and clean-tree inspection.
- Conditions are projections of existing fixed schedules, not current availability.
- Retain uncertain-text fallback/limitations rather than promise a truth oracle.

## Discoveries and final verification summary

**Result: 935 passed, 1 xfailed** (baseline 907 passed, 2 strict xfail).
`python -m compileall -q app` clean, `python -m pip check` reports no broken
requirements, packaging/startup tests unchanged and passing. The diff touches
only app/formulation.py, app/grounding.py, the new app/grounding_claims.py, the
four test modules and the four documents; no config, data, runner or thesis
change.

Of the two documented limitations, one is corrected and is now a genuine
regression test: a gender claim that contradicts a cited curated restriction is
rejected as `target_claim_contradicted`. The second remains an explicit xfail:
`minor injuries` still matches the target vocabulary lexically. That case now
resolves to *undecidable* rather than to a truth claim, so it falls back in a
controlled way — but it is not fixed, and the limitation stays documented.

Discoveries during implementation, each with the correction made:

- NFKD decomposes Cyrillic `й` into `и` plus a combining breve, so folding
  before transliteration turned `сейчас` into `seichas` and no `seychas` stem
  could ever match. Transliteration now runs before combining marks are
  stripped.
- Curated literals are English snake_case (`drinking_water`,
  `overnight_accommodation`). Word boundaries therefore treat `_` as a
  separator, otherwise those values could not support their own concepts.
- The curated German description says `volljährige`, not `erwachsene`; the
  adult concept needed the curated wording in every language. Prefix matching at
  word start keeps `niepełnolet`/`nesovershennolet` out of the adult concept.
- `aktuell`/`currently` would have flagged the drinking-fountain wording
  `aktueller Betriebsstatus unbekannt`, which the system is supposed to say. An
  explicit unknown-marker guard keeps that safe statement valid.
- The first sentence's claim type stays fixed by `answer_type`. A referral
  answer therefore still opens with `referral`; the offer's own evidenced
  service belongs in a later sentence. That rule was deliberately not changed.
- `Dort bekommst du einen Schlafplatz.` is an existing accepted answer shape.
  The admission guard was narrowed to explicit admission wording and to assured
  place allocation (`gibt dir sicher einen Schlafplatz`), so describing an
  evidenced service in the second person stays allowed.

Residual limitation, stated deliberately and not papered over: the validator
still has no additional model stage and cannot check free multilingual
paraphrase for meaning. What is secured are concretely checkable statements;
wording outside the closed vocabulary is not recognised and resolves to
*undecidable*. No general truth check is claimed.
