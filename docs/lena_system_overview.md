# LENA System Overview

## 1. Purpose and Scope

LENA is a Master's thesis prototype for low-threshold, multilingual information access in the context of Leipzig street social work and Verweisberatung. It helps users find local support services such as food, sleeping places, clothing, medical help, counselling, hygiene, documents, water, and emergency contacts.

The intended scenario is a public or semi-public terminal where a user can choose a language, ask a short question by voice or text, or use symbol-guided navigation. LENA is not a general chatbot. It is also not a replacement for professional counselling, emergency services, medical diagnosis, legal advice, or staff judgement.

The core design principle is source-grounded answering: LENA first retrieves controlled entries from the local knowledge base and only then formulates an answer. The LLM, when enabled, is a rewrite and translation layer over retrieved evidence, not the primary knowledge source.

## 2. High-Level Architecture

```text
User
  |
  v
Static frontend: app/static/index.html, app/static/app.js, app/static/styles.css
  |       |              |
  |       |              +-- Leaflet map display from /api/query/answer or /api/symbol/answer
  |       +-- Browser STT/TTS fallback where available
  v
FastAPI backend: app/main.py
  |
  +-- STT provider: app/providers/stt.py
  +-- Session manager: app/sessions.py
  +-- Temporal context: app/temporal.py
  +-- Retrieval engine: app/retrieval.py
  |       |
  |       v
  |   Published KB: data/published/index/*.json, data/published/pages/*.md
  |
  +-- Rewrite provider: app/providers/rewrite.py
  |       +-- template fallback
  |       +-- Ollama
  |       +-- Blablador/OpenAI-compatible
  |
  +-- TTS provider: app/providers/tts.py
  +-- Map builder: app/maps.py
  +-- Symbol navigation: app/symbols.py
  +-- Transcript/session stores: data/runtime/
  |
  +-- Admin/scraper/maintenance:
          app/scraper/*.py, app/maintenance.py, scripts/run_kb_maintenance.py
```

Main runtime flow:

1. The frontend sends a typed or transcribed request to `/api/query/answer`.
2. `SessionManager.prepare_request()` resolves session state and follow-up context.
3. `RetrievalEngine.retrieve()` ranks KB pages from `data/published/`.
4. The selected rewrite provider returns a `KnowledgeAnswer`.
5. `MapBuilder.build_for_answer()` attaches map destinations when retrieved pages have safe Leipzig coordinates.
6. The response is stored in `data/runtime/transcripts.jsonl` and rendered in the UI.
7. Optional TTS is requested through `/api/speech/synthesize`.

## 3. Repository Structure

`app/`
: Runtime backend code. `main.py` creates the FastAPI app and wires settings, KB, sessions, providers, map, symbols, scraper admin endpoints, and static assets.

`app/providers/`
: Speech and rewrite providers. `stt.py` contains mock and faster-whisper STT. `tts.py` contains mock and Piper TTS. `rewrite.py` contains deterministic template answering, Ollama, Blablador, and generic OpenAI-compatible rewrite providers.

`app/scraper/`
: Scraper and publishing track. `pipeline.py` fetches, extracts, structures, expands, validates, publishes, and promotes KB artifacts. `canonical.py` manages canonical entity/document history in SQLite. `qc.py` contains optional OpenAI-compatible build-time quality review. `run.py` is the module entry point for scraper runs.

`app/static/`
: Browser frontend. `index.html` defines screens and panels. `app.js` handles language selection, voice/text input, symbol mode, session state, API calls, answer rendering, map rendering, browser speech fallback, and request cancellation. `styles.css` contains layout and responsive UI styling. `vendor/leaflet/` is the vendored map library.

`data/published/`
: Runtime KB consumed by the application. It contains `pages/*.md` plus indexes under `index/`. This is the reviewed/pinned data path used by `KnowledgeBase`. Edit manually only with care; normally updates should come through the scraper/promotion workflow.

`data/scraper_sources/`
: Source registry and geocoding overrides. `sources.json` defines public sources, source types, categories, crawl settings, trust tiers, and metadata. `geo_overrides.json` contains manual coordinate corrections.

`data/scraper_workspace/`
: Generated scraper workspace. `raw/` contains source snapshots, `published/` contains candidate KB artifacts, `reports/` contains run reports, and `intake/` is for manual source intake. This path is ignored by Git, but it can be thesis-relevant evidence and should not be deleted casually.

