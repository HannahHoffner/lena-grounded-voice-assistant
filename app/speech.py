"""Adapter für OpenAI-kompatible Transkription sowie OpenAI-/Edge-TTS."""

from __future__ import annotations

import asyncio
import importlib.util
import re
from dataclasses import dataclass

import httpx

from .config import Settings
from .models import Language


LANGUAGE_HINTS = {
    Language.DE: "de",
    Language.EN: "en",
    Language.PL: "pl",
    Language.RO: "ro",
    Language.RU: "ru",
}

TTS_LANGUAGE_NAMES = {
    Language.DE: "German",
    Language.EN: "English",
    Language.PL: "Polish",
    Language.RO: "Romanian",
    Language.RU: "Russian",
}

TTS_MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}

EDGE_VOICES = {
    Language.DE: "de-DE-KatjaNeural",
    Language.EN: "en-US-JennyNeural",
    Language.PL: "pl-PL-ZofiaNeural",
    Language.RO: "ro-RO-AlinaNeural",
    Language.RU: "ru-RU-SvetlanaNeural",
}

EMERGENCY_NUMBER_SPEECH = {
    Language.DE: "eins eins zwei",
    Language.EN: "one one two",
    Language.PL: "jeden jeden dwa",
    Language.RO: "unu unu doi",
    Language.RU: "один один два",
}


def normalize_tts_text(text: str, language: Language) -> str:
    """Spricht die Notrufnummer als einzelne Ziffern, ohne den Sichttext zu ändern."""
    normalized = " ".join(text.split())
    return re.sub(r"\b112\b", EMERGENCY_NUMBER_SPEECH[language], normalized)


class SpeechTranscriptionError(RuntimeError):
    pass


class SpeechTranscriptionTimeoutError(SpeechTranscriptionError):
    """Kennzeichnet eine abgelaufene STT-Gesamtgrenze."""


class SpeechSynthesisError(RuntimeError):
    pass


class SpeechSynthesisTimeoutError(SpeechSynthesisError):
    """Kennzeichnet eine abgelaufene TTS-Gesamtgrenze."""


@dataclass(frozen=True)
class SpeechTranscriber:
    """Sendet rohe Audiodaten an einen konfigurierten Transkriptionsdienst."""
    settings: Settings

    @property
    def configured(self) -> bool:
        return self.settings.speech_transcription_configured

    async def transcribe(self, audio: bytes, *, content_type: str, language: Language) -> str:
        """Transkribiert die ausschließlich im Speicher gehaltenen Audiodaten.

        Raises:
            SpeechTranscriptionError: Bei fehlender Konfiguration oder Providerfehlern.
        """
        if not self.configured:
            raise SpeechTranscriptionError("Speech transcription is not configured")
        if not audio:
            raise SpeechTranscriptionError("No audio was supplied")

        filename = _filename_for_content_type(content_type)
        files = {"file": (filename, audio, content_type or "audio/webm")}
        data = {
            "model": self.settings.speech_transcription_model or "",
            "language": LANGUAGE_HINTS.get(language, language.value),
            "response_format": "json",
            "prompt": "LENA. Hilfsangebote in Leipzig. Essen, Schlafplatz, Medizin, Beratung, Hilfebus.",
        }
        headers = {"Authorization": f"Bearer {self.settings.speech_transcription_api_key}"}
        url = f"{(self.settings.speech_transcription_base_url or '').rstrip('/')}/audio/transcriptions"

        try:
            async with asyncio.timeout(self.settings.speech_transcription_timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.settings.speech_transcription_timeout_seconds)
                ) as client:
                    response = await client.post(url, headers=headers, data=data, files=files)
                    response.raise_for_status()
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise SpeechTranscriptionTimeoutError("Speech transcription timed out") from exc
        except httpx.HTTPError as exc:
            raise SpeechTranscriptionError("Speech transcription request failed") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            text = response.text.strip()
            if text:
                return text
            raise SpeechTranscriptionError("Speech transcription response is not JSON") from exc

        transcript = str(payload.get("text") or "").strip()
        if not transcript:
            raise SpeechTranscriptionError("Speech transcription response contains no text")
        return " ".join(transcript.split())


@dataclass(frozen=True)
class SpeechSynthesizer:
    """Synthetisiert Sprache über Edge oder einen OpenAI-kompatiblen Dienst."""
    settings: Settings

    @property
    def configured(self) -> bool:
        if self.settings.speech_synthesis_provider == "edge":
            return importlib.util.find_spec("edge_tts") is not None
        return self.settings.speech_synthesis_configured

    @property
    def media_type(self) -> str:
        if self.settings.speech_synthesis_provider == "edge":
            return "audio/mpeg"
        return TTS_MEDIA_TYPES.get(self.settings.speech_synthesis_response_format.casefold(), "audio/mpeg")

    async def synthesize(self, text: str, *, language: Language) -> bytes:
        if not self.configured:
            raise SpeechSynthesisError("Speech synthesis is not configured")
        normalized = normalize_tts_text(text, language)
        if not normalized:
            raise SpeechSynthesisError("No text was supplied")

        try:
            async with asyncio.timeout(self.settings.speech_synthesis_timeout_seconds):
                if self.settings.speech_synthesis_provider == "edge":
                    return await self._synthesize_edge(normalized, language=language)
                return await self._synthesize_openai(normalized, language=language)
        except TimeoutError as exc:
            raise SpeechSynthesisTimeoutError("Speech synthesis timed out") from exc

    async def _synthesize_openai(self, text: str, *, language: Language) -> bytes:
        """Ruft den OpenAI-kompatiblen TTS-Endpunkt innerhalb der Gesamtgrenze auf."""

        payload = {
            "model": self.settings.speech_synthesis_model or "",
            "input": text,
            "voice": self.settings.speech_synthesis_voice,
            "response_format": self.settings.speech_synthesis_response_format,
        }
        if (self.settings.speech_synthesis_model or "").startswith("gpt-4o"):
            payload["instructions"] = (
                f"Speak in {TTS_LANGUAGE_NAMES.get(language, language.value)}. "
                "Use a calm, clear, friendly voice. Pronounce times naturally."
            )
        headers = {"Authorization": f"Bearer {self.settings.speech_synthesis_api_key}"}
        url = f"{(self.settings.speech_synthesis_base_url or '').rstrip('/')}/audio/speech"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.speech_synthesis_timeout_seconds)
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SpeechSynthesisTimeoutError("Speech synthesis timed out") from exc
        except httpx.HTTPError as exc:
            raise SpeechSynthesisError("Speech synthesis request failed") from exc

        if not response.content:
            raise SpeechSynthesisError("Speech synthesis response contains no audio")
        return response.content

    async def _synthesize_edge(self, text: str, *, language: Language) -> bytes:
        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=EDGE_VOICES.get(language, EDGE_VOICES[Language.DE]),
                rate="-8%",
            )
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
        except Exception as exc:
            raise SpeechSynthesisError("Edge speech synthesis request failed") from exc

        audio = b"".join(chunks)
        if not audio:
            raise SpeechSynthesisError("Edge speech synthesis response contains no audio")
        return audio


def _filename_for_content_type(content_type: str) -> str:
    lowered = content_type.casefold()
    if "mp4" in lowered:
        return "speech.mp4"
    if "mpeg" in lowered or "mp3" in lowered:
        return "speech.mp3"
    if "wav" in lowered:
        return "speech.wav"
    if "ogg" in lowered:
        return "speech.ogg"
    return "speech.webm"
