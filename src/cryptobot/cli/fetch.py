"""Console script to fetch OHLCV data."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..data.fetch import fetch_ohlcv
from ..data.io import save_ohlcv_tsv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch OHLCV data and store as TSV.")
    parser.add_argument("--symbol", required=True, help="Trading symbol, e.g. BTCUSDT")
    parser.add_argument(
        "--interval",
        required=True,
        help="Candle interval (1m, 5m, 1h, 1d, etc.)",
    )
    parser.add_argument("--start", required=True, help="Start date (ISO format)")
    parser.add_argument("--end", required=True, help="End date (ISO format)")
    parser.add_argument(
        "--output",
        required=True,
        help="Output TSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = fetch_ohlcv(args.symbol, args.interval, args.start, args.end)
    save_ohlcv_tsv(data, Path(args.output))
    print(f"Saved {len(data)} rows to {args.output}")


if __name__ == "__main__":  # pragma: no cover
    main()
