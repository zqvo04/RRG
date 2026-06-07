-- ============================================================================
-- RRG app — Supabase (Postgres) schema migration
-- ----------------------------------------------------------------------------
-- Role: persistent store for the batch pipeline. The Streamlit app reads from
-- rrg_values ONLY (never recomputes, never calls a data provider at runtime).
--
-- Storage strategy:
--   * `real` (4 bytes) for all price/RRG floats — half the size of double.
--   * raw_prices is append-only (UPSERT just restates the latest few bars).
--   * Only DAILY bars are stored ('D'); weekly views are derived by sampling
--     daily rrg_values in the app (spec: no separate weekly download/compute).
--
-- Capacity (free tier = 500 MB):
--   Postgres heap row ≈ 50-80 B incl. overhead. 14 tickers × ~3 yr × 252 td
--   ≈ 10.6 k rows ≈ ~0.8 MB for raw_prices. rrg_values is similar (13 names,
--   minus warm-up) ≈ ~0.8 MB. Even a full 30-yr sector backfill stays < 8 MB.
--   => The 500 MB ceiling is effectively irrelevant for this universe.
-- ============================================================================

-- ── raw close prices (append-only, auto_adjust=True so close == adj_close) ──
create table if not exists raw_prices (
    ticker     text not null,
    interval   text not null default 'D',   -- 'D' daily only (weekly derived)
    bar_date   date not null,
    close      real not null,                -- adjusted close (auto_adjust=True)
    adj_close  real,                         -- mirror of close (kept for clarity)
    primary key (ticker, interval, bar_date)
);

-- ── precomputed RRG coordinates (one frozen param_hash for the whole system) ─
create table if not exists rrg_values (
    ticker     text not null,
    benchmark  text not null,                -- always 'SPY'
    interval   text not null default 'D',
    param_hash text not null,                -- single frozen value (rrg.config)
    bar_date   date not null,
    rs_ratio   real,                         -- x-axis (100 = in line w/ SPY)
    rs_mom     real,                         -- y-axis (momentum of RS-Ratio)
    primary key (ticker, benchmark, interval, param_hash, bar_date)
);

-- Read pattern: latest-N bars for one ticker/param. DESC index serves the
-- "tail slice" queries (ORDER BY bar_date DESC LIMIT n) without a sort.
create index if not exists idx_rrg_values_lookup
    on rrg_values (ticker, benchmark, interval, param_hash, bar_date desc);

-- ── ingest run log (idempotency anchor for incremental download) ────────────
create table if not exists ingest_log (
    run_date    date primary key,            -- the cron run's date (UTC)
    status      text not null,               -- 'success' | 'partial' | 'failed'
    rows_added  integer not null default 0,
    finished_at timestamptz not null default now()
);
