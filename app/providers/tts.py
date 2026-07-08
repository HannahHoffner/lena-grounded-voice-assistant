from __future__ import annotations

import re
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..models import Language


DIGIT_WORDS_DE = {
    "0": "null",
    "1": "eins",
    "2": "zwei",
    "3": "drei",
    "4": "vier",
    "5": "fuenf",
    "6": "sechs",
    "7": "sieben",
    "8": "acht",
    "9": "neun",
}
PHONE_CONTEXT_RE = re.compile(
    r"\b(?:telefon|tel\.?|anrufen|anruf|ruf|notruf|polizei|phone|call|emergency services)\b",
    re.IGNORECASE,
)
GERMAN_PHONE_RE = re.compile(
    r"(?<![\w:])(?:\+49[\s()./-]*(?:\d[\s()./-]*){5,}\d|\(?0\d{2,5}\)?[\s()./-]+\d{3,}(?:[\s()./-]*\d+)*|116[\s/-]*117|11[02])(?![\w:])"
)
CONTEXT_PHONE_RE = re.compile(r"(?<![\w:])(?:\+?\d[\d\s()./-]{2,}\d)(?![\w:])")
UMLAUT_REPLACEMENTS = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
)


class BaseTtsProvider(ABC):
    name = "base"
    configured_name = "base"
    ready = True
    audio_output = True
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
            "audio_output": self.audio_output,
            "detail": self.detail,
            "fallback_from": self.fallback_from,
        }


class MockTtsProvider(BaseTtsProvider):
    name = "mock"
    audio_output = False

    def __init__(self, *, configured_name: str = "mock", detail: str | None = None, fallback_from: str | None = None) -> None:
        self.configured_name = configured_name
        self.detail = detail
        self.fallback_from = fallback_from
        self.ready = fallback_from is None

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        return None


@dataclass(frozen=True, slots=True)
class PiperVoice:
    language: str
    model_path: Path
    config_path: Path
    fallback: bool = False


class PiperTtsProvider(BaseTtsProvider):
    name = "piper"

    def __init__(
        self,
        binary: str,
        voice_models: dict[str, str] | None = None,
        voice_configs: dict[str, str] | None = None,
        default_voice_model: str | None = None,
        default_voice_config: str | None = None,
        normalize_umlauts: bool = False,
    ) -> None:
        self.binary = binary
        self.voice_models = voice_models or {}
        self.voice_configs = voice_configs or {}
        self.default_voice_model = default_voice_model
        self.default_voice_config = default_voice_config
        self.normalize_umlauts = normalize_umlauts
        self.configured_name = self.name
        self.detail = _describe_piper_health(
            binary,
            self.voice_models,
            self.voice_configs,
            self.default_voice_model,
            self.default_voice_config,
        )

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        voice = self.select_voice(language)
        if not voice:
            return None

        audio_root.mkdir(parents=True, exist_ok=True)
        output_path = audio_root / f"{uuid.uuid4().hex}.wav"
        normalized_text = normalize_for_tts(text, language, normalize_umlauts=self.normalize_umlauts)
        command = [
            self.binary,
            "--model",
            str(voice.model_path),
            "--config",
            str(voice.config_path),
            "--output_file",
            str(output_path),
        ]
        subprocess.run(command, input=normalized_text, text=True, encoding="utf-8", check=True)
        return f"/runtime/audio/{output_path.name}"

    def select_voice(self, language: Language) -> PiperVoice | None:
        voice = _usable_piper_voice(language.value, self.voice_models, self.voice_configs)
        if voice:
            return voice
        default_model = self.default_voice_model or self.voice_models.get("default")
        default_config = self.default_voice_config or self.voice_configs.get("default")
        default_voice = _usable_piper_voice(
            "default",
            {"default": default_model} if default_model else {},
            {"default": default_config} if default_config else {},
        )
        if not default_voice:
            return None
        return PiperVoice(
            language=language.value,
            model_path=default_voice.model_path,
            config_path=default_voice.config_path,
            fallback=True,
        )


