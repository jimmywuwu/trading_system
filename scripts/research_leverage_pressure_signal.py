#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.models import CandlePayload, Observation, ObservationKind
from providers.file_provider import JsonLinesObservationProvider
from signals.leverage_pressure import LeveragePressureShortSignal


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def pct_return(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return end / start - 1.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * q))
    return ordered[index]


def summarize(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    wins = [value for value in values if value > 0]
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 8),
        "median": round(statistics.median(values), 8),
        "win_rate": round(len(wins) / len(values), 6),
        "p25": round(percentile(values, 0.25) or 0.0, 8),
        "p75": round(percentile(values, 0.75) or 0.0, 8),
    }


def bucket_summary(events: list[dict[str, Any]], field: str, horizon: str) -> dict[str, Any]:
    usable = [event for event in events if horizon in event["forward_short_returns"]]
    if not usable:
        return {"insufficient_events": True}
    ordered = sorted(usable, key=lambda item: item[field])
    midpoint = max(1, len(ordered) // 2)
    low = ordered[:midpoint]
    high = ordered[midpoint:] or ordered[midpoint - 1 :]
    return {
        "low_bucket": summarize([event["forward_short_returns"][horizon] for event in low]),
        "high_bucket": summarize([event["forward_short_returns"][horizon] for event in high]),
        "note": "For SHORT signal, positive forward_short_return means downside followed the signal.",
    }


def candle_close_series(observations: list[Observation], symbol: str) -> list[tuple[datetime, float]]:
    closes = []
    for observation in observations:
        if observation.symbol != symbol or observation.kind != ObservationKind.CANDLE:
            continue
        if observation.metadata.get("market_type") != "linear_perp":
            continue
        if not isinstance(observation.payload, CandlePayload):
            continue
        closes.append((observation.observed_at, observation.payload.close))
    closes.sort(key=lambda item: item[0])
    return closes


def close_at_or_after(closes: list[tuple[datetime, float]], timestamp: datetime) -> tuple[datetime, float] | None:
    for close_time, close in closes:
        if close_time >= timestamp:
            return close_time, close
    return None


def close_at_or_before(closes: list[tuple[datetime, float]], timestamp: datetime) -> tuple[datetime, float] | None:
    candidate = None
    for close_time, close in closes:
        if close_time <= timestamp:
            candidate = (close_time, close)
        else:
            break
    return candidate


def classify_regime(closes: list[tuple[datetime, float]], timestamp: datetime, median_abs_hourly_return: float) -> str:
    now = close_at_or_before(closes, timestamp)
    prior_24h = close_at_or_before(closes, timestamp - timedelta(hours=24))
    prior_1h = close_at_or_before(closes, timestamp - timedelta(hours=1))
    if now is None or prior_24h is None or prior_1h is None:
        return "insufficient_history"
    trend_return = pct_return(prior_24h[1], now[1])
    abs_hourly_return = abs(pct_return(prior_1h[1], now[1]))
    vol = "high_vol" if abs_hourly_return >= median_abs_hourly_return else "low_vol"
    if trend_return > 0.02:
        trend = "bull_24h"
    elif trend_return < -0.02:
        trend = "bear_24h"
    else:
        trend = "sideways_24h"
    return f"{trend}_{vol}"


def run_replay(path: Path, symbol: str, lookback_hours: int, horizons: list[int]) -> dict[str, Any]:
    provider = JsonLinesObservationProvider(path)
    observations = provider.get_observations(subjects=[symbol])
    observations.sort(key=lambda item: item.observed_at)
    closes = candle_close_series(observations, symbol)
    signal = LeveragePressureShortSignal(symbol=symbol)
    replay_times = sorted({item.observed_at for item in observations if item.kind in {ObservationKind.CANDLE, ObservationKind.PERP_SPOT_BASIS}})

    hourly_abs_returns = []
    for close_time, close in closes:
        prior = close_at_or_before(closes, close_time - timedelta(hours=1))
        if prior:
            hourly_abs_returns.append(abs(pct_return(prior[1], close)))
    median_abs_hourly_return = statistics.median(hourly_abs_returns) if hourly_abs_returns else 0.0

    events: list[dict[str, Any]] = []
    last_event_time: datetime | None = None
    lookback = timedelta(hours=lookback_hours)
    for replay_time in replay_times:
        visible = [item for item in observations if replay_time - lookback <= item.observed_at <= replay_time]
        event = signal.generate(visible)
        if event is None:
            continue
        # Avoid counting the same persistent condition every five minutes.
        if last_event_time is not None and event.timestamp - last_event_time < timedelta(hours=1):
            continue
        entry = close_at_or_after(closes, event.timestamp)
        if entry is None:
            continue
        forward_short_returns = {}
        forward_long_returns = {}
        for horizon in horizons:
            future = close_at_or_after(closes, event.timestamp + timedelta(hours=horizon))
            if future is None:
                continue
            long_ret = pct_return(entry[1], future[1])
            forward_long_returns[f"{horizon}h"] = round(long_ret, 8)
            forward_short_returns[f"{horizon}h"] = round(-long_ret, 8)
        events.append(
            {
                "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
                "strength": event.strength,
                "confidence": event.confidence,
                "entry_close_time": entry[0].isoformat().replace("+00:00", "Z"),
                "entry_close": entry[1],
                "funding_rate": event.metadata.get("funding_rate"),
                "open_interest_change_pct": event.metadata.get("open_interest_change_pct"),
                "basis_bps": event.metadata.get("basis_bps"),
                "regime": classify_regime(closes, event.timestamp, median_abs_hourly_return),
                "forward_long_returns": forward_long_returns,
                "forward_short_returns": forward_short_returns,
            }
        )
        last_event_time = event.timestamp

    horizon_summary = {
        f"{horizon}h": summarize([event["forward_short_returns"][f"{horizon}h"] for event in events if f"{horizon}h" in event["forward_short_returns"]])
        for horizon in horizons
    }
    regimes: dict[str, list[float]] = {}
    primary_horizon = f"{horizons[0]}h"
    for event in events:
        if primary_horizon in event["forward_short_returns"]:
            regimes.setdefault(event["regime"], []).append(event["forward_short_returns"][primary_horizon])

    first_close = closes[0] if closes else None
    last_close = closes[-1] if closes else None
    buy_hold = pct_return(first_close[1], last_close[1]) if first_close and last_close else 0.0

    result = {
        "fixture": str(path),
        "symbol": symbol,
        "observation_count": len(observations),
        "perp_candle_count": len(closes),
        "data_start_observed_at": observations[0].observed_at.isoformat().replace("+00:00", "Z") if observations else None,
        "data_end_observed_at": observations[-1].observed_at.isoformat().replace("+00:00", "Z") if observations else None,
        "lookback_hours": lookback_hours,
        "horizons": [f"{horizon}h" for horizon in horizons],
        "signal_count": len(events),
        "forward_short_return_summary": horizon_summary,
        "strength_bucket_analysis": bucket_summary(events, "strength", primary_horizon),
        "confidence_bucket_analysis": bucket_summary(events, "confidence", primary_horizon),
        "regime_summary": {regime: summarize(values) for regime, values in sorted(regimes.items())},
        "benchmarks": {
            "cash_total_return": 0.0,
            "buy_and_hold_long_total_return": round(buy_hold, 8),
            "always_short_total_return": round(-buy_hold, 8),
        },
        "events": events,
        "warnings": [
            "Historical observed_at values are conservative simulated availability timestamps, not archived receive timestamps.",
            "Settled funding history is used; live quoted/predicted funding at decision time is not reconstructed.",
            "This is a first-pass signal-behavior study, not a tradeable strategy or sizing recommendation.",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay and summarize the leverage-pressure SHORT signal on a normalized Observation JSONL fixture.")
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--horizons", type=int, nargs="+", default=[4, 8, 24])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_replay(args.fixture, args.symbol, args.lookback_hours, args.horizons)
    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
