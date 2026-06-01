from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.models import BasisPayload, FundingRatePayload, ObservationKind, OpenInterestPayload
from providers.bybit_leverage_provider import BybitLeveragePressureProvider
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
        self.assertEqual(oi.metadata["coverage_status"], "incomplete")
        self.assertEqual(oi.metadata["coverage_expected_interval"], "5m")
        self.assertIn("coverage_warning", oi.metadata)

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

    def test_open_interest_uses_sub_cap_windows_and_records_complete_coverage(self) -> None:
        requested_urls: list[str] = []

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del headers
            requested_urls.append(url)
            if "/v5/market/open-interest" not in url:
                return {"retCode": 0, "retMsg": "OK", "result": {"list": []}}
            if "startTime=1780000000000" in url:
                rows = [
                    {"openInterest": "10", "timestamp": "1780000000000"},
                    {"openInterest": "11", "timestamp": "1780000300000"},
                ]
            else:
                rows = [
                    {"openInterest": "12", "timestamp": "1780000600000"},
                    {"openInterest": "13", "timestamp": "1780000900000"},
                ]
            return {"retCode": 0, "retMsg": "OK", "result": {"list": rows}}

        provider = BybitLeveragePressureProvider(http_get=fake_http_get)
        provider.open_interest_window = timedelta(minutes=10)
        start = datetime.fromtimestamp(1780000000, tz=timezone.utc)
        end = start + timedelta(minutes=20)

        observations = provider.fetch_open_interest("BTCUSDT", start, end)

        self.assertEqual(len(observations), 4)
        self.assertEqual(len([url for url in requested_urls if "/v5/market/open-interest" in url]), 2)
        self.assertTrue(all("limit=200" in url for url in requested_urls if "/v5/market/open-interest" in url))
        self.assertEqual(observations[0].metadata["coverage_status"], "complete")
        self.assertEqual(observations[0].metadata["coverage_expected_points"], 4)
        self.assertEqual(observations[0].metadata["coverage_observed_points"], 4)
        self.assertEqual(len(observations[0].metadata["coverage_request_windows"]), 2)

    def test_open_interest_raises_when_endpoint_cap_is_reached(self) -> None:
        rows = [
            {"openInterest": str(index), "timestamp": str(1780000000000 + index * 300_000)}
            for index in range(BybitLeveragePressureProvider.open_interest_limit)
        ]

        def fake_http_get(url: str, headers: dict[str, str]) -> dict:
            del url, headers
            return {"retCode": 0, "retMsg": "OK", "result": {"list": rows}}

        provider = BybitLeveragePressureProvider(http_get=fake_http_get)
        start = datetime.fromtimestamp(1780000000, tz=timezone.utc)
        end = start + timedelta(hours=1)

        with self.assertRaisesRegex(RuntimeError, "open-interest response reached the endpoint limit"):
            provider.fetch_open_interest("BTCUSDT", start, end)

    def test_export_script_can_run_directly_from_repo_root(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/export_bybit_leverage_fixture.py", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Export a conservative Bybit leverage-pressure", result.stdout)

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
