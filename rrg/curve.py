"""Catmull-Rom spline interpolation for RRG tails (pure NumPy).

The spec forbids Plotly's ``shape='spline'`` and requires an explicit
Catmull-Rom curve through the sampled tail points, with ``samples_per_seg``
interpolated points per segment. The curve passes *through* every control
point (interpolating, not approximating), which keeps node markers exactly on
the line.
"""

from __future__ import annotations

import numpy as np

SAMPLES_PER_SEG = 20


def catmull_rom(points, samples_per_seg: int = SAMPLES_PER_SEG):
    """Dense polyline through ``points`` using a uniform Catmull-Rom spline.

    Parameters
    ----------
    points : array-like, shape (n, 2)
        Ordered control points (x, y).
    samples_per_seg : int
        Interpolated points generated per segment between consecutive controls.

    Returns
    -------
    ndarray, shape (m, 2)
        The smooth curve. For n < 3 there is nothing to interpolate, so the
        input points are returned unchanged (a 2-point tail is just a line).
    """
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 3:
        return pts.copy()

    # Phantom endpoints (duplicate first/last) so the first and last real
    # segments have control neighbours — the curve still starts/ends exactly
    # on the first/last point.
    padded = np.vstack([pts[0], pts, pts[-1]])

    t = np.linspace(0.0, 1.0, samples_per_seg, endpoint=False).reshape(-1, 1)
    t2, t3 = t * t, t * t * t

    segments = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        # Uniform Catmull-Rom basis (Cardinal spline, tension 0.5).
        seg = 0.5 * (
            (2.0 * p1)
            + (-p0 + p2) * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
            + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
        )
        segments.append(seg)
    segments.append(pts[-1].reshape(1, 2))  # close on the exact last control
    return np.vstack(segments)
