"""RRG compute batch (GitHub Actions cron, batch-only).

Pipeline role::

    raw_prices (DB read) --> rrg.compute.compute_rrg --> rrg_values UPSERT

Reads adjusted close for the whole universe + SPY from raw_prices, computes
RS-Ratio / RS-Momentum per name against SPY using the *single frozen* param
set, and UPSERTs the non-NaN coordinates. Warm-up/insufficient-history rows are
NaN and are simply not written (a name with too little data contributes no rows
and is shown as "데이터 부족" by the app).

Only DAILY rrg_values are produced; the app derives weekly/longer tails by
sampling these daily rows.

Run::

    python -m batch.compute_job              # real run (needs DATABASE_URL)
    python -m batch.compute_job --dry-run    # compute + report, no DB writes
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from rrg import compute, config
from . import db


def build_rrg_rows(wide_close: pd.DataFrame) -> tuple[list[tuple], dict[str, int]]:
    """Compute RRG rows for every universe ticker vs SPY.

    Parameters
    ----------
    wide_close
        DataFrame indexed by date, one column per ticker (adjusted close),
        including the benchmark column.

    Returns
    -------
    (rows, per_ticker_counts) where rows are rrg_values tuples and
    per_ticker_counts maps ticker -> number of non-NaN bars emitted (0 means
    insufficient data / warm-up).
    """
    if config.BENCHMARK not in wide_close.columns:
        raise RuntimeError(
            f"benchmark {config.BENCHMARK} missing from raw_prices — cannot compute RS."
        )
    bench = wide_close[config.BENCHMARK]

    rows: list[tuple] = []
    counts: dict[str, int] = {}
    for ticker in config.UNIVERSE:
        if ticker not in wide_close.columns:
            counts[ticker] = 0
            continue
        res = compute.compute_rrg(wide_close[ticker], bench).dropna()
        counts[ticker] = len(res)
        for ts, row in res.iterrows():
            rows.append((
                ticker,
                config.BENCHMARK,
                "D",
                config.PARAM_HASH,
                ts.date(),
                float(row["rs_ratio"]),
                float(row["rs_mom"]),
            ))
    return rows, counts


def run(dry_run: bool) -> int:
    conn = db.connect()
    wide = db.load_raw_close(conn, config.DOWNLOAD_TICKERS, interval="D")
    if wide.empty:
        print("[compute] raw_prices is empty — run ingest first.", file=sys.stderr)
        conn.close()
        return 1

    rows, counts = build_rrg_rows(wide)
    print(f"[compute] param_hash={config.PARAM_HASH} bars/ticker:")
    for ticker, label in config.UNIVERSE.items():
        n = counts.get(ticker, 0)
        note = "" if n else "  <- 데이터 부족 (warm-up/insufficient)"
        print(f"   {ticker:6} {label:6} {n:>5} rows{note}")
    print(f"[compute] total {len(rows)} rrg_values rows")

    if dry_run:
        print(f"[compute] DRY-RUN: would UPSERT {len(rows)} rows")
        conn.close()
        return 0

    n = db.upsert_rrg_values(conn, rows)
    conn.commit()
    conn.close()
    print(f"[compute] committed {n} rrg_values rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    p = argparse.ArgumentParser(description="Compute RRG values into Supabase.")
    p.add_argument("--dry-run", action="store_true",
                   help="compute + report only; reads DB but writes nothing")
    args = p.parse_args(argv)
    return run(args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
