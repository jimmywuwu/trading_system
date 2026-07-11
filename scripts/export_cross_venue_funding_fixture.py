"""Export a replay-safe cross-venue funding fixture (Bybit / OKX / Hyperliquid).

Usage:
    python3 scripts/export_cross_venue_funding_fixture.py --days 90 \
        --out data/cross_venue_funding_btc_90d.jsonl

Fixes milestone2's gaps: full OKX pagination (it previously fetched only the
latest page), raw payload + sha256 hash persisted per row, explicit
occurred_at/observed_at semantics (see providers/cross_venue_funding.py),
and a preflight quality report printed and saved next to the fixture.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers.cross_venue_funding import (
    normalize_bybit_row,
    normalize_hyperliquid_row,
    normalize_okx_row,
    preflight_funding_rows,
)

PAGE_SLEEP = 0.15


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"User-Agent": "trading_system_funding_fixture/0.1"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_bybit(start_ms: int, end_ms: int, symbol: str = "BTCUSDT") -> list[dict[str, Any]]:
    endpoint = "https://api.bybit.com/v5/market/funding/history"
    rows: dict[int, dict[str, Any]] = {}
    cursor_end = end_ms
    while cursor_end >= start_ms:
        params = {
            "category": "linear", "symbol": symbol,
            "startTime": str(start_ms), "endTime": str(cursor_end), "limit": "200",
        }
        data = http_json(endpoint + "?" + urllib.parse.urlencode(params))
        if data.get("retCode") != 0:
            raise RuntimeError(f"bybit retCode={data.get('retCode')} {data.get('retMsg')}")
        page = data.get("result", {}).get("list", []) or []
        if not page:
            break
        min_seen = None
        for raw in page:
            ts = int(raw["fundingRateTimestamp"])
            if start_ms <= ts <= end_ms:
                rows[ts] = raw
            min_seen = ts if min_seen is None else min(min_seen, ts)
        if len(page) < 200 or min_seen is None or min_seen <= start_ms:
            break
        cursor_end = min_seen - 1
        time.sleep(PAGE_SLEEP)
    return [rows[ts] for ts in sorted(rows)]


def fetch_okx(start_ms: int, end_ms: int, inst_id: str = "BTC-USDT-SWAP") -> list[dict[str, Any]]:
    """Walk backwards with the ``after`` cursor (returns records earlier
    than the given timestamp) until the window is covered."""
    endpoint = "https://www.okx.com/api/v5/public/funding-rate-history"
    rows: dict[int, dict[str, Any]] = {}
    after: int | None = None
    while True:
        params = {"instId": inst_id, "limit": "100"}
        if after is not None:
            params["after"] = str(after)
        data = http_json(endpoint + "?" + urllib.parse.urlencode(params))
        if data.get("code") != "0":
            raise RuntimeError(f"okx code={data.get('code')} {data.get('msg')}")
        page = data.get("data", []) or []
        if not page:
            break
        min_seen = None
        for raw in page:
            ts = int(raw["fundingTime"])
            if start_ms <= ts <= end_ms:
                rows[ts] = raw
            min_seen = ts if min_seen is None else min(min_seen, ts)
        if min_seen is None or min_seen <= start_ms or len(page) < 100:
            break
        after = min_seen
        time.sleep(PAGE_SLEEP)
    return [rows[ts] for ts in sorted(rows)]


def fetch_hyperliquid(start_ms: int, end_ms: int, coin: str = "BTC") -> list[dict[str, Any]]:
    endpoint = "https://api.hyperliquid.xyz/info"
    rows: dict[int, dict[str, Any]] = {}
    cursor_start = start_ms
    while cursor_start <= end_ms:
        payload = {"type": "fundingHistory", "coin": coin,
                   "startTime": cursor_start, "endTime": end_ms}
        page = http_json(endpoint, payload=payload)
        if not isinstance(page, list):
            raise RuntimeError(f"hyperliquid unexpected payload: {type(page).__name__}")
        if not page:
            break
        max_seen = None
        for raw in page:
            ts = int(raw["time"])
            if start_ms <= ts <= end_ms:
                rows[ts] = raw
            max_seen = ts if max_seen is None else max(max_seen, ts)
        if max_seen is None or max_seen >= end_ms or len(page) < 500:
            break
        cursor_start = max_seen + 1
        time.sleep(PAGE_SLEEP)
    return [rows[ts] for ts in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    end_ms = int(time.time() // 3600 * 3600 * 1000)
    start_ms = end_ms - args.days * 24 * 3600 * 1000

    normalized: list[dict[str, Any]] = []
    for venue, fetch, normalize in (
        ("bybit", fetch_bybit, normalize_bybit_row),
        ("okx", fetch_okx, normalize_okx_row),
        ("hyperliquid", fetch_hyperliquid, normalize_hyperliquid_row),
    ):
        raw_rows = fetch(start_ms, end_ms)
        normalized.extend(normalize(raw) for raw in raw_rows)
        print(f"{venue}: {len(raw_rows)} rows")

    normalized.sort(key=lambda row: row["observed_at"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as file:
        for row in normalized:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"fixture written: {args.out} ({len(normalized)} rows)")

    report = preflight_funding_rows(normalized, days=args.days)
    report["fixture"] = str(args.out)
    report["window"] = {"start_ms": start_ms, "end_ms": end_ms}
    report_path = args.out.with_suffix(".preflight.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"preflight report: {report_path}")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
