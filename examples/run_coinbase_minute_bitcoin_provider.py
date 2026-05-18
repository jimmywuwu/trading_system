from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from providers import CoinbaseMinuteBitcoinPriceProvider


def main() -> None:
    provider = CoinbaseMinuteBitcoinPriceProvider()
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=5)
    observations = provider.get_observations(start=start, end=end)

    for observation in observations[-5:]:
        candle = observation.payload
        print(
            observation.symbol,
            observation.occurred_at.isoformat(),
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )


if __name__ == "__main__":
    main()
