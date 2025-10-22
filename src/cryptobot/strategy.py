"""Strategy primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

import pandas as pd

from .indicators import IndicatorSet


@dataclass
class StrategyParameters:
    """A parameter grid definition."""

    names: list[str]
    bounds: list[tuple[float, float]]

    def to_dict(self, values: Iterable[float]) -> dict[str, float]:
        return {name: float(value) for name, value in zip(self.names, values)}


@dataclass
class StrategyContext:
    """Read-only view passed to strategy callbacks."""

    timestamp: pd.Timestamp
    history: pd.DataFrame
    indicators: IndicatorSet


class Broker:
    """Simple broker interface for strategy execution."""

    def __init__(self) -> None:
        self._open_positions: dict[int, Trade] = {}
        self._closed: list[ClosedTrade] = []
        self._next_id = 1

    @property
    def open_positions(self) -> list["Trade"]:
        return list(self._open_positions.values())

    @property
    def closed_positions(self) -> list["ClosedTrade"]:
        return self._closed

    def open_trade(
        self,
        direction: int,
        price: float,
        size: float,
        timestamp: pd.Timestamp,
        take_profit: float | None = None,
        stop_loss: float | None = None,
    ) -> "Trade":
        trade = Trade(
            trade_id=self._next_id,
            direction=direction,
            entry_price=price,
            size=size,
            entry_time=timestamp,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )
        self._open_positions[self._next_id] = trade
        self._next_id += 1
        return trade

    def close_trade(
        self,
        trade_id: int,
        price: float,
        timestamp: pd.Timestamp,
        reason: str = "manual",
    ) -> "ClosedTrade":
        trade = self._open_positions.pop(trade_id)
        closed = ClosedTrade(
            trade_id=trade.trade_id,
            direction=trade.direction,
            entry_price=trade.entry_price,
            exit_price=price,
            size=trade.size,
            entry_time=trade.entry_time,
            exit_time=timestamp,
            take_profit=trade.take_profit,
            stop_loss=trade.stop_loss,
            reason=reason,
        )
        self._closed.append(closed)
        return closed


@dataclass
class Trade:
    trade_id: int
    direction: int  # 1 long, -1 short
    entry_price: float
    size: float
    entry_time: pd.Timestamp
    take_profit: float | None = None
    stop_loss: float | None = None


@dataclass
class ClosedTrade:
    trade_id: int
    direction: int
    entry_price: float
    exit_price: float
    size: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    take_profit: float | None
    stop_loss: float | None
    reason: str

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.direction * self.size


class Strategy(Protocol):
    """Callable strategy interface."""

    parameters: StrategyParameters

    def __call__(self, context: StrategyContext, broker: Broker, params: dict[str, float]) -> None:  # pragma: no cover - protocol
        ...


__all__ = [
    "Strategy",
    "StrategyContext",
    "StrategyParameters",
    "Broker",
    "Trade",
    "ClosedTrade",
]
