from __future__ import annotations

from datetime import datetime
from typing import Iterable, Iterator

from core.data_provider import DataProvider
from core.models import Observation, ObservationKind


class LookaheadError(RuntimeError):
    """Raised when a component tries to read observations beyond replay time."""


class ReplayDataProvider(DataProvider):
    """Event-driven point-in-time replay over a fixed set of observations.

    Observations are sorted by ``observed_at``. During replay the provider
    tracks the current replay time and refuses to serve observations with
    ``observed_at > current_time`` — this is the system-wide lookahead guard.
    """

    source = "replay"

    def __init__(self, observations: Iterable[Observation]) -> None:
        self._observations = sorted(observations, key=lambda item: item.observed_at)
        self._current_time: datetime | None = None
        self._visible_count = 0

    @classmethod
    def from_provider(
        cls,
        provider: DataProvider,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> "ReplayDataProvider":
        return cls(provider.get_observations(start=start, end=end, kinds=kinds, subjects=subjects))

    @property
    def current_time(self) -> datetime | None:
        return self._current_time

    def replay(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Iterator[tuple[datetime, list[Observation]]]:
        """Yield ``(current_time, observations)`` grouped by identical observed_at."""
        self._current_time = None
        self._visible_count = 0

        batch: list[Observation] = []
        for index, observation in enumerate(self._observations):
            if start is not None and observation.observed_at < start:
                self._visible_count = index + 1
                continue
            if end is not None and observation.observed_at > end:
                break
            if batch and observation.observed_at != batch[-1].observed_at:
                self._current_time = batch[-1].observed_at
                self._visible_count += len(batch)
                yield self._current_time, batch
                batch = []
            batch.append(observation)

        if batch:
            self._current_time = batch[-1].observed_at
            self._visible_count += len(batch)
            yield self._current_time, batch

    def get_latest(self, subject: str, kind: ObservationKind | None = None) -> Observation | None:
        for observation in reversed(self._visible()):
            if observation.subject != subject:
                continue
            if kind is not None and observation.kind != kind:
                continue
            return observation
        return None

    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        if end is not None and self._current_time is not None and end > self._current_time:
            raise LookaheadError(
                f"requested observations up to {end.isoformat()} but replay time is "
                f"{self._current_time.isoformat()}"
            )
        kind_filter = set(kinds) if kinds is not None else None
        subject_filter = set(subjects) if subjects is not None else None

        result = []
        for observation in self._visible():
            if start is not None and observation.observed_at < start:
                continue
            if end is not None and observation.observed_at > end:
                continue
            if kind_filter is not None and observation.kind not in kind_filter:
                continue
            if subject_filter is not None and observation.subject not in subject_filter:
                continue
            result.append(observation)
        return result

    def _visible(self) -> list[Observation]:
        if self._current_time is None:
            return []
        return self._observations[: self._visible_count]
