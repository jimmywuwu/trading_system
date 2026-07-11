from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.models import BasisPayload, FundingRatePayload, ObservationKind, OpenInterestPayload
from providers.bybit_leverage_provider import BybitLeveragePressureProvider, BybitRawArchive
from providers.file_provider import JsonLinesObservationProvider


class BybitLeveragePressureProviderTest(unittest.TestCase):
    def test_emits_conservative_fixture_observations_and_round_trips_jsonl(self) -> None:
        responses = {
            "/v5/market/kline?category=linear": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        ["1780018200000", "100", "110", "90", "105", "2", "210"],
                    ]
                },
            },
            "/v5/market/kline?category=spot": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        ["1780018200000", "99", "100", "95", "100", "3", "300"],
                    ]
                },
            },
            "/v5/market/mark-price-kline?category=linear": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        ["1780018200000", "101", "106", "100", "104"],
                    ]
                },
            },
            "/v5/market/open-interest?category=linear": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {"openInterest": "10", "timestamp": "1780018500000"},
                    ]
                },
            },
            "/v5/market/funding/history?category=linear": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingRateTimestamp": "1780018500000"},
                    ]
                },
            },
        }

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del headers
            for marker, payload in responses.items():
                if marker in url:
                    return payload
            raise AssertionError(f"unexpected URL: {url}")

        provider = BybitLeveragePressureProvider(
            http_get=fake_http_get,
            ingestion_run_id="test-run",
            fixture_version="fixture-v1",
        )
        start = datetime(2026, 5, 29, 1, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 29, 2, 0, tzinfo=timezone.utc)

        observations = provider.get_observations(start=start, end=end, subjects=["BTCUSDT"])
        by_kind = {observation.kind: observation for observation in observations}

        self.assertIn(ObservationKind.PERP_FUNDING_RATE, by_kind)
        self.assertIsInstance(by_kind[ObservationKind.PERP_FUNDING_RATE].payload, FundingRatePayload)
        self.assertEqual(by_kind[ObservationKind.PERP_FUNDING_RATE].payload.funding_type, "settled")

        self.assertIn(ObservationKind.PERP_OPEN_INTEREST, by_kind)
        oi = by_kind[ObservationKind.PERP_OPEN_INTEREST]
        self.assertIsInstance(oi.payload, OpenInterestPayload)
        self.assertEqual(oi.payload.open_interest_unit, "exchange_native_linear_contract_quantity")
        self.assertEqual(oi.payload.normalization_source, "bybit_mark_price_kline_close")
        self.assertEqual(oi.payload.open_interest_notional_usdt, 1040.0)
        self.assertEqual(oi.metadata["replay_visibility"], "conservative_simulated_observed_at")

        self.assertIn(ObservationKind.PERP_SPOT_BASIS, by_kind)
        basis = by_kind[ObservationKind.PERP_SPOT_BASIS]
        self.assertIsInstance(basis.payload, BasisPayload)
        self.assertEqual(basis.payload.basis_type, "basis_from_perp_close_vs_spot_close")
        self.assertEqual(basis.payload.basis_bps, 500.0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            with path.open("w", encoding="utf-8") as file:
                for row in provider.to_jsonl_rows(observations):
                    file.write(json.dumps(row, default=str) + "\n")

            round_trip = JsonLinesObservationProvider(path).get_observations(subjects=["BTCUSDT"])
            round_trip_kinds = {observation.kind for observation in round_trip}
            self.assertIn(ObservationKind.PERP_FUNDING_RATE, round_trip_kinds)
            self.assertIn(ObservationKind.PERP_OPEN_INTEREST, round_trip_kinds)
            self.assertIn(ObservationKind.PERP_SPOT_BASIS, round_trip_kinds)

    def test_raw_archive_records_and_replays_endpoint_payloads(self) -> None:
        responses = {
            "/v5/market/open-interest?category=linear": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {"list": [{"openInterest": "100", "timestamp": "1780018500000"}]},
            },
        }

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del headers
            for marker, payload in responses.items():
                if marker in url:
                    return payload
            raise AssertionError(f"unexpected URL: {url}")

        with tempfile.TemporaryDirectory() as directory:
            archive = BybitRawArchive(Path(directory))
            provider = BybitLeveragePressureProvider(
                http_get=archive.recording_http_get(fake_http_get),
                ingestion_run_id="archive-test",
                fixture_version="fixture-archive-v1",
            )
            start = datetime(2026, 5, 29, 1, 0, tzinfo=timezone.utc)
            end = datetime(2026, 5, 29, 2, 0, tzinfo=timezone.utc)

            live_observations = provider.fetch_open_interest("BTCUSDT", start, end)
            archive_records = list(archive.iter_records())

            self.assertEqual(len(archive_records), 1)
            self.assertEqual(archive_records[0]["endpoint"], "/v5/market/open-interest")
            self.assertEqual(archive_records[0]["params"]["symbol"], "BTCUSDT")
            self.assertEqual(archive_records[0]["payload_hash"], BybitLeveragePressureProvider._hash_payload(responses["/v5/market/open-interest?category=linear"]))

            replay_provider = BybitLeveragePressureProvider(
                http_get=archive.replay_http_get(),
                ingestion_run_id="archive-test",
                fixture_version="fixture-archive-v1",
            )
            replay_observations = replay_provider.fetch_open_interest("BTCUSDT", start, end)

            self.assertEqual(
                [row.payload.open_interest_raw for row in replay_observations],
                [row.payload.open_interest_raw for row in live_observations],
            )
            self.assertEqual(
                [row.metadata["raw_payload_hash"] for row in replay_observations],
                [row.metadata["raw_payload_hash"] for row in live_observations],
            )

    def test_rate_limited_payload_retries_before_failing_window(self) -> None:
        responses = [
            {"retCode": 10006, "retMsg": "Too many visits. Exceeded the API Rate Limit.", "result": {}},
            {"retCode": 0, "retMsg": "OK", "result": {"list": [{"openInterest": "100", "timestamp": "1780018500000"}]}},
        ]
        calls = 0

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del url, headers
            nonlocal calls
            payload = responses[calls]
            calls += 1
            return payload

        provider = BybitLeveragePressureProvider(http_get=fake_http_get, request_delay_seconds=0, rate_limit_retry_delay_seconds=0)
        start = datetime(2026, 5, 29, 1, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 29, 2, 0, tzinfo=timezone.utc)

        observations = provider.fetch_open_interest("BTCUSDT", start, end)

        self.assertEqual(calls, 2)
        self.assertEqual([row.payload.open_interest_raw for row in observations], ["100"])

    def test_open_interest_follows_next_page_cursor_until_empty(self) -> None:
        pages = {
            None: {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {"openInterest": "100", "timestamp": "1780018500000"},
                    ],
                    "nextPageCursor": "cursor-1",
                },
            },
            "cursor-1": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {"openInterest": "101", "timestamp": "1780018800000"},
                    ],
                    "nextPageCursor": "cursor-2",
                },
            },
            "cursor-2": {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {"openInterest": "102", "timestamp": "1780019100000"},
                        {"openInterest": "102-duplicate", "timestamp": "1780019100000"},
                    ],
                    "nextPageCursor": "",
                },
            },
        }
        requested_cursors: list[str | None] = []

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del headers
            query = parse_qs(urlparse(url).query)
            cursor = query.get("cursor", [None])[0]
            requested_cursors.append(cursor)
            return pages[cursor]

        provider = BybitLeveragePressureProvider(http_get=fake_http_get)
        start = datetime(2026, 5, 29, 1, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 29, 2, 0, tzinfo=timezone.utc)

        observations = provider.fetch_open_interest("BTCUSDT", start, end)

        self.assertEqual(requested_cursors, [None, "cursor-1", "cursor-2"])
        self.assertEqual(
            [observation.occurred_at.isoformat() for observation in observations],
            [
                "2026-05-29T01:35:00+00:00",
                "2026-05-29T01:40:00+00:00",
                "2026-05-29T01:45:00+00:00",
            ],
        )
        self.assertEqual(
            [observation.payload.open_interest_raw for observation in observations],
            ["100", "101", "102"],
        )


if __name__ == "__main__":
    unittest.main()
