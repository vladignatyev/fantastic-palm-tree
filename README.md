# Crypto Backtesting Toolkit

This project provides a small Python toolkit for downloading OHLCV data, computing common technical indicators, designing algorithmic strategies, and backtesting them with visualizations. It is structured as a Python package with console scripts for fetching and plotting datasets.

## Requirements and Environment

The project is managed with [uv](https://github.com/astral-sh/uv). To install dependencies and run the console scripts, use:

```bash
uv sync
uv run fetch-ohlcv --help
```

The default Python version is 3.11. Candlestick visualizations are rendered with
[`mplfinance`](https://github.com/matplotlib/mplfinance), which is installed automatically
with the plotting extra (`uv sync` pulls it in by default).

## Console Scripts

Two entry points are available:

- `fetch-ohlcv`: Download OHLCV data from Binance and save it to a TSV file.
- `visualize-ohlcv`: Load a TSV file and visualize the OHLCV candles alongside the equity curve of a backtest (when available)
  using `mplfinance` candlestick charts.

Use `uv run <script>` to execute these commands inside the managed environment.

## Library Overview

The `cryptobot` package contains the following key modules:

- `cryptobot.data.fetch`: Utilities to call the Binance API and return OHLCV data as `pandas.DataFrame` instances.
- `cryptobot.data.io`: Helpers to save and load TSV files with standardized columns.
- `cryptobot.indicators`: Implementations of ATR, ADX, RSI, moving average, and exponential moving average.
- `cryptobot.strategy`: Lightweight abstractions for creating trading strategies and parameter spaces.
- `cryptobot.backtest`: Simulation engine that executes strategies candle by candle, tracks trades, and calculates metrics (PnL, Sharpe, Sortino, maximum drawdown and profit).
- `cryptobot.visualization`: Plotting utilities for datasets and backtest results.

Refer to the inline documentation in each module for usage examples.

## Example Workflow

1. Fetch historical data:
   ```bash
   uv run fetch-ohlcv --symbol BTCUSDT --interval 1h --start "2023-01-01" --end "2023-03-01" --output data/btcusdt-1h.tsv
   ```
2. Visualize the dataset:
   ```bash
   uv run visualize-ohlcv --input data/btcusdt-1h.tsv
   ```
3. Develop or load a strategy (see the sections below) and backtest it with `cryptobot.backtest.run_backtest`.
4. Use `cryptobot.backtest.optimize_strategy` to optimize parameters through SciPy-based optimization routines.

## Manual Usage Without the CLI

All functionality is exposed through the Python API if you prefer writing your own scripts or notebooks. The example below shows
how to load data, calculate indicators, and run a backtest manually:

```python
from cryptobot import Broker, StrategyContext, StrategyParameters, load_ohlcv_tsv, run_backtest
from cryptobot.indicators import IndicatorSet
from my_strategies import MyStrategy  # your custom strategy module

# Load data from disk (TSV produced by fetch-ohlcv)
data = load_ohlcv_tsv("data/btcusdt-1h.tsv")

# Inspect indicators directly
context = StrategyContext(
    timestamp=data.index[-1],
    history=data,
    indicators=IndicatorSet(data),
)
current_rsi = context.indicators.rsi(period=14).iloc[-1]
print("Latest RSI:", current_rsi)

# Run a backtest with your own strategy implementation
my_strategy_instance = MyStrategy()
result = run_backtest(
    data,
    my_strategy_instance,
    params={"example_param": 1.0},
    maker_fee=0.0002,
    taker_fee=0.0004,
)
print(result.metrics)
```

Pass `maker_fee` and `taker_fee` as decimal rates (e.g., 0.0004 = 4 basis points) to account for venue trading costs. These
fees are applied to entries and exits when computing mark-to-market equity, trade-level PnL, and all derived performance
metrics.

When working outside of `uv`, install dependencies manually:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Developing Strategies

Strategies are plain Python callables that receive a [`StrategyContext`](src/cryptobot/strategy.py) and a lightweight
[`Broker`](src/cryptobot/strategy.py) interface. To make a strategy optimizable, provide a `StrategyParameters` definition that
names every tunable parameter and its search bounds. The skeleton below illustrates the recommended structure:

```python
from dataclasses import dataclass

from cryptobot.strategy import Broker, StrategyContext, StrategyParameters


@dataclass
class MyStrategy:
    parameters: StrategyParameters = StrategyParameters(
        names=["fast_window", "slow_window"],
        bounds=[(5, 50), (20, 200)],
    )

    def __call__(self, context: StrategyContext, broker: Broker, params: dict[str, float]) -> None:
        history = context.history
        if history.empty:
            return

        fast = int(params["fast_window"])
        slow = int(params["slow_window"])
        fast_sma = context.indicators.sma(fast)
        slow_sma = context.indicators.sma(slow)

        if fast_sma.iloc[-1] > slow_sma.iloc[-1] and not broker.open_positions:
            broker.open_trade(direction=1, price=history.iloc[-1]["close"], size=1.0, timestamp=context.timestamp)
        elif fast_sma.iloc[-1] < slow_sma.iloc[-1]:
            for trade in list(broker.open_positions):
                broker.close_trade(trade.trade_id, history.iloc[-1]["close"], context.timestamp, reason="signal_flip")
```

Use `run_backtest` to simulate the strategy over any OHLCV `DataFrame`, and `optimize_strategy` to explore the parameter space
using SciPy optimizers. The `StrategyContext` exposes an `IndicatorSet`, so you can call `context.indicators.rsi(...)`,
`context.indicators.atr(...)`, etc., without recomputing them manually.

## Running the Included SMA Crossover Strategy

The repository ships with `examples/sma_crossover.py`, a moving-average crossover strategy that uses ATR-based stops and profit
targets. After fetching data, run the example via `uv`:

```bash
uv run python examples/sma_crossover.py data/btcusdt-1h.tsv --fast 15 --slow 60 --size 2 --atr-mult 2.5
```

The script prints a metrics summary to the console and, unless `--no-plot` is passed, displays the equity curve and price
action using the visualization helpers. You can modify the argument values to test different parameter combinations. If your
market charges trading fees, specify them with `--maker-fee` and `--taker-fee` (decimal rates). The backtester deducts these
costs on every fill and exposes the aggregate value through the `total_fees` metric.

To automatically search for parameters that maximize the Sharpe ratio, enable the `--optimize` flag. The example below starts
the optimization from the provided CLI arguments, runs SciPy's bounded minimizer under the hood, prints the best Sharpe-driven
parameter set, and then reports the corresponding backtest metrics:

```bash
uv run python examples/sma_crossover.py data/btcusdt-1h.tsv --fast 15 --slow 60 --size 1.0 --atr-mult 2.0 --optimize
```

Behind the scenes the script calls `cryptobot.backtest.optimize_strategy` with an objective that returns the negative Sharpe
ratio, so the optimizer searches for the highest Sharpe value supported by the dataset and strategy bounds.

### Example Optimization Session

Once you have a TSV dataset (for example, downloaded with `fetch-ohlcv` into `data/btcusdt-1h.tsv`), you can run a full
optimization session and inspect the results in the terminal. A typical invocation and its output look like:

```bash
uv run python examples/sma_crossover.py data/btcusdt-1h.tsv --fast 20 --slow 80 --size 1.5 --atr-mult 3 --optimize

# Output
Optimizing parameters for Sharpe ratio using SciPy...
Optimized parameters:
  fast_window: 17.2841
  slow_window: 92.5158
  position_size: 1.8325
  atr_multiplier: 2.4127
Backtest metrics:
  sharpe: 1.84
  sortino: 2.47
  pnl: 0.102
  max_drawdown: -0.034
  max_profit: 0.137
  total_fees: 0.018
```

Your output will vary depending on the dataset, but the structure remains the same: the script announces the optimization run,
prints the tuned parameters returned by `optimize_strategy`, and finishes with the full backtest metrics computed from the
best Sharpe ratio found (including total trading fees paid). If you omit `--no-plot`, the optimized run is plotted
automatically so you can visually inspect the equity curve and trade markers produced by the tuned configuration.

