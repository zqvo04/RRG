from pipeline.events import build_rotation_events
from pipeline.models import RRGPoint, SectorState


def state(ticker: str, ratio: float, momentum: float, quadrant: str, velocity: float) -> SectorState:
    return SectorState(ticker, ticker, ratio, momentum, quadrant, 45.0, velocity, [RRGPoint("2026-08-14", ratio - 1, momentum - 1), RRGPoint("2026-08-21", ratio, momentum)])


def test_rotation_events_include_quadrant_boundary_and_strong_move() -> None:
    current = [
        state("XLK", 100.3, 101.2, "leading", 4.0),
        state("XLF", 98.0, 98.0, "lagging", 2.0),
    ]
    previous = {
        "snapshot_id": "2026-W33",
        "sectors": [
            {"ticker": "XLK", "quadrant": "improving", "ratio": 99.4, "momentum": 101.0},
            {"ticker": "XLF", "quadrant": "lagging", "ratio": 97.0, "momentum": 97.0},
        ],
    }
    events = build_rotation_events(current, previous, "2026-08-21", boundary_distance=0.5, strong_mover_count=1)
    kinds = [item["kind"] for item in events]
    assert "quadrant_change" in kinds
    assert "boundary_approach" in kinds
    assert "strong_move" in kinds
    transition = next(item for item in events if item["kind"] == "quadrant_change")
    assert transition["previous"]["quadrant"] == "improving"
    assert transition["current"]["quadrant"] == "leading"


def test_first_snapshot_does_not_create_a_quadrant_transition() -> None:
    events = build_rotation_events([state("XLK", 102, 101, "leading", 3.0)], None, "2026-08-21", strong_mover_count=1)
    assert all(item["kind"] != "quadrant_change" for item in events)
