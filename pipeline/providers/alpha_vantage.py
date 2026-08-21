from __future__ import annotations

from datetime import date, datetime, timezone
from time import sleep

import requests

from pipeline.errors import ProviderError
from pipeline.models import PriceBar
from pipeline.providers.base import WeeklyAdjustedProvider


class AlphaVantageProvider(WeeklyAdjustedProvider):
    endpoint = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, sleep_seconds: float = 13.0) -> None:
        if not api_key:
            raise ProviderError("ALPHAVANTAGE_API_KEY is required")
        self.api_key, self.sleep_seconds, self._request_count = api_key, sleep_seconds, 0

    def fetch_weekly_adjusted(self, symbol: str) -> list[PriceBar]:
        if self._request_count:
            sleep(self.sleep_seconds)
        self._request_count += 1
        response = requests.get(self.endpoint, params={"function": "TIME_SERIES_WEEKLY_ADJUSTED", "symbol": symbol, "apikey": self.api_key}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        message = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
        if message:
            raise ProviderError(f"Alpha Vantage rejected {symbol}: {message}")
        series = payload.get("Weekly Adjusted Time Series")
        if not isinstance(series, dict):
            raise ProviderError(f"No weekly adjusted series for {symbol}")
        now = datetime.now(timezone.utc)
        try:
            return sorted([PriceBar(symbol, date.fromisoformat(day), float(row["5. adjusted close"]), "alpha_vantage", now) for day, row in series.items()], key=lambda bar: bar.week_end)
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderError(f"Invalid weekly bar for {symbol}") from error

