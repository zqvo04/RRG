from datetime import date, datetime, timedelta, timezone

import pytest

from pipeline.config import EngineSettings
from pipeline.engine import build_sector_state, quadrant
from pipeline.models import PriceBar

SETTINGS = EngineSettings(80, 52, 13, 4, 12, "rrg_proxy_v1")


def series(symbol: str, multiplier: float) -> list[PriceBar]:
    start, timestamp = date(2024, 1, 5), datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [PriceBar(symbol, start + timedelta(weeks=index), 100 * multiplier * (1 + index * 0.003), "fixture", timestamp) for index in range(80)]


def test_quadrants_cover_all_combinations() -> None:
    assert quadrant(100, 100) == "leading"
    assert quadrant(100, 99.9) == "weakening"
    assert quadrant(99.9, 99.9) == "lagging"
    assert quadrant(99.9, 100) == "improving"


def test_state_has_current_point_plus_12_prior_observations() -> None:
    state = build_sector_state("XLK", "Information Technology", series("XLK", 1.1), series("SPY", 1), SETTINGS)
    assert len(state.trail) == 13
    assert state.velocity is not None


def test_short_history_is_rejected() -> None:
    with pytest.raises(Exception, match="minimum"):
        build_sector_state("XLK", "Information Technology", series("XLK", 1)[:20], series("SPY", 1)[:20], SETTINGS)

