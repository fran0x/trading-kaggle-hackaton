# Trading Framework (Kaggle Hackathon Edition)

A cryptocurrency trading and backtesting framework developed specifically for a **hackathon hosted on [Kaggle](https://www.kaggle.com)**. This project enables participants to build, test, and evaluate algorithmic trading strategies in a structured, extensible environment.

## Overview

This framework enables teams to:

* Develop algorithmic trading strategies for cryptocurrency markets
* Backtest strategies against historical market data
* Evaluate performance using industry-standard metrics
* Package and submit strategies for evaluation in a standardized format

## Project Structure

The project is organized into the following key directories:

* `exchange/` – Core trading engine and backtesting logic
  * `engine.py` – Simulates market conditions and executes trades
* `strategy/` – User-implemented trading strategies
  * `main.py` – Entry point with the `on_data` function
  * Create your own `strategy.py` to develop custom strategies
* `data/` – Historical market data in parquet format
* `scripts/` – Utility scripts
  * `download.py` – Used to download and format market data

## Development Setup

This project uses [just](https://github.com/casey/just) for streamlined development workflows.

To get started:

1. Install `just`
2. Set up the Python environment:

   ```bash
   just install
   ```
3. View available commands:

   ```bash
   just print
   ```

## Quick Start

```shell
# Set up your Python environment (Python 3.11+ recommended)
just install

# Download default market data (ETH/USDT, BTC/USDT, ETH/BTC)
just download

# Package your strategy for submission
just tar

# Run the backtest and score your strategy
just score

# View current configuration
just print
```

## Evaluation Criteria

Strategies will be scored using a combination of profitability, risk-adjusted performance, and trading efficiency. Refer to the [Evaluation Metrics](#evaluation-metrics) section below for full details.

## Submission Format

Participants are required to submit a `.tar.gz` archive of their strategy directory, including the entry point and any custom logic. Use:

```bash
just tar
```

This will produce a submission archive in the required format.
