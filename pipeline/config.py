from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineSettings:
    calculation_weeks: int
    min_history_weeks: int
    ratio_ema_weeks: int
    momentum_lag_weeks: int
    default_tail_weeks: int
    formula_version: str


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_engine_settings(path: Path) -> EngineSettings:
    return EngineSettings(**load_json(path)["engine"])


def load_universe(path: Path) -> dict:
    return load_json(path)

