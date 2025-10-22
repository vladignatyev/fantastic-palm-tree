"""Top-level package for the crypto backtesting toolkit."""

from .data.fetch import fetch_ohlcv
from .data.io import load_ohlcv_tsv, save_ohlcv_tsv
from .indicators import (
    average_directional_index,
    average_true_range,
    exponential_moving_average,
    moving_average,
    relative_strength_index,
)
from .strategy import Strategy, StrategyContext, StrategyParameters
from .backtest import BacktestResult, run_backtest, optimize_strategy
from .visualization import plot_backtest, plot_ohlcv

__all__ = [
    "fetch_ohlcv",
    "load_ohlcv_tsv",
    "save_ohlcv_tsv",
    "average_directional_index",
    "average_true_range",
    "exponential_moving_average",
    "moving_average",
    "relative_strength_index",
    "Strategy",
    "StrategyContext",
    "StrategyParameters",
    "BacktestResult",
    "run_backtest",
    "optimize_strategy",
    "plot_backtest",
    "plot_ohlcv",
]
