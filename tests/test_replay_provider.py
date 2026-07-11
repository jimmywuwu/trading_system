from __future__ import annotations

from datetime import timedelta

import pytest

from backtest.replay import LookaheadError, ReplayDataProvider
from tests.conftest import make_candles


def test_replay_is_ordered_and_grouped():
    observations = make_candles([100, 101, 102, 103])
    provider = ReplayDataProvider(observations)

    ticks = list(provider.replay())
    assert len(ticks) == 4
    times = [time for time, _ in ticks]
    assert times == sorted(times)
    for time, batch in ticks:
        assert all(obs.observed_at == time for obs in batch)


def test_replay_never_serves_future_observations():
    observations = make_candles([100, 101, 102, 103])
    provider = ReplayDataProvider(observations)

    seen = 0
    for current_time, _ in provider.replay():
        visible = provider.get_observations()
        seen += 1
        assert len(visible) == seen
        assert all(obs.observed_at <= current_time for obs in visible)


def test_explicit_future_query_raises():
    observations = make_candles([100, 101, 102])
    provider = ReplayDataProvider(observations)

    replay = provider.replay()
    current_time, _ = next(replay)
    with pytest.raises(LookaheadError):
        provider.get_observations(end=current_time + timedelta(hours=1))


def test_replay_window_filters():
    observations = make_candles([100, 101, 102, 103, 104])
    provider = ReplayDataProvider(observations)
    all_times = [obs.observed_at for obs in observations]

    ticks = list(provider.replay(start=all_times[1], end=all_times[3]))
    assert [time for time, _ in ticks] == all_times[1:4]


def test_replay_is_deterministic():
    observations = make_candles([100, 102, 101, 103, 99])
    provider = ReplayDataProvider(observations)
    first = [(time, len(batch)) for time, batch in provider.replay()]
    second = [(time, len(batch)) for time, batch in provider.replay()]
    assert first == second