def normalize_for_tts(text: str, language: Language, *, normalize_umlauts: bool = False) -> str:
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
        ("bzw.", "beziehungsweise" if language == Language.DE else "or rather"),
        ("u. a.", "unter anderem" if language == Language.DE else "among other things"),
        ("Tel.", "Telefon" if language == Language.DE else "Phone"),
        ("Dr.", "Doktor" if language == Language.DE else "Doctor"),
        ("Mo-Fr", "Montag bis Freitag" if language == Language.DE else "Monday to Friday"),
        ("Mo-So", "Montag bis Sonntag" if language == Language.DE else "Monday to Sunday"),
        ("Sa, So, Feiertage", "Samstag, Sonntag und Feiertage" if language == Language.DE else "Saturday, Sunday and public holidays"),
        ("Sa, So, Feiertag", "Samstag, Sonntag und Feiertage" if language == Language.DE else "Saturday, Sunday and public holidays"),
        ("Str.", "Strasse" if language == Language.DE else "Street"),
        ("str.", "strasse" if language == Language.DE else "street"),
        ("Nr.", "Nummer" if language == Language.DE else "number"),
        ("ca.", "zirka" if language == Language.DE else "about"),
        (";", "."),
    ]
    for source, target in replacements:
        normalized = normalized.replace(source, target)

    if language == Language.DE:
        normalized = _normalize_german_phone_numbers(normalized)

    normalized = re.sub(
        r"(\d{1,2}(?::\d{2})?)\s*[â€“-]\s*(\d{1,2}(?::\d{2})?)\s*Uhr",
        r"\1 bis \2 Uhr",
        normalized,
    )
    normalized = re.sub(r"\bDi\.?\b", "Dienstag" if language == Language.DE else "Tuesday", normalized)
    normalized = re.sub(r"\bDo\.?\b", "Donnerstag" if language == Language.DE else "Thursday", normalized)
    normalized = re.sub(r"\bMi\.?\b", "Mittwoch" if language == Language.DE else "Wednesday", normalized)
    normalized = re.sub(r"\bFr\.?\b", "Freitag" if language == Language.DE else "Friday", normalized)
    normalized = re.sub(r"\bSa\.?\b", "Samstag" if language == Language.DE else "Saturday", normalized)
    normalized = re.sub(r"\bSo\.?\b", "Sonntag" if language == Language.DE else "Sunday", normalized)
    normalized = re.sub(r"\bMo\.?\b", "Montag" if language == Language.DE else "Monday", normalized)
    normalized = normalized.replace("â€“", " bis ").replace("/", " oder ").replace("&", " und ")
    normalized = normalized.replace("-", " - ")
    if language == Language.DE and normalize_umlauts:
        normalized = normalized.translate(UMLAUT_REPLACEMENTS)
    normalized = re.sub(r"\s{2,}", " ", normalized).strip()
    return normalized


def normalize_tts_text(text: str, language: Language) -> str:
    return normalize_for_tts(text, language)


def _normalize_german_phone_numbers(text: str) -> str:
    normalized = GERMAN_PHONE_RE.sub(lambda match: _speak_german_phone_number(match.group(0)), text)
    offset = 0
    for match in list(CONTEXT_PHONE_RE.finditer(text)):
        candidate = match.group(0)
        digits = re.sub(r"\D+", "", candidate)
        if len(digits) < 6 or GERMAN_PHONE_RE.fullmatch(candidate):
            continue
        window = text[max(0, match.start() - 36) : min(len(text), match.end() + 36)]
        if not PHONE_CONTEXT_RE.search(window):
            continue
        start = match.start() + offset
        end = match.end() + offset
        spoken = _speak_german_phone_number(candidate)
        normalized = normalized[:start] + spoken + normalized[end:]
        offset += len(spoken) - (end - start)
    return normalized


