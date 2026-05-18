from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import ObservationKind
from providers import CoinbaseMinuteBitcoinPriceProvider


def fake_http_get(url: str, headers: dict[str, str]) -> dict:
    return {
        "candles": [
            {
                "start": "1710000000",
                "low": "68000.00",
                "high": "68100.00",
                "open": "68050.00",
                "close": "68075.00",
                "volume": "12.5",
            }
        ]
    }


def main() -> None:
    provider = CoinbaseMinuteBitcoinPriceProvider(http_get=fake_http_get)
    observations = provider.get_observations(
        start=datetime(2024, 3, 9, tzinfo=timezone.utc),
        end=datetime(2024, 3, 10, tzinfo=timezone.utc),
        kinds=[ObservationKind.CANDLE],
        subjects=["BTC-USD"],
    )
    observation = observations[0]
    print(observation.kind.value, observation.symbol, observation.payload.close)


if __name__ == "__main__":
    main()
