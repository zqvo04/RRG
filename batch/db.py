"""Supabase (Postgres) access layer for the batch pipeline.

Thin wrapper over psycopg2 providing connection setup and idempotent UPSERT
helpers. psycopg2 is imported lazily so that ``--dry-run`` code paths (which
never touch the DB) run in environments without the driver installed.

Secrets: connection string comes from the ``DATABASE_URL`` env var only
(``.env`` locally, GitHub Secrets in CI). Never hard-coded.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Iterable, Sequence


def get_dsn() -> str:
    """Read the Postgres DSN from the environment (DATABASE_URL)."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not set. Put the Supabase connection string in "
            "your environment (.env locally, GitHub Secrets in CI)."
        )
    return dsn


def connect():
    """Open a psycopg2 connection (autocommit off; callers commit explicitly)."""
    import psycopg2  # lazy: only needed when actually writing to the DB

    return psycopg2.connect(get_dsn())


# ── UPSERTs (idempotent via ON CONFLICT) ────────────────────────────────────
def upsert_raw_prices(conn, rows: Sequence[tuple]) -> int:
    """UPSERT (ticker, interval, bar_date, close, adj_close) rows.

    Idempotent: re-running the same window restates close/adj_close in place.
    Returns the number of rows submitted.
    """
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    sql = """
        insert into raw_prices (ticker, interval, bar_date, close, adj_close)
        values %s
        on conflict (ticker, interval, bar_date) do update
            set close = excluded.close,
                adj_close = excluded.adj_close
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    return len(rows)


def upsert_rrg_values(conn, rows: Sequence[tuple]) -> int:
    """UPSERT (ticker, benchmark, interval, param_hash, bar_date, rs_ratio, rs_mom)."""
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    sql = """
        insert into rrg_values
            (ticker, benchmark, interval, param_hash, bar_date, rs_ratio, rs_mom)
        values %s
        on conflict (ticker, benchmark, interval, param_hash, bar_date) do update
            set rs_ratio = excluded.rs_ratio,
                rs_mom = excluded.rs_mom
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    return len(rows)


def last_success_date(conn) -> date | None:
    """Most recent ingest_log.run_date with status='success' (None if never)."""
    with conn.cursor() as cur:
        cur.execute(
            "select max(run_date) from ingest_log where status = 'success'"
        )
        (val,) = cur.fetchone()
    return val


def write_ingest_log(conn, run_date: date, status: str, rows_added: int) -> None:
    """Record (or restate) the outcome of a run. run_date is the PK."""
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into ingest_log (run_date, status, rows_added, finished_at)
            values (%s, %s, %s, now())
            on conflict (run_date) do update
                set status = excluded.status,
                    rows_added = excluded.rows_added,
                    finished_at = now()
            """,
            (run_date, status, rows_added),
        )


def load_raw_close(conn, tickers: Iterable[str], interval: str = "D"):
    """Load adjusted close for the given tickers into a wide DataFrame.

    Returns a DataFrame indexed by bar_date (DatetimeIndex) with one column per
    ticker (adjusted close). Used by the compute job; the app never calls this.
    """
    import pandas as pd

    tickers = list(tickers)
    with conn.cursor() as cur:
        cur.execute(
            """
            select bar_date, ticker, adj_close
            from raw_prices
            where interval = %s and ticker = any(%s)
            order by bar_date
            """,
            (interval, tickers),
        )
        recs = cur.fetchall()
    if not recs:
        return pd.DataFrame()
    df = pd.DataFrame(recs, columns=["bar_date", "ticker", "adj_close"])
    wide = df.pivot(index="bar_date", columns="ticker", values="adj_close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()
