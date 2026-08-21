from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pipeline.models import PriceBar

NEW_YORK = ZoneInfo("America/New_York")
FRIDAY_CLOSE = time(16, 15)


def friday_anchor(day: date) -> date:
    """Return the Friday belonging to the US trading week containing ``day``."""
    return day + timedelta(days=(4 - day.weekday()) % 7)


def last_completed_friday(reference: datetime | None = None) -> date:
    """Return the most recent Friday whose regular US session has finished."""
    local = (reference or datetime.now(NEW_YORK)).astimezone(NEW_YORK)
    days_since_friday = (local.weekday() - 4) % 7
    candidate = local.date() - timedelta(days=days_since_friday)
    if local.weekday() == 4 and local.time() < FRIDAY_CLOSE:
        candidate -= timedelta(days=7)
    return candidate


def completed_friday_bars(bars: list[PriceBar], reference: datetime | None = None) -> list[PriceBar]:
    """Keep only completed US weeks and label each bar with its Friday anchor.

    A Friday holiday may yield a Thursday source date. It is retained only after
    that Friday closes and is relabeled to Friday so every RRG observation has a
    consistent weekly coordinate.
    """
    cutoff = last_completed_friday(reference)
    chosen: dict[date, PriceBar] = {}
    for bar in bars:
        anchor = friday_anchor(bar.week_end)
        if anchor > cutoff:
            continue
        previous = chosen.get(anchor)
        if previous is None or bar.week_end > previous.week_end:
            chosen[anchor] = bar
    return [
        PriceBar(bar.symbol, anchor, bar.adjusted_close, bar.source, bar.source_timestamp)
        for anchor, bar in sorted(chosen.items())
    ]

