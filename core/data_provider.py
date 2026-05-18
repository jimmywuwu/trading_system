from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from .models import Observation, ObservationKind


class DataProvider(ABC):
    """Point-in-time observation boundary for market, message, and macro sources."""

    source: str

    @abstractmethod
    def get_latest(self, subject: str, kind: ObservationKind | None = None) -> Observation | None:
        raise NotImplementedError

    @abstractmethod
    def get_observations(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> list[Observation]:
        raise NotImplementedError

    def subscribe(
        self,
        kinds: Iterable[ObservationKind] | None = None,
        subjects: Iterable[str] | None = None,
    ) -> None:
        raise NotImplementedError("streaming subscriptions are provider-specific")
