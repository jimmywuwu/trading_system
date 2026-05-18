from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import Observation, OrderIntent, SignalEvent


class Strategy(ABC):
    """Converts signal events and portfolio state into order intents."""

    name: str

    def on_observation(self, observation: Observation) -> None:
        return None

    def on_signal(self, signal: SignalEvent) -> None:
        return None

    @abstractmethod
    def decide(self, portfolio: dict[str, Any], risk_state: dict[str, Any]) -> list[OrderIntent]:
        raise NotImplementedError
