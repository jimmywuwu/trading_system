from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from core.models import CandlePayload, Observation, ObservationKind, OrderIntent, OrderSide, OrderType, PricePayload
from core.strategy import Strategy


@dataclass
class BollingerBandMeanReversionStrategy(Strategy):
    """Long-only Bollinger Band mean-reversion baseline."""

    symbol: str
    window: int = 20
    num_stddev: float = 2.0
    target_notional: float = 10_000.0
    name: str = "bollinger_band_mean_reversion"
    _closes: deque[float] = field(default_factory=deque)
    _sum: float = 0.0
    _sum_squares: float = 0.0
    _latest_observation: Observation | None = None
    _pending_action: OrderSide | None = None
    _was_below_lower: bool = False
    _is_long_signal: bool = False

    def __post_init__(self) -> None:
        if self.window <= 1:
            raise ValueError("window must be greater than 1")
        if self.num_stddev <= 0:
            raise ValueError("num_stddev must be positive")
        if self.target_notional <= 0:
            raise ValueError("target_notional must be positive")

    def on_observation(self, observation: Observation) -> None:
        if observation.subject != self.symbol:
            return
        price = self._price(observation)
        if price is None:
            return

        self._latest_observation = observation
        self._append_price(price)
        if len(self._closes) < self.window:
            return

        middle = self._sum / self.window
        variance = max(self._sum_squares / self.window - middle * middle, 0.0)
        band_width = self.num_stddev * sqrt(variance)
        lower = middle - band_width

        if price < lower and not self._is_long_signal:
            self._pending_action = OrderSide.BUY
            self._is_long_signal = True
            self._was_below_lower = True
        elif self._is_long_signal and price >= middle:
            self._pending_action = OrderSide.SELL
            self._is_long_signal = False
            self._was_below_lower = False

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
            reason = f"bb_mean_reversion_entry_{self.window}_{self.num_stddev:g}"
        else:
            quantity = max(position, 0.0)
            reason = f"bb_mean_reversion_exit_{self.window}_{self.num_stddev:g}"

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
                    "window": self.window,
                    "num_stddev": self.num_stddev,
                    "target_notional": self.target_notional,
                },
            )
        ]

    def _append_price(self, price: float) -> None:
        self._closes.append(price)
        self._sum += price
        self._sum_squares += price * price
        if len(self._closes) > self.window:
            removed = self._closes.popleft()
            self._sum -= removed
            self._sum_squares -= removed * removed

    @staticmethod
    def _price(observation: Observation) -> float | None:
        if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
            return observation.payload.close
        if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
            return observation.payload.price
        return None
