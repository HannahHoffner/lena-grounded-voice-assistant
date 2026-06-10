from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.config import load_settings
from app.providers.stt import create_stt_provider
from app.providers.tts import create_tts_provider


MIN_PYTHON = (3, 11)


def _check(name: str, ok: bool, detail: str) -> tuple[bool, str]:
    status = "OK" if ok else "WARN"
    print(f"[{status}] {name}: {detail}")
    return ok, detail


def main() -> int:
    settings = load_settings()
    checks: list[bool] = []

    python_ok = sys.version_info >= MIN_PYTHON
    checks.append(_check("python", python_ok, f"{sys.version.split()[0]} (recommended {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)")[0])

    manifest_path = settings.published_root / "index" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        checks.append(_check("kb", True, f"published KB {manifest.get('kb_version', 'unknown')} with {manifest.get('page_count', '?')} pages")[0])
    else:
        checks.append(_check("kb", False, f"missing published KB manifest at {manifest_path}")[0])

    runtime_ok = settings.runtime_root.exists() and settings.audio_root.exists()
    checks.append(_check("runtime_dirs", runtime_ok, f"runtime={settings.runtime_root} audio={settings.audio_root}")[0])
    checks.append(_check("sessions", settings.session_timeout_seconds > 0, f"timeout={settings.session_timeout_seconds}s store={settings.sessions_path}")[0])

    stt_provider = create_stt_provider(settings.stt_provider)
    stt_health = stt_provider.health()
    checks.append(
        _check(
            "stt",
            bool(stt_health["ready"]),
            f"configured={stt_health['configured_provider']} active={stt_health['active_provider']} detail={stt_health['detail'] or 'ready'}",
        )[0]
    )

    tts_provider = create_tts_provider(
        settings.tts_provider,
        settings.piper_binary,
        settings.piper_voice_models,
        settings.piper_voice_configs,
        settings.piper_default_voice_model,
        settings.piper_default_voice_config,
    )
    tts_health = tts_provider.health()
    checks.append(
        _check(
            "tts",
            bool(tts_health["ready"]),
            f"configured={tts_health['configured_provider']} active={tts_health['active_provider']} detail={tts_health['detail'] or 'ready'}",
        )[0]
    )

    if settings.rewrite_provider == "ollama":
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.ollama_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                tags = response.json().get("models", [])
            installed_models = {item.get("name", "") for item in tags if isinstance(item, dict)}
            model_ok = settings.ollama_model in installed_models
            detail = f"reachable at {settings.ollama_url}; model={settings.ollama_model}"
            if not model_ok:
                detail += " not installed"
            checks.append(_check("ollama", model_ok, detail)[0])
        except Exception as exc:
            checks.append(_check("ollama", False, f"unreachable at {settings.ollama_url}: {exc}")[0])
    elif settings.rewrite_provider in {"openai_compatible", "blablador"}:
        provider_label = settings.rewrite_provider
        configured = bool(settings.llm_base_url and settings.llm_api_key)
        detail = f"configured={configured}; base_url={settings.llm_base_url or 'missing'}; model={settings.llm_model}"
        if not settings.llm_api_key:
            detail += "; api_key=missing"
        checks.append(_check(provider_label, configured, detail)[0])
    else:
        checks.append(_check("llm", True, "template mode selected; LLM provider not required")[0])

    degraded_mode_ok = settings.rewrite_provider == "template" and settings.stt_provider == "mock" and settings.tts_provider == "mock"
    checks.append(
        _check(
            "degraded_mode",
            True,
            "enabled" if degraded_mode_ok else "available via LENA_REWRITE_PROVIDER=template, LENA_STT_PROVIDER=mock, LENA_TTS_PROVIDER=mock",
        )[0]
    )

    return 0 if all(checks[:3]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
