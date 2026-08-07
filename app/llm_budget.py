"""Kumulatives monotones Zeitbudget ausschließlich für externe LLM-Stufen."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class LLMBudgetExhausted(RuntimeError):
    """Eine weitere externe Modellstufe darf nicht mehr gestartet werden."""


@dataclass(frozen=True, slots=True)
class LLMStageAllocation:
    started_at: float
    timeout_seconds: float


@dataclass(slots=True)
class LLMRequestBudget:
    """Misst nur die tatsächlich verstrichene Zeit um Provider-awaits.

    Deterministische Verarbeitung und Dialogzeit werden nicht abgezogen. Die
    injizierbare monotone Uhr macht Restzeit und Stufenverkürzung reproduzierbar.
    """

    total_seconds: float
    clock: Callable[[], float]
    consumed_seconds: float = 0.0

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.total_seconds - self.consumed_seconds)

    @property
    def exhausted(self) -> bool:
        return self.remaining_seconds <= 0.0

    def begin(self, stage_limit_seconds: float) -> LLMStageAllocation:
        remaining = self.remaining_seconds
        if remaining <= 0.0:
            raise LLMBudgetExhausted("llm_budget_exhausted")
        return LLMStageAllocation(
            started_at=self.clock(),
            timeout_seconds=min(stage_limit_seconds, remaining),
        )

    def finish(self, allocation: LLMStageAllocation) -> None:
        elapsed = max(0.0, self.clock() - allocation.started_at)
        self.consumed_seconds = min(self.total_seconds, self.consumed_seconds + elapsed)

