from __future__ import annotations

import bisect
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.models import (
    Observation,
    ObservationKind,
    OpenInterestPayload,
    SignalDirection,
    SignalEvent,
)
from core.signal import Signal


@dataclass
class OiContractionVolRegimeSignal(Signal):
    """Risk-regime signal: sharp 4h open-interest contraction warns of
    volatility expansion over the next 4-24h.

    Contract: reports/research/oi-contraction-vol-regime/signal_contract.md
    Direction is always FLAT — this is a volatility warning, not a
    directional signal. Edge-triggered with hysteresis: fires when the 4h
    OI change (in raw contracts) enters the bottom ``trigger_percentile``
    of its rolling distribution, re-arms above ``rearm_percentile``.
    """

    symbol: str
    change_window: timedelta = timedelta(hours=4)
    history_window: timedelta = timedelta(days=14)
    min_history: int = 300
    trigger_percentile: float = 0.10
    rearm_percentile: float = 0.20
    newest_stale_tolerance: timedelta = timedelta(minutes=30)
    reference_tolerance: timedelta = timedelta(minutes=45)
    name: str = "oi_contraction_vol_regime"

    _samples: deque[tuple[datetime, float]] = field(default_factory=deque)
    _changes: deque[tuple[datetime, float]] = field(default_factory=deque)
    _sorted_changes: list[float] = field(default_factory=list)
    _armed: bool = True

    def __post_init__(self) -> None:
        if not 0 < self.trigger_percentile < self.rearm_percentile < 1:
            raise ValueError("require 0 < trigger_percentile < rearm_percentile < 1")
        if self.min_history < 10:
            raise ValueError("min_history must be at least 10")

    def generate(self, observations: list[Observation] | dict[str, Observation]) -> SignalEvent | None:
        if isinstance(observations, dict):
            observations = list(observations.values())

        event: SignalEvent | None = None
        for observation in observations:
            if observation.subject != self.symbol:
                continue
            if observation.kind != ObservationKind.PERP_OPEN_INTEREST:
                continue
            payload = observation.payload
            if not isinstance(payload, OpenInterestPayload):
                continue
            try:
                oi_value = float(payload.open_interest_raw)
            except (TypeError, ValueError):
                continue
            if oi_value <= 0:
                continue
            event = self._update(observation.observed_at, oi_value, observation) or event
        return event

    def _update(self, now: datetime, oi_value: float, observation: Observation) -> SignalEvent | None:
        self._samples.append((now, oi_value))
        # keep samples covering change_window plus tolerance
        horizon = now - self.change_window - self.reference_tolerance
        while self._samples and self._samples[0][0] < horizon:
            self._samples.popleft()

        reference = self._reference_sample(now)
        if reference is None:
            return None
        ref_time, ref_value = reference

        change = oi_value / ref_value - 1
        pct_rank = self._percentile_rank(change)
        self._record_change(now, change)

        if pct_rank is None:
            return None

        if not self._armed:
            if pct_rank > self.rearm_percentile:
                self._armed = True
            return None

        # contraction event requires an actual decline, not just a relative
        # low: bottom decile of a positively drifting distribution can be > 0
        if pct_rank > self.trigger_percentile or change >= 0:
            return None

        self._armed = False
        strength = max(0.0, min(1.0, (self.trigger_percentile - pct_rank) / self.trigger_percentile))
        gap = abs((now - self.change_window) - ref_time)
        gap_ratio = min(gap / self.reference_tolerance, 1.0)
        confidence = 1.0 - 0.5 * gap_ratio

        return SignalEvent(
            symbol=self.symbol,
            direction=SignalDirection.FLAT,
            strength=strength,
            confidence=confidence,
            reason="oi_contraction_bottom_decile",
            timestamp=observation.observed_at,
            metadata={
                "oi_change_4h": change,
                "pct_rank": pct_rank,
                "history_count": len(self._sorted_changes),
                "oi_now_raw": oi_value,
                "oi_ref_raw": ref_value,
                "reference_gap_seconds": gap.total_seconds(),
                "trigger_percentile": self.trigger_percentile,
            },
        )

    def _reference_sample(self, now: datetime) -> tuple[datetime, float] | None:
        """Sample closest to ``now - change_window`` within tolerance.

        Also enforces newest-sample freshness: the previous sample before
        ``now`` must not be older than ``newest_stale_tolerance`` (data gap
        means the rolling state is unreliable).
        """
        if len(self._samples) < 2:
            return None
        previous_time = self._samples[-2][0]
        if now - previous_time > self.newest_stale_tolerance:
            return None

        target = now - self.change_window
        best: tuple[datetime, float] | None = None
        best_gap: timedelta | None = None
        for sample_time, value in self._samples:
            gap = abs(sample_time - target)
            if best_gap is None or gap < best_gap:
                best, best_gap = (sample_time, value), gap
        if best is None or best_gap is None or best_gap > self.reference_tolerance:
            return None
        return best

    def _percentile_rank(self, change: float) -> float | None:
        if len(self._sorted_changes) < self.min_history:
            return None
        # mid-rank so runs of tied values do not all map to the bottom
        low = bisect.bisect_left(self._sorted_changes, change)
        high = bisect.bisect_right(self._sorted_changes, change)
        return (low + high) / 2 / len(self._sorted_changes)

    def _record_change(self, now: datetime, change: float) -> None:
        self._changes.append((now, change))
        bisect.insort(self._sorted_changes, change)
        cutoff = now - self.history_window
        while self._changes and self._changes[0][0] < cutoff:
            _, old = self._changes.popleft()
            index = bisect.bisect_left(self._sorted_changes, old)
            if index < len(self._sorted_changes) and self._sorted_changes[index] == old:
                self._sorted_changes.pop(index)
