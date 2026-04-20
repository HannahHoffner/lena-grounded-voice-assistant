from __future__ import annotations

from pathlib import Path

from .models import TranscriptEvent


class TranscriptStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: TranscriptEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

