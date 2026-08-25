from __future__ import annotations

from math import atan2, degrees, hypot

from pipeline.config import EngineSettings
from pipeline.errors import DataValidationError
from pipeline.models import PriceBar, RRGPoint, SectorState


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise DataValidationError(f"Need at least {period} values for EMA")
    multiplier, output = 2 / (period + 1), [values[0]]
    for value in values[1:]:
        output.append((value - output[-1]) * multiplier + output[-1])
    return output


def quadrant(ratio: float, momentum: float) -> str:
    if ratio >= 100 and momentum >= 100:
        return "leading"
    if ratio >= 100:
        return "weakening"
    if momentum < 100:
        return "lagging"
    return "improving"


def build_sector_state(ticker: str, name: str, bars: list[PriceBar], benchmark: list[PriceBar], settings: EngineSettings) -> SectorState:
    common = sorted(set(bar.week_end.isoformat() for bar in bars) & set(bar.week_end.isoformat() for bar in benchmark))[-settings.calculation_weeks:]
    if len(common) < settings.min_history_weeks:
        raise DataValidationError(f"{ticker} has {len(common)} common weeks; minimum is {settings.min_history_weeks}")
    prices = {bar.week_end.isoformat(): bar.adjusted_close for bar in bars}
    bases = {bar.week_end.isoformat(): bar.adjusted_close for bar in benchmark}
    relative = [prices[week] / bases[week] for week in common]
    if any(value <= 0 for value in relative):
        raise DataValidationError("Adjusted close must be positive")
    baseline = ema(relative, settings.ratio_ema_weeks)
    ratios = [100 * value / average for value, average in zip(relative, baseline)]
    lag = settings.momentum_lag_weeks
    points = [RRGPoint(common[index], round(ratios[index], 4), round(100 * ratios[index] / ratios[index - lag], 4)) for index in range(lag, len(ratios))]
    required_points = settings.max_tail_weeks + 1
    if len(points) < required_points:
        raise DataValidationError(f"{ticker} does not have enough Ratio/Momentum observations for a {settings.max_tail_weeks}-week tail")
    trail, latest, previous = points[-required_points:], points[-1], points[-2]
    dx, dy = latest.ratio - previous.ratio, latest.momentum - previous.momentum
    heading = (degrees(atan2(dy, dx)) + 360) % 360 if dx or dy else None
    return SectorState(ticker, name, latest.ratio, latest.momentum, quadrant(latest.ratio, latest.momentum), round(heading, 2) if heading is not None else None, round(hypot(dx, dy), 4), trail)
