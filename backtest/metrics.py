from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def compute_metrics(
    equity_curve: list[tuple[datetime, float]],
    trades: list[dict[str, Any]],
    exposure_curve: list[float] | None = None,
) -> dict[str, Any]:
    """Summary statistics for a backtest run.

    Sharpe is annualized from the median bar interval of the equity curve;
    win rate counts closing trades (sells) with positive realized PnL.
    """
    if not equity_curve:
        return {"error": "empty equity curve"}

    values = [value for _, value in equity_curve]
    initial, final = values[0], values[-1]
    total_return = final / initial - 1 if initial > 0 else 0.0

    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, value / peak - 1)

    sharpe = _annualized_sharpe(equity_curve)

    closing = [trade for trade in trades if trade["side"] == "sell"]
    wins = [trade for trade in closing if trade.get("realized_pnl", 0.0) > 0]
    fees = sum(trade.get("fee", 0.0) for trade in trades)
    turnover = sum(trade.get("notional", 0.0) for trade in trades) / initial if initial > 0 else 0.0

    metrics: dict[str, Any] = {
        "start": equity_curve[0][0].isoformat(),
        "end": equity_curve[-1][0].isoformat(),
        "initial_equity": initial,
        "final_equity": final,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "num_trades": len(trades),
        "num_round_trips": len(closing),
        "win_rate": len(wins) / len(closing) if closing else None,
        "avg_trade_pnl": (
            sum(trade.get("realized_pnl", 0.0) for trade in closing) / len(closing) if closing else None
        ),
        "fees_paid": fees,
        "turnover": turnover,
    }
    if exposure_curve:
        metrics["avg_exposure"] = sum(exposure_curve) / len(exposure_curve)
    return metrics


def _annualized_sharpe(equity_curve: list[tuple[datetime, float]]) -> float | None:
    if len(equity_curve) < 3:
        return None

    returns = []
    intervals = []
    for (prev_time, prev_value), (time, value) in zip(equity_curve, equity_curve[1:]):
        if prev_value > 0:
            returns.append(value / prev_value - 1)
            intervals.append((time - prev_time).total_seconds())
    if len(returns) < 2:
        return None

    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None

    interval_seconds = sorted(intervals)[len(intervals) // 2]
    if interval_seconds <= 0:
        return None
    periods_per_year = 365.25 * 24 * 3600 / interval_seconds
    return mean / std * math.sqrt(periods_per_year)


def format_metrics_markdown(metrics: dict[str, Any], title: str = "Backtest Result") -> str:
    lines = [f"# {title}", ""]
    for key, value in metrics.items():
        if isinstance(value, float):
            if key in ("total_return", "max_drawdown", "win_rate", "avg_exposure", "turnover"):
                rendered = f"{value:.2%}" if key != "turnover" else f"{value:.2f}x"
            else:
                rendered = f"{value:,.4f}"
        else:
            rendered = str(value)
        lines.append(f"- **{key}**: {rendered}")
    lines.append("")
    return "\n".join(lines)
