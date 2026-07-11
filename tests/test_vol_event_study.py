from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from research.vol_event_study import realized_vol_study
from tests.conftest import make_candles


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
INTERVAL = timedelta(minutes=5)


def _synthetic_closes(total: int, burst_starts: list[int], burst_len: int = 48,
                      base_sigma: float = 0.0005, burst_sigma: float = 0.003) -> list[float]:
    """Random walk with volatility bursts at known indices (deterministic)."""
    rng = random.Random(42)
    in_burst = set()
    for start in burst_starts:
        in_burst.update(range(start, start + burst_len))
    closes = [100.0]
    for index in range(1, total):
        sigma = burst_sigma if index in in_burst else base_sigma
        closes.append(closes[-1] * math.exp(rng.gauss(0, sigma)))
    return closes


def test_detects_vol_expansion_after_events():
    burst_starts = [800, 1400, 2000, 2600]
    closes = _synthetic_closes(3200, burst_starts)
    candles = make_candles(closes, start=START, interval=INTERVAL)
    # events fire just before each burst begins
    event_times = [candles[start - 1].observed_at for start in burst_starts]

    study = realized_vol_study(
        event_times,
        candles,
        horizons=[timedelta(hours=4)],
        match_on="vol",
        controls_per_event=10,
        bootstrap_reps=200,
    )
    horizon = study["horizons"]["4h"]
    assert study["n_events"] == 4
    assert horizon["vol_lift"] > 0.5  # bursts are 6x base sigma; lift must be large
    low, _ = horizon["vol_lift_ci95"]
    assert low > 0


def test_no_lift_when_events_are_random():
    closes = _synthetic_closes(3200, burst_starts=[])
    candles = make_candles(closes, start=START, interval=INTERVAL)
    event_times = [candles[index].observed_at for index in (800, 1400, 2000, 2600)]

    study = realized_vol_study(
        event_times,
        candles,
        horizons=[timedelta(hours=4)],
        match_on="vol",
        controls_per_event=10,
        bootstrap_reps=200,
    )
    horizon = study["horizons"]["4h"]
    # homogeneous vol: lift must be near zero (sampling noise only),
    # far below any minimum-effect threshold we would act on
    assert abs(horizon["vol_lift"]) < 0.10


def test_overlapping_events_are_deduped():
    closes = _synthetic_closes(3200, burst_starts=[800])
    candles = make_candles(closes, start=START, interval=INTERVAL)
    # three events inside the same 4h window -> only the first survives
    event_times = [candles[i].observed_at for i in (799, 805, 820)]

    study = realized_vol_study(
        event_times, candles, horizons=[timedelta(hours=4)],
        controls_per_event=10, bootstrap_reps=50,
    )
    assert study["n_events"] == 1


def test_event_at_end_of_data_is_dropped():
    closes = _synthetic_closes(600, burst_starts=[])
    candles = make_candles(closes, start=START, interval=INTERVAL)
    event_times = [candles[-2].observed_at]  # no room for forward window

    study = realized_vol_study(
        event_times, candles, horizons=[timedelta(hours=4)],
        controls_per_event=10, bootstrap_reps=50,
    )
    assert study.get("error") == "no usable events"


def test_deterministic_with_seed():
    closes = _synthetic_closes(3200, burst_starts=[800, 2000])
    candles = make_candles(closes, start=START, interval=INTERVAL)
    event_times = [candles[799].observed_at, candles[1999].observed_at]

    kwargs = dict(horizons=[timedelta(hours=4)], controls_per_event=10, bootstrap_reps=100, seed=7)
    first = realized_vol_study(event_times, candles, **kwargs)
    second = realized_vol_study(event_times, candles, **kwargs)
    assert first == second


def test_return_matching_mode_runs():
    closes = _synthetic_closes(3200, burst_starts=[800])
    candles = make_candles(closes, start=START, interval=INTERVAL)
    event_times = [candles[799].observed_at]

    study = realized_vol_study(
        event_times, candles, horizons=[timedelta(hours=4)],
        match_on="return", controls_per_event=10, bootstrap_reps=50,
    )
    assert study["match_on"] == "return"
    assert study["horizons"]["4h"]["n"] == 1
