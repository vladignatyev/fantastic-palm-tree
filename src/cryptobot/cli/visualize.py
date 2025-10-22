"""Console script to visualize OHLCV data."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..data.io import load_ohlcv_tsv
from ..visualization import plot_ohlcv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize OHLCV data from TSV")
    parser.add_argument("--input", required=True, help="Path to TSV file")
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the plot instead of saving to disk",
    )
    parser.add_argument(
        "--output",
        help="Optional output image path (PNG). If omitted and --show is not set, defaults to <input>.png",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_ohlcv_tsv(Path(args.input))
    fig, _ = plot_ohlcv(data)

    if args.show:
        import matplotlib.pyplot as plt  # Local import to avoid hard dependency when not plotting

        plt.show()
    else:
        output = Path(args.output) if args.output else Path(args.input).with_suffix(".png")
        fig.savefig(output)
        print(f"Saved visualization to {output}")


if __name__ == "__main__":  # pragma: no cover
    main()
