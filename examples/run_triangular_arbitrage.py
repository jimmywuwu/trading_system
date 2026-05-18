from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from execution import PaperBroker
from providers import JsonLinesTradeProvider
from signals import TriangularArbitrageSignal
from strategies import ThresholdStrategy
from core import ObservationKind


def main() -> None:
    data_path = Path("Output1.txt")
    if not data_path.exists():
        print("Output1.txt not found. Put a Coinbase JSONL capture in the repo root to run this example.")
        return

    provider = JsonLinesTradeProvider(data_path)
    symbols = ["BTC-USDT", "ETH-BTC", "ETH-USDT"]
    observations = [
        observation
        for symbol in symbols
        if (observation := provider.get_latest(symbol, ObservationKind.PRICE)) is not None
    ]

    signal = TriangularArbitrageSignal().generate(observations)
    if signal is None:
        print("No actionable triangular arbitrage signal.")
        return

    strategy = ThresholdStrategy(min_strength=0.5)
    strategy.on_signal(signal)

    orders = strategy.decide(portfolio={}, risk_state={})
    broker = PaperBroker()
    broker.submit_many(orders)

    for order in broker.orders:
        print(order)


if __name__ == "__main__":
    main()
