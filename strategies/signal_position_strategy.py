from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models import (
    CandlePayload,
    Observation,
    ObservationKind,
    OrderIntent,
    OrderSide,
    OrderType,
    PricePayload,
    SignalDirection,
    SignalEvent,
)
from core.strategy import Strategy


@dataclass
class SignalPositionStrategy(Strategy):
    """Canonical Trader-side strategy: consumes SignalEvents, owns sizing only.

    It never computes indicators. LONG events move the position toward
    ``target_notional`` (clamped by risk_state ``max_notional``); FLAT/SHORT
    events close the position (long-only v1). By default strength acts as a
    filter via ``min_strength``; set ``size_by_strength=True`` to scale the
    target by strength instead. Order reasons chain the originating signal
    reason for attribution.
    """

    symbol: str
    target_notional: float = 10_000.0
    min_strength: float = 0.0
    min_confidence: float = 0.0
    size_by_strength: bool = False
    name: str = "signal_position"
    _pending_signal: SignalEvent | None = None
    _latest_price: float | None = None
    _latest_time: Any = None
    _seen_symbols: set[str] = field(default_factory=set)

    def on_observation(self, observation: Observation) -> None:
        if observation.subject != self.symbol:
            return
        price = _price_of(observation)
        if price is not None and price > 0:
            self._latest_price = price
            self._latest_time = observation.observed_at

    def on_signal(self, signal: SignalEvent) -> None:
        if signal.symbol != self.symbol:
            return
        if signal.strength < self.min_strength or signal.confidence < self.min_confidence:
            return
        self._pending_signal = signal

    def decide(self, portfolio: dict[str, Any], risk_state: dict[str, Any]) -> list[OrderIntent]:
        signal, self._pending_signal = self._pending_signal, None
        if signal is None:
            return []
        if risk_state.get("halted", False):
            return []
        allowed = risk_state.get("allowed_symbols")
        if allowed is not None and self.symbol not in allowed:
            return []
        if self._latest_price is None or self._latest_price <= 0:
            return []

        position = float(portfolio.get("positions", {}).get(self.symbol, 0.0))
        price = self._latest_price

        if signal.direction == SignalDirection.LONG:
            notional_cap = float(risk_state.get("max_notional", self.target_notional))
            target_value = self.target_notional
            if self.size_by_strength:
                target_value *= max(signal.strength, 0.0)
            target_value = min(target_value, notional_cap)
            target_quantity = target_value / price
            delta = target_quantity - position
            if delta > 0:
                side, quantity = OrderSide.BUY, delta
            elif delta < 0:
                side, quantity = OrderSide.SELL, -delta
            else:
                return []
        else:
            if position <= 0:
                return []
            side, quantity = OrderSide.SELL, position

        return [
            OrderIntent(
                symbol=self.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                reason=f"{self.name}:{signal.reason}",
                timestamp=self._latest_time or signal.timestamp,
                metadata={
                    "signal_reason": signal.reason,
                    "signal_strength": signal.strength,
                    "signal_confidence": signal.confidence,
                    "target_notional": self.target_notional,
                },
            )
        ]


def _price_of(observation: Observation) -> float | None:
    if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
        return observation.payload.close
    if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
        return observation.payload.price
    return None
