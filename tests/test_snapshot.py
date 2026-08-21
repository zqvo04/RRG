from pipeline.config import EngineSettings
from pipeline.models import RRGPoint, SectorState
from pipeline.publisher import atomic_publish
from pipeline.snapshot import build_snapshot, write_snapshot


def test_snapshot_becomes_latest_after_publish(tmp_path) -> None:
    state = SectorState("XLK", "Information Technology", 101, 100.5, "leading", 45, 0.3, [RRGPoint(f"2026-W{index}", 100 + index / 10, 99 + index / 10) for index in range(13)])
    snapshot = build_snapshot([state], "2026-03-27", "fixture", "SPY", EngineSettings(104, 52, 13, 4, 12, "rrg_proxy_v1"))
    output = write_snapshot(snapshot, tmp_path / "output")
    atomic_publish(output, tmp_path / "data")
    assert (tmp_path / "data" / "latest.json").exists()
    assert (tmp_path / "data" / "snapshots" / snapshot["snapshot_id"] / "manifest.json").exists()

