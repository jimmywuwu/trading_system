from __future__ import annotations

from dataclasses import dataclass, field

from core.models import OrderIntent


@dataclass
class PaperBroker:
    """Records order intents without sending them to an exchange."""

    orders: list[OrderIntent] = field(default_factory=list)

    def submit(self, order: OrderIntent) -> OrderIntent:
        self.orders.append(order)
        return order

    def submit_many(self, orders: list[OrderIntent]) -> list[OrderIntent]:
        for order in orders:
            self.submit(order)
        return orders