`data/canonical/`
: Canonical SQLite history from the scraper track, especially `kb.sqlite3`. It supports reproducibility of entity/document history.

`data/maintenance/`
: Maintenance workspace with manual overrides, proposals, reports, review logs, releases, snapshots, and curated data. `manual_overrides.json` is loaded at runtime by `KnowledgeBase` through `app.maintenance.active_manual_overrides()`.

`data/runtime/`
: Generated runtime state. `sessions.json` stores active/recent sessions, `transcripts.jsonl` stores turn records, and `audio/` stores Piper WAV files served under `/runtime/audio/`. This is generated and ignored, but transcripts may be useful for local debugging and may contain sensitive user text.

`data/evals/`
: Evaluation inputs and generated outputs. `assistant_eval_cases.json` is the reusable dataset. `results/` contains timestamped evaluation output and should be kept when it supports thesis reproducibility.

`data/prompts/`
: Prompt files, currently `system_prompt.md` for LLM rewrite providers.

`data/voices/` and `tools/piper/`
: Local Piper voice models and Piper binaries. These are generated/local installation artifacts needed for offline TTS, not source code.

`scripts/`
: Utility entry points: `preflight.py`, `evaluate_models.py`, `run_kb_maintenance.py`, `list_openai_models.py`, `test_tts.py`, and `install_piper.ps1`.

`tests/`
: Pytest suite covering API behavior, config, contract, retrieval, rewrite guardrails, scraper, sessions, maintenance, symbols, temporal context, maps, TTS, hygiene queries, and evaluation dataset structure.

`docs/`
: Human-facing technical documentation. This file is the main system overview.

## 4. Backend Functionality

The backend entry point is `app/main.py`.

`create_app()`
: Loads settings, ensures maintenance/runtime directories, optionally bootstraps runtime KB from scraper output, constructs the FastAPI app, creates shared services, mounts `/static` and `/runtime/audio`, and registers routes.

`GET /api/health`
: Returns service health, KB version, active/configured STT and TTS providers, rewrite provider/model, session timeout, and map tile configuration.

`POST /api/speech/transcribe`
: Accepts an uploaded audio file plus language form field. Uses `app.state.stt_provider.transcribe()`. A `debug_transcript` form field bypasses real STT for tests/manual debugging.

`POST /api/query/answer`
: Main query endpoint. It builds temporal context with `build_temporal_context()`, resolves session context with `SessionManager.prepare_request()`, calls `rewrite_provider.answer()`, attaches map data with `MapBuilder`, records the turn in session storage, and appends a transcript event through `TranscriptStore`.

`GET /api/symbol/config`
: Returns localized symbol categories from `app.symbols.get_symbol_config()`.

`POST /api/symbol/answer`
: Handles symbol-guided requests. `build_symbol_answer()` creates deterministic cards and map destinations, then the request is recorded in the same session/transcript infrastructure as text queries.

`POST /api/session/end`
: Marks a session as ended through `SessionManager.end_session()`.

`POST /api/speech/synthesize`
: Uses `tts_provider.synthesize()` and returns a URL under `/runtime/audio/` or an unavailable/error status.

`POST /api/admin/scrape/run`
: Runs the scraper pipeline into the scraper workspace without automatically changing runtime data.

`POST /api/admin/published/promote`
: Promotes `data/scraper_workspace/published/` into `data/published/`. Promotion can be blocked by `validate_publishable_dataset()` when entries need review, are stale, conflict, or lack traceability.

`GET /api/admin/maintenance/report`
: Builds and writes maintenance report artifacts using `app.maintenance`.

`POST /api/admin/transcripts/clear`
: Clears transcript and session stores.

`GET /`
: Serves the static frontend.

Important backend support files:

- `app/config.py`: environment loading and `Settings`.
- `app/models.py`: Pydantic request/response/data models.
- `app/kb.py`: `KnowledgeBase` loader for manifest, pages, aliases, field indexes, and manual overrides.
- `app/maps.py`: map destination creation and Leipzig coordinate filtering.
- `app/sessions.py`: session lifecycle and follow-up context.
- `app/temporal.py`: local date/weekend/season context.
- `app/transcripts.py`: JSONL transcript append/clear.

