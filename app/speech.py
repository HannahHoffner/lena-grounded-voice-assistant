"""Adapter für OpenAI-kompatible Transkription sowie OpenAI-/Edge-TTS."""

from __future__ import annotations

import asyncio
import importlib.util
import io
import re
import wave
from dataclasses import dataclass

import av
import httpx

from .config import Settings
from .models import Language
from .policy_facts import EMERGENCY_NUMBER


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

# Live beobachtet: ein kompaktes "H(:MM)-H(:MM)"-Zeitspannenmuster (z. B.
# "12-13:30 Uhr", von Formulator oder Quelldaten teils ohne oder mit
# Leerzeichen um den Trennzeichen geschrieben) wird von den Edge-Neural-Stimmen
# ziffernweise vorgelesen ("eins zwei bis eins drei dreißig Uhr") statt als
# Uhrzeit ("zwölf bis dreizehn Uhr dreißig"). Ein einzelner klar durch
# Leerzeichen abgesetzter Zwei-Punkt-Bindestrich wird dagegen zuverlässig als
# Zahl erkannt; das Muster wird daher vor der Synthese in Zahl + gesprochenes
# Trennwort + Zahl aufgelöst. Das Trennzeichen ist bewusst kein reiner ASCII-
# Bindestrich (U+002D): der Formulator schreibt Zeitspannen live reproduziert
# mit einem geschützten Halbgeviertstrich (U+2011, "09:00‑10:00"), einzelne
# Quelldaten nutzen einen Halbgeviertstrich (U+2013, "06:00 – 22:00") -- eine
# frühere Fassung matchte nur U+002D und griff dadurch beim häufigsten Fall
# (Formulatorantworten) nie. Eine menschliche Hörprüfung wird damit nicht
# behauptet (siehe docs/safety-and-error-policy.md zum selben Vorbehalt bei
# der Notrufnummer); dies behebt nur die konkret gemeldeten/beobachteten
# Trennzeichen.
_TIME_RANGE_SEPARATOR_SPEECH = {
    Language.DE: "bis",
    Language.EN: "to",
    Language.PL: "do",
    Language.RO: "până la",
    Language.RU: "до",
}
_DASH_CHARS = "-‐‑‒–—−"
_TIME_RANGE_RE = re.compile(
    rf"(?<!\d)(\d{{1,2}}(?::\d{{2}})?)\s*[{_DASH_CHARS}]\s*(\d{{1,2}}(?::\d{{2}})?)(?!\d)"
)


def normalize_tts_text(text: str, language: Language) -> str:
    """Löst Notrufnummer und kompakte Uhrzeit-Spannen in eine sprechbare Form auf, ohne den Sichttext zu ändern."""
    normalized = " ".join(text.split())
    separator = _TIME_RANGE_SEPARATOR_SPEECH[language]
    normalized = _TIME_RANGE_RE.sub(rf"\1 {separator} \2", normalized)
    return re.sub(rf"\b{re.escape(EMERGENCY_NUMBER)}\b", EMERGENCY_NUMBER_SPEECH[language], normalized)


class SpeechTranscriptionError(RuntimeError):
    """Basisklasse fuer redigierbare STT-Fehler ohne Providerinhalte."""

    code = "stt_failed"


class SpeechTranscriptionAudioError(SpeechTranscriptionError):
    """Die uebergebene Browseraufnahme konnte nicht sicher dekodiert werden."""

    code = "stt_audio_invalid"


class SpeechTranscriptionAudioTooLongError(SpeechTranscriptionAudioError):
    """Die dekodierte Aufnahme ueberschreitet die lokale Laufzeitgrenze."""

    code = "stt_audio_too_long"


class SpeechTranscriptionProviderError(SpeechTranscriptionError):
    """Der externe STT-Dienst hat den normalisierten Request abgelehnt."""

    code = "stt_provider_http_error"

    def __init__(self, *, upstream_status: int | None = None) -> None:
        super().__init__(self.code)
        self.upstream_status = upstream_status


class SpeechTranscriptionTimeoutError(SpeechTranscriptionError):
    """Kennzeichnet eine abgelaufene STT-Gesamtgrenze."""

    code = "stt_timeout"


class SpeechTranscriptionNotConfiguredError(SpeechTranscriptionError):
    """Das STT-Profil ist deaktiviert oder unvollständig konfiguriert."""

    code = "stt_not_configured"


class SpeechSynthesisError(RuntimeError):
    """Basisklasse für redigierbare TTS-Fehler ohne Providerinhalte.

    Dieselbe Struktur wie bei STT: ein geschlossener ``code`` und optional der
    HTTP-Status des Upstreams, nie Antworttext, URL oder Zugangsdaten.
    """

    code = "tts_failed"

    def __init__(self, message: str = "Speech synthesis failed", *, upstream_status: int | None = None) -> None:
        super().__init__(message)
        self.upstream_status = upstream_status


class SpeechSynthesisNotConfiguredError(SpeechSynthesisError):
    """Das TTS-Profil ist deaktiviert oder unvollständig konfiguriert."""

    code = "tts_not_configured"


class SpeechSynthesisProviderError(SpeechSynthesisError):
    """Der externe TTS-Dienst hat abgelehnt oder war nicht erreichbar."""

    code = "tts_provider_http_error"


