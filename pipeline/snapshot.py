from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.config import EngineSettings
from pipeline.models import SectorState


def snapshot_id(as_of_week: str) -> str:
    year, week, _ = datetime.fromisoformat(as_of_week).isocalendar()
    return f"{year}-W{week:02d}"


def build_snapshot(
    states: list[SectorState],
    as_of_week: str,
    universe_id: str,
    benchmark: str,
    settings: EngineSettings,
    quality: dict[str, Any],
    events: list[dict[str, Any]] | None = None,
    provenance: dict[str, Any] | None = None,
    previous_snapshot_id: str | None = None,
) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot_id(as_of_week),
        "status": "verified",
        "as_of_week": as_of_week,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe_id": universe_id,
        "benchmark": benchmark,
        "frequency": "weekly",
        "weekly_anchor": "friday_regular_close",
        "anchor_timezone": "America/New_York",
        "price_basis": "weekly_adjusted_close",
        "formula_version": settings.formula_version,
        "tail_weeks": settings.max_tail_weeks,
        "default_tail_weeks": settings.default_tail_weeks,
        "sectors": [state.to_dict() for state in states],
        "quality": quality,
        "events": events or [],
        "previous_snapshot_id": previous_snapshot_id,
        "provenance": provenance or {},
    }


def write_snapshot(snapshot: dict[str, Any], output_root: Path) -> Path:
    destination = output_root / "snapshots" / snapshot["snapshot_id"]
    destination.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(snapshot, indent=2, ensure_ascii=False)
    (destination / "rrg.json").write_text(payload, encoding="utf-8")
    with (destination / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "name", "quadrant", "ratio", "momentum", "heading_degrees", "velocity"])
        writer.writeheader()
        writer.writerows({key: sector[key] for key in writer.fieldnames} for sector in snapshot["sectors"])
    manifest = {
        "snapshot_id": snapshot["snapshot_id"],
        "as_of_week": snapshot["as_of_week"],
        "formula_version": snapshot["formula_version"],
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "quality": snapshot["quality"],
        "event_count": len(snapshot["events"]),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination
