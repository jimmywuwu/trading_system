from __future__ import annotations

"""Cross-venue perp funding history: normalization + preflight.

Timing semantics (SourceNote: reports/data_quality/cross_venue_funding_source_note.md):
- ``occurred_at`` = exchange funding settlement timestamp (the rate applies
  to the interval ending at this moment and is fixed at settlement).
- ``observed_at`` = occurred_at + 60s, a conservative simulated availability
  delay: the settled rate is queryable from the public history endpoint
  shortly after settlement; +60s guards against endpoint lag. Live systems
  must replace this with the actual retrieval timestamp.

Symbols are normalized to the asset ("BTC"); the venue lives in ``source``
so research code aligns series by (symbol, source).
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

OBSERVED_DELAY = timedelta(seconds=60)

VENUE_INTERVALS = {"bybit": "8h", "okx": "8h", "hyperliquid": "1h"}


def _iso(ms: int, delay: timedelta = timedelta()) -> str:
    moment = datetime.fromtimestamp(ms / 1000, tz=timezone.utc) + delay
    return moment.isoformat().replace("+00:00", "Z")


def _row(
    venue: str,
    instrument: str,
    settle_ms: int,
    rate_raw: str,
    endpoint: str,
    raw: dict[str, Any],
    asset: str = "BTC",
) -> dict[str, Any]:
    raw_json = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return {
        "observed_at": _iso(settle_ms, OBSERVED_DELAY),
        "occurred_at": _iso(settle_ms),
        "symbol": asset,
        "source": venue,
        "kind": "perp_funding_rate",
        "payload": {
            "funding_rate": float(rate_raw),
            "funding_rate_raw": str(rate_raw),
            "funding_type": "settled",
            "funding_interval": VENUE_INTERVALS[venue],
        },
        "metadata": {
            "instrument": instrument,
            "source_endpoint": endpoint,
            "settle_ms": settle_ms,
            "raw_payload": raw,
            "raw_payload_hash": hashlib.sha256(raw_json.encode()).hexdigest(),
            "observed_at_rule": "occurred_at + 60s conservative simulated availability",
        },
    }


def normalize_bybit_row(raw: dict[str, Any], asset: str = "BTC") -> dict[str, Any]:
    return _row(
        "bybit",
        raw["symbol"],
        int(raw["fundingRateTimestamp"]),
        raw["fundingRate"],
        "https://api.bybit.com/v5/market/funding/history",
        raw,
        asset,
    )


def normalize_okx_row(raw: dict[str, Any], asset: str = "BTC") -> dict[str, Any]:
    # history rows carry the settled rate in realizedRate on newer schema
    # versions and fundingRate on older ones
    rate = raw.get("realizedRate") or raw["fundingRate"]
    return _row(
        "okx",
        raw["instId"],
        int(raw["fundingTime"]),
        rate,
        "https://www.okx.com/api/v5/public/funding-rate-history",
        raw,
        asset,
    )


def normalize_hyperliquid_row(raw: dict[str, Any], asset: str = "BTC") -> dict[str, Any]:
    return _row(
        "hyperliquid",
        raw["coin"],
        int(raw["time"]),
        raw["fundingRate"],
        "https://api.hyperliquid.xyz/info#fundingHistory",
        raw,
        asset,
    )


def preflight_funding_rows(rows: list[dict[str, Any]], days: float) -> dict[str, Any]:
    """Data-quality report for normalized funding observation rows.

    Checks per source: monotonic settle times, duplicates, coverage vs the
    venue's settlement cadence, observed_at > occurred_at, and absolute
    rate sanity (< 1% per interval).
    """
    report: dict[str, Any] = {"days": days, "sources": {}, "passed": True}
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)

    for source, source_rows in sorted(by_source.items()):
        settles = [row["metadata"]["settle_ms"] for row in source_rows]
        duplicates = len(settles) - len(set(settles))
        monotonic = all(a <= b for a, b in zip(settles, settles[1:]))
        interval_hours = 1 if VENUE_INTERVALS.get(source) == "1h" else 8
        expected = int(days * 24 / interval_hours)
        coverage = len(set(settles)) / expected if expected else None
        visibility_ok = all(row["observed_at"] > row["occurred_at"] for row in source_rows)
        max_abs_rate = max((abs(row["payload"]["funding_rate"]) for row in source_rows), default=0.0)
        checks = {
            "count": len(source_rows),
            "expected": expected,
            "coverage": round(coverage, 4) if coverage is not None else None,
            "duplicates": duplicates,
            "monotonic": monotonic,
            "observed_after_occurred": visibility_ok,
            "max_abs_rate": max_abs_rate,
        }
        ok = (
            duplicates == 0
            and monotonic
            and visibility_ok
            and max_abs_rate < 0.01
            and coverage is not None
            and coverage >= 0.95
        )
        checks["ok"] = ok
        report["sources"][source] = checks
        report["passed"] = report["passed"] and ok
    return report
