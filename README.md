# Trading Framework (Kaggle Hackathon Edition)

A cryptocurrency trading and backtesting framework developed specifically for a **hackathon hosted on [Kaggle](https://www.kaggle.com)**.

This project enables participants to build, test, and evaluate algorithmic trading strategies in a structured, extensible environment.

## Overview

This framework enables teams to:

* Develop algorithmic trading strategies for cryptocurrency markets
* Backtest strategies against historical market data
* Evaluate performance using industry-standard metrics
* Package and submit strategies for evaluation in a standardized format

## Project Structure

The project is organized into the following key directories:

* `exchange/`: core trading engine and backtesting logic
  * `engine.py`: simulates market conditions and executes trades
* `scripts/`: utility scripts
  * `download.py`: used to download and format market data
* `strategy/`: user-implemented trading strategies
  * `main.py`: entry point with the `on_data` function
  * Create your own `strategy.py` to develop custom strategies

## Development Setup

This project uses [just](https://github.com/casey/just) for streamlined development workflows.

To get started:

1. Install `just`
2. Set up the Python environment: `just install`
3. View available commands: `just print`

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

Strategies will be scored using a combination of profitability, risk-adjusted performance, and trading efficiency.

## Submission Format

Participants are required to submit a `.tar.gz` archive of their strategy directory, including the entry point and any custom logic.

To produce a submission archive in the required format run: `just tar`