## 5. Frontend Functionality

Frontend files:

- `app/static/index.html`: screen structure, navigation, panels, forms, map container, and script/style includes.
- `app/static/app.js`: frontend state machine and API integration.
- `app/static/styles.css`: responsive layout, navigation, language buttons, symbol cards, answer panels, map panel, and accessibility states.
- `app/static/vendor/leaflet/`: vendored Leaflet assets.

Implemented user flows:

- Language selection for `de`, `en`, `pl`, `ro`, and `ru`.
- Home screen with voice/text, text-only, symbol, and emergency modes.
- Voice input through MediaRecorder/backend STT when available.
- Browser speech recognition fallback where the browser supports it.
- Typed fallback through the manual question form.
- Answer rendering with status text and request cancellation.
- Backend TTS through `/api/speech/synthesize`.
- Browser speech synthesis fallback if backend TTS is unavailable.
- Symbol-guided navigation through `/api/symbol/config` and `/api/symbol/answer`.
- Emergency button/navigation path that uses the deterministic emergency symbol response.
- Session state display, timeout handling, explicit end conversation, language reset, and context reset.
- Map display with Leaflet, origin marker, destination markers, destination list, detail panel, and tile-load fallback text.

The frontend intentionally calls the backend for grounded answers. Browser-only speech features are fallbacks for input/output, not separate knowledge logic.

## 6. Knowledge Base

Runtime KB location:

- `data/published/index/manifest.json`
- `data/published/index/pages.json`
- `data/published/index/aliases.json`
- Optional/richer indexes: `entities.jsonl`, `alias_index.json`, `field_indexes/*.json`, `runtime_snapshot.sqlite`
- `data/published/pages/*.md`

Current published manifest inspected during this cleanup:

- `kb_version`: `20260421054309`
- `source_count`: `37`
- `page_count`: `61`

Observed categories in the published runtime KB:

- `housing`
- `social`
- `food`
- `addiction`
- `medical`
- `reference`
- `documents`
- `crisis`
- `clothing`
- `water`
- `hygiene`
- `emergency`

KB entries are represented by `PageMetadata` in `app/models.py`. Important fields include identifiers, title/canonical title, category, service type, language, source URL(s), update/verification dates, publisher/organization, address, coordinates/geocoding status, opening hours, description, target groups, eligibility, gender access, registration/appointment flags, languages, contact fields, tags, aliases, source trust/conflict/stale/review status, validation issues, source snapshot/hash fields, summary, and markdown file path.

`KnowledgeBase` in `app/kb.py` loads the published data, preferring `entities.jsonl` and `alias_index.json` when present and falling back to `pages.json` and `aliases.json`. It also loads field indexes and active manual overrides.

Manual editing guidance:

- Prefer changing source definitions and rerunning the scraper when source data changes.
- Use `data/maintenance/manual_overrides.json` for explicit reviewed overrides rather than silently changing retrieved facts.
- Do not manually edit generated scraper workspace files unless documenting a one-off thesis experiment.
- Keep published KB snapshots and evaluation data when they support reproducibility.

## 7. Retrieval Logic

Retrieval is implemented in `app/retrieval.py`.

The main class is `RetrievalEngine`. It:

1. Normalizes and tokenizes the user transcript with German umlaut folding and Unicode normalization.
2. Expands query terms through controlled synonym/intent rules for food, clothing, medical help, debt, shelter, addiction, water, hygiene, toilet, shower, appointment, gender, overdose, seasonal needs, and related cases.
3. Looks up aliases and field indexes from the KB to build candidate page IDs.
4. Scores candidate pages across metadata fields, aliases, address, opening hours, summary, markdown passages, category hints, temporal hints, seasonal hints, exact matches, detail tokens, and manual overrides.
5. Penalizes documents/catalog pages when a concrete location is needed, entries needing review, stale/deprecated/removed/merged entries, conflicts, and missing detail for detail-specific queries.
6. Returns ranked `RetrievedPage` objects with page ID, title, and score.

Clarification and weak-match behavior:

- `should_clarify()` flags generic or ambiguous queries, especially when score gaps are small or top scores are weak.
- `minimum_match_threshold`, `weak_match_threshold`, and `clarification_gap_threshold` are configured in `app/config.py` from environment variables.
- Weak matches are preserved as `status="weak_match"` and get localized weak-match wording in the rewrite/template layer.

