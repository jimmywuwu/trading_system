from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from core.data_provider import DataProvider
from core.models import (
    BasisPayload,
    CandlePayload,
    FundingRatePayload,
    Observation,
    ObservationKind,
    OpenInterestPayload,
)

HttpGet = Callable[[str, dict[str, str]], dict[str, Any]]


class BybitRawArchive:
    """Append-only archive for Bybit raw REST responses.

    The archive records endpoint-level payloads before normalization so a fixture
    can be regenerated without live API calls and audited from raw payload hash to
    normalized rows.
    """

    def __init__(self, directory: Path | str, filename: str = "raw_payloads.jsonl") -> None:
        self.directory = Path(directory)
        self.path = self.directory / filename

    def recording_http_get(self, http_get: HttpGet) -> HttpGet:
        def wrapped(url: str, headers: dict[str, str]) -> dict[str, Any]:
            payload = http_get(url, headers)
            self.append(url, payload)
            return payload

        return wrapped

    def replay_http_get(self) -> HttpGet:
        records_by_key: dict[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], dict[str, Any]] = {}
        for record in self.iter_records():
            key = self._key(record["endpoint"], record["params"])
            records_by_key[key] = record["payload"]

        def replay(url: str, headers: dict[str, str]) -> dict[str, Any]:
            del headers
            endpoint, params = self._endpoint_and_params(url)
            key = self._key(endpoint, params)
            if key not in records_by_key:
                raise KeyError(f"raw archive has no Bybit payload for {endpoint} params={params}")
            return json.loads(json.dumps(records_by_key[key]))

        return replay

    def append(self, url: str, payload: dict[str, Any]) -> None:
        endpoint, params = self._endpoint_and_params(url)
        record = {
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "endpoint": endpoint,
            "params": params,
            "payload_hash": BybitLeveragePressureProvider._hash_payload(payload),
            "payload": payload,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def iter_records(self) -> Iterable[dict[str, Any]]:
        if not self.path.exists():
            return iter(())
        return self._read_records()

    def _read_records(self) -> Iterable[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    yield json.loads(line)

    @classmethod
    def _endpoint_and_params(cls, url: str) -> tuple[str, dict[str, str]]:
        parsed = urlparse(url)
        params = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
        return parsed.path, params

    @classmethod
    def _key(cls, endpoint: str, params: dict[str, str]) -> tuple[str, tuple[tuple[str, tuple[str, ...]], ...]]:
        normalized = tuple(sorted((key, (str(value),)) for key, value in params.items()))
        return endpoint, normalized


class BybitLeveragePressureProvider(DataProvider):
    """Bybit public REST provider for first-pass leverage-pressure fixtures.

    The provider intentionally emits a conservative historical replay fixture:
    historical `observed_at` values are simulated availability timestamps, not
    archived API receive timestamps. Live capture should use actual receive time.
    """

    source = "bybit_rest"
    venue = "bybit"
    supported_symbols = ("BTCUSDT", "ETHUSDT")
    default_interval = "5"
    max_limit = 1000

    _KLINE_ENDPOINT = "/v5/market/kline"
    _MARK_PRICE_KLINE_ENDPOINT = "/v5/market/mark-price-kline"
    _OPEN_INTEREST_ENDPOINT = "/v5/market/open-interest"
    _FUNDING_HISTORY_ENDPOINT = "/v5/market/funding/history"

    def __init__(
        self,
        base_url: str = "https://api.bybit.com",
        http_get: HttpGet | None = None,
        request_delay_seconds: float = 0.0,
        candle_observed_lag: timedelta = timedelta(seconds=30),
        funding_observed_lag: timedelta = timedelta(seconds=60),
        open_interest_observed_lag: timedelta = timedelta(seconds=60),
        ingestion_run_id: str | None = None,
        fixture_version: str | None = None,
        rate_limit_retry_delay_seconds: float = 2.0,
        rate_limit_max_retries: int = 5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http_get = http_get or self._default_http_get
        self.request_delay_seconds = request_delay_seconds
        self.candle_observed_lag = candle_observed_lag
        self.funding_observed_lag = funding_observed_lag
        self.open_interest_observed_lag = open_interest_observed_lag
        self.ingestion_run_id = ingestion_run_id or f"bybit-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        self.fixture_version = fixture_version or self.ingestion_run_id
        self.rate_limit_retry_delay_seconds = rate_limit_retry_delay_seconds
        self.rate_limit_max_retries = rate_limit_max_retries

    def get_latest(self, subject: str, kind: ObservationKind | None = None) -> Observation | None:
        end = self._floor_to_interval(datetime.now(timezone.utc), self.default_interval)
        start = end - timedelta(minutes=30)
        observations = self.get_observations(start=start, end=end, kinds=[kind] if kind else None, subjects=[subject])
        if not observations:
            return None
        return max(observations, key=lambda item: item.observed_at)

    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        end = self._as_utc(end or datetime.now(timezone.utc))
        start = self._as_utc(start or end - timedelta(days=14))
        if start >= end:
            raise ValueError("start must be before end")

        kind_filter = set(kinds) if kinds is not None else self._default_kinds()
        subject_filter = set(subjects) if subjects is not None else set(self.supported_symbols)
        unknown_subjects = subject_filter - set(self.supported_symbols)
        if unknown_subjects:
            raise ValueError(f"unsupported Bybit leverage-pressure subjects: {sorted(unknown_subjects)}")

        observations: list[Observation] = []
        for symbol in sorted(subject_filter):
            symbol_observations: list[Observation] = []
            if ObservationKind.CANDLE in kind_filter:
                symbol_observations.extend(self.fetch_perp_candles(symbol, start, end))
                self._delay()
                symbol_observations.extend(self.fetch_spot_candles(symbol, start, end))
                self._delay()
            if ObservationKind.PERP_MARK_PRICE in kind_filter:
                symbol_observations.extend(self.fetch_mark_price_candles(symbol, start, end))
                self._delay()
            if ObservationKind.PERP_OPEN_INTEREST in kind_filter:
                symbol_observations.extend(self.fetch_open_interest(symbol, start, end))
                self._delay()
            if ObservationKind.PERP_FUNDING_RATE in kind_filter:
                symbol_observations.extend(self.fetch_funding_rates(symbol, start, end))
                self._delay()

            if ObservationKind.PERP_OPEN_INTEREST in kind_filter and ObservationKind.PERP_MARK_PRICE in kind_filter:
                symbol_observations = self._with_normalized_open_interest(symbol_observations)

            observations.extend(symbol_observations)

            if ObservationKind.PERP_SPOT_BASIS in kind_filter:
                # Basis is derived from already-fetched point-in-time-safe perp and spot candles.
                perp = [item for item in symbol_observations if item.kind == ObservationKind.CANDLE and item.metadata.get("market_type") == "linear_perp"]
                spot = [item for item in symbol_observations if item.kind == ObservationKind.CANDLE and item.metadata.get("market_type") == "spot"]
                observations.extend(self.derive_perp_spot_basis(symbol, perp, spot))

        observations.sort(key=lambda item: (item.observed_at, item.symbol, item.kind.value))
        return observations

    def fetch_perp_candles(self, symbol: str, start: datetime, end: datetime, interval: str = default_interval) -> list[Observation[CandlePayload]]:
        return self._fetch_kline_observations(
            endpoint=self._KLINE_ENDPOINT,
            category="linear",
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            kind=ObservationKind.CANDLE,
            market_type="linear_perp",
            observed_lag=self.candle_observed_lag,
            volume_field="base_volume",
            turnover_field="turnover_usdt",
        )

    def fetch_spot_candles(self, symbol: str, start: datetime, end: datetime, interval: str = default_interval) -> list[Observation[CandlePayload]]:
        return self._fetch_kline_observations(
            endpoint=self._KLINE_ENDPOINT,
            category="spot",
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            kind=ObservationKind.CANDLE,
            market_type="spot",
            observed_lag=self.candle_observed_lag,
            volume_field="base_volume",
            turnover_field="quote_turnover",
        )

    def fetch_mark_price_candles(self, symbol: str, start: datetime, end: datetime, interval: str = default_interval) -> list[Observation[CandlePayload]]:
        return self._fetch_kline_observations(
            endpoint=self._MARK_PRICE_KLINE_ENDPOINT,
            category="linear",
            symbol=symbol,
            start=start,
            end=end,
            interval=interval,
            kind=ObservationKind.PERP_MARK_PRICE,
            market_type="linear_perp_mark_price",
            observed_lag=self.candle_observed_lag,
            volume_field=None,
            turnover_field=None,
        )

    def fetch_open_interest(self, symbol: str, start: datetime, end: datetime) -> list[Observation[OpenInterestPayload]]:
        rows: list[dict[str, Any]] = []
        for payload in self._iter_windowed_payloads(
            self._OPEN_INTEREST_ENDPOINT,
            {
                "category": "linear",
                "symbol": symbol,
                "intervalTime": "5min",
            },
            start,
            end,
            start_param="startTime",
            end_param="endTime",
        ):
            rows.extend(payload.get("result", {}).get("list", []))

        observations = []
        for row in rows:
            occurred_at = self._from_millis(row["timestamp"])
            if not start <= occurred_at < end:
                continue
            raw_payload_hash = self._hash_payload(row)
            observations.append(
                Observation(
                    observed_at=occurred_at + self.open_interest_observed_lag,
                    occurred_at=occurred_at,
                    symbol=symbol,
                    source=self.source,
                    kind=ObservationKind.PERP_OPEN_INTEREST,
                    payload=OpenInterestPayload(
                        open_interest_raw=str(row["openInterest"]),
                        open_interest_unit="exchange_native_linear_contract_quantity",
                        open_interest_notional_usdt=None,
                        normalization_price=None,
                        normalization_source=None,
                    ),
                    metadata=self._metadata(
                        endpoint=self._OPEN_INTEREST_ENDPOINT,
                        market_type="linear_perp",
                        source_category="linear",
                        raw_payload=row,
                        raw_payload_hash=raw_payload_hash,
                        visibility_note="historical observed_at is simulated as timestamp + 60s; not archived receive time",
                    ),
                )
            )
        return self._dedupe(observations)

    def fetch_funding_rates(self, symbol: str, start: datetime, end: datetime) -> list[Observation[FundingRatePayload]]:
        rows: list[dict[str, Any]] = []
        for payload in self._iter_windowed_payloads(
            self._FUNDING_HISTORY_ENDPOINT,
            {
                "category": "linear",
                "symbol": symbol,
            },
            start,
            end,
            start_param="startTime",
            end_param="endTime",
            window=timedelta(days=7),
        ):
            rows.extend(payload.get("result", {}).get("list", []))

        observations = []
        for row in rows:
            occurred_at = self._from_millis(row["fundingRateTimestamp"])
            if not start <= occurred_at < end:
                continue
            raw_payload_hash = self._hash_payload(row)
            observations.append(
                Observation(
                    observed_at=occurred_at + self.funding_observed_lag,
                    occurred_at=occurred_at,
                    symbol=symbol,
                    source=self.source,
                    kind=ObservationKind.PERP_FUNDING_RATE,
                    payload=FundingRatePayload(
                        funding_rate=float(row["fundingRate"]),
                        funding_rate_raw=str(row["fundingRate"]),
                        funding_type="settled",
                        funding_interval="8h",
                    ),
                    metadata=self._metadata(
                        endpoint=self._FUNDING_HISTORY_ENDPOINT,
                        market_type="linear_perp",
                        source_category="linear",
                        raw_payload=row,
                        raw_payload_hash=raw_payload_hash,
                        visibility_note="historical funding is settled funding; predicted/quoted history is not reconstructed",
                    ),
                )
            )
        return self._dedupe(observations)

    def derive_perp_spot_basis(
        self,
        symbol: str,
        perp_candles: Iterable[Observation[CandlePayload]],
        spot_candles: Iterable[Observation[CandlePayload]],
    ) -> list[Observation[BasisPayload]]:
        spot_by_time = {item.occurred_at: item for item in spot_candles}
        observations: list[Observation[BasisPayload]] = []
        for perp in perp_candles:
            spot = spot_by_time.get(perp.occurred_at)
            if spot is None or spot.payload.close == 0:
                continue
            basis_bps = (perp.payload.close - spot.payload.close) / spot.payload.close * 10_000
            occurred_at = max(perp.occurred_at, spot.occurred_at)
            observed_at = max(perp.observed_at, spot.observed_at)
            raw = {
                "perp_close": perp.payload.close,
                "spot_close": spot.payload.close,
                "perp_observed_at": perp.observed_at.isoformat(),
                "spot_observed_at": spot.observed_at.isoformat(),
            }
            observations.append(
                Observation(
                    observed_at=observed_at,
                    occurred_at=occurred_at,
                    symbol=symbol,
                    source=self.source,
                    kind=ObservationKind.PERP_SPOT_BASIS,
                    payload=BasisPayload(
                        basis_bps=basis_bps,
                        perp_price=perp.payload.close,
                        spot_price=spot.payload.close,
                        basis_type="basis_from_perp_close_vs_spot_close",
                    ),
                    metadata=self._metadata(
                        endpoint="derived:perp_spot_basis",
                        market_type="derived",
                        source_category="derived",
                        raw_payload=raw,
                        raw_payload_hash=self._hash_payload(raw),
                        visibility_note="derived observation is visible only after both source candles are visible",
                    ),
                )
            )
        return observations

    def to_jsonl_rows(self, observations: Iterable[Observation]) -> list[dict[str, Any]]:
        return [self.to_jsonl_row(observation) for observation in observations]

    def to_jsonl_row(self, observation: Observation) -> dict[str, Any]:
        payload = asdict(observation.payload) if hasattr(observation.payload, "__dataclass_fields__") else observation.payload
        return {
            "kind": observation.kind.value,
            "symbol": observation.symbol,
            "source": observation.source,
            "occurred_at": observation.occurred_at.isoformat().replace("+00:00", "Z"),
            "observed_at": observation.observed_at.isoformat().replace("+00:00", "Z"),
            "payload": payload,
            "metadata": observation.metadata,
        }

    def _with_normalized_open_interest(self, observations: list[Observation]) -> list[Observation]:
        mark_by_time = {
            item.occurred_at: item
            for item in observations
            if item.kind == ObservationKind.PERP_MARK_PRICE and isinstance(item.payload, CandlePayload)
        }
        normalized: list[Observation] = []
        for observation in observations:
            if observation.kind != ObservationKind.PERP_OPEN_INTEREST or not isinstance(observation.payload, OpenInterestPayload):
                normalized.append(observation)
                continue
            mark = mark_by_time.get(observation.occurred_at)
            if mark is None or not isinstance(mark.payload, CandlePayload):
                normalized.append(observation)
                continue
            open_interest_raw = float(observation.payload.open_interest_raw)
            notional = open_interest_raw * mark.payload.close
            metadata = dict(observation.metadata)
            metadata.update(
                {
                    "normalization_source": "bybit_mark_price_kline_close",
                    "normalization_observed_at": max(observation.observed_at, mark.observed_at).isoformat().replace("+00:00", "Z"),
                    "normalization_price_observation_kind": mark.kind.value,
                    "normalization_price_source_endpoint": mark.metadata.get("source_endpoint"),
                }
            )
            normalized.append(
                Observation(
                    observed_at=max(observation.observed_at, mark.observed_at),
                    occurred_at=observation.occurred_at,
                    symbol=observation.symbol,
                    source=observation.source,
                    kind=observation.kind,
                    payload=OpenInterestPayload(
                        open_interest_raw=observation.payload.open_interest_raw,
                        open_interest_unit=observation.payload.open_interest_unit,
                        open_interest_notional_usdt=notional,
                        normalization_price=mark.payload.close,
                        normalization_source="bybit_mark_price_kline_close",
                    ),
                    metadata=metadata,
                )
            )
        return normalized

    def _fetch_kline_observations(
        self,
        endpoint: str,
        category: str,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str,
        kind: ObservationKind,
        market_type: str,
        observed_lag: timedelta,
        volume_field: str | None,
        turnover_field: str | None,
    ) -> list[Observation[CandlePayload]]:
        interval_delta = self._interval_delta(interval)
        observations: list[Observation[CandlePayload]] = []
        for payload in self._iter_windowed_payloads(
            endpoint,
            {
                "category": category,
                "symbol": symbol,
                "interval": interval,
            },
            start,
            end,
            start_param="start",
            end_param="end",
        ):
            for row in payload.get("result", {}).get("list", []):
                opened_at = self._from_millis(row[0])
                closed_at = opened_at + interval_delta
                if not start <= closed_at < end:
                    continue
                # Bybit may include the current in-progress candle. Do not emit it as closed.
                if closed_at > datetime.now(timezone.utc):
                    continue
                raw_payload_hash = self._hash_payload(row)
                observations.append(
                    Observation(
                        observed_at=closed_at + observed_lag,
                        occurred_at=closed_at,
                        symbol=symbol,
                        source=self.source,
                        kind=kind,
                        payload=CandlePayload(
                            open=float(row[1]),
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                            volume=float(row[5]) if len(row) > 5 else 0.0,
                            granularity=f"{interval}m" if interval.isdigit() else interval,
                        ),
                        metadata=self._metadata(
                            endpoint=endpoint,
                            market_type=market_type,
                            source_category=category,
                            raw_payload=row,
                            raw_payload_hash=raw_payload_hash,
                            visibility_note="historical closed candle observed_at is simulated as interval close + publication lag",
                            extra={
                                "occurred_at_start": opened_at.isoformat().replace("+00:00", "Z"),
                                "interval": interval,
                                "volume_field": volume_field,
                                "turnover_field": turnover_field,
                                "turnover": row[6] if len(row) > 6 and turnover_field else None,
                            },
                        ),
                    )
                )
        return self._dedupe(observations)

    def _iter_windowed_payloads(
        self,
        endpoint: str,
        base_params: dict[str, str],
        start: datetime,
        end: datetime,
        start_param: str,
        end_param: str,
        window: timedelta = timedelta(days=2),
    ) -> Iterable[dict[str, Any]]:
        current = self._as_utc(start)
        end = self._as_utc(end)
        while current < end:
            window_end = min(current + window, end)
            params = dict(base_params)
            params[start_param] = str(int(current.timestamp() * 1000))
            params[end_param] = str(int(window_end.timestamp() * 1000))
            params["limit"] = str(self.max_limit)
            seen_cursors: set[str] = set()
            while True:
                attempts = 0
                while True:
                    payload = self._request(endpoint, params)
                    ret_code = payload.get("retCode")
                    if ret_code == 0:
                        break
                    if ret_code == 10006 and attempts < self.rate_limit_max_retries:
                        attempts += 1
                        if self.rate_limit_retry_delay_seconds > 0:
                            time.sleep(self.rate_limit_retry_delay_seconds * attempts)
                        continue
                    raise RuntimeError(f"Bybit request failed for {endpoint}: {ret_code} {payload.get('retMsg')}")
                yield payload

                next_cursor = payload.get("result", {}).get("nextPageCursor")
                if not next_cursor:
                    break
                if next_cursor in seen_cursors:
                    raise RuntimeError(f"Bybit pagination cursor repeated for {endpoint}: {next_cursor}")
                seen_cursors.add(next_cursor)
                params["cursor"] = next_cursor
                self._delay()
            current = window_end
            self._delay()

    def _request(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        return self._http_get(f"{self.base_url}{endpoint}?{urlencode(params)}", {"Accept": "application/json"})

    def _metadata(
        self,
        endpoint: str,
        market_type: str,
        source_category: str,
        raw_payload: Any,
        raw_payload_hash: str,
        visibility_note: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = {
            "venue": self.venue,
            "market_type": market_type,
            "source_category": source_category,
            "source_endpoint": endpoint,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "raw_payload_hash": raw_payload_hash,
            "ingestion_run_id": self.ingestion_run_id,
            "fixture_version": self.fixture_version,
            "replay_visibility": "conservative_simulated_observed_at",
            "visibility_note": visibility_note,
            "raw_payload": raw_payload,
        }
        if extra:
            metadata.update(extra)
        return metadata

    def _delay(self) -> None:
        if self.request_delay_seconds > 0:
            time.sleep(self.request_delay_seconds)

    @classmethod
    def _default_kinds(cls) -> set[ObservationKind]:
        return {
            ObservationKind.CANDLE,
            ObservationKind.PERP_MARK_PRICE,
            ObservationKind.PERP_OPEN_INTEREST,
            ObservationKind.PERP_FUNDING_RATE,
            ObservationKind.PERP_SPOT_BASIS,
        }

    @staticmethod
    def _dedupe(observations: Iterable[Observation]) -> list[Observation]:
        by_key: dict[tuple[str, ObservationKind, datetime, str], Observation] = {}
        for observation in observations:
            endpoint = observation.metadata.get("source_endpoint", "")
            by_key.setdefault((observation.symbol, observation.kind, observation.occurred_at, endpoint), observation)
        return sorted(by_key.values(), key=lambda item: item.occurred_at)

    @staticmethod
    def _hash_payload(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    @staticmethod
    def _default_http_get(url: str, headers: dict[str, str]) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _from_millis(value: str | int) -> datetime:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _interval_delta(interval: str) -> timedelta:
        if interval.isdigit():
            return timedelta(minutes=int(interval))
        if interval == "D":
            return timedelta(days=1)
        if interval == "W":
            return timedelta(weeks=1)
        if interval == "M":
            return timedelta(days=30)
        raise ValueError(f"unsupported Bybit interval: {interval}")

    @classmethod
    def _floor_to_interval(cls, value: datetime, interval: str) -> datetime:
        value = cls._as_utc(value)
        delta = cls._interval_delta(interval)
        seconds = int(delta.total_seconds())
        floored = int(value.timestamp()) // seconds * seconds
        return datetime.fromtimestamp(floored, tz=timezone.utc)
