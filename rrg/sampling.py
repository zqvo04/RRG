"""Timeframe presets + tail sampling (pure pandas).

The daily ``rrg_values`` are sampled per timeframe so each tail keeps a roughly
constant, curve-friendly number of points (~5-15) regardless of range — longer
ranges use coarser steps. Sampling counts back from the newest bar so the most
recent point is always included; the oldest in-range bar is always included
too (anchors the tail).

Preset -> (range in trading days, sampling step in trading days). Steps are
chosen to realise the spec's target point counts (5/10/7/13/13/13).
"""

from __future__ import annotations

import pandas as pd

# preset -> (range_td, step_td)
PRESETS: dict[str, tuple[int, int]] = {
    "1W": (5, 1),     # ~5 pts  (every day)
    "2W": (10, 1),    # ~10 pts (every day)
    "1M": (21, 3),    # ~7 pts  (every 3rd day)
    "3M": (63, 5),    # ~13 pts (~weekly)
    "6M": (126, 10),  # ~13 pts (~twice/3wk)
    "1Y": (252, 20),  # ~13 pts (~biweekly)
}
PRESET_ORDER = ["1W", "2W", "1M", "3M", "6M", "1Y"]
DEFAULT_PRESET = "3M"

# A tail needs at least this many sampled points to be drawable.
MIN_POINTS = 3


def sample_tail(df: pd.DataFrame, preset: str) -> pd.DataFrame:
    """Slice ``df`` to the preset range and subsample by the preset step.

    Parameters
    ----------
    df : DataFrame
        One ticker's rrg values, sorted ascending by bar_date, with columns
        ``rs_ratio`` and ``rs_mom`` (and a date index or ``bar_date`` column).
    preset : str
        One of :data:`PRESETS`.

    Returns
    -------
    DataFrame
        The sampled rows in chronological order. Newest and oldest in-range
        bars are always present.
    """
    range_td, step = PRESETS[preset]
    tail = df.iloc[-range_td:] if len(df) > range_td else df
    n = len(tail)
    if n == 0:
        return tail

    # If the available history is short, shrink the step so we still keep at
    # least MIN_POINTS (a big step over few bars would collapse to endpoints).
    max_step = max(1, (n - 1) // (MIN_POINTS - 1))
    step = min(step, max_step)

    # Indices counted back from the newest (n-1) so the endpoint is always in.
    keep = set(range(n - 1, -1, -step))
    keep.add(0)  # always anchor the oldest in-range bar
    return tail.iloc[sorted(keep)]
