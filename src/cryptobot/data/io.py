"""Utilities for reading and writing OHLCV data."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_COLUMNS = ["open", "high", "low", "close", "volume"]


def save_ohlcv_tsv(data: pd.DataFrame, path: str | Path) -> None:
    """Save OHLCV data to a TSV file."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = data.copy()
    if output.index.name != "timestamp":
        output.index.name = "timestamp"
    output.reset_index().to_csv(path, sep="\t", index=False)


def load_ohlcv_tsv(path: str | Path) -> pd.DataFrame:
    """Load OHLCV data from a TSV file."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, sep="\t")
    if "timestamp" not in frame.columns:
        raise ValueError("Missing 'timestamp' column in TSV file")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.set_index("timestamp").sort_index()
    missing = [col for col in DEFAULT_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns in TSV file: {missing}")
    return frame


__all__ = ["save_ohlcv_tsv", "load_ohlcv_tsv", "DEFAULT_COLUMNS"]
