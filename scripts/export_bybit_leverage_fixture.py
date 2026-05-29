from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from providers.bybit_leverage_provider import BybitLeveragePressureProvider


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a conservative Bybit leverage-pressure Observation JSONL fixture.")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--end", type=parse_timestamp, default=None, help="UTC end timestamp, e.g. 2026-05-28T00:00:00Z")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--output", type=Path, default=Path("data/bybit_leverage_pressure_fixture.jsonl"))
    parser.add_argument("--request-delay", type=float, default=0.05)
    args = parser.parse_args()

    end = args.end or datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    provider = BybitLeveragePressureProvider(request_delay_seconds=args.request_delay)
    observations = provider.get_observations(start=start, end=end, subjects=args.symbols)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for row in provider.to_jsonl_rows(observations):
            file.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    print(
        f"wrote {len(observations)} observations to {args.output} "
        f"for {','.join(args.symbols)} from {start.isoformat()} to {end.isoformat()}"
    )


if __name__ == "__main__":
    main()
