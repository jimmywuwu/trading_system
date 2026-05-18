from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import Observation, ObservationKind, PricePayload
from signals import TriangularArbitrageSignal


def main() -> None:
    observed_at = datetime.now(timezone.utc)
    observations = [
        Observation(
            observed_at=observed_at,
            occurred_at=observed_at,
            source="smoke",
            kind=ObservationKind.PRICE,
            symbol="BTC-USDT",
            payload=PricePayload(last=100_000),
        ),
        Observation(
            observed_at=observed_at,
            occurred_at=observed_at,
            source="smoke",
            kind=ObservationKind.PRICE,
            symbol="ETH-BTC",
            payload=PricePayload(last=0.05),
        ),
        Observation(
            observed_at=observed_at,
            occurred_at=observed_at,
            source="smoke",
            kind=ObservationKind.PRICE,
            symbol="ETH-USDT",
            payload=PricePayload(last=5_100),
        ),
    ]

    signal = TriangularArbitrageSignal(min_net_profit_pct=0.001).generate(observations)
    print(signal.reason if signal else "No actionable triangular arbitrage signal.")


if __name__ == "__main__":
    main()
