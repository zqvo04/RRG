from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.calendar import completed_friday_bars, last_completed_friday
from pipeline.config import load_engine_settings, load_event_settings, load_universe
from pipeline.engine import build_sector_state
from pipeline.events import build_rotation_events
from pipeline.providers import AlphaVantageProvider
from pipeline.publisher import atomic_publish
from pipeline.quality import validate_snapshot_inputs
from pipeline.snapshot import build_snapshot, write_snapshot


def _load_previous_snapshot(data_root: Path | None) -> dict[str, Any] | None:
    latest_path = data_root / "latest.json" if data_root else None
    if not latest_path or not latest_path.exists():
        return None
    return json.loads(latest_path.read_text(encoding="utf-8"))


def run(output: Path, settings_path: Path, universe_path: Path, data_root: Path | None, reference_time: datetime | None = None) -> None:
    settings, universe = load_engine_settings(settings_path), load_universe(universe_path)
    event_settings = load_event_settings(settings_path)
    provider = AlphaVantageProvider(os.environ.get("ALPHAVANTAGE_API_KEY", ""))

    benchmark = completed_friday_bars(provider.fetch_weekly_adjusted(universe["benchmark"]), reference_time)
    sector_bars = {
        item["ticker"]: completed_friday_bars(provider.fetch_weekly_adjusted(item["ticker"]), reference_time)
        for item in universe["symbols"]
    }
    states = [
        build_sector_state(item["ticker"], item["name"], sector_bars[item["ticker"]], benchmark, settings)
        for item in universe["symbols"]
    ]
    as_of_weeks = {state.trail[-1].week for state in states}
    if len(as_of_weeks) != 1:
        raise ValueError(f"Symbols are not aligned to one completed week: {sorted(as_of_weeks)}")
    as_of_week = as_of_weeks.pop()
    quality, provenance = validate_snapshot_inputs(
        benchmark=benchmark,
        sector_bars=sector_bars,
        states=states,
        expected_symbols=len(universe["symbols"]) + 1,
        expected_as_of_week=last_completed_friday(reference_time),
        min_history_weeks=settings.min_history_weeks,
    )
    previous_snapshot = _load_previous_snapshot(data_root)
    events = build_rotation_events(
        states,
        previous_snapshot,
        as_of_week,
        boundary_distance=float(event_settings.get("boundary_distance", 1.0)),
        strong_mover_count=int(event_settings.get("strong_mover_count", 3)),
    )
    snapshot = build_snapshot(
        states,
        as_of_week,
        universe["universe_id"],
        universe["benchmark"],
        settings,
        quality=quality,
        events=events,
        provenance=provenance,
        previous_snapshot_id=previous_snapshot.get("snapshot_id") if previous_snapshot else None,
    )
    directory = write_snapshot(snapshot, output)
    if data_root:
        atomic_publish(directory, data_root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a verified weekly RRG snapshot")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--settings", type=Path, default=Path("config/settings.json"))
    parser.add_argument("--universe", type=Path, default=Path("config/universe.us-sector-spdr.json"))
    args = parser.parse_args()
    run(args.output, args.settings, args.universe, args.data_root)


if __name__ == "__main__":
    main()