def _speak_german_phone_number(phone: str) -> str:
    groups = [group for group in re.split(r"[\s()./-]+", phone.strip()) if group]
    spoken_groups: list[str] = []
    for group in groups:
        prefix = ""
        digits = group
        if group.startswith("+"):
            prefix = "plus "
            digits = group[1:]
        words = [DIGIT_WORDS_DE[digit] for digit in digits if digit.isdigit()]
        if words:
            spoken_groups.append(prefix + " ".join(words))
    return ", ".join(spoken_groups)


def create_tts_provider(
    name: str,
    binary: str,
    voice_models: dict[str, str] | None = None,
    voice_configs: dict[str, str] | None = None,
    default_voice_model: str | None = None,
    default_voice_config: str | None = None,
    normalize_umlauts: bool = False,
) -> BaseTtsProvider:
    if name == "piper":
        missing_issues = _piper_readiness_issues(
            binary,
            voice_models or {},
            voice_configs or {},
            default_voice_model,
            default_voice_config,
        )
        if not missing_issues:
            return PiperTtsProvider(
                binary=binary,
                voice_models=voice_models,
                voice_configs=voice_configs,
                default_voice_model=default_voice_model,
                default_voice_config=default_voice_config,
                normalize_umlauts=normalize_umlauts,
            )
        return MockTtsProvider(
            configured_name=name,
            detail="; ".join(missing_issues),
            fallback_from=name,
        )
    return MockTtsProvider(configured_name=name)


def _describe_piper_health(
    binary: str,
    voice_models: dict[str, str],
    voice_configs: dict[str, str],
    default_voice_model: str | None,
    default_voice_config: str | None,
) -> str:
    issues = _piper_readiness_issues(binary, voice_models, voice_configs, default_voice_model, default_voice_config)
    if issues:
        return "; ".join(issues)
    available_languages = ", ".join(_usable_piper_languages(voice_models, voice_configs, default_voice_model, default_voice_config))
    return f"Binary and voice models available for: {available_languages}"


def _piper_readiness_issues(
    binary: str,
    voice_models: dict[str, str],
    voice_configs: dict[str, str],
    default_voice_model: str | None,
    default_voice_config: str | None,
) -> list[str]:
    issues: list[str] = []
    binary_path = Path(binary)
    if not binary_path.exists():
        issues.append(f"Missing Piper binary: {binary}")
    if not voice_models and not default_voice_model:
        issues.append("No Piper voice models configured")
        return issues

    usable_languages = _usable_piper_languages(voice_models, voice_configs, default_voice_model, default_voice_config)
    if not usable_languages:
        issues.append("No usable Piper voices configured")
    return issues


def _usable_piper_languages(
    voice_models: dict[str, str],
    voice_configs: dict[str, str],
    default_voice_model: str | None,
    default_voice_config: str | None,
) -> list[str]:
    languages = ["de", "en", "pl", "ro", "ru"]
    usable = [language for language in languages if _usable_piper_voice(language, voice_models, voice_configs)]
    default_voice = _usable_piper_voice(
        "default",
        {"default": default_voice_model} if default_voice_model else {},
        {"default": default_voice_config} if default_voice_config else {},
    )
    if default_voice:
        usable.append("default")
    return usable


def _usable_piper_voice(language: str, voice_models: dict[str, str], voice_configs: dict[str, str]) -> PiperVoice | None:
    model_path_raw = voice_models.get(language)
    if not model_path_raw:
        return None
    model_path = Path(model_path_raw)
    config_path = _piper_config_path(model_path, voice_configs.get(language))
    if not model_path.exists() or not config_path.exists():
        return None
    return PiperVoice(language=language, model_path=model_path, config_path=config_path)


def _piper_config_path(model_path: Path, explicit_config: str | None = None) -> Path:
    if explicit_config:
        return Path(explicit_config)
    return Path(str(model_path) + ".json")
