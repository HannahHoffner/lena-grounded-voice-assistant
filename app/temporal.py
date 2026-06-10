from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import TemporalContext


WEEKDAYS_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAYS_DE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def build_temporal_context(now: datetime | None = None, timezone: str = "Europe/Berlin") -> TemporalContext:
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Europe/Berlin")

    current = now or datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    weekday_index = current.weekday()
    season = _season_for_month(current.month)
    return TemporalContext(
        now_iso=current.isoformat(),
        date_iso=current.date().isoformat(),
        weekday_index=weekday_index,
        weekday_en=WEEKDAYS_EN[weekday_index],
        weekday_de=WEEKDAYS_DE[weekday_index],
        is_weekend=weekday_index >= 5,
        month=current.month,
        season=season,
        season_hints=_season_hints(season),
    )


def _season_for_month(month: int) -> str:
    if month in {12, 1, 2}:
        return "winter"
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def _season_hints(season: str) -> list[str]:
    if season == "winter":
        return ["cold", "warm clothing", "blankets", "sleeping bags", "emergency overnight help"]
    if season == "summer":
        return ["heat", "drinking water", "hydration", "public drinking fountains"]
    return []
