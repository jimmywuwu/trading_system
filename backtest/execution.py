from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.models import (
    CandlePayload,
    Observation,
    ObservationKind,
    OrderIntent,
    OrderSide,
    OrderType,
    PricePayload,
)


@dataclass(frozen=True)
class Fill:
    order: OrderIntent
    price: float
    quantity: float
    fee: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def symbol(self) -> str:
        return self.order.symbol

    @property
    def side(self) -> OrderSide:
        return self.order.side

    @property
    def notional(self) -> float:
        return self.price * self.quantity


class SimulatedExecution:
    """Fills pending order intents against newly visible observations.

    Fill rules (v1, per BACKTEST.md):
    - market orders fill at the next visible candle *open* (or price payload price),
      never at the same observation that produced the signal.
    - limit orders fill at the limit price when the candle range touches it
      (buy: low <= limit, sell: high >= limit).
    - fee is ``fee_rate`` of notional; slippage is ``slippage_bps`` applied
      against the trade direction on market orders.
    """

    def __init__(self, fee_rate: float = 0.001, slippage_bps: float = 0.0) -> None:
        if fee_rate < 0:
            raise ValueError("fee_rate must be >= 0")
        if slippage_bps < 0:
            raise ValueError("slippage_bps must be >= 0")
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps
        self._pending: list[OrderIntent] = []

    @property
    def pending_orders(self) -> list[OrderIntent]:
        return list(self._pending)

    def submit(self, orders: list[OrderIntent]) -> None:
        self._pending.extend(orders)

    def cancel_all(self) -> list[OrderIntent]:
        cancelled, self._pending = self._pending, []
        return cancelled

    def on_observations(self, observations: list[Observation], current_time: datetime) -> list[Fill]:
        if not self._pending:
            return []

        fills: list[Fill] = []
        remaining: list[OrderIntent] = []
        for order in self._pending:
            fill = self._try_fill(order, observations, current_time)
            if fill is None:
                remaining.append(order)
            else:
                fills.append(fill)
        self._pending = remaining
        return fills

    def _try_fill(
        self,
        order: OrderIntent,
        observations: list[Observation],
        current_time: datetime,
    ) -> Fill | None:
        for observation in observations:
            if observation.subject != order.symbol:
                continue
            price = self._fill_price(order, observation)
            if price is None:
                continue
            fee = price * order.quantity * self.fee_rate
            return Fill(
                order=order,
                price=price,
                quantity=order.quantity,
                fee=fee,
                timestamp=current_time,
                metadata={
                    "fill_source": observation.source,
                    "fill_kind": observation.kind.value,
                    "order_reason": order.reason,
                },
            )
        return None

    def _fill_price(self, order: OrderIntent, observation: Observation) -> float | None:
        payload = observation.payload
        if order.order_type == OrderType.MARKET:
            if observation.kind == ObservationKind.CANDLE and isinstance(payload, CandlePayload):
                base = payload.open
            elif observation.kind == ObservationKind.PRICE and isinstance(payload, PricePayload):
                base = payload.price
            else:
                return None
            if base is None or base <= 0:
                return None
            slip = base * self.slippage_bps / 10_000
            return base + slip if order.side == OrderSide.BUY else base - slip

        if order.order_type == OrderType.LIMIT and order.price is not None:
            if observation.kind == ObservationKind.CANDLE and isinstance(payload, CandlePayload):
                if order.side == OrderSide.BUY and payload.low <= order.price:
                    return order.price
                if order.side == OrderSide.SELL and payload.high >= order.price:
                    return order.price
            elif observation.kind == ObservationKind.PRICE and isinstance(payload, PricePayload):
                price = payload.price
                if price is None:
                    return None
                if order.side == OrderSide.BUY and price <= order.price:
                    return order.price
                if order.side == OrderSide.SELL and price >= order.price:
                    return order.price
        return None
