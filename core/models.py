from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar


class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class ObservationKind(str, Enum):
    PRICE = "price"
    CANDLE = "candle"
    TRADE = "trade"
    MESSAGE = "message"
    MACRO = "macro"
    ORDERBOOK = "orderbook"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PayloadT = TypeVar("PayloadT")


@dataclass(frozen=True)
class PricePayload:
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: float | None = None

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2

    @property
    def price(self) -> float | None:
        return self.mid or self.last


@dataclass(frozen=True)
class CandlePayload:
    open: float
    high: float
    low: float
    close: float
    volume: float
    granularity: str

    @property
    def price(self) -> float:
        return self.close


@dataclass(frozen=True)
class MessagePayload:
    text: str
    author: str | None = None
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MacroPayload:
    name: str
    actual: float | None = None
    forecast: float | None = None
    previous: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Observation(Generic[PayloadT]):
    """Point-in-time visible data from any source."""

    observed_at: datetime
    occurred_at: datetime
    symbol: str
    source: str
    kind: ObservationKind
    payload: PayloadT
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def subject(self) -> str:
        return self.symbol

    @property
    def timestamp(self) -> datetime:
        return self.observed_at


@dataclass(frozen=True)
class SignalEvent:
    symbol: str
    direction: SignalDirection
    strength: float
    confidence: float
    reason: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.strength <= 1:
            raise ValueError("strength must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    reason: str
    timestamp: datetime = field(default_factory=utc_now)
    price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("limit orders require a price")