Out-of-scope behavior:

- `app/providers/rewrite.py` detects self-description, crisis, and out-of-scope requests before LLM calls.
- Out-of-scope responses are deterministic and redirect users to supported Leipzig help domains.

Sources and evidence:

- Retrieval returns page IDs. The rewrite provider builds an evidence context from the corresponding markdown and metadata.
- The response returns `retrieved_page_ids`; frontend map/source display uses structured page and map data, not free-form model invention.

Map selection:

- `MapBuilder.build_for_answer()` uses retrieved page IDs and includes only concrete service locations with address and Leipzig coordinates.
- It deduplicates by entity signature or normalized title/address.

Current limitations:

- Retrieval is lexical/rule-based, not vector-based.
- Opening-hours logic can hint by weekday, but it does not fully parse all real-world time intervals.
- The KB is primarily German; multilingual matching depends on curated expansions and LLM/template translation.

## 8. LLM / Rewrite Provider

Rewrite providers live in `app/providers/rewrite.py`.

Available providers:

- `TemplateRewriteProvider`: deterministic fallback and baseline. No external model required.
- `OllamaRewriteProvider`: local Ollama chat/generate path.
- `OpenAICompatibleRewriteProvider`: generic `/chat/completions` endpoint.
- `BlabladorRewriteProvider`: OpenAI-compatible subclass with default Blablador base URL.

Selection is controlled by `LENA_REWRITE_PROVIDER` or CLI flags in `python -m app`:

```powershell
python -m app --rewrite-provider template
python -m app --rewrite-provider ollama --ollama-model translategemma:4b
python -m app --rewrite-provider blablador --llm-model alias-large
```

Important environment variables:

- `LENA_REWRITE_PROVIDER`
- `LENA_SYSTEM_PROMPT_PATH`
- `LENA_OLLAMA_URL`
- `LENA_OLLAMA_MODEL`
- `LENA_OLLAMA_TIMEOUT_SECONDS`
- `LENA_LLM_BASE_URL`
- `LENA_LLM_API_KEY`
- `LENA_LLM_MODEL`
- `LENA_LLM_TIMEOUT_SECONDS`
- `LENA_LLM_MAX_TOKENS`
- `LENA_LLM_TEMPERATURE`
- `LENA_LLM_FALLBACK_PROVIDER`

Guardrails:

- Crisis, self-description, out-of-scope, toilet, water, and selected location/detail-sensitive cases are handled deterministically before or around LLM use.
- The LLM prompt includes only retrieved KB evidence and explicitly requires answering only from that evidence.
- The LLM must return JSON matching `LLMKnowledgeAnswer`.
- Invalid JSON, timeouts, HTTP errors, connection errors, schema mismatches, empty answers, unsupported sensitive facts, and unsafe location behavior fall back to deterministic templates.
- Post-validation checks sensitive facts such as numbers, times, phone-like strings, and emails against the evidence context.

The LLM may:

- Rephrase controlled evidence in simple language.
- Translate descriptions into the selected UI language.
- Select concise wording for a stressed user.

The LLM may not:

- Invent services, addresses, opening hours, phone numbers, eligibility, emergency instructions, or diagnoses.
- Use external knowledge beyond retrieved KB evidence.
- Redirect basic location help to search engines or generic external apps when a concrete KB place is available.

## 9. Speech Input and Output

Speech-to-text is implemented in `app/providers/stt.py`.

Providers:

- `faster_whisper`: loads `WhisperModel("small")` with `device="auto"` and `compute_type="auto"`, writes upload data to a temporary file, transcribes with VAD filtering, then deletes the temp file.
- `mock`: returns deterministic sample text per language or a supplied `debug_transcript`.

`create_stt_provider()` attempts faster-whisper when configured and falls back to mock if initialization fails. Supported application languages are `de`, `en`, `pl`, `ro`, and `ru`.

Text-to-speech is implemented in `app/providers/tts.py`.

Providers:

- `piper`: runs the configured Piper binary with a selected language-specific `.onnx` model and matching `.onnx.json`, writes WAV output under `data/runtime/audio/`, and returns `/runtime/audio/<file>.wav`.
- `mock`: returns unavailable so the frontend can use browser TTS where available.