class SpeechSynthesisTimeoutError(SpeechSynthesisError):
    """Kennzeichnet eine abgelaufene TTS-Gesamtgrenze."""

    code = "tts_timeout"


@dataclass(frozen=True)
class SpeechTranscriber:
    """Normalisiert Browseraudio und sendet ausschliesslich PCM-WAV an STT."""
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
            raise SpeechTranscriptionNotConfiguredError("Speech transcription is not configured")
        if not audio:
            raise SpeechTranscriptionError("No audio was supplied")

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
                # MediaRecorder liefert je nach Browser WebM/Opus, Ogg oder MP4.
                # Der konfigurierte Blablador-Endpunkt akzeptiert diese Container
                # nicht verlaesslich und erwartet aktuell RIFF/WAV. Die zentrale
                # Normalisierung haelt den Browservertrag deshalb providerneutral.
                normalized_audio = await asyncio.to_thread(_normalize_audio_to_wav, audio)
                files = {"file": ("speech.wav", normalized_audio, "audio/wav")}
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.settings.speech_transcription_timeout_seconds)
                ) as client:
                    response = await client.post(url, headers=headers, data=data, files=files)
                    response.raise_for_status()
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise SpeechTranscriptionTimeoutError("Speech transcription timed out") from exc
        except SpeechTranscriptionAudioError:
            raise
        except httpx.HTTPStatusError as exc:
            raise SpeechTranscriptionProviderError(upstream_status=exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise SpeechTranscriptionProviderError() from exc

        try:
            payload = response.json()
        except ValueError as exc:
            text = response.text.strip()
            if text:
                return text
            raise SpeechTranscriptionError("Speech transcription response is not JSON") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise SpeechTranscriptionError("Speech transcription response contains no text")
        transcript = payload["text"].strip()
        if not transcript:
            raise SpeechTranscriptionError("Speech transcription response contains no text")
        return " ".join(transcript.split())


@dataclass(frozen=True)
class SpeechSynthesizer:
    """Synthetisiert Sprache über Edge oder einen OpenAI-kompatiblen Dienst."""
    settings: Settings

    @property
    def edge_client_installed(self) -> bool:
        return importlib.util.find_spec("edge_tts") is not None

    @property
    def configured(self) -> bool:
        if self.settings.speech_synthesis_provider == "edge":
            return self.edge_client_installed
        return self.settings.speech_synthesis_configured

    @property
    def media_type(self) -> str:
        if self.settings.speech_synthesis_provider == "edge":
            return "audio/mpeg"
        return TTS_MEDIA_TYPES.get(self.settings.speech_synthesis_response_format.casefold(), "audio/mpeg")

    async def synthesize(self, text: str, *, language: Language) -> bytes:
        if not self.configured:
            raise SpeechSynthesisNotConfiguredError("Speech synthesis is not configured")
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
        except httpx.HTTPStatusError as exc:
            # Z. B. 404 bei einem Endpunkt ohne das konfigurierte TTS-Modell.
            raise SpeechSynthesisProviderError(upstream_status=exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            raise SpeechSynthesisProviderError() from exc

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
            raise SpeechSynthesisProviderError("Edge speech synthesis request failed") from exc

        audio = b"".join(chunks)
        if not audio:
            raise SpeechSynthesisError("Edge speech synthesis response contains no audio")
        return audio


_STT_SAMPLE_RATE = 16_000
_STT_MAX_DECODED_SECONDS = 120
_STT_MAX_SAMPLES = _STT_SAMPLE_RATE * _STT_MAX_DECODED_SECONDS


def _normalize_audio_to_wav(audio: bytes) -> bytes:
    """Dekodiert akzeptierte Audiocontainer zu mono PCM16/16 kHz im Speicher.

    Die dekodierte Dauer wird unabhaengig von der komprimierten Requestgroesse
    begrenzt. Weder Eingabe noch WAV werden auf die Festplatte geschrieben.
    """

    output = io.BytesIO()
    sample_count = 0
    try:
        with av.open(io.BytesIO(audio), mode="r") as container:
            audio_stream = next((stream for stream in container.streams if stream.type == "audio"), None)
            if audio_stream is None:
                raise SpeechTranscriptionAudioError("stt_audio_invalid")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=_STT_SAMPLE_RATE)
            with wave.open(output, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(_STT_SAMPLE_RATE)
                for frame in container.decode(audio_stream):
                    for converted in resampler.resample(frame):
                        sample_count = _write_pcm_frame(wav_file, converted, sample_count)
                for converted in resampler.resample(None):
                    sample_count = _write_pcm_frame(wav_file, converted, sample_count)
    except SpeechTranscriptionAudioError:
        raise
    except (av.error.FFmpegError, EOFError, OSError, ValueError) as exc:
        raise SpeechTranscriptionAudioError("stt_audio_invalid") from exc

    if sample_count == 0:
        raise SpeechTranscriptionAudioError("stt_audio_invalid")
    return output.getvalue()


def _write_pcm_frame(wav_file: wave.Wave_write, frame: av.AudioFrame, sample_count: int) -> int:
    next_count = sample_count + frame.samples
    if next_count > _STT_MAX_SAMPLES:
        raise SpeechTranscriptionAudioTooLongError("stt_audio_too_long")
    pcm = bytes(frame.planes[0])[: frame.samples * 2]
    wav_file.writeframesraw(pcm)
    return next_count
