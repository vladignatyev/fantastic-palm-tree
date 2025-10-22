"""Visualization helpers using :mod:`mplfinance`."""

from __future__ import annotations

import mplfinance as mpf
import pandas as pd

from .backtest import BacktestResult

_REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


def _prepare_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in _REQUIRED_COLUMNS if col not in data.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {', '.join(missing)}")

    ohlcv = data[_REQUIRED_COLUMNS].copy()
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        ohlcv.index = pd.to_datetime(ohlcv.index)
    ohlcv = ohlcv.sort_index()
    return ohlcv


def plot_ohlcv(data: pd.DataFrame, style: str = "yahoo") -> tuple[object, list[object]]:
    """Render OHLCV candles with volume using :mod:`mplfinance`."""

    ohlcv = _prepare_ohlcv(data)
    fig, axes = mpf.plot(
        ohlcv,
        type="candle",
        volume=True,
        style=style,
        returnfig=True,
        figsize=(12, 8),
        title="OHLCV Candles",
    )
    return fig, axes


def plot_backtest(
    data: pd.DataFrame,
    result: BacktestResult,
    style: str = "yahoo",
) -> tuple[object, list[object]]:
    """Plot price candles, trade markers, and the equity curve."""

    ohlcv = _prepare_ohlcv(data)

    entries = pd.Series(index=ohlcv.index, dtype=float)
    exits = pd.Series(index=ohlcv.index, dtype=float)

    for trade in result.trades:
        entry_idx = ohlcv.index.get_indexer([trade.entry_time], method="nearest")
        if entry_idx.size and entry_idx[0] != -1:
            entries.iloc[entry_idx[0]] = trade.entry_price
        exit_time = getattr(trade, "exit_time", None)
        if exit_time is not None:
            exit_idx = ohlcv.index.get_indexer([exit_time], method="nearest")
            if exit_idx.size and exit_idx[0] != -1:
                exits.iloc[exit_idx[0]] = trade.exit_price

    add_plots: list[object] = []
    if not entries.dropna().empty:
        add_plots.append(
            mpf.make_addplot(entries.dropna(), type="scatter", markersize=80, marker="^", color="g")
        )
    if not exits.dropna().empty:
        add_plots.append(
            mpf.make_addplot(exits.dropna(), type="scatter", markersize=80, marker="v", color="r")
        )

    equity: pd.Series | None
    if result.equity_curve.empty:
        equity = None
    else:
        equity = result.equity_curve.copy()
        if not isinstance(equity.index, pd.DatetimeIndex):
            equity.index = pd.to_datetime(equity.index)
        equity = equity.reindex(ohlcv.index, method="pad")
        if equity.isna().all():
            equity = None
        else:
            add_plots.append(
                mpf.make_addplot(
                    equity,
                    panel=2,
                    ylabel="Equity",
                    color="tab:purple",
                )
            )

    fig, axes = mpf.plot(
        ohlcv,
        type="candle",
        volume=True,
        style=style,
        addplot=add_plots if add_plots else None,
        panel_ratios=(3, 1, 1) if equity is not None else (3, 1),
        returnfig=True,
        figsize=(14, 10),
        title="Backtest Result",
    )
    return fig, axes


__all__ = ["plot_ohlcv", "plot_backtest"]
