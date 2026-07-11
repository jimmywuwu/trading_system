from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from core.models import (
    CandlePayload,
    Observation,
    ObservationKind,
    SignalDirection,
    SignalEvent,
)
from core.signal import Signal


@dataclass
class SmaCrossSignal(Signal):
    """Emits LONG on fast/slow SMA cross up and FLAT on cross down.

    Stateful incremental signal: the engine feeds each replay tick's new
    observations to ``generate()``; rolling SMA state lives inside the signal.
    Reason codes: ``sma_cross_up``, ``sma_cross_down``.
    """

    symbol: str
    fast_window: int = 20
    slow_window: int = 100
    name: str = "sma_cross"
    _closes: deque[float] = field(default_factory=deque)
    _fast_sum: float = 0.0
    _slow_sum: float = 0.0
    _previous_spread: float | None = None

    def __post_init__(self) -> None:
        if self.fast_window <= 0 or self.slow_window <= 0:
            raise ValueError("windows must be positive")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

    def generate(self, observations: list[Observation] | dict[str, Observation]) -> SignalEvent | None:
        if isinstance(observations, dict):
            observations = list(observations.values())

        event: SignalEvent | None = None
        for observation in observations:
            if observation.subject != self.symbol:
                continue
            if observation.kind != ObservationKind.CANDLE:
                continue
            payload = observation.payload
            if not isinstance(payload, CandlePayload):
                continue
            event = self._update(payload.close, observation) or event
        return event

    def _update(self, close: float, observation: Observation) -> SignalEvent | None:
        self._closes.append(close)
        self._fast_sum += close
        self._slow_sum += close
        if len(self._closes) > self.fast_window:
            self._fast_sum -= self._closes[-self.fast_window - 1]
        if len(self._closes) > self.slow_window:
            self._slow_sum -= self._closes[0]
            self._closes.popleft()

        if len(self._closes) < self.slow_window:
            return None

        fast_sma = self._fast_sum / self.fast_window
        slow_sma = self._slow_sum / self.slow_window
        spread = fast_sma - slow_sma
        previous = self._previous_spread
        self._previous_spread = spread

        if previous is None:
            return None

        direction: SignalDirection | None = None
        reason = ""
        if previous <= 0 < spread:
            direction, reason = SignalDirection.LONG, "sma_cross_up"
        elif previous >= 0 > spread:
            direction, reason = SignalDirection.FLAT, "sma_cross_down"
        if direction is None:
            return None

        strength = min(abs(spread) / slow_sma * 100, 1.0) if slow_sma > 0 else 0.0
        return SignalEvent(
            symbol=self.symbol,
            direction=direction,
            strength=strength,
            confidence=1.0,
            reason=reason,
            timestamp=observation.observed_at,
            metadata={
                "fast_window": self.fast_window,
                "slow_window": self.slow_window,
                "fast_sma": fast_sma,
                "slow_sma": slow_sma,
                "close": close,
            },
        )
