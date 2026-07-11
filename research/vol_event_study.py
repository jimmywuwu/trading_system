from __future__ import annotations

import bisect
import math
import random
from datetime import datetime, timedelta
from typing import Any

from core.models import CandlePayload, Observation


def realized_vol_study(
    event_times: list[datetime],
    candles: list[Observation],
    horizons: list[timedelta],
    match_on: str = "vol",
    trailing_vol_window: timedelta = timedelta(hours=24),
    trailing_return_window: timedelta = timedelta(hours=4),
    controls_per_event: int = 20,
    bootstrap_reps: int = 1000,
    seed: int = 20260708,
) -> dict[str, Any]:
    """Event study for volatility-regime hypotheses.

    For each event, measures forward realized vol (sqrt of summed squared
    log close returns) and absolute forward return over each horizon, and
    compares against ``controls_per_event`` control anchors matched on a
    trailing measure (``match_on``: "vol" = trailing realized vol,
    "return" = trailing signed return). Control anchors within
    ``max(horizons)`` of any event are excluded so controls are not
    contaminated by event windows. Events are de-overlapped: an event
    inside the previous kept event's ``max(horizons)`` window is dropped.

    Lift per horizon = event mean / matched-control mean - 1.
    CI95 is an event-level bootstrap (resampling events with replacement,
    deterministic ``seed``).
    """
    if match_on not in ("vol", "return"):
        raise ValueError("match_on must be 'vol' or 'return'")
    if not horizons:
        raise ValueError("need at least one horizon")

    ordered = [
        obs for obs in sorted(candles, key=lambda item: item.observed_at)
        if isinstance(obs.payload, CandlePayload)
    ]
    if len(ordered) < 10:
        return {"error": "not enough candles"}

    times = [obs.observed_at for obs in ordered]
    closes = [obs.payload.close for obs in ordered]  # type: ignore[union-attr]

    # prefix sums: log returns and squared log returns
    log_prices = [math.log(price) for price in closes]
    sq_prefix = [0.0]
    for previous, current in zip(log_prices, log_prices[1:]):
        step = current - previous
        sq_prefix.append(sq_prefix[-1] + step * step)

    max_horizon = max(horizons)

    def index_at_or_before(moment: datetime) -> int:
        return bisect.bisect_right(times, moment) - 1

    def window_vol(start_index: int, end_index: int) -> float | None:
        if start_index < 0 or end_index <= start_index or end_index >= len(times):
            return None
        return math.sqrt(sq_prefix[end_index] - sq_prefix[start_index])

    def window_return(start_index: int, end_index: int) -> float | None:
        if start_index < 0 or end_index <= start_index or end_index >= len(times):
            return None
        return log_prices[end_index] - log_prices[start_index]

    def trailing_measure(index: int) -> float | None:
        if match_on == "vol":
            start = index_at_or_before(times[index] - trailing_vol_window)
            return window_vol(start, index)
        start = index_at_or_before(times[index] - trailing_return_window)
        return window_return(start, index)

    def forward_outcomes(index: int, horizon: timedelta) -> tuple[float, float] | None:
        end = index_at_or_before(times[index] + horizon)
        vol = window_vol(index, end)
        ret = window_return(index, end)
        if vol is None or ret is None:
            return None
        return vol, abs(ret)

    # anchor events at the first candle strictly after the event time
    event_indices: list[int] = []
    last_kept: datetime | None = None
    for event_time in sorted(event_times):
        if last_kept is not None and event_time - last_kept < max_horizon:
            continue
        index = bisect.bisect_right(times, event_time)
        if index >= len(times):
            continue
        if trailing_measure(index) is None or forward_outcomes(index, max_horizon) is None:
            continue
        event_indices.append(index)
        last_kept = event_time

    if not event_indices:
        return {"error": "no usable events"}

    # eligible control anchors: full trailing + forward windows, far from events
    event_time_list = [times[i] for i in event_indices]
    controls: list[tuple[float, int]] = []
    for index in range(len(times)):
        moment = times[index]
        near_event = any(abs(moment - event_moment) <= max_horizon for event_moment in event_time_list)
        if near_event:
            continue
        measure = trailing_measure(index)
        if measure is None or forward_outcomes(index, max_horizon) is None:
            continue
        controls.append((measure, index))
    controls.sort()
    control_measures = [measure for measure, _ in controls]

    if len(controls) < controls_per_event:
        return {"error": "not enough control anchors"}

    def matched_controls(measure: float) -> list[int]:
        position = bisect.bisect_left(control_measures, measure)
        low, high = position - 1, position
        chosen: list[int] = []
        while len(chosen) < controls_per_event and (low >= 0 or high < len(controls)):
            low_gap = abs(control_measures[low] - measure) if low >= 0 else math.inf
            high_gap = abs(control_measures[high] - measure) if high < len(controls) else math.inf
            if low_gap <= high_gap:
                chosen.append(controls[low][1])
                low -= 1
            else:
                chosen.append(controls[high][1])
                high += 1
        return chosen

    per_event_matches = {
        index: matched_controls(trailing_measure(index)) for index in event_indices
    }

    result: dict[str, Any] = {
        "match_on": match_on,
        "n_events": len(event_indices),
        "n_controls": len(controls),
        "controls_per_event": controls_per_event,
        "horizons": {},
        "seed": seed,
    }

    rng = random.Random(seed)
    for horizon in horizons:
        label = _label(horizon)
        rows = []
        for index in event_indices:
            event_outcome = forward_outcomes(index, horizon)
            control_outcomes = [
                outcome
                for control_index in per_event_matches[index]
                if (outcome := forward_outcomes(control_index, horizon)) is not None
            ]
            if event_outcome is None or not control_outcomes:
                continue
            control_vol = sum(item[0] for item in control_outcomes) / len(control_outcomes)
            control_abs = sum(item[1] for item in control_outcomes) / len(control_outcomes)
            rows.append((event_outcome[0], control_vol, event_outcome[1], control_abs))

        if not rows:
            result["horizons"][label] = {"error": "no rows"}
            continue

        def lift(sample: list[tuple[float, float, float, float]], vol_side: bool) -> float | None:
            event_mean = sum(row[0 if vol_side else 2] for row in sample) / len(sample)
            control_mean = sum(row[1 if vol_side else 3] for row in sample) / len(sample)
            if control_mean == 0:
                return None
            return event_mean / control_mean - 1

        boot_vol, boot_abs = [], []
        for _ in range(bootstrap_reps):
            sample = [rows[rng.randrange(len(rows))] for _ in range(len(rows))]
            vol_lift = lift(sample, vol_side=True)
            abs_lift = lift(sample, vol_side=False)
            if vol_lift is not None:
                boot_vol.append(vol_lift)
            if abs_lift is not None:
                boot_abs.append(abs_lift)

        result["horizons"][label] = {
            "n": len(rows),
            "event_mean_vol": sum(row[0] for row in rows) / len(rows),
            "control_mean_vol": sum(row[1] for row in rows) / len(rows),
            "vol_lift": lift(rows, vol_side=True),
            "vol_lift_ci95": _ci95(boot_vol),
            "event_mean_abs_return": sum(row[2] for row in rows) / len(rows),
            "control_mean_abs_return": sum(row[3] for row in rows) / len(rows),
            "abs_return_lift": lift(rows, vol_side=False),
            "abs_return_lift_ci95": _ci95(boot_abs),
        }
    return result


def _ci95(samples: list[float]) -> tuple[float, float] | None:
    if len(samples) < 40:
        return None
    ordered = sorted(samples)
    low = ordered[int(0.025 * len(ordered))]
    high = ordered[int(0.975 * len(ordered)) - 1]
    return (low, high)


def _label(horizon: timedelta) -> str:
    total = int(horizon.total_seconds())
    if total % 86_400 == 0:
        return f"{total // 86_400}d"
    if total % 3_600 == 0:
        return f"{total // 3_600}h"
    return f"{total // 60}m"
