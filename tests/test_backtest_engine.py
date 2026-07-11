from __future__ import annotations

from backtest import BacktestConfig, BacktestEngine, ReplayDataProvider
from research.benchmarks import buy_and_hold_metrics
from signals.sma_cross import SmaCrossSignal
from strategies.signal_position_strategy import SignalPositionStrategy
from tests.conftest import make_candles


def _trend_closes() -> list[float]:
    flat = [100.0] * 10
    up = [100.0 + 2 * i for i in range(1, 21)]
    down = [140.0 - 3 * i for i in range(1, 11)]
    return flat + up + down


def _build_engine(observations, risk_state=None):
    provider = ReplayDataProvider(observations)
    signal = SmaCrossSignal(symbol="BTC-USD", fast_window=3, slow_window=6)
    strategy = SignalPositionStrategy(symbol="BTC-USD", target_notional=10_000.0)
    config = BacktestConfig(initial_cash=10_000.0, fee_rate=0.001)
    if risk_state is not None:
        config.risk_state = risk_state
    return BacktestEngine(provider, strategy, signals=[signal], config=config)


def test_engine_end_to_end_produces_trades_and_metrics():
    observations = make_candles(_trend_closes())
    result = _build_engine(observations).run()

    assert result.metrics["num_trades"] >= 2
    assert result.signal_events, "expected at least one signal event"
    buys = [trade for trade in result.trades if trade["side"] == "buy"]
    sells = [trade for trade in result.trades if trade["side"] == "sell"]
    assert buys and sells
    # order reasons chain the signal reason for attribution
    assert all("sma_cross" in trade["reason"] for trade in result.trades)


def test_fills_happen_after_signal_bar():
    observations = make_candles(_trend_closes())
    result = _build_engine(observations).run()

    event_times = [event.timestamp for event in result.signal_events]
    first_trade_time = result.trades[0]["timestamp"]
    assert first_trade_time > min(event_times).isoformat()


def test_risk_halt_blocks_all_trading():
    observations = make_candles(_trend_closes())
    result = _build_engine(observations, risk_state={"halted": True}).run()
    assert result.trades == []


def test_engine_is_deterministic():
    observations = make_candles(_trend_closes())
    first = _build_engine(observations).run()
    second = _build_engine(observations).run()
    assert first.metrics == second.metrics
    assert first.trades == second.trades


def test_equity_curve_consistency():
    observations = make_candles(_trend_closes())
    result = _build_engine(observations).run()

    final_equity = result.equity_curve[-1][1]
    snapshot = result.portfolio.snapshot()
    assert abs(result.metrics["final_equity"] - final_equity) < 1e-9
    open_position = sum(snapshot["positions"].values())
    if open_position == 0:
        assert abs(snapshot["cash"] - final_equity) < 1e-9


def test_benchmark_runs_on_same_data():
    observations = make_candles(_trend_closes())
    metrics = buy_and_hold_metrics(observations, symbol="BTC-USD", initial_cash=10_000.0)
    assert metrics["benchmark"] == "buy_and_hold"
    assert metrics["num_trades"] == 2
