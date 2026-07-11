"""Vol event study for oi_contraction_vol_regime on Bybit fixtures.

Usage:
    python3 reports/research/oi-contraction-vol-regime/run_vol_event_study.py \
        data/bybit_leverage_pressure_fixture_90d.jsonl \
        --out reports/research/oi-contraction-vol-regime/vol_event_study_90d.json

Point-in-time: signal events are produced through backtest.ReplayDataProvider
(lookahead guard active); the study anchors outcomes at the first candle
strictly after each event time.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backtest import ReplayDataProvider
from core.models import (
    CandlePayload,
    Observation,
    ObservationKind,
    OpenInterestPayload,
)
from research.vol_event_study import realized_vol_study
from signals.oi_contraction_vol_regime import OiContractionVolRegimeSignal

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
HORIZONS = [timedelta(hours=4), timedelta(hours=8), timedelta(hours=24)]


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_lean(path: Path) -> tuple[dict[str, list[Observation]], dict[str, list[Observation]]]:
    """Stream-parse the fixture keeping only OI and linear-perp candles,
    with metadata dropped to keep memory bounded."""
    oi: dict[str, list[Observation]] = {symbol: [] for symbol in SYMBOLS}
    candles: dict[str, list[Observation]] = {symbol: [] for symbol in SYMBOLS}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            row = json.loads(line)
            symbol = row.get("symbol")
            if symbol not in SYMBOLS:
                continue
            kind = row.get("kind")
            if kind == "perp_open_interest":
                payload = row["payload"]
                oi[symbol].append(
                    Observation(
                        observed_at=parse_time(row["observed_at"]),
                        occurred_at=parse_time(row["occurred_at"]),
                        symbol=symbol,
                        source=row.get("source", "fixture"),
                        kind=ObservationKind.PERP_OPEN_INTEREST,
                        payload=OpenInterestPayload(
                            open_interest_raw=str(payload["open_interest_raw"]),
                            open_interest_unit=str(payload["open_interest_unit"]),
                        ),
                    )
                )
            elif kind == "candle" and row.get("metadata", {}).get("market_type") == "linear_perp":
                payload = row["payload"]
                candles[symbol].append(
                    Observation(
                        observed_at=parse_time(row["observed_at"]),
                        occurred_at=parse_time(row["occurred_at"]),
                        symbol=symbol,
                        source=row.get("source", "fixture"),
                        kind=ObservationKind.CANDLE,
                        payload=CandlePayload(
                            open=float(payload["open"]),
                            high=float(payload["high"]),
                            low=float(payload["low"]),
                            close=float(payload["close"]),
                            volume=float(payload.get("volume", 0) or 0),
                            granularity=str(payload.get("granularity", "5m")),
                        ),
                    )
                )
    for symbol in SYMBOLS:
        oi[symbol].sort(key=lambda item: item.observed_at)
        candles[symbol].sort(key=lambda item: item.observed_at)
    return oi, candles


def signal_events(oi_observations: list[Observation], symbol: str) -> list[datetime]:
    signal = OiContractionVolRegimeSignal(
        symbol=symbol,
        change_window=timedelta(hours=4),
        history_window=timedelta(days=14),
        min_history=300,
    )
    events = []
    for current_time, batch in ReplayDataProvider(oi_observations).replay():
        event = signal.generate(batch)
        if event is not None:
            assert event.timestamp <= current_time
            events.append(event.timestamp)
    return events


def run_symbol(symbol: str, oi_observations: list[Observation], candles: list[Observation]) -> dict:
    events = signal_events(oi_observations, symbol)
    result: dict = {"symbol": symbol, "raw_event_count": len(events)}
    if not events:
        result["error"] = "no events"
        return result

    for match_on in ("vol", "return"):
        result[f"full_{match_on}_matched"] = realized_vol_study(
            events, candles, HORIZONS, match_on=match_on
        )

    midpoint = candles[len(candles) // 2].observed_at
    halves = {
        "first_half": (
            [t for t in events if t < midpoint],
            [c for c in candles if c.observed_at < midpoint],
        ),
        "second_half": (
            [t for t in events if t >= midpoint],
            [c for c in candles if c.observed_at >= midpoint],
        ),
    }
    result["midpoint"] = midpoint.isoformat()
    for name, (half_events, half_candles) in halves.items():
        result[name] = realized_vol_study(
            half_events, half_candles, [timedelta(hours=24)], match_on="vol"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    oi, candles = load_lean(args.fixture)
    output = {
        "fixture": str(args.fixture),
        "generated_at": datetime.now().isoformat(),
        "signal_params": {
            "change_window": "4h",
            "history_window": "14d",
            "min_history": 300,
            "trigger_percentile": 0.10,
            "rearm_percentile": 0.20,
        },
        "symbols": {},
    }
    for symbol in SYMBOLS:
        print(f"running {symbol}: oi={len(oi[symbol])} candles={len(candles[symbol])}")
        output["symbols"][symbol] = run_symbol(symbol, oi[symbol], candles[symbol])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"written: {args.out}")

    for symbol in SYMBOLS:
        data = output["symbols"][symbol]
        print(f"\n=== {symbol} (raw events: {data.get('raw_event_count')}) ===")
        for key in ("full_vol_matched", "full_return_matched", "first_half", "second_half"):
            block = data.get(key)
            if not block or "horizons" not in block:
                print(f"  {key}: {block.get('error') if block else 'missing'}")
                continue
            for label, row in block["horizons"].items():
                if "error" in row:
                    print(f"  {key} {label}: {row['error']}")
                    continue
                print(
                    f"  {key} {label}: n={row['n']} vol_lift={row['vol_lift']:+.3f} "
                    f"ci95={row['vol_lift_ci95']} abs_ret_lift={row['abs_return_lift']:+.3f}"
                )


if __name__ == "__main__":
    main()
