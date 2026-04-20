from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_root: Path
    data_root: Path
    prompt_root: Path
    system_prompt_path: Path
    published_root: Path
    scraper_workspace_root: Path
    scraper_published_root: Path
    scraper_raw_root: Path
    scraper_reports_root: Path
    runtime_root: Path
    transcripts_path: Path
    audio_root: Path
    source_registry: Path
    stt_provider: str
    rewrite_provider: str
    tts_provider: str
    ollama_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    piper_binary: str
    minimum_match_threshold: float
    weak_match_threshold: float
    clarification_gap_threshold: float
    bootstrap_runtime_from_scraper: bool


def load_settings() -> Settings:
    app_root = Path(__file__).resolve().parent.parent
    data_root = app_root / "data"
    prompt_root = data_root / "prompts"
    raw_system_prompt_path = Path(os.getenv("LENA_SYSTEM_PROMPT_PATH", prompt_root / "system_prompt.md"))
    system_prompt_path = raw_system_prompt_path if raw_system_prompt_path.is_absolute() else app_root / raw_system_prompt_path
    published_root = data_root / "published"
    scraper_workspace_root = data_root / "scraper_workspace"
    scraper_published_root = scraper_workspace_root / "published"
    scraper_raw_root = scraper_workspace_root / "raw"
    scraper_reports_root = scraper_workspace_root / "reports"
    runtime_root = data_root / "runtime"
    transcripts_path = runtime_root / "transcripts.jsonl"
    audio_root = runtime_root / "audio"
    source_registry = data_root / "scraper_sources" / "sources.json"

    runtime_root.mkdir(parents=True, exist_ok=True)
    audio_root.mkdir(parents=True, exist_ok=True)
    prompt_root.mkdir(parents=True, exist_ok=True)
    scraper_workspace_root.mkdir(parents=True, exist_ok=True)
    scraper_published_root.mkdir(parents=True, exist_ok=True)
    scraper_raw_root.mkdir(parents=True, exist_ok=True)
    scraper_reports_root.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_root=app_root,
        data_root=data_root,
        prompt_root=prompt_root,
        system_prompt_path=system_prompt_path,
        published_root=published_root,
        scraper_workspace_root=scraper_workspace_root,
        scraper_published_root=scraper_published_root,
        scraper_raw_root=scraper_raw_root,
        scraper_reports_root=scraper_reports_root,
        runtime_root=runtime_root,
        transcripts_path=transcripts_path,
        audio_root=audio_root,
        source_registry=source_registry,
        stt_provider=os.getenv("LENA_STT_PROVIDER", "faster_whisper"),
        rewrite_provider=os.getenv("LENA_REWRITE_PROVIDER", "ollama"),
        tts_provider=os.getenv("LENA_TTS_PROVIDER", "mock"),
        ollama_url=os.getenv("LENA_OLLAMA_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("LENA_OLLAMA_MODEL", "translategemma:4b"),
        ollama_timeout_seconds=float(os.getenv("LENA_OLLAMA_TIMEOUT_SECONDS", "45")),
        piper_binary=os.getenv("LENA_PIPER_BINARY", "piper"),
        minimum_match_threshold=float(os.getenv("LENA_MINIMUM_MATCH_THRESHOLD", "0.08")),
        weak_match_threshold=float(os.getenv("LENA_WEAK_MATCH_THRESHOLD", "0.18")),
        clarification_gap_threshold=float(os.getenv("LENA_CLARIFICATION_GAP_THRESHOLD", "0.03")),
        bootstrap_runtime_from_scraper=os.getenv("LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER", "true").lower() in {"1", "true", "yes", "on"},
    )
