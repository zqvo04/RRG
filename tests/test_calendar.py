from datetime import date, datetime
from zoneinfo import ZoneInfo

from pipeline.calendar import completed_friday_bars, last_completed_friday
from pipeline.models import PriceBar

NY = ZoneInfo("America/New_York")


def bar(day: str) -> PriceBar:
    return PriceBar("SPY", date.fromisoformat(day), 100.0, "fixture", datetime(2026, 1, 1, tzinfo=NY))


def test_current_friday_is_excluded_before_us_market_close() -> None:
    reference = datetime(2026, 8, 21, 15, 30, tzinfo=NY)
    assert last_completed_friday(reference) == date(2026, 8, 14)
    actual = completed_friday_bars([bar("2026-08-14"), bar("2026-08-20")], reference)
    assert [item.week_end for item in actual] == [date(2026, 8, 14)]


def test_current_friday_is_available_after_us_market_close() -> None:
    reference = datetime(2026, 8, 21, 16, 20, tzinfo=NY)
    assert last_completed_friday(reference) == date(2026, 8, 21)
    actual = completed_friday_bars([bar("2026-08-14"), bar("2026-08-21")], reference)
    assert [item.week_end for item in actual] == [date(2026, 8, 14), date(2026, 8, 21)]


def test_saturday_korea_time_uses_completed_us_friday() -> None:
    reference = datetime(2026, 8, 29, 17, 17, tzinfo=ZoneInfo("Asia/Seoul"))
    assert last_completed_friday(reference) == date(2026, 8, 28)


def test_friday_before_regular_close_uses_prior_week() -> None:
    reference = datetime(2026, 8, 28, 16, 14, tzinfo=NY)
    assert last_completed_friday(reference) == date(2026, 8, 21)


def test_friday_after_regular_close_uses_current_week() -> None:
    reference = datetime(2026, 8, 28, 16, 15, tzinfo=NY)
    assert last_completed_friday(reference) == date(2026, 8, 28)


def test_thursday_holiday_close_is_labeled_with_its_friday_anchor() -> None:
    reference = datetime(2026, 7, 10, 16, 20, tzinfo=NY)
    normalized = completed_friday_bars([bar("2026-07-09")], reference)
    assert normalized[0].week_end == date(2026, 7, 10)

