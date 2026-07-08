# LENA Architecture

LENA is a closed-domain assistant for help services in Leipzig. It helps people find local support such as food, sleep and emergency accommodation, medical help, clothing, hygiene, social advice, documents, addiction help, water, and urgent help.

LENA supports symbol navigation, typed input, speech input, speech output, result cards, and map display. The application is designed for low-threshold use: short text, clear choices, local facts, and no open internet search at answer time.

## Versions And Entry Points

Version 1 remains the default application.

```powershell
python -m app
```

By default V1 serves the main frontend from `app/static/` and starts on `http://127.0.0.1:8000/` unless another port is passed.

Version 2 is a separate experimental app.

```powershell
python -m app.v2 --port 8001
```

V2 serves its frontend from `app/v2/static/` and uses the V2 curated knowledge base in `data/v2/curated_kb/offers.json`. V2 also mounts the shared Leaflet assets from the V1 static folder so map rendering stays consistent without adding another dependency.

When V2 starts, it automatically prefers the real-provider profile:

- LLM: Blablador/OpenAI-compatible (`LENA_REWRITE_PROVIDER=blablador`, model `alias-large`)
- STT: `faster_whisper`
- TTS: Piper

Missing credentials, dependencies, models, or voice files do not crash the app. They are reported through `/api/health`, and the frontend falls back where possible. To force the degraded test profile, start V2 with `--rewrite-provider template --stt-provider mock --tts-provider mock`.

## Main Components

- Frontend V1: `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`.
- Frontend V2: `app/v2/static/index.html`, `app/v2/static/app.js`, `app/v2/static/styles.css`.
- Backend V1: `app/main.py:create_app`.
- Backend V2: `app/v2/main.py:create_v2_app`.
- Retrieval V1: `app/retrieval.py` over the published local KB.
- Retrieval V2: `app/v2/service.py` over `app/v2/kb.py` and `data/v2/curated_kb/offers.json`.
- Knowledge base V1: `data/published/` plus scraper and maintenance workflow data.
- Knowledge base V2: one reviewed curated dataset generated from Leipzig help-offer source material and the annotated local Markdown files.
- LLM/rewrite providers: `app/providers/rewrite.py` for V1-compatible providers; V2 answer flow lives in `app/v2/service.py` and can use Blablador/OpenAI-compatible intent and answer calls.
- STT: `app/providers/stt.py`, mounted through `/api/speech/transcribe`.
- TTS: `app/providers/tts.py`, mounted through `/api/speech/synthesize`.
- Sessions: `app/sessions.py`.
- Maps and result cards: `app/maps.py`, `app/models.py`, frontend map rendering in V1/V2 JavaScript.

## Request Flow

1. The user selects a language, taps a symbol, types a question, or records speech.
2. If speech is used, the frontend uploads audio to `/api/speech/transcribe`.
3. The frontend sends the text, selected language, session id, and category context to the backend.
4. The backend builds or resumes session context with `app/sessions.py`.
5. The backend detects deterministic special cases first: crisis, self-description, out-of-scope requests, sleep/emergency accommodation mode, and category hints.
6. Retrieval searches the local KB only.
7. Results are ranked by category, keywords, location/map availability, target group, time/weekday hints, and session context where implemented.
8. The answer is produced by a deterministic template or by an LLM rewrite provider using only the retrieved KB context.
9. The backend returns answer text, retrieved ids, evidence/sources, result cards, and map marker data.
10. The frontend renders the answer, cards, map, and optional TTS audio.

Text diagram:

```text
User
-> Frontend V1/V2
-> Backend API
-> Intent detection / session context
-> Retrieval over local KB
-> Deterministic templates or LLM rewrite provider
-> Answer + cards + map markers
-> Frontend display
-> optional TTS output
```

## Knowledge Sources

LENA answers must be grounded in the local curated knowledge base. The LLM does not freely search the internet and must not invent offers, addresses, phone numbers, opening hours, costs, target groups, or requirements.

V1 reads the published KB under `data/published/`.

V2 reads `data/v2/curated_kb/offers.json`. The V2 KB is built from the annotated source material in:

- `data/wissensbasis_hilfsangebote_leipzig_annotiert.md`
- `data/keyword_uebersicht_hilfsangebote_leipzig.md`
- `data/v2/curated_kb/sources.json`

The build script is `scripts/build_v2_kb_from_annotated_md.py`. It keeps source URLs, source evidence, detail URLs, reviewed status, map coordinates, card summaries, keywords, facts, and last-checked metadata.

If a fact is not in the KB, LENA should say that it has no suitable listed information or ask the user to check/contact the offer. If a deterministic template is used, the template class is visible through the response status or mode, for example `self_description`, `out_of_scope`, `crisis`, symbol category answer, or sleep response mode.

## LLM Providers

The repository supports template fallback, local Ollama-style providers, Blablador, and generic OpenAI-compatible endpoints.

Provider selection is controlled through CLI flags or environment/config values such as:

```powershell
python -m app.v2 --port 8001
python -m app.v2 --port 8001 --rewrite-provider blablador
python -m app.v2 --port 8001 --rewrite-provider template
```

