"""Batch jobs (GitHub Actions cron only): ingest + RRG compute.

These modules perform network/DB I/O and MUST NOT be imported by the Streamlit
app. Heavy/optional deps (psycopg2, yfinance) are imported lazily inside
functions so that ``--dry-run`` paths work without a DB driver installed.
"""
