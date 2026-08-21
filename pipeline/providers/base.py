from abc import ABC, abstractmethod

from pipeline.models import PriceBar


class WeeklyAdjustedProvider(ABC):
    @abstractmethod
    def fetch_weekly_adjusted(self, symbol: str) -> list[PriceBar]:
        """Return a complete, ascending series of weekly adjusted price bars."""

