"""Helpers for downloading OHLCV data from public crypto APIs."""

from __future__ import annotations

import datetime as dt
from typing import Iterable, Optional

import pandas as pd
import requests

BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"


class BinanceError(RuntimeError):
    """Raised when Binance returns an error response."""


_INTERVAL_ALIASES = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}


def _to_milliseconds(value: dt.datetime | str) -> int:
    if isinstance(value, str):
        value = dt.datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return int(value.timestamp() * 1000)


def _chunk_timerange(
    start: dt.datetime,
    end: dt.datetime,
    limit: int,
    interval_ms: int,
) -> Iterable[tuple[int, int]]:
    """Yield timestamp ranges respecting Binance's limit parameter."""

    start_ms = _to_milliseconds(start)
    end_ms = _to_milliseconds(end)
    step = limit * interval_ms
    cursor = start_ms
    while cursor < end_ms:
        yield cursor, min(cursor + step - interval_ms, end_ms)
        cursor += step


def _interval_to_milliseconds(interval: str) -> int:
    unit = interval[-1]
    amount = int(interval[:-1])
    match unit:
        case "m":
            return amount * 60_000
        case "h":
            return amount * 3_600_000
        case "d":
            return amount * 86_400_000
        case "w":
            return amount * 604_800_000
        case "M":
            return amount * 2_592_000_000  # approximate month (30 days)
        case _:
            raise ValueError(f"Unsupported interval unit: {unit}")


def fetch_ohlcv(
    symbol: str,
    interval: str,
    start: dt.datetime | str,
    end: dt.datetime | str,
    limit: int = 1000,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """Fetch OHLCV data from Binance.

    Parameters
    ----------
    symbol:
        Trading symbol, e.g. ``"BTCUSDT"``.
    interval:
        Candle interval supported by Binance (``1h``, ``1d``, etc.).
    start, end:
        Datetime bounds. Naive datetimes are interpreted as UTC.
    limit:
        Binance limit per response (maximum 1000).
    session:
        Optional requests session for connection pooling.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by datetime with columns open, high, low, close, volume.
    """

    if interval not in _INTERVAL_ALIASES:
        raise ValueError(f"Unsupported interval: {interval}")

    if isinstance(start, str):
        start_dt = dt.datetime.fromisoformat(start)
    else:
        start_dt = start
    if isinstance(end, str):
        end_dt = dt.datetime.fromisoformat(end)
    else:
        end_dt = end

    if end_dt <= start_dt:
        raise ValueError("end must be after start")

    interval_ms = _interval_to_milliseconds(interval)
    sess = session or requests.Session()
    frames: list[pd.DataFrame] = []
    for chunk_start, chunk_end in _chunk_timerange(start_dt, end_dt, limit, interval_ms):
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": chunk_start,
            "endTime": chunk_end,
            "limit": limit,
        }
        response = sess.get(BINANCE_BASE_URL, params=params, timeout=30)
        if response.status_code != 200:
            raise BinanceError(
                f"Binance API error ({response.status_code}): {response.text}"
            )
        raw = response.json()
        if not raw:
            break
        frame = pd.DataFrame(
            raw,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_base",
                "taker_quote",
                "ignore",
            ],
        )
        frame = frame[["open_time", "open", "high", "low", "close", "volume"]]
        frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
        numeric_cols = ["open", "high", "low", "close", "volume"]
        frame[numeric_cols] = frame[numeric_cols].astype(float)
        frames.append(frame)

    if session is None:
        sess.close()

    if not frames:
        raise BinanceError("No data returned for the given parameters")

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values("open_time").drop_duplicates("open_time")
    data = data.set_index("open_time").rename_axis("timestamp")
    return data


__all__ = ["fetch_ohlcv", "BinanceError"]
