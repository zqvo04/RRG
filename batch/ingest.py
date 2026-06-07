"""Incremental price ingestion (GitHub Actions cron, batch-only).

Pipeline role::

    yfinance (incremental download) --> raw_prices UPSERT
                          |
                          └─ on failure per-ticker --> stooq fallback

Key behaviours (spec):
  * auto_adjust=True  -> close is already split/dividend adjusted; we mirror it
    into adj_close so downstream can read either column.
  * Incremental only  -> download starts just after the last successful run
    (ingest_log), with a small overlap window so restated bars get corrected.
  * Idempotent        -> raw_prices UPSERT (ON CONFLICT DO UPDATE).
  * SPY is downloaded in the same call as the universe so trading-day calendars
    line up.
  * stooq fallback    -> any ticker yfinance fails/empties is retried via stooq.

Run::

    python -m batch.ingest                 # real run (needs DATABASE_URL)
    python -m batch.ingest --dry-run       # fetch + report only, no DB needed
    python -m batch.ingest --dry-run --days 30
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta

import pandas as pd

from rrg import config

# Re-fetch this many calendar days before the last success, so late
# restatements (dividends, corrections) overwrite cleanly via UPSERT.
OVERLAP_DAYS = 7
# First-ever run backfills this many years (env BACKFILL_YEARS overrides).
DEFAULT_BACKFILL_YEARS = 3


# ── data sources ────────────────────────────────────────────────────────────
def fetch_yfinance(tickers: list[str], start: date) -> dict[str, pd.Series]:
    """Download daily adjusted close for ``tickers`` since ``start``.

    Returns {ticker: close Series (DatetimeIndex)}. Tickers that come back empty
    are simply omitted from the dict (the caller routes them to the fallback).
    """
    import yfinance as yf

    raw = yf.download(
        tickers,
        start=start.isoformat(),
        interval="1d",
        auto_adjust=True,      # close == adjusted close
        progress=False,
        group_by="ticker",
        threads=True,
    )
    out: dict[str, pd.Series] = {}
    if raw is None or len(raw) == 0:
        return out
    for t in tickers:
        try:
            s = raw[t]["Close"].dropna()
        except (KeyError, TypeError):
            continue
        if len(s):
            out[t] = s
    return out


def fetch_stooq(tickers: list[str], start: date) -> dict[str, pd.Series]:
    """Fallback: pull daily close from stooq via pandas-datareader.

    stooq US symbols are suffixed ``.US`` and returned newest-first. Coverage is
    solid for the SPDR sectors + SPY; newer crypto ETFs may be thin, which is
    acceptable since this is only a backstop for yfinance outages.
    """
    from pandas_datareader import data as pdr

    out: dict[str, pd.Series] = {}
    for t in tickers:
        try:
            df = pdr.DataReader(f"{t}.US", "stooq", start=start)
        except Exception as exc:  # noqa: BLE001 — best-effort backstop
            print(f"  [stooq] {t}: {exc!r}", file=sys.stderr)
            continue
        if df is None or df.empty or "Close" not in df:
            continue
        s = df["Close"].sort_index().dropna()
        if len(s):
            out[t] = s
    return out


# ── row building ────────────────────────────────────────────────────────────
def build_rows(prices: dict[str, pd.Series]) -> list[tuple]:
    """Flatten {ticker: close Series} into raw_prices tuples.

    close and adj_close are identical (auto_adjust=True), per decision #1.
    """
    rows: list[tuple] = []
    for ticker, s in prices.items():
        for ts, val in s.items():
            if pd.isna(val):
                continue
            d = ts.date() if hasattr(ts, "date") else ts
            c = float(val)
            rows.append((ticker, "D", d, c, c))
    return rows


# ── start-date resolution ───────────────────────────────────────────────────
def resolve_start(conn, backfill_years: int) -> date:
    """Incremental start: (last_success - overlap), else backfill horizon."""
    last = db.last_success_date(conn)
    if last is not None:
        return last - timedelta(days=OVERLAP_DAYS)
    return date.today() - timedelta(days=365 * backfill_years)


# ── orchestration ───────────────────────────────────────────────────────────
def run(dry_run: bool, days: int, backfill_years: int) -> int:
    tickers = config.DOWNLOAD_TICKERS  # universe + SPY, same call

    if dry_run:
        start = date.today() - timedelta(days=days)
        conn = None
    else:
        conn = db.connect()
        start = resolve_start(conn, backfill_years)

    print(f"[ingest] start={start} tickers={len(tickers)} dry_run={dry_run}")

    # Primary source, then route empties to the fallback.
    prices = fetch_yfinance(tickers, start)
    missing = [t for t in tickers if t not in prices]
    if missing:
        print(f"[ingest] yfinance missing {missing} -> stooq fallback")
        prices.update(fetch_stooq(missing, start))

    got = sorted(prices.keys())
    still_missing = [t for t in tickers if t not in prices]
    rows = build_rows(prices)
    print(f"[ingest] fetched {len(got)}/{len(tickers)} tickers, {len(rows)} rows")
    for t in tickers:
        s = prices.get(t)
        tag = f"{len(s):>4} rows  {s.index.min().date()}..{s.index.max().date()}" \
            if s is not None else "   MISSING"
        print(f"   {t:6} {tag}")

    status = "success" if not still_missing else (
        "partial" if got else "failed"
    )

    if dry_run:
        print(f"[ingest] DRY-RUN: would UPSERT {len(rows)} rows, status={status}")
        return 0

    n = db.upsert_raw_prices(conn, rows)
    db.write_ingest_log(conn, date.today(), status, n)
    conn.commit()
    conn.close()
    print(f"[ingest] committed {n} rows, status={status}")
    return 0 if status != "failed" else 1


def main(argv: list[str] | None = None) -> int:
    import os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    p = argparse.ArgumentParser(description="Incremental price ingest into Supabase.")
    p.add_argument("--dry-run", action="store_true",
                   help="fetch + report only; no DB connection or writes")
    p.add_argument("--days", type=int, default=30,
                   help="dry-run lookback window in days (default 30)")
    args = p.parse_args(argv)

    backfill_years = int(os.environ.get("BACKFILL_YEARS", DEFAULT_BACKFILL_YEARS))
    return run(args.dry_run, args.days, backfill_years)


# Imported lazily at module level only when not dry-running keeps things simple;
# db itself imports psycopg2 lazily, so importing it here is cheap.
from . import db  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
