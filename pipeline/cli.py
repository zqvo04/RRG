from __future__ import annotations

import argparse, os
from pathlib import Path

from pipeline.config import load_engine_settings, load_universe
from pipeline.engine import build_sector_state
from pipeline.errors import DataValidationError
from pipeline.providers import AlphaVantageProvider
from pipeline.publisher import atomic_publish
from pipeline.snapshot import build_snapshot, write_snapshot


def run(output: Path, settings_path: Path, universe_path: Path, data_root: Path | None) -> None:
    settings, universe = load_engine_settings(settings_path), load_universe(universe_path)
    provider = AlphaVantageProvider(os.environ.get("ALPHAVANTAGE_API_KEY", ""))
    benchmark = provider.fetch_weekly_adjusted(universe["benchmark"])
    states = [build_sector_state(item["ticker"], item["name"], provider.fetch_weekly_adjusted(item["ticker"]), benchmark, settings) for item in universe["symbols"]]
    as_of_weeks = {state.trail[-1].week for state in states}
    if len(as_of_weeks) != 1:
        raise DataValidationError(f"Symbols are not aligned to one completed week: {sorted(as_of_weeks)}")
    as_of_week = as_of_weeks.pop()
    snapshot = build_snapshot(states, as_of_week, universe["universe_id"], universe["benchmark"], settings)
    directory = write_snapshot(snapshot, output)
    if data_root: atomic_publish(directory, data_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a verified weekly RRG snapshot")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--settings", type=Path, default=Path("config/settings.json"))
    parser.add_argument("--universe", type=Path, default=Path("config/universe.us-sector-spdr.json"))
    args = parser.parse_args(); run(args.output, args.settings, args.universe, args.data_root)


if __name__ == "__main__": main()
