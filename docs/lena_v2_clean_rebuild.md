# LENA v2 Clean Rebuild

## Purpose

LENA v2 is a clean experimental rebuild beside the stable LENA v1 runtime.
V1 remains the fallback and continues to start through:

```powershell
python -m app
```

V2 starts separately:

```powershell
python -m app.v2 --port 8001
```

## What Changed

The old v2 attempt was removed from the active rebuild branch and preserved in a backup branch before this work.
The new v2 code lives under `app/v2/`.
Shared v1 files only expose backward-compatible response fields for source/evidence metadata.

## Source Policy

The v2 runtime KB is intentionally small.
The authoritative source is:

https://www.leipzig.de/leben-in-leipzig/gesundheit/suchthilfe/schadensminimierung

Allowed detail pages are only pages directly linked from that source page, or directly linked provider detail pages needed to complete facts for an offer already listed there.
Broad v1 offers, unrelated social services, and Tafel are excluded unless the authoritative source page lists them and they fit the scenario.

Runtime does not depend on live scraping.
The reviewed KB is stored in:

```text
data/v2/curated_kb/offers.json
```

Source metadata is stored in:

```text
data/v2/curated_kb/sources.json
```

## KB Maintenance

Run the source checker:

```powershell
python scripts/check_v2_sources.py
```

The checker fetches the Leipzig page, saves raw and text snapshots under `data/v2/source_checks/`, computes hashes, validates reviewed offers, and writes JSON/Markdown reports.
It does not update the runtime KB.

Publishing a v2 KB update should follow this sequence:

1. Run the source checker.
2. Review source snapshots, hashes, and report.
3. Update structured offers by hand or through a reviewed extraction step.
4. Ensure every offer has source evidence.
5. Run `python -m pytest tests/test_v2_clean.py`.
6. Run the full v1/v2 regression suite with `python -m pytest`.

## Runtime Architecture

V2 uses:

- `app/v2/main.py` for the separate FastAPI app factory.
- `app/v2/kb.py` for a reviewed one-source KB loader compatible with shared session/map protocols.
- `app/v2/service.py` for intent handling, retrieval, deterministic safety paths, and optional Blablador/OpenAI-compatible answer generation.
- `app/v2/static/` for the separate low-literacy UI.

Shared components reused from v1:

- STT provider in `app/providers/stt.py`.
- TTS provider in `app/providers/tts.py`.
- Session handling in `app/sessions.py`.
- Temporal context in `app/temporal.py`.
- Map rendering support in `app/maps.py`.

## LLM Role

Blablador/OpenAI-compatible providers may be used in v2 for intent extraction and multilingual answer generation.
The selected UI language is passed explicitly.
The KB remains German and source-grounded.
The LLM must not invent phone numbers, times, addresses, requirements, costs, medical advice, or legal advice.
Deterministic crisis and out-of-scope paths bypass the LLM.

## UI Strategy

After language selection, v2 shows four primary help symbols:

- Essen
- Schlafen
- Medizin
- Beratung

The voice mode is separate under `Sprich mit mir`.
Speech input shows a transcript review panel before sending, so users can edit or cancel the recognized text.

## TTS Voices

V2 reuses local Piper TTS.
German prefers `de_DE-ramona-low` when available and no explicit `LENA_PIPER_VOICE_DE` is set.
Female voices for English, Polish, Romanian, and Russian are not confirmed in the current local inventory, so v2 reports a documented local fallback limitation in `/api/health`.

## Current Limitations

- The reviewed v2 KB is hand-structured from the source snapshot and should be reviewed by a domain expert before field deployment.
- Many offers on the source page do not expose full addresses, coordinates, or precise times.
- V2 multilingual answers are deterministic unless Blablador/OpenAI-compatible credentials are configured.
- Voice gender quality must be reviewed with generated audio samples before thesis/demo claims.
