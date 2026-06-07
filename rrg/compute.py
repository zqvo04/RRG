"""RRG calculation engine (pure, deterministic, no I/O).

Implements the frozen RRG definition from the project spec. Given a security's
close-price series and the benchmark's close-price series, produces the two RRG
coordinates per bar:

    RS-Ratio     -> x-axis (relative strength, 100 = in line with benchmark)
    RS-Momentum  -> y-axis (rate of change of relative strength)

Formula chain (all parameters are constants from ``rrg.config``)::

    RS_t        = 100 * (P_t / B_t)
    RS_smooth   = EMA(RS, span=ema_span)
    RS-Ratio    = 100 + clip(zscore_roll(RS_smooth, ratio_window), -3.5, 3.5) * scale
    M_t         = RS-Ratio_t / RS-Ratio_{t-1}
    RS-Momentum = 100 + clip(zscore_roll(EMA(M, span=ema_span), mom_window), -3.5, 3.5) * scale

where zscore_roll(x, w) = (x - SMA(x, w)) / max(rolling_std(x, w), eps).

Guards (spec-mandated):
  * Price NaNs are dropped, never forward-filled.
  * Warm-up guard: until ``ratio_window + mom_window`` valid bars exist, output
    is NaN. No interpolation of intermediate NaNs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


# ── primitive transforms ────────────────────────────────────────────────────
def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average (pandas ``ewm``, ``adjust=False``).

    ``adjust=False`` gives the classic recursive EMA used in technical analysis
    (each point depends only on the prior EMA + current value), which is
    deterministic and matches charting conventions.
    """
    return series.ewm(span=span, adjust=False).mean()


def zscore_rolling(
    series: pd.Series,
    window: int,
    *,
    std_floor: float = config.STD_FLOOR,
    ddof: int = config.ZSCORE_DDOF,
) -> pd.Series:
    """Rolling z-score: (x - SMA) / max(rolling_std, eps).

    Mean and std are simple (SMA-based) rolling statistics over ``window`` bars.
    The std floor (epsilon) prevents division by zero on flat windows.
    """
    roll = series.rolling(window=window, min_periods=window)
    mean = roll.mean()
    std = roll.std(ddof=ddof)
    # Clamp std up to the floor element-wise (preserves NaN where window is short).
    std_safe = std.clip(lower=std_floor)
    return (series - mean) / std_safe


def _axis(z: pd.Series) -> pd.Series:
    """Convert a rolling z-score into an RRG axis value: 100 + clip(z) * scale."""
    return 100.0 + z.clip(lower=-config.CLIP, upper=config.CLIP) * config.SCALE


# ── main entry point ────────────────────────────────────────────────────────
def compute_rrg(
    price: pd.Series,
    benchmark: pd.Series,
    *,
    ema_span: int = config.EMA_SPAN,
    ratio_window: int = config.RATIO_WINDOW,
    mom_window: int = config.MOM_WINDOW,
) -> pd.DataFrame:
    """Compute RS-Ratio / RS-Momentum for one security against the benchmark.

    Parameters
    ----------
    price, benchmark
        Close-price series indexed by bar date. They are inner-joined on their
        shared index so only co-observed bars are used.

    Returns
    -------
    DataFrame indexed by bar date with float columns ``rs_ratio`` and
    ``rs_mom``. Rows inside the warm-up region (or with insufficient data) are
    NaN. The frame is reindexed back onto the *full* aligned date range so the
    caller always sees one row per co-observed bar.
    """
    # 1) Align on shared dates and drop any bar where either price is missing.
    #    (No forward-fill — gaps stay gaps.)
    df = pd.concat({"p": price, "b": benchmark}, axis=1).dropna()

    full_index = df.index
    n_valid = len(df)

    # 2) Warm-up guard: not enough history -> all NaN, no partial output.
    if n_valid < config.WARMUP_BARS:
        return pd.DataFrame(
            {"rs_ratio": np.nan, "rs_mom": np.nan},
            index=full_index,
            dtype="float64",
        )

    # 3) Relative strength and its smoothed form.
    rs = 100.0 * (df["p"] / df["b"])           # RS_t
    rs_smooth = ema(rs, ema_span)              # EMA(RS)

    # 4) RS-Ratio (x-axis): z-score of smoothed RS over ratio_window.
    rs_ratio = _axis(zscore_rolling(rs_smooth, ratio_window))

    # 5) Momentum: bar-over-bar ratio of RS-Ratio, smoothed, then z-scored.
    mom = rs_ratio / rs_ratio.shift(1)         # M_t
    mom_smooth = ema(mom, ema_span)            # EMA(M)
    rs_mom = _axis(zscore_rolling(mom_smooth, mom_window))

    out = pd.DataFrame({"rs_ratio": rs_ratio, "rs_mom": rs_mom})
    # Reindex onto the full aligned range (cosmetic: keeps every co-observed bar).
    return out.reindex(full_index).astype("float64")


def to_weekly(daily_close: pd.Series) -> pd.Series:
    """Derive a weekly (W-FRI) close series from a daily close series.

    Spec: weekly bars are *derived* by resampling daily — never downloaded
    separately. Uses last observation in each Friday-anchored week.
    """
    return daily_close.resample("W-FRI").last().dropna()
