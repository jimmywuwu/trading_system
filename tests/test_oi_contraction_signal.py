from __future__ import annotations

import math
from datetime import timedelta

from core.models import SignalDirection
from signals.oi_contraction_vol_regime import OiContractionVolRegimeSignal
from tests.conftest import make_open_interest


def _signal(**overrides) -> OiContractionVolRegimeSignal:
    params = dict(
        symbol="BTCUSDT",
        change_window=timedelta(hours=1),
        history_window=timedelta(hours=24),
        min_history=20,
        trigger_percentile=0.10,
        rearm_percentile=0.20,
        newest_stale_tolerance=timedelta(minutes=30),
        reference_tolerance=timedelta(minutes=30),
    )
    params.update(overrides)
    return OiContractionVolRegimeSignal(**params)


def _drift_series(count: int, base: float = 100_000.0) -> list[float]:
    # smooth deterministic wobble so the change distribution is continuous
    return [base * (1 + 0.002 * math.sin(0.7 * index) + 0.001 * math.sin(0.13 * index)) for index in range(count)]


def _run_segments(signal: OiContractionVolRegimeSignal, values: list[float]):
    """Feed the whole series, return (observation, event-or-None) pairs."""
    pairs = []
    for observation in make_open_interest(values):
        pairs.append((observation, signal.generate([observation])))
    return pairs


def test_no_events_during_warmup():
    signal = _signal()
    pairs = _run_segments(signal, _drift_series(15))
    assert all(event is None for _, event in pairs)


def test_sharp_contraction_triggers_flat_event_at_drop():
    wobble = _drift_series(60)
    pairs = _run_segments(_signal(), wobble + [70_000.0])  # ~-30% vs 1h ago

    drop_observation, drop_event = pairs[-1]
    assert drop_event is not None, "sharp contraction must emit an event"
    assert drop_event.direction == SignalDirection.FLAT
    assert drop_event.reason == "oi_contraction_bottom_decile"
    assert drop_event.timestamp == drop_observation.observed_at
    assert drop_event.strength > 0.9  # extreme tail of the distribution
    assert drop_event.metadata["oi_change_4h"] < -0.2
    assert drop_event.metadata["pct_rank"] <= 0.10


def test_hysteresis_blocks_repeats_in_same_episode():
    wobble = _drift_series(60)
    tail = [70_000.0, 69_000.0, 68_000.0, 67_000.0, 66_000.0]
    pairs = _run_segments(_signal(), wobble + tail)

    tail_events = [event for _, event in pairs[len(wobble):] if event is not None]
    assert len(tail_events) == 1  # only the initial edge fires


def test_expansion_does_not_trigger():
    wobble = _drift_series(60)
    expansion = [101_000.0, 103_000.0, 106_000.0, 110_000.0]
    pairs = _run_segments(_signal(), wobble + expansion)

    expansion_events = [event for _, event in pairs[len(wobble):] if event is not None]
    assert expansion_events == []


def test_all_events_are_actual_contractions():
    # relative percentile trigger must never fire on a positive change
    values = _drift_series(120)
    pairs = _run_segments(_signal(), values)
    for _, event in pairs:
        if event is not None:
            assert event.metadata["oi_change_4h"] < 0


def test_ignores_other_symbols():
    signal = _signal()
    values = _drift_series(60) + [70_000.0]
    events = [
        signal.generate([observation])
        for observation in make_open_interest(values, symbol="ETHUSDT")
    ]
    assert all(event is None for event in events)


def test_data_gap_blocks_emission():
    values = _drift_series(60)
    observations = make_open_interest(values)
    signal = _signal()
    for observation in observations:
        signal.generate([observation])

    # next sample arrives after a 3h gap with a sharp contraction
    gap_start = observations[-1].occurred_at + timedelta(hours=3)
    late = make_open_interest([70_000.0], start=gap_start)
    assert signal.generate(late) is None


def test_deterministic_across_runs():
    values = _drift_series(80) + [70_000.0] + _drift_series(20, base=70_000.0) + [50_000.0]
    first = [
        (e.reason, e.timestamp, e.strength)
        for _, e in _run_segments(_signal(), values)
        if e is not None
    ]
    second = [
        (e.reason, e.timestamp, e.strength)
        for _, e in _run_segments(_signal(), values)
        if e is not None
    ]
    assert first == second
