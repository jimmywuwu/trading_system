from __future__ import annotations

from core.models import OrderIntent, OrderSide, OrderType
from backtest.execution import SimulatedExecution
from tests.conftest import make_candles


def _market_order(side: OrderSide, quantity: float = 1.0) -> OrderIntent:
    return OrderIntent(
        symbol="BTC-USD",
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        reason="test",
    )


def test_market_order_fills_at_next_candle_open():
    candles = make_candles([100, 110, 120])
    execution = SimulatedExecution(fee_rate=0.001)
    execution.submit([_market_order(OrderSide.BUY)])

    # candle 1 opens at previous close (100 -> open 100), candle 2 open = 110
    fills = execution.on_observations([candles[1]], candles[1].observed_at)
    assert len(fills) == 1
    assert fills[0].price == 100  # candle[1] open equals candle[0] close
    assert fills[0].fee == 100 * 0.001
    assert execution.pending_orders == []


def test_market_order_slippage_direction():
    candles = make_candles([100, 100])
    execution = SimulatedExecution(fee_rate=0.0, slippage_bps=10)
    execution.submit([_market_order(OrderSide.BUY), _market_order(OrderSide.SELL)])

    fills = execution.on_observations([candles[1]], candles[1].observed_at)
    buy_fill = next(fill for fill in fills if fill.side == OrderSide.BUY)
    sell_fill = next(fill for fill in fills if fill.side == OrderSide.SELL)
    assert buy_fill.price > 100 > sell_fill.price


def test_limit_order_fills_only_on_touch():
    candles = make_candles([100, 90, 120])
    execution = SimulatedExecution(fee_rate=0.0)
    limit_buy = OrderIntent(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=95.0,
        reason="test",
    )
    execution.submit([limit_buy])

    # candle 1: open 100 close 90 -> low 90 <= 95 touches the limit
    fills = execution.on_observations([candles[1]], candles[1].observed_at)
    assert len(fills) == 1
    assert fills[0].price == 95.0


def test_limit_order_stays_pending_when_not_touched():
    candles = make_candles([100, 105])
    execution = SimulatedExecution()
    limit_buy = OrderIntent(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=1.0,
        price=95.0,
        reason="test",
    )
    execution.submit([limit_buy])

    fills = execution.on_observations([candles[1]], candles[1].observed_at)
    assert fills == []
    assert execution.pending_orders == [limit_buy]


def test_orders_ignore_other_symbols():
    candles = make_candles([100, 100], symbol="ETH-USD")
    execution = SimulatedExecution()
    execution.submit([_market_order(OrderSide.BUY)])

    fills = execution.on_observations([candles[1]], candles[1].observed_at)
    assert fills == []
    assert len(execution.pending_orders) == 1
