from __future__ import annotations

import json, shutil, tempfile
from pathlib import Path


def atomic_publish(snapshot_directory: Path, data_root: Path) -> None:
    """Publish only a complete, previously validated snapshot."""
    snapshot = json.loads((snapshot_directory / "rrg.json").read_text(encoding="utf-8"))
    snapshot_id = snapshot["snapshot_id"]
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "snapshots").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=data_root) as temporary:
        staging = Path(temporary) / snapshot_id
        shutil.copytree(snapshot_directory, staging)
        destination = data_root / "snapshots" / snapshot_id
        if destination.exists(): shutil.rmtree(destination)
        shutil.move(str(staging), destination)
    index_path = data_root / "index.json"
    old = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"snapshots": []}
    index = {"latest": snapshot_id, "snapshots": [snapshot_id, *[item for item in old["snapshots"] if item != snapshot_id]]}
    (data_root / "latest.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

