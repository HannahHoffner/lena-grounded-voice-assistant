# Fact-focused Formulator contract

## Status and acceptance contract

Implemented, reviewed and regression-tested (2026-10-22); final commit-bound
verification and live measurement pending.

The user authorizes more freedom in wording and omission of details, provided
the answer does not invent or contradict facts. The Formulator remains the
normal generator. Selected offer cards carry supplementary facts. Existing
structured clarification routing remains available for missing user information.

- [x] Separate factual safeguards from presentation/completeness requirements.
- [x] Accept harmless typography, multiple sentences in one evidence-bound block,
  optional fee/domain enumeration, and flexible opening claim types.
- [x] Retain selected-offer scope, references, role/service meaning, numeric and
  contact provenance, age restrictions, fee truth and availability boundaries.
- [x] Verify positive cases paired with false/unsupported counterexamples.
- [x] Document actual limitations: lexical checks are not complete entailment.

## Scope and repository review

Clean starting revision: ad434531af77a7040b99de30e5f70a2e73920594. No applicable
AGENTS files found. Do not modify prior thesis changes or relabel old reports.

`QueryService` builds final evidence; `BlabladorProvider` parses the structured
response; `grounding.validate_formulation` validates the whole answer and restores
mandatory cards. `grounding_references.resolve_offer_evidence` already validates
claims against all supplied facts of the same selected offer, preserving declared
citations separately. The evaluator records rejected first attempts even when a
later answer succeeds. Tests are ordinary pytest; no new dependencies required.

## Contract audit / dead-end analysis

| Current rule | Assessment and decision | Evidence / verification |
|---|---|---|
| One literal sentence and 32 words per JSON item | Presentation, not truth; allow bounded text blocks containing several sentences | Recorded sleep_minor and sleep_woman_age first attempts; paired invented-fact tests |
| Two/three sentences required by prompt | Can force unnecessary details; allow one concise relevant answer | One-offer response tests |
| Exact codepoints in names | Preserve letters/identity; accept only harmless hyphen/space typography | Recorded EM-Brunnen rejection; reject changed letters, suffixes, cross-offer identity |
| Fee must be mentioned | Completeness, not truth; make optional, keep card fee | Toilet omission succeeds; false free/paid/amount claims fail |
| Three supported domains in policy answer | Unnecessary enumeration; optional | Short boundary succeeds, substantive outside-world answer must not be invited |
| Fixed first claim type | Presentation; allow supported offer fact first, retain primary offer ordering | Opening-time-first and wrong-primary tests |
| Claim classified as service when it is an operational detail | Do not waive unknown service checks indiscriminately; accept only operational statements whose content is grounded | Hilfebus example and unsupported service with same time counterexample |
| First-person-only boundary anchors | False-positive risk; recognize scoped grammatical variants | Recorded Romanian third-person boundary; positive ability claim still fails |
| Mixed negation / changing-table vocabulary | Fix evidenced facility scope and Romanian changing-table ambiguity, not arbitrary negative statements | Counterexamples must retain absence-of-service / food hallucination checks |
| Offer IDs, cross-offer references, contacts, prices, time/service relation, age, admission | Truth-relevant; retain | Existing adversarial/regression suite |
| Arbitrary free-form questions / no evidence | Would bypass existing clarification state and weaken claim checks; no new parallel dialogue system | Existing structured clarification integration tests |
| Claims not in lexical vocabulary | Existing coverage limitation; do not claim zero hallucinations or green gates prove truth | Document and preserve manual review |

## Recommended approach and rejected alternatives

Extend the existing contracts/validators, version every changed contract and
prompt/validator, and keep the external response API unchanged. Keep bounded
length and JSON/evidence references for operability. Do not replace the
Formulator with templates, blanket-disable grounding, accept every statement
with a valid fact ID, or ask a second LLM to certify unrestricted claims.

## File impact

| File | Action / reason | Risk |
|---|---|---|
| `app/formulation.py` | Contract/prompt reflect factual priority and optional detail | Prompt/schema version change |
| `app/grounding.py` | Remove presentation-only failure paths, preserve checks | Must pair relaxation with negative tests |
| `app/grounding_constraints.py`, `app/grounding_claims.py` | Bounded normalization / fee / lexical fixes as needed | Scope must remain narrow |
| `tests/test_formulation.py`, `tests/test_public_toilets.py`, related grounding tests | Update obsolete expectations; add meaningful paired cases | Never weaken factual counterexamples |
| `docs/architecture.md`, existing evaluation docs | Document contract and limits using code-documentation skill | Historical measurements stay historical |

Existing modules exceed 400 lines; prefer cohesive presentation helpers over
additional unrelated responsibilities. Extract only if the implementation needs
a cohesive shared helper; no arbitrary module splitting.

