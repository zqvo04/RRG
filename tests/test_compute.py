"""Correctness tests for the RRG calculation engine.

Strategy: each numeric assertion is checked against an *independent* reference
(explicit-loop EMA, raw NumPy z-score) so the test does not merely echo the
implementation. Plus structural guards: warm-up, NaN handling, clipping,
constant-ratio invariants, weekly resampling.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rrg import compute, config


# ── helpers / independent reference implementations ─────────────────────────
def daily_index(n: int, start: str = "2023-01-02") -> pd.DatetimeIndex:
    """n consecutive business days."""
    return pd.bdate_range(start=start, periods=n)


def ref_ema(arr: np.ndarray, span: int) -> np.ndarray:
    """Recursive EMA reference (adjust=False), explicit loop."""
    alpha = 2.0 / (span + 1.0)
    out = np.empty(len(arr), dtype=float)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


def ref_zscore_last(arr: np.ndarray, window: int, eps: float = 1e-8) -> float:
    """z-score of the final element over the trailing window (NumPy, ddof=0)."""
    w = arr[-window:]
    mean = w.mean()
    std = max(float(w.std()), eps)  # np.std defaults to ddof=0 (population)
    return (arr[-1] - mean) / std


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def synthetic() -> tuple[pd.Series, pd.Series]:
    """Deterministic price + benchmark series (seeded geometric walk)."""
    n = 160
    idx = daily_index(n)
    rng = np.random.default_rng(42)
    p = 100.0 * np.exp(np.cumsum(rng.normal(0.0005, 0.012, n)))
    b = 400.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.009, n)))
    return pd.Series(p, index=idx), pd.Series(b, index=idx)


# ── primitive transforms ────────────────────────────────────────────────────
def test_ema_matches_reference():
    s = pd.Series([1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0])
    got = compute.ema(s, span=3).to_numpy()
    expected = ref_ema(s.to_numpy(), span=3)
    np.testing.assert_allclose(got, expected, rtol=1e-12)


def test_zscore_rolling_matches_numpy():
    rng = np.random.default_rng(7)
    arr = rng.normal(0, 1, 50)
    s = pd.Series(arr, index=daily_index(50))
    window = 10
    got = compute.zscore_rolling(s, window).to_numpy()
    # Reference: recompute each fully-populated window with NumPy ddof=0.
    for i in range(window - 1, len(arr)):
        w = arr[i - window + 1 : i + 1]
        std = max(float(w.std()), config.STD_FLOOR)
        ref = (arr[i] - w.mean()) / std
        assert got[i] == pytest.approx(ref, rel=1e-12)
    # First window-1 entries must be NaN (min_periods == window).
    assert np.isnan(got[: window - 1]).all()


def test_zscore_std_floor_prevents_divzero():
    # Flat series -> rolling std == 0 -> floored to eps -> z == 0 (not inf/nan).
    s = pd.Series([5.0] * 30, index=daily_index(30))
    z = compute.zscore_rolling(s, 10)
    tail = z.iloc[9:]  # fully-populated windows
    assert np.isfinite(tail).all()
    np.testing.assert_allclose(tail.to_numpy(), 0.0, atol=1e-6)


# ── warm-up guard ───────────────────────────────────────────────────────────
def test_warmup_guard_all_nan_when_too_short():
    n = config.WARMUP_BARS - 1
    idx = daily_index(n)
    p = pd.Series(np.linspace(100, 120, n), index=idx)
    b = pd.Series(np.linspace(400, 410, n), index=idx)
    out = compute.compute_rrg(p, b)
    assert len(out) == n
    assert out["rs_ratio"].isna().all()
    assert out["rs_mom"].isna().all()


def test_short_history_emits_partial_values(synthetic):
    # A series too short for the full 63/21 windows but >= WARMUP_BARS must still
    # emit some non-NaN tail (partial-window z-scores), not stay all-NaN.
    p, b = synthetic
    n = 50  # < RATIO_WINDOW (63) but > WARMUP_BARS (30)
    out = compute.compute_rrg(p.iloc[:n], b.iloc[:n])
    assert len(out) == n
    assert out["rs_ratio"].notna().any()
    assert out["rs_mom"].notna().any()
    assert np.isfinite(out["rs_ratio"].iloc[-1])
    assert np.isfinite(out["rs_mom"].iloc[-1])


def test_warmup_produces_values_once_enough_history(synthetic):
    p, b = synthetic
    out = compute.compute_rrg(p, b)
    # With 160 bars (> 84 warm-up) the final rows must be finite.
    assert np.isfinite(out["rs_ratio"].iloc[-1])
    assert np.isfinite(out["rs_mom"].iloc[-1])
    # Early rows (before any rolling window can fill) remain NaN, not interpolated.
    assert out["rs_ratio"].iloc[0] != out["rs_ratio"].iloc[0]  # NaN


# ── end-to-end value check against independent reference ────────────────────
def test_rs_ratio_final_value_matches_reference(synthetic):
    p, b = synthetic
    out = compute.compute_rrg(p, b)

    # Reproduce the RS-Ratio chain independently with NumPy.
    rs = 100.0 * (p.to_numpy() / b.to_numpy())
    rs_smooth = ref_ema(rs, config.EMA_SPAN)
    z = ref_zscore_last(rs_smooth, config.RATIO_WINDOW)
    z = max(-config.CLIP, min(config.CLIP, z))
    expected = 100.0 + z * config.SCALE

    assert out["rs_ratio"].iloc[-1] == pytest.approx(expected, rel=1e-9)


def test_rs_mom_final_value_matches_reference(synthetic):
    p, b = synthetic
    out = compute.compute_rrg(p, b)

    rs = 100.0 * (p.to_numpy() / b.to_numpy())
    rs_smooth = ref_ema(rs, config.EMA_SPAN)
    # Full RS-Ratio series (NumPy) so we can build momentum.
    full_idx = p.index
    n = len(rs_smooth)
    ratio_z = np.full(n, np.nan)
    # partial windows from RATIO_MIN_PERIODS (matches rolling min_periods)
    for i in range(config.RATIO_MIN_PERIODS - 1, n):
        w = rs_smooth[max(0, i - config.RATIO_WINDOW + 1) : i + 1]
        if len(w) < config.RATIO_MIN_PERIODS:
            continue
        std = max(float(w.std()), config.STD_FLOOR)
        ratio_z[i] = (rs_smooth[i] - w.mean()) / std
    ratio = 100.0 + np.clip(ratio_z, -config.CLIP, config.CLIP) * config.SCALE

    mom = np.full(n, np.nan)
    mom[1:] = ratio[1:] / ratio[:-1]
    # EMA over the momentum series, but pandas ewm skips leading NaNs; emulate by
    # using the implementation's own pathway for the final value via pandas.
    mom_s = pd.Series(mom, index=full_idx)
    mom_smooth = compute.ema(mom_s, config.EMA_SPAN).to_numpy()
    z = ref_zscore_last(mom_smooth, config.MOM_WINDOW)
    z = max(-config.CLIP, min(config.CLIP, z))
    expected = 100.0 + z * config.SCALE

    assert out["rs_mom"].iloc[-1] == pytest.approx(expected, rel=1e-9)


# ── invariants ──────────────────────────────────────────────────────────────
def test_constant_ratio_centers_at_100():
    # price exactly proportional to benchmark -> RS constant -> both axes == 100.
    n = 150
    idx = daily_index(n)
    b = pd.Series(np.linspace(400, 460, n), index=idx)
    p = b * 0.25  # constant ratio
    out = compute.compute_rrg(p, b)
    tail = out.dropna()
    np.testing.assert_allclose(tail["rs_ratio"].to_numpy(), 100.0, atol=1e-4)
    np.testing.assert_allclose(tail["rs_mom"].to_numpy(), 100.0, atol=1e-4)


def test_axes_respect_clip_bounds(synthetic):
    p, b = synthetic
    out = compute.compute_rrg(p, b).dropna()
    lo, hi = 100.0 - config.CLIP * config.SCALE, 100.0 + config.CLIP * config.SCALE
    assert out["rs_ratio"].between(lo, hi).all()
    assert out["rs_mom"].between(lo, hi).all()


def test_extreme_jump_is_clipped():
    # A huge spike pushes the z-score past 3.5; axis must saturate, not exceed.
    n = 150
    idx = daily_index(n)
    base = np.full(n, 100.0)
    base[-1] = 100_000.0  # massive outlier on the last bar
    p = pd.Series(base, index=idx)
    b = pd.Series(np.full(n, 400.0), index=idx)
    out = compute.compute_rrg(p, b)
    assert out["rs_ratio"].iloc[-1] == pytest.approx(100.0 + config.CLIP, rel=1e-6)


# ── data hygiene ────────────────────────────────────────────────────────────
def test_price_nan_dropped_not_filled(synthetic):
    p, b = synthetic
    p2 = p.copy()
    p2.iloc[50] = np.nan  # punch a hole
    out = compute.compute_rrg(p2, b)
    # The NaN bar must be absent from output (dropped), not forward-filled.
    assert p2.index[50] not in out.index
    assert len(out) == len(p) - 1


def test_misaligned_indices_inner_joined():
    idx_a = daily_index(120)
    idx_b = daily_index(120, start="2023-01-09")  # shifted by ~1 week
    p = pd.Series(np.linspace(100, 130, 120), index=idx_a)
    b = pd.Series(np.linspace(400, 430, 120), index=idx_b)
    out = compute.compute_rrg(p, b)
    shared = idx_a.intersection(idx_b)
    assert list(out.index) == list(shared)


# ── weekly derivation ───────────────────────────────────────────────────────
def test_to_weekly_resamples_to_friday():
    idx = daily_index(20)  # 4 weeks of business days
    s = pd.Series(np.arange(20, dtype=float), index=idx)
    w = compute.to_weekly(s)
    # Every weekly bar must be anchored on a Friday (weekday == 4).
    assert all(ts.weekday() == 4 for ts in w.index)
    # Last value of each week == last daily value in that week.
    assert w.iloc[0] == s.loc[: w.index[0]].iloc[-1]


# ── config sanity ───────────────────────────────────────────────────────────
def test_param_hash_is_stable_and_short():
    assert isinstance(config.PARAM_HASH, str)
    assert len(config.PARAM_HASH) == 12
    assert config.PARAM_HASH == config._compute_param_hash()


def test_universe_excludes_benchmark():
    assert config.BENCHMARK not in config.UNIVERSE
    assert config.BENCHMARK in config.DOWNLOAD_TICKERS
    assert len(config.UNIVERSE) == 21          # 11 sectors + 2 crypto + 8 sub
    # every ticker maps to exactly one group, default-off group hidden initially
    assert set(config.GROUP_OF) == set(config.UNIVERSE)
    assert config.GROUP_DEFAULT_ON["세부"] is False
    assert list(config.GROUPS) == ["기본", "세부"]
