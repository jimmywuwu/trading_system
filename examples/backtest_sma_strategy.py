from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import CandlePayload, Observation, ObservationKind, OrderIntent, OrderSide, PricePayload
from providers import JsonLinesObservationProvider
from strategies import SmaCrossoverStrategy


@dataclass
class SimplePortfolio:
    cash: float
    fee_rate: float = 0.001
    positions: dict[str, float] = field(default_factory=dict)
    fees_paid: float = 0.0
    trades: list[dict[str, float | str]] = field(default_factory=list)

    def snapshot(self) -> dict[str, object]:
        return {"cash": self.cash, "positions": dict(self.positions), "fees_paid": self.fees_paid}

    def fill(self, order: OrderIntent, price: float) -> None:
        notional = order.quantity * price
        fee = notional * self.fee_rate

        if order.side == OrderSide.BUY:
            total_cost = notional + fee
            if total_cost > self.cash:
                quantity = self.cash / (price * (1 + self.fee_rate))
                notional = quantity * price
                fee = notional * self.fee_rate
            else:
                quantity = order.quantity
            self.cash -= notional + fee
            self.positions[order.symbol] = self.positions.get(order.symbol, 0.0) + quantity
        else:
            current_position = self.positions.get(order.symbol, 0.0)
            quantity = min(order.quantity, current_position)
            notional = quantity * price
            fee = notional * self.fee_rate
            self.cash += notional - fee
            self.positions[order.symbol] = current_position - quantity

        self.fees_paid += fee
        self.trades.append(
            {
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": quantity,
                "price": price,
                "notional": notional,
                "fee": fee,
            }
        )

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + sum(quantity * prices.get(symbol, 0.0) for symbol, quantity in self.positions.items())


def main() -> None:
    data_path = Path("data/coinbase_btc_usd_1m_last_year.jsonl")
    symbol = "BTC-USD"
    initial_cash = 100_000.0

    provider = JsonLinesObservationProvider(data_path)
    observations = provider.get_observations(kinds=[ObservationKind.CANDLE], subjects=[symbol])

    strategy = SmaCrossoverStrategy(
        symbol=symbol,
        fast_window=4_320,
        slow_window=20_160,
        target_notional=50_000.0,
    )
    portfolio = SimplePortfolio(cash=initial_cash, fee_rate=0.001)

    pending_orders: list[OrderIntent] = []
    latest_prices: dict[str, float] = {}
    equity_curve: list[tuple[str, float]] = []

    for observation in observations:
        # 更新成交 order intent
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
        equity_curve.append((observation.observed_at.isoformat(), portfolio.equity(latest_prices)))

    final_equity = equity_curve[-1][1]
    total_return = final_equity / initial_cash - 1
    max_drawdown = calculate_max_drawdown([equity for _, equity in equity_curve])

    print("SMA Crossover Backtest")
    print(f"data: {data_path}")
    print(f"symbol: {symbol}")
    print(f"period: {equity_curve[0][0]} -> {equity_curve[-1][0]}")
    print(f"fast_sma: {strategy.fast_window}")
    print(f"slow_sma: {strategy.slow_window}")
    print(f"initial_cash: {initial_cash:,.2f}")
    print(f"final_equity: {final_equity:,.2f}")
    print(f"total_return: {total_return:.2%}")
    print(f"max_drawdown: {max_drawdown:.2%}")
    print(f"trades: {len(portfolio.trades)}")
    print(f"fees_paid: {portfolio.fees_paid:,.2f}")
    print(f"cash: {portfolio.cash:,.2f}")
    print(f"position_{symbol}: {portfolio.positions.get(symbol, 0.0):.8f}")


def observation_fill_price(observation: Observation) -> float | None:
    if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
        return observation.payload.open
    if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
        return observation.payload.price
    return None


def observation_mark_price(observation: Observation) -> float | None:
    if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
        return observation.payload.close
    if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
        return observation.payload.price
    return None


def calculate_max_drawdown(values: list[float]) -> float:
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return max_drawdown


if __name__ == "__main__":
    main()
