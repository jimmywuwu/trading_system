from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.models import BasisPayload, FundingRatePayload, Observation, ObservationKind, OpenInterestPayload, SignalDirection
from signals.leverage_pressure import LeveragePressureShortSignal


def _ts(minutes: int) -> datetime:
    return datetime(2026, 5, 29, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


def _oi(minutes: int, value: float) -> Observation[OpenInterestPayload]:
    occurred_at = _ts(minutes)
    return Observation(
        observed_at=occurred_at + timedelta(seconds=60),
        occurred_at=occurred_at,
        symbol="BTCUSDT",
        source="test",
        kind=ObservationKind.PERP_OPEN_INTEREST,
        payload=OpenInterestPayload(
            open_interest_raw=str(value),
            open_interest_unit="exchange_native_linear_contract_quantity",
            open_interest_notional_usdt=value,
            normalization_price=100.0,
            normalization_source="test_mark_price",
        ),
        metadata={"coverage_status": "complete"},
    )


def _funding(minutes: int, rate: float) -> Observation[FundingRatePayload]:
    occurred_at = _ts(minutes)
    return Observation(
        observed_at=occurred_at + timedelta(seconds=60),
        occurred_at=occurred_at,
        symbol="BTCUSDT",
        source="test",
        kind=ObservationKind.PERP_FUNDING_RATE,
        payload=FundingRatePayload(funding_rate=rate, funding_rate_raw=str(rate), funding_type="settled", funding_interval="8h"),
        metadata={},
    )


def _basis(minutes: int, basis_bps: float) -> Observation[BasisPayload]:
    occurred_at = _ts(minutes)
    return Observation(
        observed_at=occurred_at + timedelta(seconds=60),
        occurred_at=occurred_at,
        symbol="BTCUSDT",
        source="test",
        kind=ObservationKind.PERP_SPOT_BASIS,
        payload=BasisPayload(basis_bps=basis_bps, perp_price=101.0, spot_price=100.0, basis_type="basis_from_perp_close_vs_spot_close"),
        metadata={},
    )


def test_returns_none_when_required_observations_are_missing() -> None:
    signal = LeveragePressureShortSignal(symbol="BTCUSDT")

    assert signal.generate([_funding(120, 0.0005), _basis(120, 20.0)]) is None


def test_returns_none_when_thresholds_are_not_met() -> None:
    signal = LeveragePressureShortSignal(symbol="BTCUSDT")
    observations = [
        _oi(0, 100.0),
        _oi(120, 102.0),
        _funding(120, 0.0001),
        _basis(120, 3.0),
    ]

    assert signal.generate(observations) is None


def test_emits_short_signal_for_high_funding_rising_oi_and_perp_premium() -> None:
    signal = LeveragePressureShortSignal(symbol="BTCUSDT")
    observations = [
        _oi(0, 100.0),
        _oi(120, 112.0),
        _funding(120, 0.0005),
        _basis(120, 25.0),
    ]

    event = signal.generate(observations)

    assert event is not None
    assert event.symbol == "BTCUSDT"
    assert event.direction == SignalDirection.SHORT
    assert event.reason == "leverage_pressure_short"
    assert event.timestamp == max(item.observed_at for item in observations)
    assert 0 < event.strength <= 1
    assert 0 < event.confidence <= 1
    assert event.metadata["funding_rate"] == 0.0005
    assert event.metadata["open_interest_change_pct"] == 0.12
    assert event.metadata["basis_bps"] == 25.0
    assert event.metadata["used_observation_count"] == 4


def test_returns_none_when_recent_microstructure_inputs_are_stale() -> None:
    signal = LeveragePressureShortSignal(symbol="BTCUSDT", stale_tolerance=timedelta(minutes=15))
    observations = [
        _oi(0, 100.0),
        _oi(120, 115.0),
        _funding(120, 0.0005),
        _basis(200, 30.0),
    ]

    assert signal.generate(observations) is None


def test_signal_generation_is_deterministic_under_replay_ordering() -> None:
    signal = LeveragePressureShortSignal(symbol="BTCUSDT")
    observations = [_oi(0, 100.0), _oi(120, 112.0), _funding(120, 0.0005), _basis(120, 25.0)]

    first = signal.generate(observations)
    second = signal.generate(list(reversed(observations)))

    assert first == second