TTS normalization expands common abbreviations, weekday abbreviations, street abbreviations, and German phone numbers for clearer speech. Displayed answer text is not changed by this speech-only normalization.

Known limitations:

- Browser STT/TTS availability depends on browser and OS.
- faster-whisper and Piper require local model files and can be slow on low-power hardware.
- Some existing localized strings contain encoding artifacts and should be reviewed before final user-facing deployment.

## 10. Session Handling

Session handling is implemented in `app/sessions.py`.

Runtime storage:

- `data/runtime/sessions.json`
- `data/runtime/transcripts.jsonl`

Lifecycle:

- New request without a known session creates a `ConversationSession`.
- Sessions are active for `LENA_SESSION_TIMEOUT_SECONDS` seconds, default `300`.
- Expired sessions are marked expired and a new session is created.
- Explicit end marks the session ended and future use creates a new session.
- Language changes reset the session.
- Self-contained topic shifts can reset context when the previous context no longer fits.

Follow-up context:

- Referential follow-ups prefer the last concrete place.
- Alternative requests exclude the previous place family where possible.
- Topic-shift follow-ups preserve a compact history summary.
- The system stores only structured recent turns, page IDs, topics, last intent, and a short answer summary, not the full prompt transcript as model context.

Privacy considerations:

- Runtime transcripts and sessions are local generated files and ignored by Git.
- They may contain personal or sensitive user text and should not be shared or committed.
- `POST /api/admin/transcripts/clear` clears both stores.

## 11. Map Integration

Map backend:

- `app/maps.py`

Map frontend:

- `app/static/app.js`
- `app/static/vendor/leaflet/`

Default origin:

- ID: `leipzig_hbf`
- Label: `Leipzig Hauptbahnhof`
- Address: `Willy-Brandt-Platz 5, 04109 Leipzig`
- Coordinates: `51.3465518`, `12.3830858`

Configuration environment variables:

- `LENA_MAP_TILE_URL_TEMPLATE`
- `LENA_MAP_TILE_ATTRIBUTION`
- `LENA_MAP_TILE_MAX_ZOOM`
- `LENA_MAP_ORIGIN_ID`
- `LENA_MAP_ORIGIN_LABEL`
- `LENA_MAP_ORIGIN_ADDRESS`
- `LENA_MAP_ORIGIN_LATITUDE`
- `LENA_MAP_ORIGIN_LONGITUDE`

Destination generation:

- Only answer statuses `ok` and `weak_match` are map eligible.
- Pages must be concrete service locations, not catalogs/program entries.
- Pages must have address, latitude, longitude, and acceptable geocoding status.
- Coordinates must fall in the configured Leipzig bounding range.
- Out-of-scope locations such as Markkleeberg, Markranstadt/Markranstaedt, and Borna are filtered for runtime maps.
- Distances are calculated with a haversine helper.

Limitations:

- The map shows straight-line distances, not routes.
- It depends on online tile loading unless the tile URL is changed to a local tile source.
- Some symbol data such as toilets and water points is embedded in `app/symbols.py` rather than loaded from the published KB.

## 12. Safety and Guardrails

Safety behavior is spread across retrieval, rewrite, symbols, maintenance, and frontend emergency affordances.

Domain boundaries:

- LENA only answers local Leipzig support-service questions.
- Out-of-scope questions receive deterministic refusal/redirection text.
- Self-description requests receive deterministic explanation text.

Crisis/emergency:

- Crisis wording is detected before external or local LLM use.
- Crisis responses return `status="crisis"` and mention `112` for emergency services and `110` for police danger/violence.
- The emergency symbol action is deterministic and does not need a map.

Medical/legal boundaries:

- Medical symbol text states that it is orientation only and not a diagnosis.
- The system must not invent legal, medical, eligibility, or emergency facts.

Source grounding:

- Answers are based on `retrieved_page_ids`.
- Sensitive facts are post-validated against retrieved evidence for LLM providers.
- Maintenance rules in `KB_MAINTENANCE.md` require evidence for sensitive fields and forbid direct publishing of LLM-generated facts.

Current limitations:

- No authentication is visible on admin endpoints in `app/main.py`; use only in trusted local development contexts.
- LENA cannot guarantee current opening status when source data lacks parseable current-day information.
- The prototype should be evaluated by domain experts before real public deployment.

## 13. Running the Application

Windows PowerShell from the repository root:

```powershell
cd "C:\Users\User\OneDrive\Dokumente\MA Projekt\code"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m app --rewrite-provider template --stt-provider mock --tts-provider mock
```

Open:

```text
http://127.0.0.1:8000/
```

Default command:

```powershell
python -m app
```

Useful local overrides:

```powershell
python -m app --no-reload
python -m app --port 8010
python -m app --rewrite-provider ollama --ollama-model translategemma:4b
python -m app --rewrite-provider blablador --llm-model alias-large
python -m app --stt-provider mock --tts-provider mock
```

Ollama setup:

```powershell
$env:LENA_REWRITE_PROVIDER="ollama"
$env:LENA_OLLAMA_URL="http://127.0.0.1:11434"
$env:LENA_OLLAMA_MODEL="translategemma:4b"
python -m app
```

Blablador setup:

```powershell
$env:LENA_REWRITE_PROVIDER="blablador"
$env:LENA_LLM_BASE_URL="https://api.blablador.fz-juelich.de/v1/"
$env:LENA_LLM_MODEL="alias-large"
$env:LENA_LLM_API_KEY="<your token>"
python -m app
```

Piper setup:

```powershell
$env:LENA_TTS_PROVIDER="piper"
$env:LENA_PIPER_BINARY="tools/piper/piper/piper.exe"
$env:LENA_PIPER_VOICE_DE="data/voices/piper/de_DE-thorsten-high.onnx"
python scripts/test_tts.py --lang de --text "Wo kann ich heute Hilfe bekommen?"
python -m app
```

Keep real secrets in `.env` or environment variables. `.env` is ignored by Git.

## 14. Testing and Evaluation

Run tests:

```powershell
cd "C:\Users\User\OneDrive\Dokumente\MA Projekt\code"
python -m pytest
```

Configured test discovery:

- `pytest.ini` sets `testpaths = tests`.

Test groups:

- `tests/test_api.py`: FastAPI endpoint behavior.
- `tests/test_config.py`: settings and environment handling.
- `tests/test_contract.py`: response/data contract expectations.
- `tests/test_retrieval.py`: retrieval ranking and query handling.
- `tests/test_rewrite.py`: rewrite/template/guardrail behavior.
- `tests/test_scraper.py`: scraper extraction/publishing behavior.
- `tests/test_sessions.py`: session lifecycle and follow-up context.
- `tests/test_maintenance.py`: maintenance report and promotion validation.
- `tests/test_symbols.py`: symbol config/action behavior.
- `tests/test_temporal.py`: date/weekend/season context.
- `tests/test_maps.py`: map destination rules.
- `tests/test_tts.py`: TTS normalization and provider behavior.
- `tests/test_hygiene_queries.py`: hygiene/toilet/shower retrieval behavior.
- `tests/test_eval_dataset.py`: evaluation dataset validity.

Preflight:

```powershell
python scripts/preflight.py
```

Preflight checks Python version, published KB manifest, runtime directories, session timeout, STT/TTS readiness, rewrite provider configuration, and degraded-mode availability.

Evaluation:

```powershell
python scripts/evaluate_models.py
python scripts/evaluate_models.py --provider template
python scripts/evaluate_models.py --provider ollama --models translategemma:4b qwen3:4b
python scripts/evaluate_models.py --provider blablador --models alias-fast alias-large alias-huge
```

Evaluation input:

- `data/evals/assistant_eval_cases.json`

Generated evaluation outputs:

- `data/evals/results/*.json`
- `data/evals/results/*.jsonl`
- `data/evals/results/*.md`

The evaluation runner records retrieved page IDs, answer source, fallback counts, prompt/evidence hashes for LLM runs, provider errors, validation errors, latency, and status distributions.

## 15. Maintenance Workflows

Update KB from configured sources:

```powershell
python -m app.scraper.run
```

or:

```powershell
python scripts/run_kb_maintenance.py --mode incremental
python scripts/run_kb_maintenance.py --mode full
python scripts/run_kb_maintenance.py --mode integrity
python scripts/run_kb_maintenance.py --mode incremental --report-only
```

