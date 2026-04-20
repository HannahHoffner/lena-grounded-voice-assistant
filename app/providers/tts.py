from __future__ import annotations

import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Language


class BaseTtsProvider(ABC):
    name = "base"

    @abstractmethod
    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        raise NotImplementedError


class MockTtsProvider(BaseTtsProvider):
    name = "mock"

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        return None


class PiperTtsProvider(BaseTtsProvider):
    name = "piper"

    def __init__(self, binary: str) -> None:
        self.binary = binary

    async def synthesize(self, text: str, language: Language, audio_root: Path) -> str | None:
        output_path = audio_root / f"{uuid.uuid4().hex}.wav"
        command = [
            self.binary,
            "--output_file",
            str(output_path),
        ]
        subprocess.run(command, input=text.encode("utf-8"), check=True)
        return f"/runtime/audio/{output_path.name}"


def create_tts_provider(name: str, binary: str) -> BaseTtsProvider:
    if name == "piper":
        return PiperTtsProvider(binary=binary)
    return MockTtsProvider()

