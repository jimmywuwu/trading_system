from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.data_provider import DataProvider
from core.models import (
    BasisPayload,
    CandlePayload,
    FundingRatePayload,
    Observation,
    ObservationKind,
    OpenInterestPayload,
    PricePayload,
)


class JsonLinesTradeProvider(DataProvider):
    """Reads Coinbase-style websocket JSONL captures as point-in-time observations."""

    source = "jsonl"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._trades: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._observations: list[Observation] = []
        self._latest: dict[tuple[str, ObservationKind], Observation] = {}
        self.reload()

    def reload(self) -> None:
        self._trades.clear()
        self._observations.clear()
        self._latest.clear()

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                self._ingest_line(line)

    def get_latest(self, subject: str, kind: ObservationKind | None = None) -> Observation | None:
        if kind is not None:
            return self._latest.get((subject, kind))

        candidates = [
            observation
            for (latest_subject, _), observation in self._latest.items()
            if latest_subject == subject
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda observation: observation.observed_at)

    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        kind_filter = set(kinds) if kinds is not None else None
        subject_filter = set(subjects) if subjects is not None else None

        observations = self._observations
        if start is not None:
            observations = [item for item in observations if item.observed_at >= start]
        if end is not None:
            observations = [item for item in observations if item.observed_at <= end]
        if kind_filter is not None:
            observations = [item for item in observations if item.kind in kind_filter]
        if subject_filter is not None:
            observations = [item for item in observations if item.subject in subject_filter]
        return observations

    def get_trades(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._trades.get(symbol, [])[-limit:]

    def _ingest_line(self, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return

        for event in payload.get("events", []):
            for trade in event.get("trades", []):
                self._ingest_trade(trade)

    def _ingest_trade(self, trade: dict[str, Any]) -> None:
        symbol = trade.get("product_id")
        price = trade.get("price")
        if symbol is None or price is None:
            return

        occurred_at = self._parse_timestamp(trade.get("time"))
        observed_at = occurred_at
        normalized = {
            "price": float(price),
            "size": float(trade.get("size", 0) or 0),
            "time": occurred_at,
            "side": trade.get("side"),
            "raw": trade,
        }

        self._trades[symbol].append(normalized)
        observation = Observation(
            symbol=symbol,
            observed_at=observed_at,
            occurred_at=occurred_at,
            source=self.source,
            kind=ObservationKind.PRICE,
            payload=PricePayload(last=normalized["price"], volume=normalized["size"]),
            metadata={
                "side": normalized["side"],
                "visibility_note": "capture has no separate ingest timestamp; observed_at equals occurred_at",
            },
        )
        self._observations.append(observation)
        self._latest[(symbol, ObservationKind.PRICE)] = observation

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))


class JsonLinesObservationProvider(DataProvider):
    """Reads normalized Observation JSONL files exported by this project."""

    source = "jsonl_observations"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._observations: list[Observation] = []
        self._latest: dict[tuple[str, ObservationKind], Observation] = {}
        self.reload()

    def reload(self) -> None:
        self._observations.clear()
        self._latest.clear()

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                observation = self._parse_line(line)
                if observation is None:
                    continue
                self._observations.append(observation)

        self._observations.sort(key=lambda item: item.observed_at)
        for observation in self._observations:
            self._latest[(observation.subject, observation.kind)] = observation

    def get_latest(self, subject: str, kind: ObservationKind | None = None) -> Observation | None:
        if kind is not None:
            return self._latest.get((subject, kind))

        candidates = [
            observation
            for (latest_subject, _), observation in self._latest.items()
            if latest_subject == subject
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda observation: observation.observed_at)

    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        kind_filter = set(kinds) if kinds is not None else None
        subject_filter = set(subjects) if subjects is not None else None

        observations = self._observations
        if start is not None:
            observations = [item for item in observations if item.observed_at >= start]
        if end is not None:
            observations = [item for item in observations if item.observed_at <= end]
        if kind_filter is not None:
            observations = [item for item in observations if item.kind in kind_filter]
        if subject_filter is not None:
            observations = [item for item in observations if item.subject in subject_filter]
        return observations

    def _parse_line(self, line: str) -> Observation | None:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None

        kind = ObservationKind(row["kind"])
        payload = self._parse_payload(kind, row.get("payload", {}))
        if payload is None:
            return None

        return Observation(
            observed_at=self._parse_timestamp(row.get("observed_at")),
            occurred_at=self._parse_timestamp(row.get("occurred_at")),
            symbol=row["symbol"],
            source=row.get("source", self.source),
            kind=kind,
            payload=payload,
            metadata=row.get("metadata", {}),
        )

    @staticmethod
    def _parse_payload(
        kind: ObservationKind,
        payload: dict[str, Any],
    ) -> CandlePayload | PricePayload | FundingRatePayload | OpenInterestPayload | BasisPayload | None:
        if kind in (ObservationKind.CANDLE, ObservationKind.PERP_MARK_PRICE):
            return CandlePayload(
                open=float(payload["open"]),
                high=float(payload["high"]),
                low=float(payload["low"]),
                close=float(payload["close"]),
                volume=float(payload.get("volume", 0) or 0),
                granularity=str(payload.get("granularity", "")),
            )
        if kind == ObservationKind.PRICE:
            return PricePayload(
                bid=float(payload["bid"]) if payload.get("bid") is not None else None,
                ask=float(payload["ask"]) if payload.get("ask") is not None else None,
                last=float(payload["last"]) if payload.get("last") is not None else None,
                volume=float(payload["volume"]) if payload.get("volume") is not None else None,
            )
        if kind == ObservationKind.PERP_FUNDING_RATE:
            return FundingRatePayload(
                funding_rate=float(payload["funding_rate"]),
                funding_rate_raw=str(payload.get("funding_rate_raw", payload["funding_rate"])),
                funding_type=str(payload.get("funding_type", "settled")),
                funding_interval=payload.get("funding_interval"),
            )
        if kind == ObservationKind.PERP_OPEN_INTEREST:
            return OpenInterestPayload(
                open_interest_raw=str(payload["open_interest_raw"]),
                open_interest_unit=str(payload["open_interest_unit"]),
                open_interest_notional_usdt=(
                    float(payload["open_interest_notional_usdt"])
                    if payload.get("open_interest_notional_usdt") is not None
                    else None
                ),
                normalization_price=(
                    float(payload["normalization_price"])
                    if payload.get("normalization_price") is not None
                    else None
                ),
                normalization_source=payload.get("normalization_source"),
            )
        if kind == ObservationKind.PERP_SPOT_BASIS:
            return BasisPayload(
                basis_bps=float(payload["basis_bps"]),
                perp_price=float(payload["perp_price"]),
                spot_price=float(payload["spot_price"]),
                basis_type=str(payload["basis_type"]),
            )
        return None

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
