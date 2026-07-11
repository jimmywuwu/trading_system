from __future__ import annotations

from core.models import SignalDirection
from signals.sma_cross import SmaCrossSignal
from tests.conftest import make_candles


def _run(signal: SmaCrossSignal, closes: list[float]):
    events = []
    for observation in make_candles(closes):
        event = signal.generate([observation])
        if event is not None:
            events.append(event)
    return events


def test_no_events_before_warmup():
    signal = SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4)
    events = _run(signal, [100, 100, 100])
    assert events == []


def test_cross_up_emits_long_and_cross_down_emits_flat():
    signal = SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4)
    closes = [100, 100, 100, 100, 100, 120, 130, 100, 80, 70]
    events = _run(signal, closes)

    directions = [event.direction for event in events]
    assert SignalDirection.LONG in directions
    assert SignalDirection.FLAT in directions
    assert directions.index(SignalDirection.LONG) < directions.index(SignalDirection.FLAT)
    reasons = {event.reason for event in events}
    assert reasons == {"sma_cross_up", "sma_cross_down"}


def test_event_timestamp_matches_observation():
    signal = SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4)
    observations = make_candles([100, 100, 100, 100, 100, 120, 130])
    events = []
    for observation in observations:
        event = signal.generate([observation])
        if event is not None:
            events.append((event, observation))
    for event, observation in events:
        assert event.timestamp == observation.observed_at


def test_ignores_other_symbols():
    signal = SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4)
    observations = make_candles([100, 100, 100, 100, 100, 150, 200], symbol="ETH-USD")
    events = [event for obs in observations if (event := signal.generate([obs]))]
    assert events == []


def test_deterministic_across_runs():
    closes = [100, 101, 99, 102, 98, 120, 130, 90, 80, 125, 60]
    first = _run(SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4), closes)
    second = _run(SmaCrossSignal(symbol="BTC-USD", fast_window=2, slow_window=4), closes)
    assert [(e.reason, e.timestamp) for e in first] == [(e.reason, e.timestamp) for e in second]
