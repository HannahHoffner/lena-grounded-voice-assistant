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

    def recent_events(self, session_id: str, limit: int = 3) -> list[TranscriptEvent]:
        if not self.path.exists():
            return []

        matches: list[TranscriptEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = TranscriptEvent.model_validate_json(line)
                except Exception:
                    continue
                if event.session_id == session_id:
                    matches.append(event)
        return matches[-limit:]

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
