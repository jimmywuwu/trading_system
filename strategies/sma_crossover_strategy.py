from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from core.models import CandlePayload, Observation, ObservationKind, OrderIntent, OrderSide, OrderType, PricePayload
from core.strategy import Strategy


@dataclass
class SmaCrossoverStrategy(Strategy):
    """Buys when fast SMA crosses above slow SMA and exits on the reverse cross."""

    symbol: str
    fast_window: int = 20
    slow_window: int = 100
    target_notional: float = 10_000.0
    name: str = "sma_crossover"
    _fast_closes: deque[float] = field(default_factory=deque)
    _slow_closes: deque[float] = field(default_factory=deque)
    _fast_sum: float = 0.0
    _slow_sum: float = 0.0
    _latest_observation: Observation | None = None
    _previous_spread: float | None = None
    _pending_action: OrderSide | None = None

    def __post_init__(self) -> None:
        if self.fast_window <= 0:
            raise ValueError("fast_window must be positive")
        if self.slow_window <= 0:
            raise ValueError("slow_window must be positive")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")
        if self.target_notional <= 0:
            raise ValueError("target_notional must be positive")

    def on_observation(self, observation: Observation) -> None:
        if observation.subject != self.symbol:
            return
        price = self._price(observation)
        if price is None:
            return

        self._latest_observation = observation
        self._fast_sum = self._append_price(self._fast_closes, self._fast_sum, price, self.fast_window)
        self._slow_sum = self._append_price(self._slow_closes, self._slow_sum, price, self.slow_window)

        if len(self._slow_closes) < self.slow_window:
            return

        fast_sma = self._fast_sum / self.fast_window
        slow_sma = self._slow_sum / self.slow_window
        spread = fast_sma - slow_sma

        if self._previous_spread is not None:
            if self._previous_spread <= 0 < spread:
                self._pending_action = OrderSide.BUY
            elif self._previous_spread >= 0 > spread:
                self._pending_action = OrderSide.SELL

        self._previous_spread = spread

    def decide(self, portfolio: dict[str, Any], risk_state: dict[str, Any]) -> list[OrderIntent]:
        if risk_state.get("halted", False) or self._pending_action is None:
            return []
        if self._latest_observation is None:
            return []

        price = self._price(self._latest_observation)
        if price is None or price <= 0:
            return []

        position = float(portfolio.get("positions", {}).get(self.symbol, 0.0))
        action = self._pending_action
        self._pending_action = None

        if action == OrderSide.BUY:
            target_quantity = self.target_notional / price
            quantity = max(target_quantity - position, 0.0)
            reason = f"sma_cross_up_{self.fast_window}_{self.slow_window}"
        else:
            quantity = max(position, 0.0)
            reason = f"sma_cross_down_{self.fast_window}_{self.slow_window}"

        if quantity <= 0:
            return []

        return [
            OrderIntent(
                symbol=self.symbol,
                side=action,
                order_type=OrderType.MARKET,
                quantity=quantity,
                reason=reason,
                timestamp=self._latest_observation.observed_at,
                metadata={
                    "fast_window": self.fast_window,
                    "slow_window": self.slow_window,
                    "target_notional": self.target_notional,
                },
            )
        ]

    @staticmethod
    def _price(observation: Observation) -> float | None:
        if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
            return observation.payload.close
        if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
            return observation.payload.price
        return None

    @staticmethod
    def _append_price(values: deque[float], total: float, price: float, window: int) -> float:
        values.append(price)
        total += price
        if len(values) > window:
            total -= values.popleft()
        return total
