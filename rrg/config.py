"""Fixed configuration for the RRG app.

All RRG parameters are *frozen constants* — the spec explicitly forbids
user-facing parameter customization, so exactly one ``PARAM_HASH`` is ever
produced. The tracking universe (US sector ETFs + crypto ETFs) and their
Korean display labels live here as the single source of truth.
"""

from __future__ import annotations

import hashlib

# ── Benchmark ──────────────────────────────────────────────────────────────
BENCHMARK: str = "SPY"

# ── RRG calculation parameters (FROZEN — do not expose to users) ────────────
EMA_SPAN: int = 10           # smoothing span for RS and Momentum EMAs
RATIO_WINDOW: int = 63       # rolling z-score window for RS-Ratio (~3 months)
MOM_WINDOW: int = 21         # rolling z-score window for RS-Momentum (~1 month)
SCALE: float = 1.0           # z-score -> RRG axis scaling
STD_FLOOR: float = 1e-8      # epsilon to avoid divide-by-zero in z-score
CLIP: float = 3.5            # z-score clamp (both sides) before scaling
ZSCORE_DDOF: int = 0         # rolling std uses population std (deterministic)

# Minimum number of valid bars required before any non-NaN value is emitted.
# Below this the warm-up guard returns NaN (no interpolation, no fill).
WARMUP_BARS: int = RATIO_WINDOW + MOM_WINDOW  # 84

# ── Tracking universe ───────────────────────────────────────────────────────
# Ticker -> Korean display label. Order here defines default legend order.
# Benchmark (SPY) is intentionally absent: every name's RS is measured vs SPY.
UNIVERSE: dict[str, str] = {
    "XLK": "기술",
    "XLV": "헬스케어",
    "XLY": "임의소비재",
    "XLP": "필수소비재",
    "XLRE": "부동산",
    "XLF": "금융",
    "XLI": "산업",
    "XLB": "소재",
    "XLE": "에너지",
    "XLU": "유틸리티",
    "XLC": "커뮤니케이션",
    "IBIT": "비트코인",
    "ETHA": "이더리움",
}

# Tickers we actually download (universe + benchmark, deduped, order-stable).
DOWNLOAD_TICKERS: list[str] = list(UNIVERSE.keys()) + [BENCHMARK]


def _compute_param_hash() -> str:
    """Deterministic short hash of the frozen parameter set.

    Encodes benchmark + every numeric parameter so that, were a parameter ever
    to change, the stored ``rrg_values`` rows would key under a different hash
    instead of being silently mixed. With frozen params this yields exactly one
    value for the entire system.
    """
    canonical = (
        f"benchmark={BENCHMARK};ema_span={EMA_SPAN};ratio_window={RATIO_WINDOW};"
        f"mom_window={MOM_WINDOW};scale={SCALE};std_floor={STD_FLOOR};"
        f"clip={CLIP};ddof={ZSCORE_DDOF}"
    )
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()[:12]


# The one and only param hash used as a DB key across the whole system.
PARAM_HASH: str = _compute_param_hash()

# ── Display ─────────────────────────────────────────────────────────────────
def label(ticker: str) -> str:
    """Korean display label for a ticker (falls back to the ticker itself)."""
    return UNIVERSE.get(ticker, ticker)
