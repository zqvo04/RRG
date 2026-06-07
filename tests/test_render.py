"""Tests for the app's pure rendering helpers: tail sampling + Catmull-Rom."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rrg import curve
from rrg.sampling import PRESETS, sample_tail


def make_df(n: int) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {"rs_ratio": np.linspace(98, 102, n), "rs_mom": np.linspace(99, 101, n)},
        index=idx,
    )


# ── sampling ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("preset,expected", [
    ("1W", 5), ("2W", 10), ("1M", 7), ("3M", 13), ("6M", 13), ("1Y", 13),
])
def test_sample_counts_match_spec(preset, expected):
    df = make_df(300)
    out = sample_tail(df, preset)
    # within ±1 of the spec's target point count
    assert abs(len(out) - expected) <= 1, (preset, len(out))


def test_sample_includes_endpoints():
    df = make_df(300)
    out = sample_tail(df, "1Y")
    range_td = PRESETS["1Y"][0]
    tail = df.iloc[-range_td:]
    assert out.index[-1] == tail.index[-1]   # newest always present
    assert out.index[0] == tail.index[0]     # oldest in-range always present


def test_sample_chronological_and_unique():
    out = sample_tail(make_df(300), "6M")
    assert list(out.index) == sorted(out.index)
    assert out.index.is_unique


def test_sample_short_series_uses_what_exists():
    df = make_df(4)  # fewer than any range
    out = sample_tail(df, "1Y")
    assert len(out) == 4
    assert out.index[-1] == df.index[-1]


# ── catmull-rom ─────────────────────────────────────────────────────────────
def test_curve_passes_through_control_points():
    pts = np.array([[100, 100], [101, 102], [99, 101], [100, 98], [102, 100]], float)
    c = curve.catmull_rom(pts, samples_per_seg=20)
    # every control point must appear on the produced curve
    for p in pts:
        d = np.hypot(c[:, 0] - p[0], c[:, 1] - p[1]).min()
        assert d < 1e-9, (p, d)


def test_curve_endpoints_preserved():
    pts = np.array([[1, 1], [2, 3], [4, 2], [5, 5]], float)
    c = curve.catmull_rom(pts, samples_per_seg=10)
    np.testing.assert_allclose(c[0], pts[0])
    np.testing.assert_allclose(c[-1], pts[-1])


def test_curve_length_formula():
    pts = np.array([[0, 0], [1, 1], [2, 0], [3, 1]], float)  # n=4
    spp = 20
    c = curve.catmull_rom(pts, samples_per_seg=spp)
    # (n-1) segments * spp + final closing point
    assert len(c) == (len(pts) - 1) * spp + 1


def test_curve_degenerate_short_input_returned_asis():
    pts = np.array([[1, 1], [2, 2]], float)
    c = curve.catmull_rom(pts)
    np.testing.assert_array_equal(c, pts)
