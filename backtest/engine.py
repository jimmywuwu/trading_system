from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.models import (
    CandlePayload,
    Observation,
    ObservationKind,
    PricePayload,
    SignalEvent,
)
from core.signal import Signal
from core.strategy import Strategy

from .execution import Fill, SimulatedExecution
from .metrics import compute_metrics
from .portfolio import Portfolio
from .replay import ReplayDataProvider


@dataclass
class BacktestConfig:
    initial_cash: float = 100_000.0
    fee_rate: float = 0.001
    slippage_bps: float = 0.0
    risk_state: dict[str, Any] = field(default_factory=lambda: {"halted": False})
    start: datetime | None = None
    end: datetime | None = None


@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: dict[str, Any]
    equity_curve: list[tuple[datetime, float]]
    trades: list[dict[str, Any]]
    signal_events: list[SignalEvent]
    portfolio: Portfolio

    def to_markdown(self, title: str = "Backtest Result") -> str:
        from .metrics import format_metrics_markdown

        header = format_metrics_markdown(self.metrics, title=title)
        assumptions = (
            "\n## Execution assumptions\n\n"
            f"- fee_rate: {self.config.fee_rate}\n"
            f"- slippage_bps: {self.config.slippage_bps}\n"
            "- market orders fill at next visible candle open\n"
            "- limit orders fill when candle range touches the limit price\n"
            f"- signal events emitted: {len(self.signal_events)}\n"
        )
        return header + assumptions


class BacktestEngine:
    """Point-in-time orchestration loop per BACKTEST.md.

    Order of operations per replay tick:
    1. fill pending orders against newly visible observations (candle open)
    2. apply fills to the portfolio
    3. feed observations to signals and strategy (candle close semantics)
    4. collect signal events, feed to strategy
    5. strategy decides; new orders join the pending queue for future ticks
    6. mark portfolio to market with latest close
    """

    def __init__(
        self,
        provider: ReplayDataProvider,
        strategy: Strategy,
        signals: list[Signal] | None = None,
        config: BacktestConfig | None = None,
    ) -> None:
        self.provider = provider
        self.strategy = strategy
        self.signals = signals or []
        self.config = config or BacktestConfig()

    def run(self) -> BacktestResult:
        config = self.config
        execution = SimulatedExecution(fee_rate=config.fee_rate, slippage_bps=config.slippage_bps)
        portfolio = Portfolio(cash=config.initial_cash)

        latest_prices: dict[str, float] = {}
        equity_curve: list[tuple[datetime, float]] = []
        exposure_curve: list[float] = []
        all_events: list[SignalEvent] = []
        all_fills: list[Fill] = []

        for current_time, observations in self.provider.replay(config.start, config.end):
            fills = execution.on_observations(observations, current_time)
            portfolio.apply(fills)
            all_fills.extend(fills)

            for observation in observations:
                mark = _mark_price(observation)
                if mark is not None:
                    latest_prices[observation.subject] = mark
                self.strategy.on_observation(observation)

            events: list[SignalEvent] = []
            for signal in self.signals:
                event = signal.generate(observations)
                if event is None:
                    continue
                if event.timestamp > current_time:
                    raise RuntimeError(
                        f"signal {signal.name} emitted event at {event.timestamp.isoformat()} "
                        f"after replay time {current_time.isoformat()}"
                    )
                events.append(event)
            for event in events:
                self.strategy.on_signal(event)
            all_events.extend(events)

            orders = self.strategy.decide(portfolio.snapshot(), config.risk_state)
            execution.submit(orders)

            equity_curve.append((current_time, portfolio.equity(latest_prices)))
            exposure_curve.append(portfolio.exposure(latest_prices))

        metrics = compute_metrics(equity_curve, portfolio.trades, exposure_curve)
        return BacktestResult(
            config=config,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=portfolio.trades,
            signal_events=all_events,
            portfolio=portfolio,
        )


def _mark_price(observation: Observation) -> float | None:
    if observation.kind == ObservationKind.CANDLE and isinstance(observation.payload, CandlePayload):
        return observation.payload.close
    if observation.kind == ObservationKind.PRICE and isinstance(observation.payload, PricePayload):
        return observation.payload.price
    return None
