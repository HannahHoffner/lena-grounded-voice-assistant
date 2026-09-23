# Execution Plan: Over-strict formal-register and proper-name rules

## Status

- State: Implemented, live re-run pending
- Owner: Claude
- Created / updated: 2026-09-23

## Objective and acceptance contract

Two lexical rules reject correct answers. Both were reached for the first time in
`run_44573fca358d4d6e84d002b364a2e026`, the first selector-formulator run that
completed instead of aborting. Neither belongs to the answer-wide grounding
contract; both predate it.

- [x] German `Sie`/`Ihr…` at the start of a sentence may be the ordinary pronoun
      `sie`/`ihr`, not the formal address. Stop rejecting it where a preceding
      sentence supplies a possible antecedent.
- [x] Keep rejecting the formal register where it is unambiguous: a capitalized
      formal token that is not sentence-initial, or a sentence-initial one with
      no preceding sentence it could refer to.
- [x] A proper name occurring only inside a cited e-mail address or URL is not a
      name mention. Those literals have their own exactness checks.
- [x] A cited naming fact must still be rendered exactly, but answer-wide per
      offer, consistent with the grounding contract already in place.
- [x] Keep every other name rule: cross-offer mentions, inflected or otherwise
      altered renderings, and the requirement to cite a name that is used.
- [x] Do not touch grounding concepts, evidence projection, prompt, models,
      timeouts, retry limits or the curated data.

## Scope

No live calls inside this change, no thesis edits, no new dependencies, no
selection or evidence redesign, no telephone normalization, no version bump of
the evidence or prompt contract (neither the evidence packet nor the visible
answer contract changes; only the validator's two lexical rules do).

## Repository review

Clean tree at 48dda16 (`Grounding Formulator überarbeiten`). No applicable
AGENTS files.

`GERMAN_FORMAL_RE` in `app/grounding.py` is case-sensitive and matches anywhere
in the stripped prose. German capitalizes the first word of every sentence, so
`Sie bieten …` ("they offer") is lexically identical to the formal `Sie`. The
rule cannot separate them by itself; it needs the surrounding register.

The proper-name rules run three overlapping checks in `_validate_sentence`.
`_contains_exact_literal` guards word characters (`(?<!\w)…(?!\w)`), but `@` is
not a word character, so `uvo@cab-leipzig.de` satisfies the boundary for the
name `UVO`. `name_like` is worse: a plain `casefold() in casefold()` substring
test with no boundary at all. Both therefore read an e-mail address as an
inexact rendering of a proper name. E-mails and URLs already have dedicated
checks (`EMAIL_NOT_CITED`, `URL_NOT_CITED`) and exact-literal comparison against
the cited values, so masking them for name reasoning removes a duplicate, not a
guarantee.

Reuse `EMAIL_RE`, `URL_RE`, `_contains_exact_literal` and the existing
`GroundingDiagnosticCode.PROPER_NAME_NOT_EXACT`. Do not add a new diagnostic:
the failure class is unchanged, only its trigger is corrected.

## Dead-end analysis

| Risk | Evidence/impact | Mitigation / proof |
|---|---|---|
| Dropping the formal check | Formal register would ship unnoticed | Only sentence-initial tokens are exempted, and only with informal address present |
| Position as blanket pardon | `Melde dich … Wir helfen Ihnen.` would pass | Non-initial formal tokens stay unconditional |
| Dropping the cited-name rendering rule | Inflected names would ship | Rule kept, only widened from sentence to the offer's sentences |
| Masking too much | Masking the name itself would void the rule | Mask only e-mail and URL matches, never naming facts |
| Adding a `NAME\w+` inflection heuristic | `Rücke` would fire inside `Rückenschmerzen` | Rejected; the residual is documented instead |
| New diagnostic codes | Would break comparability of local reports again | Reuse the existing closed codes |

## Recommended approach / alternatives rejected

**Register.** Treat a capitalized formal token as decisive when it is not
sentence-initial. Treat a sentence-initial one as decisive only when no sentence
precedes it, because a pronoun needs an antecedent to refer to. Position is
determined on the same stripped prose the rule already uses.

An earlier draft keyed this on the presence of an informal address form and was
discarded during implementation: `Geh zu Scharni. Ihr Angebot ist kostenlos.`
contains no `du` form yet `Ihr` means "their", so that signal does not separate
the two readings.

**Names.** Mask `EMAIL_RE` and `URL_RE` matches before any name-occurrence
reasoning, in all three checks. Move the "a cited naming fact must be rendered
exactly" requirement out of the per-sentence loop and apply it once per offer
over that offer's sentences, matching the answer-wide citation pool.

Rejected: a semantic pronoun resolver (no model stage authorized), digits/token
normalization of e-mails, and per-scenario exceptions.

## File impact

| File | Action / purpose |
|---|---|
| app/grounding.py | Register helper, e-mail/URL masking, answer-wide name rendering |
| tests/test_formulation.py | Regressions for both corrected triggers and the kept strictness |
| docs/architecture.md | Describe both corrected rules and the residual |
| This plan | Review and evidence |

## Milestones

1. [x] Inspect both rules, their call sites and the captured failures.
2. [x] Implement and verify narrow changes incrementally.
3. [x] Full local suite, compileall, pip check, complete diff review.
4. [ ] Re-run the selector-formulator stage and record the result.

## Validation plan

| Check | Command / expected result |
|---|---|
| Focused | python -m pytest tests/test_formulation.py tests/test_grounding_claims.py |
| Complete | python -m pytest |
| Syntax / dependencies | python -m compileall -q app; python -m pip check |
| Captured failures | Replay both rejected answers of run_44573fca; expect acceptance |
| Live | selector-formulator stage with the unchanged documented limits |

## Rollback and recovery

No migrations, no deletions, no contract version change. Roll back this patch
alone if required; existing run reports stay untouched.

## Progress / decision log

- Plan written before source edits, on a clean tree, after replaying both
  failures and confirming the exact triggering lines (grounding.py:201 and
  grounding.py:422).
- No evidence or prompt version bump: the packet and the answer contract are
  unchanged, so reports stay comparable to run_44573fca.

## Discoveries and final verification summary

**Local result: 945 passed, 1 xfailed** (before this change: 935 + 1 xfail; ten
new regressions). `compileall` clean, `pip check` clean. Both captured
rejections of `run_44573fca` were replayed and are now accepted; no existing
test changed its expectation, so the strictness those tests encode is intact.

Discoveries during implementation:

- The formal-register rule cannot be decided by the presence of an informal
  address. `Geh zu Scharni. Ihr Angebot ist kostenlos.` has no `du` form at all
  yet `Ihr` means "their". The usable discriminator is whether a preceding
  sentence exists that the pronoun could refer to, so the implemented rule keys
  on antecedent position, not on register markers.
- The e-mail false positive fired twice, not once: `name_like` compares with a
  plain `casefold() in casefold()` substring test without any word boundary, so
  masking had to cover all three name checks rather than only the cited-fact
  loop.
- A `NAME\w+` inflection heuristic was considered to compensate for widening the
  rendering rule to answer scope, and rejected: the name `Rücke` would fire
  inside `Rückenschmerzen`.

Residual limitations, stated rather than papered over: a genuine formal address
at the start of a follow-up sentence is not detected, and an inflected rendering
in one sentence is not detected when another sentence of the same offer renders
the name exactly. Both are consequences of deciding lexically without a model
stage, and both are documented in `docs/architecture.md`.