## Milestones and validation

- [x] Inspect pipeline, parser, validator, constraints, previous rejected outputs,
  and affected tests; write plan before source edits.
- [x] Implement factual/presentation separation and bounded regression coverage.
- [x] Targeted pytest, then full relevant suite; AST and whitespace checks.
- [x] Provider-free replay of stored rejected outputs with explicit contract-version
  adaptation and no claim that replay is a fresh model evaluation.
- [x] Review final diff against REVIEW_TEMPLATE; apply code-documentation workflow.
- [ ] Commit reviewed code locally and run unchanged full synthetic live sample
  once on the clean revision; report new findings without reclassifying old runs.

## Rollback and recovery

No migrations, new dependencies, source releases or public response fields.
Reverse this task's diff or local commit to restore the prior contract. Reports
are external and bind their own prompt, validator, data and code revision.

## Progress / decision log

- 2026-10-22: User prioritizes supported truth over forced wording/completeness.
  Existing cards are the supplementary detail channel; omission must not become
  a misleading free/availability/admission claim.
- Implemented contract 4, prompt 21, validator 2. Bounds remain one to three
  blocks, 220 characters per block and 600 overall; no public response API change.
- Added 31 paired/new regression cases. Corrected Polish 14-to-under-18 range
  parsing, German weekday abbreviations/ranges and Romanian evidenced facility
  scope. Retained rejection of inclusive-18, wrong weekdays/time order, unknown
  places, false free access and unsupported/exclusive payment methods.
- Replaced old presentation-only negative expectations with acceptance checks;
  all genuine factual counterexamples remain. A known schedule rule formerly
  rejected wrong dates/places indirectly via sentence count; it now has a direct
  operational day/time/location check.
- Native full suite: 1212 passed, one known strict xfail, one existing Starlette
  warning (290.95 seconds). Subsequent scoped payment/UI regression is green.
  A final fresh full suite on the committed source will be stored externally.
- Provider-free reconstruction: 17 of 20 reconstructed rejected attempts now
  accepted; three still rejected, two water attempts not reconstructed. Only
  contract_version adapted; text/references unchanged; fact inventories checked.
  This is not a live success rate or retrospective reevaluation of old gates.
- Applied code-documentation skill: updated `docs/architecture.md` and this audit;
  no speculative claim that passing lexical validation proves semantic truth.
- Self-review: source modules were reduced or kept cohesive; relational helpers
  reuse `grounding_constraints.py` (under 400 lines). No new dependencies, data
  releases, external sends or template-first answer flow. No unrelated edits.
- Final verification artifacts will be in
  `C:/Users/User/AppData/Local/LENA/evaluations/20261022-contract4`.
  Full native tests and live calls may run concurrently as independent processes;
  no latency/performance comparison is asserted. Source remains frozen/clean.

## Final verification summary

Implementation checks pass; post-commit results are recorded externally to keep
the measured software revision clean. Manual linguistic/factual review remains
necessary because unrecognized claims/grammar lie outside the finite rules.

## Follow-up after the complete contract-4 measurement

All four stages on a13b313 completed, with source clean throughout. Full native
regression: 1213 passed, one known xfail (281.02 seconds). E2E: eight technical
cases, five terminal fallbacks (four Formulator), zero automatic mismatches.
Stability: eight technical cases, seven Formulator fallbacks. Isolated stage:
seven failures, including schema errors. These reports remain unchanged in
`20261022-contract4`; they are not a successful gate chain.

Four separately bounded, one-call synthetic shape probes (not scored reruns)
included one actual schema failure: a 226-character text block exceeded 220.
The JSON object/array types and keys were correct. This confirms that keeping
the old per-sentence cap was incompatible with multi-sentence text blocks.

Before further source edits: change only the per-block cap to the existing
600-character whole-answer budget, retaining that overall budget and all factual
checks. Version the schema as contract 5 and prompt 22; validator stays 2.
Specify collection types explicitly. Add a grounded >220-character example,
an unsupported-claim counterexample within that same longer block, and a check
that multiple blocks together still cannot exceed 600. Update the existing
architecture documentation and run final tests/live stages once on a new clean
commit. This is a correction of an observed defect, not repetition of unchanged
code until passing. Final artifacts go to `20261022-contract5`.

Implemented the follow-up and reviewed its diff: only block length, schema/prompt
versions and explicit array wording changed; the 600-character total and factual
validator are unchanged. Focused final verification: 165 passed, one known xfail
(3.92 seconds), including the >220-character supported answer and its unsupported
medical-claim counterpart. Final clean-commit full regression/live evidence will
be saved externally; no further source changes during that measurement.
