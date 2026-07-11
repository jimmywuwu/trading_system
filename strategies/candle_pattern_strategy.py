from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from core.models import CandlePayload, Observation, ObservationKind, OrderIntent, OrderSide, OrderType
from core.strategy import Strategy


@dataclass
class CandlePatternStrategy(Strategy):
    """Long-only candle pattern strategy for testing new Quant-generated alpha families."""

    symbol: str
    mode: str
    lookback_window: int = 240
    target_notional: float = 25_000.0
    trigger_multiplier: float = 2.0
    holding_period: int = 240
    stop_loss_pct: float = 0.015
    take_profit_pct: float = 0.03
    name: str = "candle_pattern"
    _candles: deque[CandlePayload] = field(default_factory=deque)
    _latest_observation: Observation | None = None
    _entry_price: float | None = None
    _bars_held: int = 0
    _pending_action: OrderSide | None = None
    _pending_reason: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"volume_surge_momentum", "range_expansion_reversal", "pullback_continuation"}:
            raise ValueError(f"unsupported candle pattern mode: {self.mode}")
        if self.lookback_window <= 1:
            raise ValueError("lookback_window must be greater than 1")
        if self.target_notional <= 0:
            raise ValueError("target_notional must be positive")
        if self.holding_period <= 0:
            raise ValueError("holding_period must be positive")

    def on_observation(self, observation: Observation) -> None:
        if observation.subject != self.symbol:
            return
        if observation.kind != ObservationKind.CANDLE or not isinstance(observation.payload, CandlePayload):
            return

        candle = observation.payload
        self._latest_observation = observation
        self._update_exit_state(candle.close)

        if self._entry_price is None and len(self._candles) >= self.lookback_window:
            if self.mode == "volume_surge_momentum" and self._volume_surge_momentum(candle):
                self._pending_action = OrderSide.BUY
                self._pending_reason = "volume_surge_momentum_entry"
            elif self.mode == "range_expansion_reversal" and self._range_expansion_reversal(candle):
                self._pending_action = OrderSide.BUY
                self._pending_reason = "range_expansion_reversal_entry"
            elif self.mode == "pullback_continuation" and self._pullback_continuation(candle):
                self._pending_action = OrderSide.BUY
                self._pending_reason = "pullback_continuation_entry"

        self._candles.append(candle)
        if len(self._candles) > self.lookback_window:
            self._candles.popleft()

    def decide(self, portfolio: dict[str, Any], risk_state: dict[str, Any]) -> list[OrderIntent]:
        if risk_state.get("halted", False) or self._pending_action is None:
            return []
        if self._latest_observation is None:
            return []

        candle = self._latest_observation.payload
        if not isinstance(candle, CandlePayload) or candle.close <= 0:
            return []

        position = float(portfolio.get("positions", {}).get(self.symbol, 0.0))
        action = self._pending_action
        reason = self._pending_reason or f"{self.mode}_signal"
        self._pending_action = None
        self._pending_reason = None

        if action == OrderSide.BUY:
            if position > 0:
                return []
            quantity = self.target_notional / candle.close
            self._entry_price = candle.close
            self._bars_held = 0
        else:
            quantity = max(position, 0.0)
            self._entry_price = None
            self._bars_held = 0

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
                    "mode": self.mode,
                    "lookback_window": self.lookback_window,
                    "target_notional": self.target_notional,
                    "trigger_multiplier": self.trigger_multiplier,
                    "holding_period": self.holding_period,
                    "stop_loss_pct": self.stop_loss_pct,
                    "take_profit_pct": self.take_profit_pct,
                },
            )
        ]

    def _update_exit_state(self, price: float) -> None:
        if self._entry_price is None:
            return
        self._bars_held += 1
        pnl_pct = price / self._entry_price - 1
        if pnl_pct <= -self.stop_loss_pct:
            self._pending_action = OrderSide.SELL
            self._pending_reason = f"{self.mode}_stop_loss"
        elif pnl_pct >= self.take_profit_pct:
            self._pending_action = OrderSide.SELL
            self._pending_reason = f"{self.mode}_take_profit"
        elif self._bars_held >= self.holding_period:
            self._pending_action = OrderSide.SELL
            self._pending_reason = f"{self.mode}_time_exit"

    def _volume_surge_momentum(self, candle: CandlePayload) -> bool:
        avg_volume = sum(item.volume for item in self._candles) / len(self._candles)
        return candle.close > candle.open and candle.volume > avg_volume * self.trigger_multiplier

    def _range_expansion_reversal(self, candle: CandlePayload) -> bool:
        avg_range = sum(item.high - item.low for item in self._candles) / len(self._candles)
        candle_range = candle.high - candle.low
        if candle_range <= 0:
            return False
        close_location = (candle.close - candle.low) / candle_range
        return candle_range > avg_range * self.trigger_multiplier and close_location < 0.25

    def _pullback_continuation(self, candle: CandlePayload) -> bool:
        closes = [item.close for item in self._candles]
        long_avg = sum(closes) / len(closes)
        short_count = min(30, len(closes))
        short_avg = sum(closes[-short_count:]) / short_count
        return candle.close > long_avg and candle.close < short_avg and candle.close < candle.open
