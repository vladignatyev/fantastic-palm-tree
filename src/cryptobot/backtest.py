"""Backtesting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .indicators import IndicatorSet
from .strategy import Broker, ClosedTrade, Strategy, StrategyContext


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[ClosedTrade]
    metrics: dict[str, float]


def _evaluate_metrics(equity: pd.Series, trades: list[ClosedTrade]) -> dict[str, float]:
    returns = equity.pct_change().dropna()
    downside = returns[returns < 0]

    pnl = equity.iloc[-1] - equity.iloc[0]
    max_equity = equity.max()
    min_equity = equity.min()
    drawdown = (equity.cummax() - equity).max()
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if not returns.empty else np.nan
    sortino = (
        (returns.mean() / downside.std()) * np.sqrt(252)
        if not downside.empty and downside.std() != 0
        else np.nan
    )

    return {
        "pnl": pnl,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": drawdown,
        "max_profit": max_equity - equity.iloc[0],
        "min_equity": min_equity,
        "max_equity": max_equity,
        "closed_trades": len(trades),
        "total_fees": sum(trade.total_fees for trade in trades),
    }


def _simulate_candle(broker: Broker, candle: pd.Series, timestamp: pd.Timestamp) -> None:
    high = candle["high"]
    low = candle["low"]
    close = candle["close"]

    to_close: list[int] = []
    for trade in broker.open_positions:
        if trade.take_profit is not None:
            if trade.direction == 1 and high >= trade.take_profit:
                broker.close_trade(
                    trade.trade_id,
                    trade.take_profit,
                    timestamp,
                    reason="take_profit",
                    fee_type="maker",
                )
                to_close.append(trade.trade_id)
                continue
            if trade.direction == -1 and low <= trade.take_profit:
                broker.close_trade(
                    trade.trade_id,
                    trade.take_profit,
                    timestamp,
                    reason="take_profit",
                    fee_type="maker",
                )
                to_close.append(trade.trade_id)
                continue
        if trade.stop_loss is not None:
            if trade.direction == 1 and low <= trade.stop_loss:
                broker.close_trade(
                    trade.trade_id,
                    trade.stop_loss,
                    timestamp,
                    reason="stop_loss",
                    fee_type="taker",
                )
                to_close.append(trade.trade_id)
                continue
            if trade.direction == -1 and high >= trade.stop_loss:
                broker.close_trade(
                    trade.trade_id,
                    trade.stop_loss,
                    timestamp,
                    reason="stop_loss",
                    fee_type="taker",
                )
                to_close.append(trade.trade_id)
                continue

    # Remove trades already closed during this candle to avoid double closing
    for trade_id in to_close:
        broker._open_positions.pop(trade_id, None)


def run_backtest(
    data: pd.DataFrame,
    strategy: Strategy,
    params: dict[str, float] | None = None,
    initial_equity: float = 10_000.0,
    maker_fee: float = 0.0,
    taker_fee: float = 0.0,
) -> BacktestResult:
    """Run a backtest over the provided OHLCV data."""

    broker = Broker(maker_fee=maker_fee, taker_fee=taker_fee)
    params = params or {name: np.mean(bounds) for name, bounds in zip(strategy.parameters.names, strategy.parameters.bounds)}
    equity = [initial_equity]
    index = []

    for timestamp, candle in data.iterrows():
        history = data.loc[:timestamp]
        indicators = IndicatorSet(history)
        context = StrategyContext(timestamp=timestamp, history=history, indicators=indicators)
        strategy(context, broker, params)
        _simulate_candle(broker, candle, timestamp)

        # Update equity based on open positions using close price mark-to-market
        mtm = sum(
            (candle["close"] - trade.entry_price) * trade.direction * trade.size - trade.entry_fee
            for trade in broker.open_positions
        )
        closed_profit = sum(trade.pnl for trade in broker.closed_positions)
        equity.append(initial_equity + mtm + closed_profit)
        index.append(timestamp)

    equity_series = pd.Series(equity[1:], index=index, name="equity")
    metrics = _evaluate_metrics(equity_series, broker.closed_positions)
    return BacktestResult(equity_series, broker.closed_positions, metrics)


def optimize_strategy(
    data: pd.DataFrame,
    strategy: Strategy,
    objective: Callable[[BacktestResult], float],
    initial_guess: Iterable[float] | None = None,
    maker_fee: float = 0.0,
    taker_fee: float = 0.0,
) -> tuple[np.ndarray, BacktestResult]:
    """Optimize strategy parameters using SciPy's ``minimize``."""

    bounds = strategy.parameters.bounds
    guess = (
        np.array(list(initial_guess))
        if initial_guess is not None
        else np.array([np.mean(b) for b in bounds])
    )

    def _objective(values: np.ndarray) -> float:
        params = strategy.parameters.to_dict(values)
        result = run_backtest(
            data,
            strategy,
            params,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
        )
        return objective(result)

    result = minimize(_objective, guess, bounds=bounds)
    best_params = result.x
    best_result = run_backtest(
        data,
        strategy,
        strategy.parameters.to_dict(best_params),
        maker_fee=maker_fee,
        taker_fee=taker_fee,
    )
    return best_params, best_result


__all__ = ["BacktestResult", "run_backtest", "optimize_strategy"]
