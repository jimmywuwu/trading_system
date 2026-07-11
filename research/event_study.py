from __future__ import annotations

import bisect
from datetime import datetime, timedelta
from typing import Any

from core.models import CandlePayload, Observation, ObservationKind, SignalEvent


def forward_return_study(
    events: list[SignalEvent],
    observations: list[Observation],
    horizons: list[timedelta],
    symbol: str | None = None,
) -> dict[str, Any]:
    """Forward returns after signal events, using the first tradable price
    strictly after the event time (next candle open) as entry.

    This is the phase-3 research primitive: answer "does the signal predict
    anything" before building a portfolio backtest.
    """
    candles = [
        obs
        for obs in sorted(observations, key=lambda item: item.observed_at)
        if obs.kind == ObservationKind.CANDLE
        and isinstance(obs.payload, CandlePayload)
        and (symbol is None or obs.subject == symbol)
    ]
    times = [obs.observed_at for obs in candles]

    def entry_after(moment: datetime) -> tuple[datetime, float] | None:
        index = bisect.bisect_right(times, moment)
        if index >= len(candles):
            return None
        obs = candles[index]
        return obs.observed_at, obs.payload.open  # type: ignore[union-attr]

    def close_at_or_after(moment: datetime) -> float | None:
        index = bisect.bisect_left(times, moment)
        if index >= len(candles):
            return None
        return candles[index].payload.close  # type: ignore[union-attr]

    per_horizon: dict[str, list[float]] = {_label(h): [] for h in horizons}
    rows: list[dict[str, Any]] = []

    for event in events:
        entry = entry_after(event.timestamp)
        if entry is None:
            continue
        entry_time, entry_price = entry
        if entry_price <= 0:
            continue
        row: dict[str, Any] = {
            "event_time": event.timestamp.isoformat(),
            "direction": event.direction.value,
            "strength": event.strength,
            "confidence": event.confidence,
            "reason": event.reason,
            "entry_price": entry_price,
        }
        for horizon in horizons:
            exit_price = close_at_or_after(entry_time + horizon)
            label = _label(horizon)
            if exit_price is None:
                row[label] = None
                continue
            forward = exit_price / entry_price - 1
            row[label] = forward
            per_horizon[label].append(forward)
        rows.append(row)

    summary = {
        label: {
            "count": len(values),
            "mean": sum(values) / len(values) if values else None,
            "median": sorted(values)[len(values) // 2] if values else None,
            "positive_rate": sum(1 for item in values if item > 0) / len(values) if values else None,
        }
        for label, values in per_horizon.items()
    }
    return {"events_evaluated": len(rows), "summary": summary, "rows": rows}


def _label(horizon: timedelta) -> str:
    total = int(horizon.total_seconds())
    if total % 86_400 == 0:
        return f"{total // 86_400}d"
    if total % 3_600 == 0:
        return f"{total // 3_600}h"
    return f"{total // 60}m"