Generated scraper outputs:

- Raw source snapshots: `data/scraper_workspace/raw/`
- Candidate published data: `data/scraper_workspace/published/`
- Run reports: `data/scraper_workspace/reports/`
- Canonical database: `data/canonical/kb.sqlite3`
- Maintenance reports: `data/maintenance/reports/`

Promote candidate data:

```powershell
curl -X POST http://127.0.0.1:8000/api/admin/published/promote
```

Promotion is blocked by default when validation finds review-needed entries, stale entries, unresolved conflicts, removed/deprecated/merged entries, missing source traceability, missing required files, or missing manifest/index artifacts.

Add or adjust sources:

1. Edit `data/scraper_sources/sources.json`.
2. Add manual intake files under `data/scraper_workspace/intake/` if needed for `manual_files`.
3. Add coordinate corrections to `data/scraper_sources/geo_overrides.json` when automated or embedded geocoding is insufficient.
4. Run scraper/maintenance.
5. Review `data/scraper_workspace/published/` and maintenance reports.
6. Promote only reviewed candidate data.

Adjust categories, aliases, labels:

- Runtime category/service behavior is mostly in `data/scraper_sources/sources.json`, extracted metadata, and `app/retrieval.py`.
- Symbol labels and symbol categories are in `app/symbols.py`.
- Frontend screen labels are in `app/static/app.js`.
- Language enum support is in `app/models.py`.

Adjust prompts/providers:

- General LLM system prompt: `data/prompts/system_prompt.md`.
- Provider selection/configuration: `.env`, `.env.example`, `app/config.py`, and `app/__main__.py`.
- Provider behavior and guardrails: `app/providers/rewrite.py`.

## 16. Known Limitations and TODOs

- KB freshness depends on source updates, scraper runs, review, and promotion.
- The published KB inspected here is from `2026-04-21`; review freshness before using as current live guidance.
- Opening-hours logic is limited and cannot reliably answer all "open now/today" cases.
- Admin endpoints are not visibly authenticated in the FastAPI app.
- Browser STT/TTS support varies by browser, OS, and installed voices.
- faster-whisper and Piper require local models and can be heavy for public-terminal hardware.
- Multilingual quality depends on LLM/template translation and curated strings; some existing strings show encoding artifacts and need review.
- Map distances are straight-line distances, not routing instructions.
- Embedded water/toilet points in `app/symbols.py` should be reviewed against current official datasets.
- Runtime transcripts may contain sensitive text; retention/deletion policy should be defined for real deployments.
- Evaluation is useful for regression testing but is not a substitute for field evaluation with street social work professionals and target users.

## 17. Cleanup Summary

Files removed during this cleanup:

- `.pytest_cache/`: generated pytest cache, ignored by Git, not tracked.
- `app/__pycache__/`: generated Python bytecode, ignored by Git, not tracked.
- `app/providers/__pycache__/`: generated Python bytecode, ignored by Git, not tracked.
- `app/scraper/__pycache__/`: generated Python bytecode, ignored by Git, not tracked.
- `scripts/__pycache__/`: generated Python bytecode, ignored by Git, not tracked.
- `tests/__pycache__/`: generated Python bytecode, ignored by Git, not tracked.
- `tmp_ui_checks/`: untracked temporary UI screenshots; no references found with `rg`.

Files intentionally kept despite being generated or ignored:

- `data/runtime/`: local runtime sessions, transcripts, and audio. Generated, but potentially useful for debugging and sensitive enough to avoid casual deletion.
- `data/scraper_workspace/`: raw snapshots, candidate published data, and scraper reports. Generated, but important for traceability and reproducibility.
- `data/evals/results/`: generated model evaluation outputs. Kept because they can support thesis comparisons.
- `data/voices/piper/` and `tools/piper/`: local model/binary assets required for offline TTS.
- `data/canonical/kb.sqlite3`: canonical scraper history for reproducibility.
- `data/maintenance/`: maintenance workspace and manual overrides.

Files needing future manual review:

- Existing localized strings with mojibake/encoding artifacts in provider and symbol/frontend text.
- Admin endpoint access control if the prototype is used outside trusted local development.
- Freshness and review status of the `20260421054309` published KB.
- Whether generated runtime transcripts/audio should be cleared before archival or sharing.
