from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
import tempfile
import warnings

from fastapi import UploadFile

from ..models import Language


class BaseSttProvider(ABC):
    name = "base"
    configured_name = "base"
    ready = True
    real_audio = True
    detail: str | None = None
    fallback_from: str | None = None

    @abstractmethod
    async def transcribe(self, audio: UploadFile, language: Language | str, debug_transcript: str | None = None) -> str:
        raise NotImplementedError

    def health(self) -> dict[str, object]:
        return {
            "configured_provider": self.configured_name,
            "active_provider": self.name,
            "ready": self.ready,
            "real_audio": self.real_audio,
            "detail": self.detail,
            "fallback_from": self.fallback_from,
        }


class MockSttProvider(BaseSttProvider):
    name = "mock"
    real_audio = False

    def __init__(self, *, configured_name: str = "mock", detail: str | None = None, fallback_from: str | None = None) -> None:
        self.configured_name = configured_name
        self.detail = detail
        self.fallback_from = fallback_from
        self.ready = fallback_from is None

    async def transcribe(self, audio: UploadFile, language: Language | str, debug_transcript: str | None = None) -> str:
        if debug_transcript:
            return debug_transcript
        raise RuntimeError("Mock STT cannot transcribe real audio. Provide debug_transcript or configure faster_whisper.")


class FasterWhisperProvider(BaseSttProvider):
    name = "faster_whisper"

    def __init__(self, model_name: str = "small") -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional install/runtime policy
            raise RuntimeError("faster-whisper backend is unavailable") from exc
        self._model_factory = WhisperModel
        self._model_name = model_name
        self._model = None
        self.configured_name = self.name
        self.detail = f"Model {model_name}"

    def _get_model(self):
        if self._model is None:
            self._model = self._model_factory(self._model_name, device="auto", compute_type="auto")
        return self._model

    async def transcribe(self, audio: UploadFile, language: Language | str, debug_transcript: str | None = None) -> str:
        if debug_transcript:
            return debug_transcript
        normalized_language = _normalize_language(language)
        suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(await audio.read())
            temp_path = handle.name
        try:
            segments, _ = self._get_model().transcribe(temp_path, language=normalized_language.value, vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _normalize_language(language: Language | str) -> Language:
    if isinstance(language, Language):
        return language
    return Language(language)


def create_stt_provider(name: str) -> BaseSttProvider:
    if name == "faster_whisper":
        try:
            provider = FasterWhisperProvider()
            provider._get_model()
            return provider
        except Exception as exc:
            warnings.warn(
                f"Falling back to mock STT because faster-whisper could not be initialized: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return MockSttProvider(
                configured_name=name,
                detail=f"faster-whisper initialization failed: {exc}",
                fallback_from=name,
            )
    return MockSttProvider(configured_name=name)
