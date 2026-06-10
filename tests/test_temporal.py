from __future__ import annotations

from datetime import datetime, timezone

from app.temporal import build_temporal_context


def test_temporal_context_winter_fixed_date() -> None:
    context = build_temporal_context(datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc))

    assert context.season == "winter"
    assert context.date_iso == "2026-01-15"
    assert context.weekday_en == "Thursday"
    assert context.weekday_de == "Donnerstag"


def test_temporal_context_summer_fixed_date() -> None:
    context = build_temporal_context(datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc))

    assert context.season == "summer"
    assert context.month == 7
    assert "drinking water" in context.season_hints


def test_temporal_context_weekend() -> None:
    saturday = build_temporal_context(datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc))
    sunday = build_temporal_context(datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc))

    assert saturday.is_weekend is True
    assert sunday.is_weekend is True


def test_temporal_context_uses_europe_berlin_timezone() -> None:
    context = build_temporal_context(datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc))

    assert context.date_iso == "2026-01-02"
    assert context.weekday_en == "Friday"
