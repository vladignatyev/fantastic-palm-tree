"""Example strategy using the cryptobot toolkit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pandas as pd

from cryptobot.backtest import optimize_strategy, run_backtest
from cryptobot.data.io import load_ohlcv_tsv
from cryptobot.strategy import Broker, StrategyContext, StrategyParameters
from cryptobot.visualization import plot_backtest


@dataclass
class SmaCrossoverStrategy:
    """Simple moving-average crossover strategy with ATR-based exits."""

    parameters: StrategyParameters = field(
        default_factory=lambda: StrategyParameters(
            names=["fast_window", "slow_window", "position_size", "atr_multiplier"],
            bounds=[(5, 60), (20, 200), (0.1, 5.0), (1.0, 5.0)],
        )
    )

    def __call__(self, context: StrategyContext, broker: Broker, params: dict[str, float]) -> None:
        history = context.history
        if history.empty:
            return

        fast_period = max(1, int(params["fast_window"]))
        slow_period = max(fast_period + 1, int(params["slow_window"]))
        size = float(params["position_size"])
        atr_multiplier = float(params["atr_multiplier"])

        fast_series = context.indicators.sma(fast_period)
        slow_series = context.indicators.sma(slow_period)

        if len(fast_series) < 2 or len(slow_series) < 2:
            return

        fast_prev, fast_curr = fast_series.iloc[-2], fast_series.iloc[-1]
        slow_prev, slow_curr = slow_series.iloc[-2], slow_series.iloc[-1]

        if pd.isna(fast_prev) or pd.isna(fast_curr) or pd.isna(slow_prev) or pd.isna(slow_curr):
            return

        close_price = history.iloc[-1]["close"]
        atr_series = context.indicators.atr(period=14)
        atr_value = atr_series.iloc[-1]
        if pd.isna(atr_value) or atr_value == 0:
            atr_value = close_price * 0.01

        has_long = any(trade.direction == 1 for trade in broker.open_positions)

        # Bullish crossover: fast SMA crosses above slow SMA.
        if not has_long and fast_prev <= slow_prev and fast_curr > slow_curr:
            broker.open_trade(
                direction=1,
                price=close_price,
                size=size,
                timestamp=context.timestamp,
                take_profit=close_price + atr_multiplier * atr_value,
                stop_loss=close_price - atr_multiplier * atr_value,
            )
            return

        # Bearish crossover: fast SMA crosses below slow SMA.
        if has_long and fast_prev >= slow_prev and fast_curr < slow_curr:
            for trade in list(broker.open_positions):
                broker.close_trade(trade.trade_id, close_price, context.timestamp, reason="bearish_cross")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SMA crossover strategy on a TSV dataset.")
    parser.add_argument("input", type=str, help="Path to the TSV file produced by fetch-ohlcv.")
    parser.add_argument("--fast", type=float, default=20, help="Fast SMA window length.")
    parser.add_argument("--slow", type=float, default=50, help="Slow SMA window length.")
    parser.add_argument("--size", type=float, default=1.0, help="Position size in units.")
    parser.add_argument(
        "--atr-mult", type=float, default=2.0, help="ATR multiplier for stop-loss/take-profit placement."
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip plotting the backtest results (useful in headless environments).",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run SciPy-based parameter optimization to maximize Sharpe ratio before the final backtest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_ohlcv_tsv(args.input)

    strategy = SmaCrossoverStrategy()
    params = {
        "fast_window": args.fast,
        "slow_window": args.slow,
        "position_size": args.size,
        "atr_multiplier": args.atr_mult,
    }
    if args.optimize:
        print("Optimizing parameters for Sharpe ratio using SciPy...")

        def negative_sharpe(result):
            sharpe = result.metrics.get("sharpe")
            return -sharpe if sharpe is not None and not pd.isna(sharpe) else 1e9

        best_values, best_result = optimize_strategy(
            data,
            strategy,
            objective=negative_sharpe,
            initial_guess=[
                params["fast_window"],
                params["slow_window"],
                params["position_size"],
                params["atr_multiplier"],
            ],
        )
        params = strategy.parameters.to_dict(best_values)
        result = best_result
        print("Optimized parameters:")
        for name, value in params.items():
            print(f"  {name}: {value:.4f}")
    else:
        result = run_backtest(data, strategy, params)

    print("Backtest metrics:")
    for key, value in result.metrics.items():
        print(f"  {key}: {value}")

    if not args.no_plot:
        fig, _ = plot_backtest(data, result)
        import matplotlib.pyplot as plt  # Imported lazily to avoid unnecessary dependency when running headless

        plt.show()


if __name__ == "__main__":
    main()
