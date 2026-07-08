# LENA Grounded Voice Assistant

This repository contains a local grounded voice assistant for Leipzig support services.
It combines speech input, retrieval over a small `llm-wiki` knowledge base, grounded answer generation, and optional local text-to-speech.

For the full thesis-friendly technical overview, see [`docs/lena_system_overview.md`](docs/lena_system_overview.md).

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
cd code
pip install -r requirements.txt
python -m app
```

Open `http://127.0.0.1:8000/`.

The UI includes both speech input and a small typed-question field so retrieval can be tested even when local or browser STT is unavailable.

## LENA v2 Clean Prototype

LENA v1 remains the default and uses the published KB in `data/published/`.
The clean v2 prototype runs as a separate FastAPI app so it can be rebuilt without changing v1 behavior.

```powershell
cd code
python -m app.v2 --port 8001
```

Open `http://127.0.0.1:8001/`.

By default, the v2 app now starts with the real-provider profile:

- LLM: `blablador`
- STT: `faster_whisper`
- TTS: `piper`

If the Blablador API key, Whisper dependency/model, Piper binary, or Piper voice files are missing, v2 keeps running and reports the fallback/availability state in `/api/health`. For a deliberate degraded test run, pass explicit overrides:

```powershell
python -m app.v2 --port 8001 --rewrite-provider template --stt-provider mock --tts-provider mock
```

V2 uses `data/v2/curated_kb/offers.json`, a small reviewed KB derived from the Leipzig Schadensminimierung source page:

https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung

The v2 runtime does not scrape the live page. To check whether the source page changed and create review snapshots/reports, run:

```powershell
python scripts/check_v2_sources.py
```

Manual review is required before publishing any v2 KB update. See `docs/lena_v2_clean_rebuild.md`.

Optional one-command overrides:

```powershell
python -m app --rewrite-provider ollama --ollama-model translategemma:4b
python -m app --rewrite-provider blablador --llm-model alias-large
python -m app --stt-provider mock --tts-provider mock
python -m app --no-reload
```

## Default Providers

The app now starts with the local LLM answer path enabled by default:

- STT: `faster_whisper`, with automatic fallback to `mock` if the backend cannot be initialized
- rewrite: `ollama`
- default Ollama model: `translategemma:4b`
- TTS: `mock` unless `piper` is configured
- external rewrite options: `blablador` and `openai_compatible`, both with deterministic template fallback

Environment variables:

```powershell
$env:LENA_LLM_API_KEY="<your Blablador token for v2>"
$env:LENA_STT_PROVIDER="faster_whisper"
$env:LENA_REWRITE_PROVIDER="ollama"
$env:LENA_TTS_PROVIDER="piper"
$env:LENA_OLLAMA_MODEL="translategemma:4b"
$env:LENA_SYSTEM_PROMPT_PATH="data/prompts/system_prompt.md"
```

The editable Ollama system prompt lives in `data/prompts/system_prompt.md`.

## Speech API Setup And Manual Checks

Speech input and output are provider-based backend APIs shared by V1 and V2.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8001/api/health
```

STT endpoint:

```text
POST /api/speech/transcribe
```

Mock STT is for tests and explicit debugging only. It does not pretend to recognize real audio. Without `debug_transcript`, mock STT returns a graceful error so the UI can offer typed input.

Debug STT test:

```powershell
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value "mock audio placeholder"
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/api/speech/transcribe `
  -Form @{ language = "de"; debug_transcript = "Ich brauche Medizin."; audio = Get-Item $tmp }
Remove-Item $tmp
```

Real STT uses `faster-whisper` when configured:

```powershell
python -m app.v2 --port 8001 --stt-provider faster_whisper --tts-provider mock --rewrite-provider template
```

If `faster-whisper` or the local model cannot initialize, LENA falls back gracefully and reports the reason in `/api/health`.

TTS endpoint:

```text
POST /api/speech/synthesize
```

Mock TTS returns `status=unavailable`. Piper is used when configured with a local binary and voice files. If backend TTS is unavailable, the frontend can fall back to browser `speechSynthesis`.

Manual TTS test:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/api/speech/synthesize `
  -ContentType "application/json" `
  -Body '{"text":"Ich bin LENA.","language":"de"}'
