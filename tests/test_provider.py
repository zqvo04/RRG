from unittest.mock import Mock

import pytest
import requests

from pipeline.errors import ProviderError
from pipeline.providers.alpha_vantage import AlphaVantageProvider


def test_provider_retries_transient_request_failure(monkeypatch) -> None:
    provider = AlphaVantageProvider("key", sleep_seconds=0, retry_attempts=2)
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"Weekly Adjusted Time Series": {"2026-08-21": {"5. adjusted close": "100"}}}
    request = Mock(side_effect=[requests.ConnectionError("temporary"), response])
    monkeypatch.setattr("pipeline.providers.alpha_vantage.requests.get", request)
    monkeypatch.setattr("pipeline.providers.alpha_vantage.sleep", lambda _: None)
    bars = provider.fetch_weekly_adjusted("SPY")
    assert len(bars) == 1
    assert request.call_count == 2


def test_provider_classifies_rate_limit_response_without_retry(monkeypatch) -> None:
    provider = AlphaVantageProvider("key", sleep_seconds=0, retry_attempts=3)
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"Note": "rate limit"}
    request = Mock(return_value=response)
    monkeypatch.setattr("pipeline.providers.alpha_vantage.requests.get", request)
    with pytest.raises(ProviderError, match="rejected"):
        provider.fetch_weekly_adjusted("SPY")
    assert request.call_count == 1
