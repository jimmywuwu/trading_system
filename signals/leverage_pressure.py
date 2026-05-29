from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

from core.models import (
    BasisPayload,
    FundingRatePayload,
    Observation,
    ObservationKind,
    OpenInterestPayload,
    SignalDirection,
    SignalEvent,
)
from core.signal import Signal


@dataclass(frozen=True)
class LeveragePressureShortSignal(Signal):
    """Minimal leverage-pressure SHORT signal for smoke/replay validation.

    This is deliberately conservative and contract-shaped rather than tuned for
    performance. It only converts point-in-time observations into a deterministic
    SignalEvent when funding, open-interest change, and perp-vs-spot premium all
    cross explicit thresholds. Position sizing stays with Trader.
    """

    symbol: str = "BTCUSDT"
    name: str = "leverage_pressure_short"
    min_funding_rate: float = 0.0003
    min_open_interest_change_pct: float = 0.05
    min_basis_bps: float = 10.0
    stale_tolerance: timedelta = timedelta(minutes=15)
    funding_stale_tolerance: timedelta = timedelta(hours=8, minutes=30)

    def generate(self, observations: list[Observation] | dict[str, Observation]) -> SignalEvent | None:
        items = self._items(observations)
        relevant = [item for item in items if item.symbol == self.symbol]
        latest_funding = self._latest(relevant, ObservationKind.PERP_FUNDING_RATE)
        latest_basis = self._latest(relevant, ObservationKind.PERP_SPOT_BASIS)
        oi_series = self._series(relevant, ObservationKind.PERP_OPEN_INTEREST)

        if latest_funding is None or latest_basis is None or len(oi_series) < 2:
            return None

        signal_time = max(
            latest_funding.observed_at,
            latest_basis.observed_at,
            oi_series[-1].observed_at,
        )
        if signal_time - latest_basis.observed_at > self.stale_tolerance:
            return None
        if signal_time - oi_series[-1].observed_at > self.stale_tolerance:
            return None
        if signal_time - latest_funding.observed_at > self.funding_stale_tolerance:
            return None

        funding_payload = latest_funding.payload
        basis_payload = latest_basis.payload
        if not isinstance(funding_payload, FundingRatePayload) or not isinstance(basis_payload, BasisPayload):
            return None

        start_oi = self._open_interest_value(oi_series[0])
        end_oi = self._open_interest_value(oi_series[-1])
        if start_oi is None or end_oi is None or start_oi <= 0:
            return None

        oi_change_pct = (end_oi - start_oi) / start_oi
        funding_rate = funding_payload.funding_rate
        basis_bps = basis_payload.basis_bps

        if funding_rate < self.min_funding_rate:
            return None
        if oi_change_pct < self.min_open_interest_change_pct:
            return None
        if basis_bps < self.min_basis_bps:
            return None

        funding_component = funding_rate / max(self.min_funding_rate * 3, 1e-12)
        oi_component = oi_change_pct / max(self.min_open_interest_change_pct * 3, 1e-12)
        basis_component = basis_bps / max(self.min_basis_bps * 3, 1e-12)
        strength = min((funding_component + oi_component + basis_component) / 3, 1.0)

        confidence = min(
            0.35
            + 0.20 * min(funding_component, 1.0)
            + 0.25 * min(oi_component, 1.0)
            + 0.10 * min(basis_component, 1.0)
            + 0.10 * self._coverage_bonus(oi_series[-1]),
            1.0,
        )

        used_observations = [oi_series[0], oi_series[-1], latest_funding, latest_basis]
        return SignalEvent(
            symbol=self.symbol,
            direction=SignalDirection.SHORT,
            strength=round(strength, 6),
            confidence=round(confidence, 6),
            reason="leverage_pressure_short",
            timestamp=signal_time,
            metadata={
                "signal_name": self.name,
                "funding_rate": funding_rate,
                "funding_observed_at": latest_funding.observed_at.isoformat(),
                "open_interest_start": start_oi,
                "open_interest_end": end_oi,
                "open_interest_change_pct": round(oi_change_pct, 12),
                "open_interest_start_observed_at": oi_series[0].observed_at.isoformat(),
                "open_interest_end_observed_at": oi_series[-1].observed_at.isoformat(),
                "open_interest_coverage_status": oi_series[-1].metadata.get("coverage_status"),
                "basis_bps": basis_bps,
                "basis_observed_at": latest_basis.observed_at.isoformat(),
                "thresholds": {
                    "min_funding_rate": self.min_funding_rate,
                    "min_open_interest_change_pct": self.min_open_interest_change_pct,
                    "min_basis_bps": self.min_basis_bps,
                },
                "used_observation_count": len(used_observations),
                "used_observation_kinds": [item.kind.value for item in used_observations],
                "position_sizing": "not_defined_by_quant_signal",
            },
        )

    @staticmethod
    def _items(observations: list[Observation] | dict[str, Observation]) -> list[Observation]:
        return list(observations.values()) if isinstance(observations, dict) else list(observations)

    @staticmethod
    def _latest(observations: Iterable[Observation], kind: ObservationKind) -> Observation | None:
        candidates = [item for item in observations if item.kind == kind]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.observed_at)

    @staticmethod
    def _series(observations: Iterable[Observation], kind: ObservationKind) -> list[Observation]:
        return sorted((item for item in observations if item.kind == kind), key=lambda item: (item.occurred_at, item.observed_at))

    @staticmethod
    def _open_interest_value(observation: Observation) -> float | None:
        payload = observation.payload
        if not isinstance(payload, OpenInterestPayload):
            return None
        if payload.open_interest_notional_usdt is not None:
            return float(payload.open_interest_notional_usdt)
        return float(payload.open_interest_raw)

    @staticmethod
    def _coverage_bonus(observation: Observation) -> float:
        return 1.0 if observation.metadata.get("coverage_status") == "complete" else 0.0
