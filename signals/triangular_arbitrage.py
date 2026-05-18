from __future__ import annotations

from dataclasses import dataclass

from core.models import Observation, ObservationKind, PricePayload, SignalDirection, SignalEvent
from core.signal import Signal


@dataclass(frozen=True)
class TriangularArbitrageSignal(Signal):
    base_symbol: str = "BTC-USDT"
    cross_symbol: str = "ETH-BTC"
    quote_symbol: str = "ETH-USDT"
    fee_rate: float = 0.001
    min_net_profit_pct: float = 0.001
    notional: float = 1000.0
    name: str = "triangular_arbitrage"

    def generate(self, observations: list[Observation] | dict[str, Observation]) -> SignalEvent | None:
        latest_prices = self._latest_price_observations(observations)
        missing = {self.base_symbol, self.cross_symbol, self.quote_symbol} - set(latest_prices)
        if missing:
            return None

        btc_usdt = self._price(latest_prices[self.base_symbol])
        eth_btc = self._price(latest_prices[self.cross_symbol])
        eth_usdt = self._price(latest_prices[self.quote_symbol])
        if btc_usdt is None or eth_btc is None or eth_usdt is None:
            return None

        path_one_pct = self._path_one_profit_pct(btc_usdt, eth_btc, eth_usdt)
        path_two_pct = self._path_two_profit_pct(btc_usdt, eth_btc, eth_usdt)
        best_path = "USDT-BTC-ETH-USDT" if path_one_pct >= path_two_pct else "USDT-ETH-BTC-USDT"
        best_pct = max(path_one_pct, path_two_pct)
        net_pct = best_pct - self.fee_rate * 3

        if net_pct < self.min_net_profit_pct:
            return None

        return SignalEvent(
            symbol="TRIANGLE:" + ",".join([self.base_symbol, self.cross_symbol, self.quote_symbol]),
            direction=SignalDirection.LONG,
            strength=min(net_pct / max(self.min_net_profit_pct * 5, 1e-12), 1),
            confidence=min(net_pct / max(self.min_net_profit_pct * 2, 1e-12), 1),
            reason="triangular_arbitrage_net_profit",
            timestamp=max(item.observed_at for item in latest_prices.values()),
            metadata={
                "path": best_path,
                "gross_profit_pct": best_pct,
                "net_profit_pct": net_pct,
                "notional": self.notional,
                "observed_at": {
                    symbol: observation.observed_at.isoformat()
                    for symbol, observation in latest_prices.items()
                },
                "prices": {
                    self.base_symbol: btc_usdt,
                    self.cross_symbol: eth_btc,
                    self.quote_symbol: eth_usdt,
                },
            },
        )

    def _path_one_profit_pct(self, btc_usdt: float, eth_btc: float, eth_usdt: float) -> float:
        btc = self.notional / btc_usdt
        eth = btc / eth_btc
        usdt = eth * eth_usdt
        return (usdt - self.notional) / self.notional

    def _path_two_profit_pct(self, btc_usdt: float, eth_btc: float, eth_usdt: float) -> float:
        eth = self.notional / eth_usdt
        btc = eth * eth_btc
        usdt = btc * btc_usdt
        return (usdt - self.notional) / self.notional

    @staticmethod
    def _price(observation: Observation) -> float | None:
        payload = observation.payload
        if not isinstance(payload, PricePayload):
            return None
        return payload.price

    @staticmethod
    def _latest_price_observations(
        observations: list[Observation] | dict[str, Observation],
    ) -> dict[str, Observation]:
        items = observations.values() if isinstance(observations, dict) else observations
        latest: dict[str, Observation] = {}
        for observation in items:
            if observation.kind != ObservationKind.PRICE:
                continue
            existing = latest.get(observation.subject)
            if existing is None or observation.observed_at > existing.observed_at:
                latest[observation.subject] = observation
        return latest
