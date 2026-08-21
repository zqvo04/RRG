from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Literal

Quadrant = Literal["leading", "weakening", "lagging", "improving"]


@dataclass(frozen=True)
class PriceBar:
    symbol: str
    week_end: date
    adjusted_close: float
    source: str
    source_timestamp: datetime


@dataclass(frozen=True)
class RRGPoint:
    week: str
    ratio: float
    momentum: float


@dataclass(frozen=True)
class SectorState:
    ticker: str
    name: str
    ratio: float
    momentum: float
    quadrant: Quadrant
    heading_degrees: float | None
    velocity: float | None
    trail: list[RRGPoint]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["trail"] = [asdict(point) for point in self.trail]
        return data

