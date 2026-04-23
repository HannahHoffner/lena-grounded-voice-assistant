# LENA Grounded Voice Assistant

This repository contains a local grounded voice assistant for Leipzig support services.
It combines speech input, retrieval over a small `llm-wiki` knowledge base, grounded answer generation, and optional local text-to-speech.

## Structure

- `app/`: backend API, providers, scraper pipeline, and static frontend
- `data/published/`: pinned runtime KB artifacts consumed by the app
- `data/scraper_sources/`: source registry for the scraper track
- `data/scraper_workspace/`: isolated scraper outputs (`raw/`, `published/`)
- `tests/`: contract, API, and scraper tests

## Runtime Contract

The runtime only reads published KB artifacts from `data/published/`:

- `pages/*.md`
- `index/pages.json`
- `index/manifest.json`
- `index/aliases.json`

The scraper now also maintains a canonical SQLite KB and richer runtime exports:

- canonical build DB: `data/canonical/kb.sqlite3`
- `index/entities.jsonl`
- `index/alias_index.json`
- `index/field_indexes/*.json`
- `index/runtime_snapshot.sqlite`

The scraper track generates its own artifacts under `data/scraper_workspace/published/`.
Those artifacts are promoted into the runtime KB only when explicitly requested.

## Quick Start

```powershell
cd Code
pip install -r requirements.txt
python -m app
```

Open `http://127.0.0.1:8000/`.

The UI includes both speech input and a small typed-question field so retrieval can be tested even when local or browser STT is unavailable.

Optional one-command overrides:

```powershell
python -m app --rewrite-provider ollama --ollama-model translategemma:4b
python -m app --stt-provider mock --tts-provider mock
python -m app --no-reload
```

## Default Providers

The app now starts with the local LLM answer path enabled by default:

- STT: `faster_whisper`, with automatic fallback to `mock` if the backend cannot be initialized
- rewrite: `ollama`
- default Ollama model: `translategemma:4b`
- TTS: `mock` unless `piper` is configured

Environment variables:

```powershell
$env:LENA_STT_PROVIDER="faster_whisper"
$env:LENA_REWRITE_PROVIDER="ollama"
$env:LENA_TTS_PROVIDER="piper"
$env:LENA_OLLAMA_MODEL="translategemma:4b"
$env:LENA_SYSTEM_PROMPT_PATH="data/prompts/system_prompt.md"
```

The editable Ollama system prompt lives in `data/prompts/system_prompt.md`.

## Test

```powershell
cd Code
python -m pytest
```

## Evaluation

The reusable model-evaluation baseline lives in `data/evals/assistant_eval_cases.json`.
Run the shared grounded evaluation pipeline with:

```powershell
cd Code
python scripts/evaluate_models.py
```

Timestamped reports are written to `data/evals/results/` and are treated as generated artifacts rather than tracked source files.

## Separate Scraper Track

Run the scraper without changing the runtime KB:

```powershell
cd Code
python -m app.scraper.run
```

Each scraper run writes:
- raw snapshots to `data/scraper_workspace/raw/`
- published candidate artifacts to `data/scraper_workspace/published/`
- a run report to `data/scraper_workspace/reports/`
- canonical entity/document history to `data/canonical/kb.sqlite3`

Promote the latest scraper output into the runtime KB:

```powershell
curl -X POST http://127.0.0.1:8000/api/admin/published/promote
```

Run the scheduled maintenance entrypoint:

```powershell
cd Code
python scripts/run_kb_maintenance.py --mode incremental
python scripts/run_kb_maintenance.py --mode full
```
