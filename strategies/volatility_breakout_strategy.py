from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from core.models import CandlePayload, Observation, ObservationKind, OrderIntent, OrderSide, OrderType, PricePayload
from core.strategy import Strategy


@dataclass
class VolatilityBreakoutStrategy(Strategy):
    """Long-only breakout strategy gated by realized volatility."""

    symbol: str
    breakout_window: int = 240
    volatility_window: int = 120
    max_realized_volatility: float = 0.0025
    target_notional: float = 10_000.0
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    name: str = "volatility_breakout"
    _closes: deque[float] = field(default_factory=deque)
    _returns: deque[float] = field(default_factory=deque)
    _latest_observation: Observation | None = None
    _previous_price: float | None = None
    _entry_price: float | None = None
    _pending_action: OrderSide | None = None
    _pending_reason: str | None = None

    def __post_init__(self) -> None:
        if self.breakout_window <= 1:
            raise ValueError("breakout_window must be greater than 1")
        if self.volatility_window <= 1:
            raise ValueError("volatility_window must be greater than 1")
        if self.target_notional <= 0:
            raise ValueError("target_notional must be positive")
        if self.stop_loss_pct <= 0:
            raise ValueError("stop_loss_pct must be positive")
        if self.take_profit_pct <= 0:
            raise ValueError("take_profit_pct must be positive")

    def on_observation(self, observation: Observation) -> None:
        if observation.subject != self.symbol:
            return
        price = self._price(observation)
        if price is None or price <= 0:
            return

        self._latest_observation = observation
        prior_high = max(self._closes) if len(self._closes) >= self.breakout_window else None

        if self._previous_price is not None and self._previous_price > 0:
            self._returns.append(price / self._previous_price - 1)
            if len(self._returns) > self.volatility_window:
                self._returns.popleft()
        self._previous_price = price

        self._closes.append(price)
        if len(self._closes) > self.breakout_window:
            self._closes.popleft()

        if len(self._returns) < self.volatility_window or prior_high is None:
            return

        realized_volatility = self._realized_volatility()
        if self._entry_price is not None:
            pnl_pct = price / self._entry_price - 1
            if pnl_pct <= -self.stop_loss_pct:
                self._pending_action = OrderSide.SELL
                self._pending_reason = "volatility_breakout_stop_loss"
            elif pnl_pct >= self.take_profit_pct:
                self._pending_action = OrderSide.SELL
                self._pending_reason = "volatility_breakout_take_profit"
            return

        if price > prior_high and realized_volatility <= self.max_realized_volatility:
            self._pending_action = OrderSide.BUY
            self._pending_reason = "volatility_breakout_entry"

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
        reason = self._pending_reason or "volatility_breakout"
        self._pending_action = None
        self._pending_reason = None

        if action == OrderSide.BUY:
            if position > 0:
                return []
            quantity = self.target_notional / price
            self._entry_price = price
        else:
            quantity = max(position, 0.0)
            self._entry_price = None

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
                    "breakout_window": self.breakout_window,
                    "volatility_window": self.volatility_window,
                    "max_realized_volatility": self.max_realized_volatility,
                    "target_notional": self.target_notional,
                    "stop_loss_pct": self.stop_loss_pct,
                    "take_profit_pct": self.take_profit_pct,
                },
            )
        ]

    def _realized_volatility(self) -> float:
        mean_return = sum(self._returns) / len(self._returns)
        variance = sum((item - mean_return) ** 2 for item in self._returns) / len(self._returns)
        return sqrt(max(variance, 0.0))

    @staticmethod
    def _price(observation: Observation) -> float | None:
        if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
            return observation.payload.close
        if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
            return observation.payload.price
        return None