```

## Answer Style and Safety

User-facing answers should use simple language: short sentences, direct wording, and one idea per sentence where possible. Internal terms such as knowledge base, retrieval, context, provider, or database must not appear in end-user fallback answers.

For unknown or out-of-scope requests, LENA uses short deterministic messages and redirects users to supported local-help topics such as food, sleeping places, clothing, medical help, counselling, hygiene, documents, and water.

For basic help-location questions, LENA must not shift the task to external apps, websites, online search, or Google Maps. External links may stay in source metadata and may be shown only as secondary evidence. The answer itself should name concrete local places from the curated KB when the user asks for water, food, sleeping places, clothing, hygiene, medical help, counselling, or similar help. If the KB does not contain a safe concrete place, LENA says this plainly instead of telling the user to find it somewhere else.

Acute dangerous situations are handled before any external or local LLM call. Self-harm intent, intent to harm others, violence, immediate danger, overdose, poisoning, unconsciousness, severe injury, severe bleeding, breathing problems, chest pain, freezing, and similar emergency wording return `status=crisis` with a deterministic short response. Crisis responses mention 112 for emergency services and 110 for police danger or violence. This is not a replacement for emergency services, medical care, or professional counselling.

## Local Piper TTS Voices

LENA keeps text-to-speech local by using Piper when `LENA_TTS_PROVIDER=piper` is configured. Voice selection is language-specific, so the backend chooses the configured voice for the request/UI language (`de`, `en`, `pl`, `ro`, `ru`). If a language-specific voice is unavailable, LENA falls back to `LENA_PIPER_DEFAULT_VOICE` when configured; otherwise the synthesize endpoint returns unavailable and the existing browser/system TTS fallback can be used by the frontend.

Download Piper voices from the `rhasspy/piper-voices` repository on Hugging Face:

https://huggingface.co/rhasspy/piper-voices

Each voice requires both files:

- `<voice>.onnx`
- `<voice>.onnx.json`

Place them under a local directory such as `data/voices/piper/` and configure paths in `.env`:

```powershell
$env:LENA_TTS_PROVIDER="piper"
$env:LENA_PIPER_BINARY="tools/piper/piper/piper.exe"
$env:LENA_PIPER_VOICE_DE="data/voices/piper/<german-voice>.onnx"
$env:LENA_PIPER_VOICE_EN="data/voices/piper/<english-voice>.onnx"
$env:LENA_PIPER_VOICE_PL="data/voices/piper/<polish-voice>.onnx"
$env:LENA_PIPER_VOICE_RO="data/voices/piper/<romanian-voice>.onnx"
$env:LENA_PIPER_VOICE_RU="data/voices/piper/<russian-voice>.onnx"
$env:LENA_TTS_NORMALIZE_UMLAUTS="false"
```

Piper normally uses the matching config file at the same path plus `.json`, for example `data/voices/piper/<english-voice>.onnx.json`. If needed, set `LENA_PIPER_VOICE_CONFIG_DE`, `LENA_PIPER_VOICE_CONFIG_EN`, `LENA_PIPER_VOICE_CONFIG_PL`, `LENA_PIPER_VOICE_CONFIG_RO`, or `LENA_PIPER_VOICE_CONFIG_RU` explicitly.

Prefer medium or high quality voices for user-facing evaluation. Voice gender, warmth, intelligibility, and naturalness should be evaluated subjectively per language; do not assume that a voice name or metadata alone is sufficient for LENA's target setting.

Before text is sent to Piper, LENA applies speech-only normalization. The displayed answer text is not changed. German phone numbers such as `112`, `110`, `116 117`, `0341 123456`, and `+49 341 123456` are spoken digit by digit or in small groups. Common German abbreviations such as `z. B.`, `bzw.`, `ca.`, `Dr.`, `Tel.`, and weekday abbreviations are expanded for clearer speech.

German umlauts are preserved by default because many Piper voices handle real UTF-8 text correctly. If a specific voice reads umlauts poorly, set `LENA_TTS_NORMALIZE_UMLAUTS=true` to transliterate umlauts for speech only, for example `ü` to `ue` and `ß` to `ss`.

Generate a quick local sample:

```powershell
python scripts/test_tts.py --lang en --text "Where can I get help today?"
```

## Temporal and Seasonal Context

For each answer request, LENA computes local temporal context deterministically in the backend. The default timezone is `Europe/Berlin` and can be changed with `LENA_TIMEZONE`. The context includes date, weekday, weekend flag, month, and a coarse season.

Seasonal context is only a retrieval and formulation hint. It is not a source of new facts: winter or summer advice may only mention services already present in the retrieved KB context. Likewise, "today" answers depend on available KB opening-hours evidence. If today's opening status cannot be determined reliably, LENA should say that instead of guessing.

The runtime KB is primarily German. Answer language is controlled separately: LLM prompts require German KB descriptions to be translated into the requested answer language while keeping official names, organization names, addresses, street names, and source titles unchanged. The deterministic template path avoids copying long German descriptions into non-German answers.

## Blablador and OpenAI-Compatible LLMs

LENA can use Blablador as an experimental academic LLM provider through the same grounded rewrite path used by local models. The LLM is not a knowledge source: retrieval still selects a small KB context first, the prompt instructs the model to answer only from that context, and invalid or ungrounded output falls back to `TemplateRewriteProvider`.

Crisis cases bypass Blablador, OpenAI-compatible providers, and Ollama. The deterministic crisis response is returned before any model client is called.

Blablador configuration:

```powershell
$env:LENA_REWRITE_PROVIDER="blablador"
$env:LENA_LLM_BASE_URL="https://api.blablador.fz-juelich.de/v1/"
$env:LENA_LLM_MODEL="alias-large"
$env:LENA_LLM_API_KEY="<your token>"
```

To obtain the API key, register or log in at Helmholtz Codebase, create a GitLab Personal Access Token with `read_user` scope, and store it locally as `LENA_LLM_API_KEY`. Do not commit real tokens; `.env` files are ignored by Git.

Recommended Blablador aliases:

- `alias-fast` for latency-oriented tests
- `alias-large` for balanced quality and speed
- `alias-huge` for quality-oriented but slower tests

Concrete model availability can change, so prefer aliases where possible. You can list available model IDs with:

```powershell
python scripts/list_openai_models.py
```

For another OpenAI-compatible endpoint, use `LENA_REWRITE_PROVIDER=openai_compatible` plus `LENA_LLM_BASE_URL`, `LENA_LLM_API_KEY`, and `LENA_LLM_MODEL`.

## Test

```powershell
cd code
python -m pytest
```

## Evaluation

The reusable model-evaluation baseline lives in `data/evals/assistant_eval_cases.json`.
Run the shared grounded evaluation pipeline with:

```powershell
cd code
python scripts/evaluate_models.py
```

Useful variants:

```powershell
python scripts/evaluate_models.py --provider template
python scripts/evaluate_models.py --provider ollama --models translategemma:4b qwen3:4b
python scripts/evaluate_models.py --provider ollama --models qwen3:8b gemma3:12b
python scripts/evaluate_models.py --provider blablador --models alias-fast alias-large alias-huge
```

The evaluation runner records the resolved query, retrieved page IDs, evidence context hash, prompt hashes for LLM runs, answer source, provider errors, validation errors, answer-status distribution, fallback counts, and latency statistics. This makes model comparisons reproducible under the same local KB, prompts, and test cases. The template provider is useful as a deterministic baseline; Ollama model runs should start with installed small models before trying larger local models. Blablador evaluation sends only predefined test questions and retrieved KB context.

Timestamped JSON, JSONL, and Markdown reports are written to `data/evals/results/` and are treated as generated artifacts rather than tracked source files.

## Grounding and Session Safety

LENA keeps conversation context as compact structured state rather than passing the full chat history to the model. Sessions track the selected language, recent turns, last intent/topic/place, last retrieved pages, a short answer summary, clarification state, timeout, and explicit end/reset events.

For local LLM answers, deterministic retrieval and guardrails run before model generation. Detail-sensitive follow-ups such as addresses, opening hours, appointment requirements, and missing details use the grounded template path when needed. LLM output is post-validated for sensitive facts such as numbers, times, phone-like strings, and email addresses; unsupported details fall back to the deterministic answer.

## Separate Scraper Track

Run the scraper without changing the runtime KB:

```powershell
cd code
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
cd code
python scripts/run_kb_maintenance.py --mode incremental
python scripts/run_kb_maintenance.py --mode full
```
