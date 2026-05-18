from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from providers import CoinbaseMinuteBitcoinPriceProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Coinbase BTC-USD one-minute candles as Observation JSONL.")
    parser.add_argument("--days", type=int, default=365, help="Number of days to fetch ending at now.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / "coinbase_btc_usd_1m_last_year.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between Coinbase API requests in seconds.")
    args = parser.parse_args()

    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=args.days)
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = CoinbaseMinuteBitcoinPriceProvider(request_delay_seconds=args.delay)
    count = 0
    first_observed_at = None
    last_observed_at = None

    with output_path.open("w", encoding="utf-8") as file:
        for observation in provider.iter_observations(start=start, end=end):
            count += 1
            first_observed_at = first_observed_at or observation.observed_at
            last_observed_at = observation.observed_at
            file.write(
                json.dumps(
                    {
                        "observed_at": observation.observed_at.isoformat(),
                        "occurred_at": observation.occurred_at.isoformat(),
                        "symbol": observation.symbol,
                        "source": observation.source,
                        "kind": observation.kind.value,
                        "payload": asdict(observation.payload),
                        "metadata": observation.metadata,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

            if count % 50_000 == 0:
                print(f"fetched={count} last_observed_at={last_observed_at.isoformat()}")

    print(f"output={output_path}")
    print(f"count={count}")
    print(f"first_observed_at={first_observed_at.isoformat() if first_observed_at else None}")
    print(f"last_observed_at={last_observed_at.isoformat() if last_observed_at else None}")
    print(f"requested_start={start.isoformat()}")
    print(f"requested_end={end.isoformat()}")


if __name__ == "__main__":
    main()
