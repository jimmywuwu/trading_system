from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Iterator
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.data_provider import DataProvider
from core.models import CandlePayload, Observation, ObservationKind

HttpGet = Callable[[str, dict[str, str]], dict]


class CoinbaseMinuteBitcoinPriceProvider(DataProvider):
    """Coinbase public one-minute candle provider for Bitcoin."""

    source = "coinbase"
    product_id = "BTC-USD"
    granularity = "ONE_MINUTE"
    candle_duration = timedelta(minutes=1)
    max_candles_per_request = 350

    def __init__(
        self,
        base_url: str = "https://api.coinbase.com",
        http_get: HttpGet | None = None,
        request_delay_seconds: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http_get = http_get or self._default_http_get
        self.request_delay_seconds = request_delay_seconds

    def get_latest(
        self,
        subject: str = product_id,
        kind: ObservationKind | None = ObservationKind.CANDLE,
    ) -> Observation | None:
        if subject != self.product_id:
            return None
        if kind not in (None, ObservationKind.CANDLE):
            return None

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=5)
        observations = self.get_observations(start=start, end=end, kinds=[ObservationKind.CANDLE], subjects=[subject])
        if not observations:
            return None
        return max(observations, key=lambda observation: observation.occurred_at)

    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        if kinds is not None and ObservationKind.CANDLE not in set(kinds):
            return []
        if subjects is not None and self.product_id not in set(subjects):
            return []

        end = end or datetime.now(timezone.utc)
        start = start or end - timedelta(minutes=350)
        start = self._as_utc(start)
        end = self._as_utc(end)
        if start >= end:
            raise ValueError("start must be before end")

        observations = list(
            self.iter_observations(
                start=start,
                end=end,
                kinds=kinds,
                subjects=subjects,
            )
        )
        observations.sort(key=lambda observation: observation.occurred_at)
        return observations

    def iter_observations(
        self,
        start: datetime,
        end: datetime,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> Iterator[Observation]:
        if kinds is not None and ObservationKind.CANDLE not in set(kinds):
            return
        if subjects is not None and self.product_id not in set(subjects):
            return

        start = self._as_utc(start)
        end = self._as_utc(end)
        if start >= end:
            raise ValueError("start must be before end")

        current = start
        while current < end:
            window_end = min(
                current + self.candle_duration * self.max_candles_per_request,
                end,
            )
            payload = self._fetch_candles(start=current, end=window_end)
            candles = payload.get("candles", [])
            observations = [self._to_observation(candle) for candle in candles]
            observations.sort(key=lambda observation: observation.occurred_at)
            for observation in observations:
                yield observation

            current = window_end
            if self.request_delay_seconds > 0 and current < end:
                time.sleep(self.request_delay_seconds)

    def _fetch_candles(self, start: datetime, end: datetime) -> dict:
        params = {
            "start": str(int(start.timestamp())),
            "end": str(int(end.timestamp())),
            "granularity": self.granularity,
            "limit": "350",
        }
        url = (
            f"{self.base_url}/api/v3/brokerage/market/products/"
            f"{self.product_id}/candles?{urlencode(params)}"
        )
        return self._http_get(url, {"Accept": "application/json"})

    def _to_observation(self, candle: dict) -> Observation[CandlePayload]:
        occurred_at = datetime.fromtimestamp(int(candle["start"]), tz=timezone.utc)
        observed_at = occurred_at + self.candle_duration
        return Observation(
            observed_at=observed_at,
            occurred_at=occurred_at,
            source=self.source,
            kind=ObservationKind.CANDLE,
            symbol=self.product_id,
            payload=CandlePayload(
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle["volume"]),
                granularity=self.granularity,
            ),
            metadata={
                "product_id": self.product_id,
                "endpoint": "public_product_candles",
            },
        )

    @staticmethod
    def _default_http_get(url: str, headers: dict[str, str]) -> dict:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
