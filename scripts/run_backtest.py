"""Run a point-in-time backtest with the canonical Signal -> Strategy slice.

Usage:
    python3 scripts/run_backtest.py --data data/coinbase_btc_usd_1m_last_year.jsonl \
        --symbol BTC-USD --fast 240 --slow 1440 --notional 50000 [--max-lines 100000] \
        [--report reports/backtests/my_run.md]

Always prints the buy-and-hold benchmark next to the strategy result; a
strategy result without its benchmark is not a result.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest import BacktestConfig, BacktestEngine, ReplayDataProvider
from core.models import ObservationKind
from providers.file_provider import JsonLinesObservationProvider
from research.benchmarks import buy_and_hold_metrics
from signals.sma_cross import SmaCrossSignal
from strategies.signal_position_strategy import SignalPositionStrategy


def load_observations(path: Path, symbol: str, max_lines: int | None):
    if max_lines is None:
        provider = JsonLinesObservationProvider(path)
        return provider.get_observations(kinds=[ObservationKind.CANDLE], subjects=[symbol])

    import tempfile

    with path.open("r", encoding="utf-8") as source:
        head = list(itertools.islice(source, max_lines))
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp.writelines(head)
        tmp_path = Path(tmp.name)
    try:
        provider = JsonLinesObservationProvider(tmp_path)
        return provider.get_observations(kinds=[ObservationKind.CANDLE], subjects=[symbol])
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--fast", type=int, default=240)
    parser.add_argument("--slow", type=int, default=1440)
    parser.add_argument("--notional", type=float, default=50_000.0)
    parser.add_argument("--cash", type=float, default=100_000.0)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--max-lines", type=int, default=None, help="limit input lines for quick runs")
    parser.add_argument("--report", type=Path, default=None, help="write a markdown report here")
    args = parser.parse_args()

    observations = load_observations(args.data, args.symbol, args.max_lines)
    if not observations:
        raise SystemExit(f"no candle observations for {args.symbol} in {args.data}")

    engine = BacktestEngine(
        provider=ReplayDataProvider(observations),
        strategy=SignalPositionStrategy(symbol=args.symbol, target_notional=args.notional),
        signals=[SmaCrossSignal(symbol=args.symbol, fast_window=args.fast, slow_window=args.slow)],
        config=BacktestConfig(
            initial_cash=args.cash,
            fee_rate=args.fee_rate,
            slippage_bps=args.slippage_bps,
        ),
    )
    result = engine.run()
    benchmark = buy_and_hold_metrics(
        observations, symbol=args.symbol, initial_cash=args.cash, fee_rate=args.fee_rate
    )

    print(json.dumps({"strategy": result.metrics, "benchmark": benchmark}, indent=2, default=str))

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        body = result.to_markdown(title=f"SMA cross {args.fast}/{args.slow} on {args.symbol}")
        body += "\n## Benchmark: buy and hold\n\n"
        for key, value in benchmark.items():
            body += f"- **{key}**: {value}\n"
        args.report.write_text(body, encoding="utf-8")
        print(f"report written to {args.report}")


if __name__ == "__main__":
    main()
