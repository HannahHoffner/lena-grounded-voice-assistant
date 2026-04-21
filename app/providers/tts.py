from __future__ import annotations

import re
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Language


class BaseTtsProvider(ABC):
    name = "base"
    configured_name = "base"
    ready = True
    detail: str | None = None
    fallback_from: str | None = None

    @abstractmethod
    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        raise NotImplementedError

    def health(self) -> dict[str, object]:
        return {
            "configured_provider": self.configured_name,
            "active_provider": self.name,
            "ready": self.ready,
            "detail": self.detail,
            "fallback_from": self.fallback_from,
        }


class MockTtsProvider(BaseTtsProvider):
    name = "mock"

    def __init__(self, *, configured_name: str = "mock", detail: str | None = None, fallback_from: str | None = None) -> None:
        self.configured_name = configured_name
        self.detail = detail
        self.fallback_from = fallback_from
        self.ready = fallback_from is None

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        return None


class PiperTtsProvider(BaseTtsProvider):
    name = "piper"

    def __init__(self, binary: str, voice_models: dict[str, str] | None = None) -> None:
        self.binary = binary
        self.voice_models = voice_models or {}
        self.configured_name = self.name
        self.detail = _describe_piper_health(binary, self.voice_models)

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        output_path = audio_root / f"{uuid.uuid4().hex}.wav"
        normalized_text = normalize_tts_text(text, language)
        command = [
            self.binary,
            "--output_file",
            str(output_path),
        ]
        model = self.voice_models.get(language.value)
        if model:
            command.extend(["--model", model])
        subprocess.run(command, input=normalized_text.encode("utf-8"), check=True)
        return f"/runtime/audio/{output_path.name}"


def normalize_tts_text(text: str, language: Language) -> str:
    normalized = " ".join((text or "").split()).strip()
    if not normalized:
        return normalized

    replacements = [
        ("AWW", "Advent Wohlfahrtswerk" if language == Language.DE else "Advent Welfare Association"),
        ("DRK", "Deutsches Rotes Kreuz" if language == Language.DE else "German Red Cross"),
        ("SZL", "Suchtzentrum Leipzig" if language == Language.DE else "Leipzig addiction support center"),
        ("e.V.", "eingetragener Verein" if language == Language.DE else "registered association"),
        ("gGmbH", "gemeinnuetzige Gesellschaft mit beschraenkter Haftung" if language == Language.DE else "non profit limited company"),
        ("z. B.", "zum Beispiel" if language == Language.DE else "for example"),
        ("u. a.", "unter anderem" if language == Language.DE else "among other things"),
        ("Mo-Fr", "Montag bis Freitag" if language == Language.DE else "Monday to Friday"),
        ("Mo – Fr", "Montag bis Freitag" if language == Language.DE else "Monday to Friday"),
        ("Mo-So", "Montag bis Sonntag" if language == Language.DE else "Monday to Sunday"),
        ("Sa, So, Feiertage", "Samstag, Sonntag und Feiertage" if language == Language.DE else "Saturday, Sunday and public holidays"),
        ("Sa, So, Feiertag", "Samstag, Sonntag und Feiertage" if language == Language.DE else "Saturday, Sunday and public holidays"),
        ("Str.", "Strasse" if language == Language.DE else "Street"),
        ("str.", "strasse" if language == Language.DE else "street"),
        ("Nr.", "Nummer" if language == Language.DE else "number"),
        ("ca.", "circa"),
        (";", "."),
    ]
    for source, target in replacements:
        normalized = normalized.replace(source, target)

    normalized = re.sub(
        r"(\d{1,2}(?::\d{2})?)\s*[–-]\s*(\d{1,2}(?::\d{2})?)\s*Uhr",
        r"\1 bis \2 Uhr",
        normalized,
    )
    normalized = re.sub(r"\bDi\b", "Dienstag" if language == Language.DE else "Tuesday", normalized)
    normalized = re.sub(r"\bDo\b", "Donnerstag" if language == Language.DE else "Thursday", normalized)
    normalized = re.sub(r"\bMi\b", "Mittwoch" if language == Language.DE else "Wednesday", normalized)
    normalized = re.sub(r"\bFr\b", "Freitag" if language == Language.DE else "Friday", normalized)
    normalized = re.sub(r"\bSa\b", "Samstag" if language == Language.DE else "Saturday", normalized)
    normalized = re.sub(r"\bSo\b", "Sonntag" if language == Language.DE else "Sunday", normalized)
    normalized = re.sub(r"\bMo\b", "Montag" if language == Language.DE else "Monday", normalized)
    normalized = normalized.replace("–", " bis ").replace("/", " oder ").replace("&", " und ")
    normalized = normalized.replace("-", " - ")
    normalized = re.sub(r"\s{2,}", " ", normalized).strip()
    return normalized


def create_tts_provider(name: str, binary: str, voice_models: dict[str, str] | None = None) -> BaseTtsProvider:
    if name == "piper":
        missing_issues = _piper_readiness_issues(binary, voice_models or {})
        if not missing_issues:
            return PiperTtsProvider(binary=binary, voice_models=voice_models)
        return MockTtsProvider(
            configured_name=name,
            detail="; ".join(missing_issues),
            fallback_from=name,
        )
    return MockTtsProvider(configured_name=name)


def _describe_piper_health(binary: str, voice_models: dict[str, str]) -> str:
    issues = _piper_readiness_issues(binary, voice_models)
    if issues:
        return "; ".join(issues)
    available_languages = ", ".join(sorted(voice_models))
    return f"Binary and voice models available for: {available_languages}"


def _piper_readiness_issues(binary: str, voice_models: dict[str, str]) -> list[str]:
    issues: list[str] = []
    binary_path = Path(binary)
    if not binary_path.exists():
        issues.append(f"Missing Piper binary: {binary}")
    if not voice_models:
        issues.append("No Piper voice models configured")
        return issues

    missing_languages: list[str] = []
    for language in ["de", "en", "pl", "ro", "ru"]:
        model_path_raw = voice_models.get(language)
        if not model_path_raw:
            missing_languages.append(language)
            continue
        model_path = Path(model_path_raw)
        config_path = model_path.with_suffix(model_path.suffix + ".json")
        if not model_path.exists():
            issues.append(f"Missing Piper model for {language}: {model_path}")
        if not config_path.exists():
            issues.append(f"Missing Piper config for {language}: {config_path}")
    if missing_languages:
        issues.append(f"No Piper voices configured for: {', '.join(missing_languages)}")
    return issues
