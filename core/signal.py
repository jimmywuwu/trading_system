from __future__ import annotations

from abc import ABC, abstractmethod

from .data_provider import DataProvider
from .models import Observation, SignalEvent


class Signal(ABC):
    """Transforms point-in-time observations into tradeable signal events."""

    name: str

    def warmup(self, provider: DataProvider) -> None:
        return None

    @abstractmethod
    def generate(self, observations: list[Observation] | dict[str, Observation]) -> SignalEvent | None:
        raise NotImplementedError
