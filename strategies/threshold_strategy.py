from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models import OrderIntent, OrderSide, OrderType, SignalDirection, SignalEvent
from core.strategy import Strategy


@dataclass
class ThresholdStrategy(Strategy):
    name: str = "threshold_strategy"
    min_strength: float = 0.5
    default_quantity: float = 1.0
    order_type: OrderType = OrderType.MARKET
    _signals: list[SignalEvent] = field(default_factory=list)

    def on_signal(self, signal: SignalEvent) -> None:
        self._signals.append(signal)

    def decide(self, portfolio: dict[str, Any], risk_state: dict[str, Any]) -> list[OrderIntent]:
        if risk_state.get("halted", False):
            return []

        orders: list[OrderIntent] = []
        for signal in self._signals:
            if signal.strength < self.min_strength or signal.direction == SignalDirection.FLAT:
                continue

            side = OrderSide.BUY if signal.direction == SignalDirection.LONG else OrderSide.SELL
            quantity = float(signal.metadata.get("quantity", self.default_quantity))
            orders.append(
                OrderIntent(
                    symbol=signal.symbol,
                    side=side,
                    order_type=self.order_type,
                    quantity=quantity,
                    reason=signal.reason,
                    metadata={"signal": signal.metadata},
                )
            )

        self._signals.clear()
        return orders
