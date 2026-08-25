from __future__ import annotations

from typing import Any

from pipeline.models import SectorState


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}[severity]


def _event(event_id: str, kind: str, severity: str, ticker: str, message: str, previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "kind": kind,
        "severity": severity,
        "ticker": ticker,
        "message": message,
        "previous": previous,
        "current": current,
    }


def build_rotation_events(current_states: list[SectorState], previous_snapshot: dict[str, Any] | None, as_of_week: str, boundary_distance: float = 1.0, strong_mover_count: int = 3) -> list[dict[str, Any]]:
    """Build deterministic, auditable sector-rotation events from two verified snapshots."""
    previous_sectors = {item["ticker"]: item for item in (previous_snapshot or {}).get("sectors", [])}
    previous_snapshot_id = (previous_snapshot or {}).get("snapshot_id")
    events: list[dict[str, Any]] = []

    for state in current_states:
        previous = previous_sectors.get(state.ticker)
        if previous and previous.get("quadrant") != state.quadrant:
            events.append(_event(
                f"quadrant-change:{state.ticker}:{as_of_week}",
                "quadrant_change",
                "high",
                state.ticker,
                f"{state.ticker} moved from {previous['quadrant']} to {state.quadrant}.",
                {"snapshot_id": previous_snapshot_id, "quadrant": previous["quadrant"], "ratio": previous["ratio"], "momentum": previous["momentum"]},
                {"quadrant": state.quadrant, "ratio": state.ratio, "momentum": state.momentum},
            ))

        close_axes = [axis for axis, value in (("ratio", state.ratio), ("momentum", state.momentum)) if abs(value - 100) <= boundary_distance]
        if close_axes:
            events.append(_event(
                f"boundary-approach:{state.ticker}:{as_of_week}",
                "boundary_approach",
                "medium",
                state.ticker,
                f"{state.ticker} is within {boundary_distance:.1f} points of the 100 baseline on {', '.join(close_axes)}.",
                {"snapshot_id": previous_snapshot_id, "ratio": previous.get("ratio") if previous else None, "momentum": previous.get("momentum") if previous else None},
                {"ratio": state.ratio, "momentum": state.momentum, "axes": close_axes, "distance": min(abs(state.ratio - 100), abs(state.momentum - 100))},
            ))

    movers = sorted((state for state in current_states if state.velocity is not None), key=lambda state: state.velocity or 0, reverse=True)[:strong_mover_count]
    for state in movers:
        if not state.velocity or state.velocity <= 0:
            continue
        previous = previous_sectors.get(state.ticker, {})
        events.append(_event(
            f"strong-move:{state.ticker}:{as_of_week}",
            "strong_move",
            "medium",
            state.ticker,
            f"{state.ticker} is one of this week's strongest RRG movers.",
            {"snapshot_id": previous_snapshot_id, "ratio": previous.get("ratio"), "momentum": previous.get("momentum")},
            {"ratio": state.ratio, "momentum": state.momentum, "heading_degrees": state.heading_degrees, "velocity": state.velocity},
        ))

    return sorted(events, key=lambda item: (_severity_rank(item["severity"]), item["ticker"], item["kind"]))
