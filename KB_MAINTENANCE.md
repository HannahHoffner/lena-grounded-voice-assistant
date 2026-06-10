# LENA KB Maintenance Rules

## Mission
Maintain LENA's local help information for Leipzig in a source-grounded, auditable, safety-sensitive way. The runtime assistant may only use reviewed published data.

## Core Safety Rules
- Do not invent institutions, addresses, opening hours, phone numbers, eligibility rules, medical advice, legal advice, or emergency instructions.
- Treat LLM output as a draft proposal, never as truth.
- Keep raw source snapshots and hashes immutable.
- Never overwrite reviewed staff data silently.
- Do not publish draft, stale, rejected, contradictory, or unreviewed sensitive changes.
- Do not use runtime transcripts or personal data for KB maintenance prompts.

## Source Grounding
Every proposed public field must cite source evidence:
- source URL
- snapshot path or snapshot ID
- fetch timestamp or last checked date
- exact evidence text for sensitive fields

Sensitive fields are:
addresses, coordinates, opening hours, phones, emails, emergency numbers, medical offers, admission requirements, gender or age restrictions, target groups, crisis advice, and currently-open claims.

## Allowed Operations
- Fetch configured public source pages.
- Store raw snapshots, extracted text, status code, hashes, final URL, etag, and last-modified headers.
- Compare current and previous snapshots.
- Create change proposals with field-level evidence.
- Suggest categories, aliases, summaries, and missing-field warnings.
- Generate review reports for staff.

## Forbidden Operations
- Directly publish LLM-generated updates.
- Add unsupported services or facts.
- Replace human-reviewed fields without a visible diff and review decision.
- Infer emergency, medical, legal, or eligibility advice beyond the cited source.
- Hide stale or contradictory source information.

## Review Workflow
Use these states:
- `draft`: created by scraper or LLM, not trusted.
- `pending_review`: ready for staff review.
- `reviewed`: accepted by staff but not yet released.
- `published`: included in runtime artifacts.
- `rejected`: rejected by staff.
- `stale`: source is too old, failed, or likely outdated.
- `contradiction`: sources or fields disagree and need resolution.

Review decisions must include reviewer, date, reason, and affected fields.

## Manual Overrides
Staff may add overrides for ranking, text, warnings, closures, intake priority, or visibility. Overrides require author, reason, status, validity period when temporary, and whether they are public-visible.

Ranking overrides may influence retrieval order but must not create unsupported answer facts.

## Output Format for LLM Proposals
Return JSON only. Include:
- `proposal_id`
- `source_id`
- `source_snapshot_id`
- `affected_service_ids`
- `proposed_changes`
- `diff`
- `evidence`
- `llm_model`
- `prompt_hash`
- `status`

If evidence is missing, set the field to `unknown` or omit the change.