Relevant configuration is in `app/config.py` and the V2 app factory. The active provider and model can be checked at:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/health
```

The LLM may help with multilingual understanding and answer formulation. It receives the selected UI language, compact session context, the inferred intent, and controlled fields from retrieved KB offers. It must not decide facts. V2 also uses deterministic paths for crisis, self-description, out-of-scope, symbol category answers, and sleep/emergency accommodation routing.

If an LLM provider is unavailable, lacks credentials, times out, returns invalid JSON, or fails schema validation, LENA falls back to deterministic/template behavior where possible. The health endpoint reports `configured_rewrite_provider`, `llm_active`, `llm_base_url_configured`, `llm_api_key_configured`, active provider, and model.

## STT

Speech-to-text is implemented in `app/providers/stt.py`.

Available providers:

- `faster_whisper`: intended local STT backend.
- `mock`: test/debug backend.

Endpoint:

```text
POST /api/speech/transcribe
```

The endpoint accepts multipart form data:

- `audio`: uploaded browser audio, for example `webm` or `wav`.
- `language`: one of `de`, `en`, `pl`, `ro`, `ru`.
- `debug_transcript`: optional explicit test transcript.

Response fields include:

- `transcript`: backward-compatible transcript field.
- `text`: same transcript text for structured consumers.
- `language`: selected/known language.
- `provider`
- `status`
- `detail`

Mock STT is debug-only. It never pretends to recognize real audio. If the mock provider is active and no explicit `debug_transcript` is sent, the endpoint returns a graceful error and the UI should let the user type instead. If `faster-whisper` or its model cannot initialize, provider creation falls back safely and reports the reason in health output.

The health output includes `speech.stt.real_audio`. It is `false` for mock STT and `true` for real STT providers.

Manual STT test with mock/debug:

```powershell
$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value "mock audio placeholder"
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/api/speech/transcribe `
  -Form @{ language = "de"; debug_transcript = "Ich brauche Medizin."; audio = Get-Item $tmp }
Remove-Item $tmp
```

For real STT, install/configure `faster-whisper`, start LENA with `--stt-provider faster_whisper`, then test through the browser microphone or upload a real browser/audio recording.

Known limitations:

- Real STT depends on local `faster-whisper` installation and model availability.
- Browser recording support depends on browser permissions and supported audio formats.

## TTS

Text-to-speech is implemented in `app/providers/tts.py`.

Available providers:

- `piper`: intended local/offline TTS backend.
- `mock`: test/debug backend.

Endpoint:

```text
POST /api/speech/synthesize
```

Request:

```json
{
  "text": "Ich bin LENA.",
  "language": "de"
}
```

Response:

- `status`: `ok`, `unavailable`, or `error`.
- `provider`
- `audio_url` when synthesis succeeds.
- `detail` for errors.

Piper voices are configured through environment/config paths. If the binary or voice model is missing, LENA returns `unavailable` instead of crashing. Generated audio is served from `/runtime/audio/...`.

The health output includes `speech.tts.audio_output`. It is `false` for mock TTS and `true` for real audio-producing TTS providers.

V2 can request startup intro speech once after explicit language selection:

- German: "Ich bin LENA und helfe dir bei Fragen zum Hilfesystem in Leipzig. Klicke auf das passende Symbol oder frage mich direkt im Chat."
- English: "I am LENA and I help you with questions about support services in Leipzig. Click the right symbol or ask me directly in the chat."

The frontend does not block if TTS fails. Answer speech uses the same endpoint and selected language. V1 and V2 can fall back to browser `speechSynthesis` when backend TTS is unavailable.

Manual TTS test:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/api/speech/synthesize `
  -ContentType "application/json" `
  -Body '{"text":"Ich bin LENA.","language":"de"}'
```

Known limitations:

- Voice availability depends on local Piper model files.
- If a configured female voice is missing for a language, the provider falls back according to configured local voices or reports unavailable.

## Map And Cards

Both versions return structured map data with a Leipzig Hauptbahnhof origin and destination markers when offers have coordinates. V2 result cards carry user-facing fields such as title, short description, target group, address, time, phone, services, notes, and source metadata. The frontend uses the shared Leaflet assets and keeps names/addresses in German while localizing generic labels.

## Smoke Tests

V1 quick check:

```powershell
python -m app --port 8000 --rewrite-provider template --stt-provider mock --tts-provider mock
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Manual V1 browser check:

- Open `http://127.0.0.1:8000/`.
- Select a language.
- Ask a typed query.
- Confirm answer, result data, and map still render.

V2 quick check:

```powershell
python -m app.v2 --port 8001
Invoke-RestMethod http://127.0.0.1:8001/api/health
```

For a deliberate mock/template smoke test:

```powershell
python -m app.v2 --port 8001 --rewrite-provider template --stt-provider mock --tts-provider mock
```

Manual V2 browser check:

- Open `http://127.0.0.1:8001/`.
- Select a language.
- Confirm the intro text appears and TTS failure does not block the UI.
- Tap Food, Sleep, Medical, and Advice.
- Confirm cards and map markers appear.
- Ask "Wo kann ich am Mittwoch schlafen?" and use target-group follow-up buttons.
- Check that speech with mock STT reports unavailable unless `debug_transcript` is explicitly used.

## Cleanup Notes

The repository contains workflow directories that may be empty but are meaningful, for example maintenance, review, source-check, and scraper intake folders. Do not delete those only because they are empty. Generated runtime files under `data/runtime/` can be cleaned carefully when they are known screenshots, temporary source snapshots, or audio/session artifacts no longer needed for debugging.
