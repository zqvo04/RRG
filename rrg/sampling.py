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


def sample_range(df: pd.DataFrame, range_td: int, step: int) -> pd.DataFrame:
    """Take the last ``range_td`` rows of ``df`` and keep every ``step``-th.

    Counts back from the newest row so the latest bar is always kept; the oldest
    in-range bar is always kept too. On short history the step is shrunk so at
    least :data:`MIN_POINTS` remain.
    """
    tail = df.iloc[-range_td:] if len(df) > range_td else df
    n = len(tail)
    if n == 0:
        return tail
    max_step = max(1, (n - 1) // (MIN_POINTS - 1))
    step = max(1, min(step, max_step))
    keep = set(range(n - 1, -1, -step))  # newest backward -> endpoint always in
    keep.add(0)                          # anchor oldest in-range bar
    return tail.iloc[sorted(keep)]


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
    return sample_range(df, range_td, step)


def sample_by_dates(df: pd.DataFrame, start, end, target_points: int = 13) -> pd.DataFrame:
    """Custom window: rows within [start, end], subsampled to ~target_points.

    The step is derived from how many bars fall in the window so the tail keeps
    a curve-friendly point count regardless of how wide a range the user picks.
    """
    mask = (df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))
    win = df.loc[mask]
    n = len(win)
    if n == 0:
        return win
    step = max(1, round(n / max(2, target_points)))
    return sample_range(win, n, step)
