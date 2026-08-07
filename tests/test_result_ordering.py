from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.candidate_contract import FactsUsed
from app.config import Settings
from app.kb_loader import load_active_knowledge_base
from app.result_ordering import order_social_results, social_result_distance
from app.result_time import ServiceWindow, food_schedule_matches, opening_windows, windows_match
from app.resources import packaged_bootstrap_data_root


BERLIN = ZoneInfo("Europe/Berlin")


def _facts(day: str | None = None, time: str | None = None) -> FactsUsed:
    return FactsUsed.model_validate(
        {
            "age": None,
            "age_group": "unknown",
            "gender": "unknown",
            "drug_use": "unknown",
            "no_social_benefit_entitlement": "unknown",
            "district": None,
            "requested_day": day,
            "requested_time": time,
        }
    )


def _kb(tmp_path: Path):
    settings = Settings(
        app_root=tmp_path,
        kb_path=packaged_bootstrap_data_root() / "canonical" / "offers.json",
        rewrite_provider="template",
        blablador_base_url=None,
        blablador_api_key=None,
        blablador_model=None,
        blablador_timeout_seconds=30,
        blablador_max_context_chars=50_000,
        data_dir=tmp_path / "data",
        runtime_dir=tmp_path / "runtime",
        bootstrap_data_dir=packaged_bootstrap_data_root(),
        wfs_auto_sync=False,
    )
    return load_active_knowledge_base(settings)


def test_food_schedule_explicit_today_tomorrow_and_weekday() -> None:
    monday = datetime(2026, 8, 3, 12, 0, tzinfo=BERLIN)
    assert food_schedule_matches("tuesday_17_18", [], _facts("tuesday"), monday)
    assert food_schedule_matches("tuesday_17_18", [], _facts("tomorrow"), monday)
    assert not food_schedule_matches("sunday_20_21", [], _facts("today"), monday)


def test_food_schedule_later_now_and_finished_today() -> None:
    before = datetime(2026, 8, 4, 16, 0, tzinfo=BERLIN)
    during = datetime(2026, 8, 4, 17, 30, tzinfo=BERLIN)
    after = datetime(2026, 8, 4, 18, 1, tzinfo=BERLIN)
    assert food_schedule_matches("tuesday_17_18", [], _facts(), before)
    assert food_schedule_matches("tuesday_17_18", [], _facts(), during)
    assert not food_schedule_matches("tuesday_17_18", [], _facts(), after)


def test_food_explicit_time_must_be_inside_source_window() -> None:
    tuesday = datetime(2026, 8, 4, 9, 0, tzinfo=BERLIN)
    assert food_schedule_matches("tuesday_17_18", [], _facts("today", "17:15"), tuesday)
    assert not food_schedule_matches("tuesday_17_18", [], _facts("today", "19:00"), tuesday)


def test_opening_hours_parser_handles_daily_ranges_and_unknown_time() -> None:
    windows = opening_windows(["> Montag - Freitag: 08:00 - 16:00 Uhr", "> Sonntag: 09:00 - 15:00 Uhr"])
    assert windows_match(windows, _facts("monday", "10:00"), datetime(2026, 8, 3, tzinfo=BERLIN))
    assert windows_match(windows, _facts("sunday", "14:00"), datetime(2026, 8, 3, tzinfo=BERLIN))
    assert not food_schedule_matches(None, [], _facts(), datetime(2026, 8, 3, tzinfo=BERLIN))


def test_opening_hours_parser_handles_arbitrary_and_wrapped_weekday_ranges() -> None:
    windows = opening_windows(
        [
            "> Donnerstag bis Sonntag: 12:00 - 18:00 Uhr",
            "> Freitag bis Montag: 20:00 - 22:00 Uhr",
        ]
    )
    reference = datetime(2026, 8, 3, tzinfo=BERLIN)
    assert windows_match(windows, _facts("saturday", "14:00"), reference)
    assert windows_match(windows, _facts("monday", "21:00"), reference)
    assert not windows_match(windows, _facts("tuesday", "21:00"), reference)


def test_cross_midnight_window_is_not_misread_as_closed() -> None:
    window = (ServiceWindow(frozenset({0}), 16 * 60, 8 * 60),)
    monday = datetime(2026, 8, 3, 22, 0, tzinfo=BERLIN)
    assert windows_match(window, _facts("today", "22:00"), monday)


def test_mandatory_and_fachpriority_precede_distance(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    offers = [kb.by_id()["10"], kb.by_id()["25"], kb.by_id()["7"]]
    ordered = order_social_results(
        offers,
        mandatory_order=["7"],
        priority_tiers={"7": 0, "25": 10, "10": 50},
        service="medical",
    )
    assert [offer.id for offer in ordered] == ["7", "25", "10"]


def test_mobile_actual_stand_precedes_office_and_unknown_stand_is_not_ranked(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    schwanenteich = kb.by_id()["14"]
    care_bags = kb.by_id()["16"]
    assert social_result_distance(schwanenteich, service="food") is not None
    assert social_result_distance(care_bags, service="food") is None


def test_stable_id_breaks_equal_distance() -> None:
    # No coordinates: both records share the same non-rankable class, then ID is stable.
    from app.models import OfferRecord

    def offer(offer_id: str) -> OfferRecord:
        return OfferRecord(
            id=offer_id,
            source_index=int(offer_id),
            source_title=offer_id,
            name=offer_id,
            source_category="x",
            short_description="x",
            raw_text="x",
        )

    assert [item.id for item in order_social_results([offer("20"), offer("10")])] == ["10", "20"]
