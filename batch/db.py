"""Supabase access layer for the batch pipeline — REST (PostgREST) over HTTPS.

Why REST instead of a Postgres driver:
  * GitHub Actions runners are IPv4-only; Supabase *direct* connections are
    IPv6-only, and the *pooler* only accepts the built-in ``postgres`` user
    (custom roles are rejected with "tenant/user not found"). The managed CI
    network also blocks non-443 ports. REST over HTTPS sidesteps all of this.

Auth: the batch uses the project's ``service_role`` key (a pre-signed JWT that
bypasses RLS), supplied via ``SUPABASE_SERVICE_KEY``. The app keeps using the
read-only anon key, so write access stays confined to CI secrets.

Only the standard library is used (urllib) — no psycopg2, no supabase-py.
Function names/signatures mirror the previous driver version so ingest.py and
compute_job.py are unchanged (the returned ``Client`` exposes no-op
``commit``/``close`` for call-site compatibility).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date
from typing import Iterable, Sequence

_MAX_RETRY = 4
_PAGE = 1000  # PostgREST page size for reads / UPSERT batch size for writes


class Client:
    """Minimal Supabase REST client (base URL + service key)."""

    def __init__(self, base_url: str, key: str):
        self.base = base_url.rstrip("/")
        self.key = key

    # call-site compatibility with the old psycopg2 connection object
    def commit(self) -> None:  # noqa: D401 - REST writes are immediate
        pass

    def close(self) -> None:
        pass


def get_client() -> Client:
    """Build a Client from env (SUPABASE_URL + SUPABASE_SERVICE_KEY)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set.")
    if not key:
        raise RuntimeError(
            "SUPABASE_SERVICE_KEY is not set (use the project's service_role key)."
        )
    return Client(url, key)


# Kept for source compatibility with the previous driver-based module.
def connect() -> Client:
    return get_client()


# ── low-level request with retry/backoff ────────────────────────────────────
def _request(
    client: Client,
    method: str,
    path: str,
    body=None,
    extra_headers: dict | None = None,
) -> tuple[int, str]:
    headers = {"apikey": client.key, "Authorization": f"Bearer {client.key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    url = f"{client.base}/rest/v1/{path}"

    for attempt in range(_MAX_RETRY):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            # Retry only on transient 5xx; surface 4xx immediately.
            if e.code < 500 or attempt == _MAX_RETRY - 1:
                raise RuntimeError(f"{method} {path} -> {e.code}: {detail}")
        except urllib.error.URLError:
            if attempt == _MAX_RETRY - 1:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{method} {path}: exhausted retries")  # unreachable


# ── UPSERT helpers (idempotent via PostgREST merge-duplicates) ──────────────
def _upsert(client: Client, table: str, rows: list[dict], on_conflict: str) -> int:
    n = 0
    for i in range(0, len(rows), _PAGE):
        chunk = rows[i : i + _PAGE]
        _request(
            client,
            "POST",
            f"{table}?on_conflict={on_conflict}",
            body=chunk,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        n += len(chunk)
    return n


def upsert_raw_prices(client: Client, rows: Sequence[tuple]) -> int:
    """rows: (ticker, interval, bar_date, close, adj_close)."""
    if not rows:
        return 0
    payload = [
        {
            "ticker": t,
            "interval": iv,
            "bar_date": d.isoformat() if hasattr(d, "isoformat") else d,
            "close": c,
            "adj_close": a,
        }
        for (t, iv, d, c, a) in rows
    ]
    return _upsert(client, "raw_prices", payload, "ticker,interval,bar_date")


def upsert_rrg_values(client: Client, rows: Sequence[tuple]) -> int:
    """rows: (ticker, benchmark, interval, param_hash, bar_date, rs_ratio, rs_mom)."""
    if not rows:
        return 0
    payload = [
        {
            "ticker": t,
            "benchmark": b,
            "interval": iv,
            "param_hash": ph,
            "bar_date": d.isoformat() if hasattr(d, "isoformat") else d,
            "rs_ratio": rr,
            "rs_mom": rm,
        }
        for (t, b, iv, ph, d, rr, rm) in rows
    ]
    return _upsert(
        client,
        "rrg_values",
        payload,
        "ticker,benchmark,interval,param_hash,bar_date",
    )


def last_success_date(client: Client) -> date | None:
    """Most recent ingest_log.run_date with status='success' (None if never)."""
    _, body = _request(
        client,
        "GET",
        "ingest_log?select=run_date&status=eq.success&order=run_date.desc&limit=1",
    )
    recs = json.loads(body)
    if not recs:
        return None
    return date.fromisoformat(recs[0]["run_date"])


def write_ingest_log(client: Client, run_date: date, status: str, rows_added: int) -> None:
    """UPSERT a run row (run_date is the PK)."""
    _upsert(
        client,
        "ingest_log",
        [{"run_date": run_date.isoformat(), "status": status, "rows_added": rows_added}],
        "run_date",
    )


def load_raw_close(client: Client, tickers: Iterable[str], interval: str = "D"):
    """Load adjusted close for ``tickers`` into a wide DataFrame (date × ticker).

    Pages through PostgREST results (``limit``/``offset``) since the table holds
    more rows than a single response returns.
    """
    import pandas as pd

    tickers = list(tickers)
    in_list = ",".join(tickers)
    recs: list[dict] = []
    offset = 0
    while True:
        _, body = _request(
            client,
            "GET",
            f"raw_prices?select=bar_date,ticker,adj_close"
            f"&interval=eq.{interval}&ticker=in.({in_list})"
            f"&order=bar_date.asc&limit={_PAGE}&offset={offset}",
        )
        page = json.loads(body)
        recs.extend(page)
        if len(page) < _PAGE:
            break
        offset += _PAGE

    if not recs:
        return pd.DataFrame()
    df = pd.DataFrame(recs)
    wide = df.pivot(index="bar_date", columns="ticker", values="adj_close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()
