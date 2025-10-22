"""Technical indicators used by strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd


def moving_average(data: pd.Series, period: int = 20) -> pd.Series:
    """Simple moving average."""

    return data.rolling(window=period, min_periods=period).mean()


def exponential_moving_average(data: pd.Series, period: int = 20) -> pd.Series:
    """Exponential moving average."""

    return data.ewm(span=period, adjust=False).mean()


def average_true_range(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average true range."""

    high = data["high"]
    low = data["low"]
    close = data["close"].shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - close).abs(),
            (low - close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def _directional_movement(high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    return plus_dm, minus_dm


def average_directional_index(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index (ADX)."""

    high = data["high"]
    low = data["low"]
    close = data["close"]
    plus_dm, minus_dm = _directional_movement(high, low)
    tr = average_true_range(data, period)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx


def relative_strength_index(data: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (RSI)."""

    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


class IndicatorSet:
    """Container that lazily evaluates and caches indicators."""

    def __init__(self, data: pd.DataFrame) -> None:
        self._data = data
        self._cache: dict[tuple[str, int], pd.Series] = {}

    def _cache_key(self, name: str, period: int) -> tuple[str, int]:
        return name.lower(), int(period)

    def atr(self, period: int = 14) -> pd.Series:
        key = self._cache_key("atr", period)
        if key not in self._cache:
            self._cache[key] = average_true_range(self._data, period)
        return self._cache[key]

    def adx(self, period: int = 14) -> pd.Series:
        key = self._cache_key("adx", period)
        if key not in self._cache:
            self._cache[key] = average_directional_index(self._data, period)
        return self._cache[key]

    def rsi(self, period: int = 14) -> pd.Series:
        key = self._cache_key("rsi", period)
        if key not in self._cache:
            self._cache[key] = relative_strength_index(self._data["close"], period)
        return self._cache[key]

    def sma(self, period: int = 20) -> pd.Series:
        key = self._cache_key("sma", period)
        if key not in self._cache:
            self._cache[key] = moving_average(self._data["close"], period)
        return self._cache[key]

    def ema(self, period: int = 20) -> pd.Series:
        key = self._cache_key("ema", period)
        if key not in self._cache:
            self._cache[key] = exponential_moving_average(self._data["close"], period)
        return self._cache[key]


__all__ = [
    "moving_average",
    "exponential_moving_average",
    "average_true_range",
    "average_directional_index",
    "relative_strength_index",
    "IndicatorSet",
]
