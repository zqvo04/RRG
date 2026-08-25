from __future__ import annotations

from datetime import date
from typing import Any

from pipeline.errors import DataValidationError
from pipeline.models import PriceBar, SectorState


def _check(passed: bool, observed: Any, expected: Any, message: str) -> dict[str, Any]:
    return {"passed": passed, "observed": observed, "expected": expected, "message": message}


def validate_snapshot_inputs(
    benchmark: list[PriceBar],
    sector_bars: dict[str, list[PriceBar]],
    states: list[SectorState],
    expected_symbols: int,
    expected_as_of_week: date,
    min_history_weeks: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return public quality/provenance metadata and block publication on failed hard checks."""
    all_series = {benchmark[0].symbol if benchmark else "benchmark": benchmark, **sector_bars}
    duplicate_symbols = sorted(symbol for symbol, bars in all_series.items() if len({bar.week_end for bar in bars}) != len(bars))
    non_positive_symbols = sorted(symbol for symbol, bars in all_series.items() if any(bar.adjusted_close <= 0 for bar in bars))
    histories = {symbol: len(bars) for symbol, bars in all_series.items()}
    state_dates = sorted({state.trail[-1].week for state in states if state.trail})
    expected_week = expected_as_of_week.isoformat()
    checks = {
        "symbol_set": _check(len(all_series) == expected_symbols, len(all_series), expected_symbols, "All benchmark and sector series were received."),
        "history_length": _check(bool(histories) and min(histories.values()) >= min_history_weeks, min(histories.values()) if histories else 0, min_history_weeks, "Every series has the minimum completed-week history."),
        "duplicate_weeks": _check(not duplicate_symbols, duplicate_symbols, [], "No completed-week duplicates are present."),
        "positive_prices": _check(not non_positive_symbols, non_positive_symbols, [], "All adjusted close values are positive."),
        "date_alignment": _check(len(state_dates) == 1 and state_dates[0] == expected_week, state_dates, [expected_week], "All sectors align to the expected completed Friday."),
    }
    hard_failures = [name for name, value in checks.items() if not value["passed"]]
    if hard_failures:
        raise DataValidationError(f"Snapshot quality checks failed: {', '.join(hard_failures)}")

    provider_times = [bar.source_timestamp.isoformat() for bars in all_series.values() for bar in bars]
    provenance = {
        "providers": sorted({bar.source for bars in all_series.values() for bar in bars}),
        "source_latest_at": max(provider_times) if provider_times else None,
        "series": {symbol: {"observations": len(bars), "latest_week": bars[-1].week_end.isoformat() if bars else None} for symbol, bars in sorted(all_series.items())},
    }
    return {
        "symbols_expected": expected_symbols,
        "symbols_received": len(all_series),
        "dates_aligned": True,
        "publishable": True,
        "checks": checks,
    }, provenance
