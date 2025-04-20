# Junz Trading Framework

A backtesting framework for cryptocurrency trading strategies with a simple, extensible architecture.

## Overview

Junz is a trading strategy evaluation framework that allows you to:
- Develop algorithmic trading strategies for cryptocurrency markets
- Backtest strategies against historical market data
- Evaluate performance with industry-standard metrics
- Deploy strategies in a containerized environment

## Quick Start

```shell
# Install dependencies
just install

# Download market data (defaults to BTC/USDT)
just download

# Create strategy archive
just tar

# Run backtest and evaluate strategy
just score
```

## Evaluation Metrics

Strategies are evaluated using several key performance metrics:

### Primary Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| **Score** | Combined performance metric | Higher is better. Weighted combination of other metrics. |
| **Sharpe Ratio** | Risk-adjusted return | Higher is better. Measures excess return per unit of risk. |
| **Maximum Drawdown** | Largest peak-to-trough decline | Closer to zero is better. Represents worst-case scenario. |
| **Profit and Loss (PnL)** | Absolute and percentage returns | Higher is better. Shows raw profitability. |
| **Turnover** | Total trading volume | Generally lower is better. Indicates trading frequency and costs. |

### Calculation Details

- **Score** = 0.7 × Sharpe - 0.2 × abs(MaxDrawdown) - 0.1 × (Turnover/1,000,000)
- **Sharpe Ratio** = (Annualized Returns - Risk-Free Rate) / Volatility
- **Maximum Drawdown** = min((equity - running_max) / running_max)
- **Absolute PnL** = Final Equity - Initial Equity
- **Percentage PnL** = (Absolute PnL / Initial Equity) × 100%
- **Turnover** = Sum of all trade notional values in USD

### Output Analysis

The scoring output provides detailed metrics for strategy evaluation:

```json
{
  "score": 2.31,                  // Final combined performance score
  "pnl": {                        // Profit and Loss metrics
    "absolute": 22.12,            // Raw profit in USD
    "percentage": 0.22,           // Percentage return
    "initial_equity": 10000.0,    // Starting capital
    "final_equity": 10022.12      // Ending capital
  },
  "sharpe": 3.32,                 // Risk-adjusted return measure
  "max_drawdown": -0.013,         // Worst peak-to-trough decline
  "turnover": 105417.47,          // Total trading volume in USD
  "score_components": {           // Score breakdown
    "sharpe_contribution": 2.32,  // 70% of Sharpe
    "drawdown_penalty": 0.0025,   // 20% of abs(max_drawdown)
    "turnover_penalty": 0.011     // 10% of turnover/1M
  }
}
```

The output has been reorganized for better readability, with metrics grouped logically from most important to most detailed. The full equity curve is stored internally but not displayed in the output.

The score prioritizes risk-adjusted returns (70%) while penalizing drawdowns (20%) and excessive trading (10%).

## Strategy Development

Trading strategies are implemented in the `strategy/` directory:

1. `strategy/main.py` - Strategy entry point with the required `on_tick` function
2. `strategy/basic.py` - Example mean-reversion strategy implementation

To implement your own strategy:
1. Modify `basic.py` or create your own strategy module
2. Return trading signals from the `on_tick` function in this format:
   ```python
   # Buy signal
   {"side": "buy", "qty": 0.01}
   
   # Sell signal
   {"side": "sell", "qty": 0.01}
   
   # No action
   None
   ```

## Configuration

Edit the `justfile` to customize:
- Trading symbol (e.g., "BTC/USDT", "ETH/USDT")
- Time frame (default: "1m" for 1-minute candles)
- Date range for backtesting
- Team identifier for submissions

Run `just print` to view current configuration settings.

## Docker Support

Build and run the containerized environment:
```shell
just build
docker run -it junz
```

## License

See the [LICENSE](LICENSE) file for details.