from __future__ import annotations

from typing import Any

from core.models import CandlePayload, Observation, ObservationKind
from backtest.metrics import compute_metrics


def buy_and_hold_metrics(
    observations: list[Observation],
    symbol: str,
    initial_cash: float = 100_000.0,
    fee_rate: float = 0.001,
) -> dict[str, Any]:
    """Buy-and-hold benchmark under the same fee assumptions.

    Buys at the first candle open (paying entry fee), marks to market at each
    close, sells at the last close (paying exit fee). Every strategy result
    must be compared against at least this benchmark before any conclusion.
    """
    candles = [
        obs
        for obs in sorted(observations, key=lambda item: item.observed_at)
        if obs.subject == symbol
        and obs.kind == ObservationKind.CANDLE
        and isinstance(obs.payload, CandlePayload)
    ]
    if len(candles) < 2:
        return {"error": "not enough candles for buy-and-hold benchmark"}

    entry_price = candles[0].payload.open  # type: ignore[union-attr]
    quantity = initial_cash / (entry_price * (1 + fee_rate))
    entry_fee = quantity * entry_price * fee_rate

    # First point is pre-entry cash so total_return includes the entry fee.
    equity_curve = [(candles[0].observed_at, initial_cash)]
    for obs in candles[1:]:
        close = obs.payload.close  # type: ignore[union-attr]
        equity_curve.append((obs.observed_at, quantity * close))

    exit_close = candles[-1].payload.close  # type: ignore[union-attr]
    exit_fee = quantity * exit_close * fee_rate
    equity_curve[-1] = (candles[-1].observed_at, quantity * exit_close - exit_fee)

    trades = [
        {
            "timestamp": candles[0].observed_at.isoformat(),
            "symbol": symbol,
            "side": "buy",
            "quantity": quantity,
            "price": entry_price,
            "notional": quantity * entry_price,
            "fee": entry_fee,
            "realized_pnl": 0.0,
            "reason": "benchmark_buy_and_hold_entry",
        },
        {
            "timestamp": candles[-1].observed_at.isoformat(),
            "symbol": symbol,
            "side": "sell",
            "quantity": quantity,
            "price": exit_close,
            "notional": quantity * exit_close,
            "fee": exit_fee,
            "realized_pnl": quantity * (exit_close - entry_price) - entry_fee - exit_fee,
            "reason": "benchmark_buy_and_hold_exit",
        },
    ]
    metrics = compute_metrics(equity_curve, trades, exposure_curve=[1.0] * len(equity_curve))
    metrics["benchmark"] = "buy_and_hold"
    return metrics
