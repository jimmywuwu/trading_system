from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import CandlePayload, ObservationKind
from examples.backtest_sma_strategy import (
    SimplePortfolio,
    calculate_max_drawdown,
    observation_fill_price,
    observation_mark_price,
)
from providers import JsonLinesObservationProvider
from strategies import SmaCrossoverStrategy


SYMBOL = "BTC-USD"
INITIAL_CASH = 100_000.0
TARGET_NOTIONAL = 50_000.0
FEE_RATE = 0.001

FAST_WINDOWS = [60, 180, 360, 720, 1_440, 2_880, 4_320]
SLOW_WINDOWS = [720, 1_440, 2_880, 4_320, 10_080, 20_160, 43_200]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate SMA parameters with a train/test split.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/coinbase_btc_usd_1m_last_year.jsonl"),
        help="Observation JSONL data path.",
    )
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Fraction of observations used for training.")
    args = parser.parse_args()

    if not 0 < args.train_ratio < 1:
        raise ValueError("--train-ratio must be between 0 and 1")

    provider = JsonLinesObservationProvider(args.data)
    observations = [
        observation
        for observation in provider.get_observations(kinds=[ObservationKind.CANDLE], subjects=[SYMBOL])
        if isinstance(observation.payload, CandlePayload)
    ]

    split_index = int(len(observations) * args.train_ratio)
    train_observations = observations[:split_index]
    test_observations = observations[split_index:]

    train_results = []
    for fast_window in FAST_WINDOWS:
        for slow_window in SLOW_WINDOWS:
            if fast_window >= slow_window or slow_window >= len(train_observations):
                continue
            train_results.append(run_backtest(train_observations, fast_window, slow_window))

    train_results.sort(key=lambda result: (result["return"], result["max_drawdown"]), reverse=True)

    print(f"data: {args.data}")
    print(f"bars: total={len(observations)} train={len(train_observations)} test={len(test_observations)}")
    print(f"train_period: {train_observations[0].observed_at.isoformat()} -> {train_observations[-1].observed_at.isoformat()}")
    print(f"test_period: {test_observations[0].observed_at.isoformat()} -> {test_observations[-1].observed_at.isoformat()}")
    print()
    print("Top train params and continuous out-of-sample test")
    print(
        "rank fast  slow  train_ret train_mdd train_trades | "
        "test_ret test_mdd test_trades test_start_eq test_end_eq"
    )

    for rank, train_result in enumerate(train_results[:10], start=1):
        test_result = run_continuous_test(
            observations,
            split_index,
            int(train_result["fast"]),
            int(train_result["slow"]),
        )
        print(
            f"{rank:>4d} {int(train_result['fast']):5d} {int(train_result['slow']):5d} "
            f"{train_result['return']:9.2%} {train_result['max_drawdown']:9.2%} "
            f"{int(train_result['trades']):12d} | "
            f"{test_result['return']:8.2%} {test_result['max_drawdown']:8.2%} "
            f"{int(test_result['trades']):11d} "
            f"{test_result['start_equity']:13.2f} {test_result['final_equity']:11.2f}"
        )

    print()
    print("BTC buy-and-hold benchmark")
    print(f"train_bh: {buy_and_hold_return(train_observations):.2%}")
    print(f"test_bh: {buy_and_hold_return(test_observations):.2%}")
    print(f"full_bh: {buy_and_hold_return(observations):.2%}")


def run_backtest(observations: list, fast_window: int, slow_window: int) -> dict[str, float]:
    strategy = SmaCrossoverStrategy(
        symbol=SYMBOL,
        fast_window=fast_window,
        slow_window=slow_window,
        target_notional=TARGET_NOTIONAL,
    )
    portfolio = SimplePortfolio(cash=INITIAL_CASH, fee_rate=FEE_RATE)
    pending_orders = []
    latest_prices = {}
    equity_values = []

    for observation in observations:
        fill_price = observation_fill_price(observation)
        if fill_price is not None:
            for order in pending_orders:
                portfolio.fill(order, fill_price)
            pending_orders.clear()

        mark_price = observation_mark_price(observation)
        if mark_price is None:
            continue

        latest_prices[observation.subject] = mark_price
        strategy.on_observation(observation)
        pending_orders.extend(strategy.decide(portfolio.snapshot(), risk_state={"halted": False}))
        equity_values.append(portfolio.equity(latest_prices))

    final_equity = equity_values[-1]
    return {
        "fast": float(fast_window),
        "slow": float(slow_window),
        "final_equity": final_equity,
        "return": final_equity / INITIAL_CASH - 1,
        "max_drawdown": calculate_max_drawdown(equity_values),
        "trades": float(len(portfolio.trades)),
        "fees": portfolio.fees_paid,
    }


def run_continuous_test(
    observations: list,
    split_index: int,
    fast_window: int,
    slow_window: int,
) -> dict[str, float]:
    strategy = SmaCrossoverStrategy(
        symbol=SYMBOL,
        fast_window=fast_window,
        slow_window=slow_window,
        target_notional=TARGET_NOTIONAL,
    )
    portfolio = SimplePortfolio(cash=INITIAL_CASH, fee_rate=FEE_RATE)
    pending_orders = []
    latest_prices = {}
    test_equity_values = []
    start_equity = None
    test_trades = 0

    for index, observation in enumerate(observations):
        fill_price = observation_fill_price(observation)
        if fill_price is not None:
            trades_before_fill = len(portfolio.trades)
            for order in pending_orders:
                portfolio.fill(order, fill_price)
            pending_orders.clear()
            if index >= split_index:
                test_trades += len(portfolio.trades) - trades_before_fill

        mark_price = observation_mark_price(observation)
        if mark_price is None:
            continue

        latest_prices[observation.subject] = mark_price
        strategy.on_observation(observation)
        pending_orders.extend(strategy.decide(portfolio.snapshot(), risk_state={"halted": False}))

        equity = portfolio.equity(latest_prices)
        if index == split_index:
            start_equity = equity
        if index >= split_index:
            test_equity_values.append(equity)

    if start_equity is None:
        raise ValueError("split_index did not produce a test equity value")

    final_equity = test_equity_values[-1]
    return {
        "fast": float(fast_window),
        "slow": float(slow_window),
        "start_equity": start_equity,
        "final_equity": final_equity,
        "return": final_equity / start_equity - 1,
        "max_drawdown": calculate_max_drawdown(test_equity_values),
        "trades": float(test_trades),
    }


def buy_and_hold_return(observations: list) -> float:
    return observations[-1].payload.close / observations[0].payload.close - 1


if __name__ == "__main__":
    main()
