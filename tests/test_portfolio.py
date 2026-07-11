from __future__ import annotations

from datetime import datetime, timezone

from core.models import OrderIntent, OrderSide, OrderType
from backtest.execution import Fill
from backtest.portfolio import Portfolio


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fill(side: OrderSide, quantity: float, price: float, fee_rate: float = 0.001) -> Fill:
    order = OrderIntent(
        symbol="BTC-USD",
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        reason="test",
    )
    return Fill(order=order, price=price, quantity=quantity, fee=price * quantity * fee_rate, timestamp=NOW)


def test_buy_updates_cash_position_and_fees():
    portfolio = Portfolio(cash=10_000.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0)])

    assert portfolio.positions["BTC-USD"].quantity == 1.0
    assert portfolio.positions["BTC-USD"].avg_cost == 100.0
    assert portfolio.cash == 10_000.0 - 100.0 - 0.1
    assert portfolio.fees_paid == 0.1


def test_sell_realizes_pnl_net_of_fees():
    portfolio = Portfolio(cash=10_000.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0)])
    portfolio.apply([_fill(OrderSide.SELL, quantity=1.0, price=110.0)])

    assert portfolio.positions["BTC-USD"].quantity == 0.0
    expected_realized = (110.0 - 100.0) * 1.0 - 110.0 * 0.001
    assert abs(portfolio.realized_pnl - expected_realized) < 1e-9
    assert abs(portfolio.cash - (10_000.0 - 100.1 + 110.0 - 0.11)) < 1e-9


def test_buy_is_clamped_to_available_cash():
    portfolio = Portfolio(cash=50.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0)])

    quantity = portfolio.positions["BTC-USD"].quantity
    assert 0 < quantity < 1.0
    assert portfolio.cash >= -1e-9


def test_sell_is_clamped_to_position():
    portfolio = Portfolio(cash=1_000.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0)])
    portfolio.apply([_fill(OrderSide.SELL, quantity=5.0, price=100.0)])

    assert portfolio.positions["BTC-USD"].quantity == 0.0
    sells = [trade for trade in portfolio.trades if trade["side"] == "sell"]
    assert sells[0]["quantity"] == 1.0


def test_average_cost_across_multiple_buys():
    portfolio = Portfolio(cash=100_000.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0, fee_rate=0.0)])
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=200.0, fee_rate=0.0)])

    assert portfolio.positions["BTC-USD"].avg_cost == 150.0


def test_equity_and_exposure():
    portfolio = Portfolio(cash=1_000.0)
    portfolio.apply([_fill(OrderSide.BUY, quantity=1.0, price=100.0, fee_rate=0.0)])

    prices = {"BTC-USD": 120.0}
    assert portfolio.equity(prices) == 900.0 + 120.0
    assert abs(portfolio.exposure(prices) - 120.0 / 1_020.0) < 1e-9
