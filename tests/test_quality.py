from datetime import date, datetime, timedelta, timezone

import pytest

from pipeline.errors import DataValidationError
from pipeline.models import PriceBar, RRGPoint, SectorState
from pipeline.quality import validate_snapshot_inputs


def bars(symbol: str, count: int = 52) -> list[PriceBar]:
    start = date(2025, 8, 29)
    stamp = datetime(2026, 8, 22, tzinfo=timezone.utc)
    return [PriceBar(symbol, start + timedelta(weeks=index), 100 + index, "fixture", stamp) for index in range(count)]


def state(ticker: str, week: str = "2026-08-21") -> SectorState:
    return SectorState(ticker, ticker, 101, 102, "leading", 45, 1.4, [RRGPoint("2026-08-14", 100, 101), RRGPoint(week, 101, 102)])


def test_quality_records_real_passed_checks() -> None:
    benchmark = bars("SPY")
    sectors = {"XLK": bars("XLK")}
    quality, provenance = validate_snapshot_inputs(benchmark, sectors, [state("XLK")], 2, date(2026, 8, 21), 52)
    assert quality["publishable"]
    assert all(check["passed"] for check in quality["checks"].values())
    assert provenance["series"]["SPY"]["observations"] == 52


def test_quality_blocks_duplicate_weeks() -> None:
    benchmark = bars("SPY")
    duplicate = bars("XLK")
    duplicate[-1] = duplicate[-2]
    with pytest.raises(DataValidationError, match="duplicate_weeks"):
        validate_snapshot_inputs(benchmark, {"XLK": duplicate}, [state("XLK")], 2, date(2026, 8, 21), 52)


def test_quality_blocks_stale_snapshot_date() -> None:
    with pytest.raises(DataValidationError, match="date_alignment"):
        validate_snapshot_inputs(bars("SPY"), {"XLK": bars("XLK")}, [state("XLK", "2026-08-14")], 2, date(2026, 8, 21), 52)
