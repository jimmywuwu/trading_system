from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models import OrderSide

from .execution import Fill


@dataclass
class Position:
    quantity: float = 0.0
    avg_cost: float = 0.0


@dataclass
class Portfolio:
    """Long-only cash/position accounting driven exclusively by fills."""

    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    trades: list[dict[str, Any]] = field(default_factory=list)

    def apply(self, fills: list[Fill]) -> None:
        for fill in fills:
            self._apply_fill(fill)

    def _apply_fill(self, fill: Fill) -> None:
        position = self.positions.setdefault(fill.symbol, Position())
        quantity = fill.quantity
        realized = 0.0

        if fill.side == OrderSide.BUY:
            affordable = self.cash / (fill.price * (1 + self.fee_rate_of(fill)))
            quantity = min(quantity, max(affordable, 0.0))
            if quantity <= 0:
                return
            notional = quantity * fill.price
            fee = notional * self.fee_rate_of(fill)
            total_cost = position.avg_cost * position.quantity + notional
            position.quantity += quantity
            position.avg_cost = total_cost / position.quantity if position.quantity > 0 else 0.0
            self.cash -= notional + fee
        else:
            quantity = min(quantity, position.quantity)
            if quantity <= 0:
                return
            notional = quantity * fill.price
            fee = notional * self.fee_rate_of(fill)
            realized = (fill.price - position.avg_cost) * quantity - fee
            position.quantity -= quantity
            if position.quantity <= 0:
                position.quantity = 0.0
                position.avg_cost = 0.0
            self.cash += notional - fee
            self.realized_pnl += realized

        self.fees_paid += fee
        self.trades.append(
            {
                "timestamp": fill.timestamp.isoformat(),
                "symbol": fill.symbol,
                "side": fill.side.value,
                "quantity": quantity,
                "price": fill.price,
                "notional": notional,
                "fee": fee,
                "realized_pnl": realized,
                "reason": fill.order.reason,
            }
        )

    @staticmethod
    def fee_rate_of(fill: Fill) -> float:
        if fill.quantity <= 0 or fill.price <= 0:
            return 0.0
        return fill.fee / (fill.quantity * fill.price)

    def equity(self, prices: dict[str, float]) -> float:
        value = self.cash
        for symbol, position in self.positions.items():
            if position.quantity > 0:
                value += position.quantity * prices.get(symbol, position.avg_cost)
        return value

    def exposure(self, prices: dict[str, float]) -> float:
        equity = self.equity(prices)
        if equity <= 0:
            return 0.0
        held = sum(
            position.quantity * prices.get(symbol, position.avg_cost)
            for symbol, position in self.positions.items()
        )
        return held / equity

    def snapshot(self) -> dict[str, Any]:
        """Dict view used by Strategy.decide(); keeps the existing contract."""
        return {
            "cash": self.cash,
            "positions": {symbol: pos.quantity for symbol, pos in self.positions.items()},
            "avg_costs": {symbol: pos.avg_cost for symbol, pos in self.positions.items()},
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
        }
