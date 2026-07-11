from __future__ import annotations

from datetime import timedelta

from core.models import SignalDirection, SignalEvent
from research.event_study import forward_return_study
from tests.conftest import make_candles


def test_forward_returns_use_next_candle_open_entry():
    # closes: 100 -> 110 -> 121 -> 133.1 (10% per bar)
    observations = make_candles([100.0, 110.0, 121.0, 133.1])
    event = SignalEvent(
        symbol="BTC-USD",
        direction=SignalDirection.LONG,
        strength=0.5,
        confidence=1.0,
        reason="test",
        timestamp=observations[0].observed_at,
    )

    study = forward_return_study([event], observations, horizons=[timedelta(minutes=1)])

    assert study["events_evaluated"] == 1
    row = study["rows"][0]
    # entry: first candle strictly after event = candle[1], open = 100 (prev close)
    assert row["entry_price"] == 100.0
    # exit: close at/after entry_time + 1m = candle[2] close = 121
    assert abs(row["1m"] - (121.0 / 100.0 - 1)) < 1e-9
    assert study["summary"]["1m"]["count"] == 1


def test_event_at_end_of_data_is_skipped():
    observations = make_candles([100.0, 110.0])
    event = SignalEvent(
        symbol="BTC-USD",
        direction=SignalDirection.LONG,
        strength=0.5,
        confidence=1.0,
        reason="test",
        timestamp=observations[-1].observed_at,
    )
    study = forward_return_study([event], observations, horizons=[timedelta(minutes=1)])
    assert study["events_evaluated"] == 0


def test_summary_statistics():
    observations = make_candles([100.0] * 5 + [120.0] + [120.0] * 4)
    events = [
        SignalEvent(
            symbol="BTC-USD",
            direction=SignalDirection.LONG,
            strength=0.5,
            confidence=1.0,
            reason="test",
            timestamp=observations[index].observed_at,
        )
        for index in (0, 1, 2)
    ]
    study = forward_return_study(events, observations, horizons=[timedelta(minutes=5)])
    summary = study["summary"]["5m"]
    assert summary["count"] == 3
    assert summary["positive_rate"] == 1.0  # all windows capture the 100 -> 120 jump
