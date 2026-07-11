from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from core.models import CandlePayload, Observation, ObservationKind, OpenInterestPayload


def make_candles(
    closes: list[float],
    symbol: str = "BTC-USD",
    start: datetime | None = None,
    interval: timedelta = timedelta(minutes=1),
) -> list[Observation]:
    """Synthetic candle series: each candle opens at the previous close.

    ``observed_at`` is the bucket end (close time), matching the visibility
    rule that a candle's close is only known after the bucket ends.
    """
    start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
    observations = []
    previous_close = closes[0]
    for index, close in enumerate(closes):
        open_price = previous_close
        high = max(open_price, close)
        low = min(open_price, close)
        bucket_start = start + index * interval
        observations.append(
            Observation(
                observed_at=bucket_start + interval,
                occurred_at=bucket_start,
                symbol=symbol,
                source="test",
                kind=ObservationKind.CANDLE,
                payload=CandlePayload(
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=1.0,
                    granularity="ONE_MINUTE",
                ),
            )
        )
        previous_close = close
    return observations


def make_open_interest(
    values: list[float],
    symbol: str = "BTCUSDT",
    start: datetime | None = None,
    interval: timedelta = timedelta(minutes=15),
) -> list[Observation]:
    """Synthetic perp OI series in raw contract quantity, one sample per interval."""
    start = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
    observations = []
    for index, value in enumerate(values):
        occurred = start + index * interval
        observations.append(
            Observation(
                observed_at=occurred + timedelta(minutes=1),
                occurred_at=occurred,
                symbol=symbol,
                source="test",
                kind=ObservationKind.PERP_OPEN_INTEREST,
                payload=OpenInterestPayload(
                    open_interest_raw=str(value),
                    open_interest_unit="exchange_native_linear_contract_quantity",
                ),
            )
        )
    return observations


@pytest.fixture
def candle_factory():
    return make_candles
