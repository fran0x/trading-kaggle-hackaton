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

# Download market data (defaults to ETH/USDT, BTC/USDT, ETH/BTC)
just download

# Create strategy archive
just tar

# Run backtest and evaluate strategy
just score

# Custom settings (team name, tokens, initial balances, fee)
# just score [team] [token1] [token2] [fiat] [token1_balance] [token2_balance] [fiat_balance] [fee]
just score myteam SOL AVAX USDC 50 5 1000000 5

# View default configuration
just print
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
| **HODL Comparison** | Performance vs buy-and-hold | Strategy should outperform HODL. |
| **Trading Fees** | Total fees paid in FIAT | Lower is better. Direct cost of trading. |
| **Trade Count** | Number of executed trades | Context-dependent. Shows trading frequency. |
| **Turnover** | Total trading volume | Generally lower is better. Indicates trading frequency and costs. |

### Calculation Details

- **Score** = 0.7 × Sharpe - 0.2 × abs(MaxDrawdown) - 0.1 × (Turnover/1,000,000)
- **Sharpe Ratio** = (Annualized Returns - Risk-Free Rate) / Volatility
- **Maximum Drawdown** = min((equity - running_max) / running_max)
- **Absolute PnL** = Final Equity - Initial Equity
- **Percentage PnL** = (Absolute PnL / Initial Equity) × 100%
- **Turnover** = Sum of all trade notional values in USD
- **HODL Performance** = Value of initial portfolio if held without trading
- **Total Fees Paid** = Sum of all trading fees paid in FIAT

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
  "balances": {                   // Detailed balance information
    "initial": {                  // Initial balances for each asset
      "fiat": 500000.0,
      "token_1": 100.0,
      "token_2": 10.0,
      "total_in_fiat": 510000.0   // Initial portfolio value in FIAT
    },
    "final": {                    // Final balances for each asset
      "fiat": 510000.0,
      "token_1": 95.0,
      "token_2": 9.5,
      "total_in_fiat": 512200.0   // Final portfolio value in FIAT
    }
  },
  "prices": {                     // Market prices
    "initial": {                  // Initial prices used for valuation
      "token_1/fiat": 100.0,
      "token_2/fiat": 40000.0,
      "token_1/token_2": 0.0025
    },
    "final": {                    // Final prices used for valuation
      "token_1/fiat": 120.0,
      "token_2/fiat": 50000.0,
      "token_1/token_2": 0.0024
    }
  },
  "trading": {                    // Trading activity metrics
    "trade_count": 12,            // Total number of executed trades
    "turnover": 105417.47,        // Total trading volume in USD
    "total_fees_paid": 21.08      // Total fees paid in FIAT
  },
  "hodl_pnl": {                   // Buy and hold performance
    "absolute": 1000.0,           // HODL profit/loss in FIAT
    "percentage": 0.2,            // HODL percentage return
    "initial_equity": 510000.0,   // Initial HODL value
    "final_equity": 511000.0      // Final HODL value
  },
  "sharpe": 3.32,                 // Risk-adjusted return measure
  "max_drawdown": -0.013,         // Worst peak-to-trough decline
  "score_components": {           // Score breakdown
    "sharpe_contribution": 2.32,  // 70% of Sharpe
    "drawdown_penalty": 0.0025,   // 20% of abs(max_drawdown)
    "turnover_penalty": 0.011     // 10% of turnover/1M
  }
}
```

The output has been reorganized for better readability, with metrics grouped logically from most important to most detailed. The full equity curve is stored internally but not displayed in the output.

The score prioritizes risk-adjusted returns (70%) while penalizing drawdowns (20%) and excessive trading (10%).

## Market Data Processing

The trading engine processes market data with a sophisticated time-synchronized approach to ensure realistic multi-pair trading:

### Data Synchronization

1. **Chronological Processing**: All market data is processed in strict timestamp order, ensuring a realistic simulation of market conditions.

2. **Cross-Pair Synchronization**: At each timestamp, the engine provides data for all available trading pairs simultaneously:
   - Data from each pair (e.g., ETH/USDT, BTC/USDT, ETH/BTC) is merged and sorted by timestamp
   - For each minute, all pairs with data at that timestamp are grouped together
   - The strategy receives a consolidated view of all markets at each timestamp

3. **Time-Consistent Decisions**: This approach allows strategies to:
   - Make trading decisions based on complete market snapshots
   - Compare prices across different pairs at the exact same moment
   - Implement cross-market strategies like triangular arbitrage

4. **Market Data Format**: For each timestamp, the strategy receives:
   ```python
   {
     "token_1/fiat": {
       "timestamp": 1743292800000,
       "open": 2500.0,
       "high": 2505.0,
       "low": 2495.0,
       "close": 2502.5,
       "volume": 125.5,
       "fee": 0.0002  # Added by the engine
     },
     "token_2/fiat": { ... },
     "token_1/token_2": { ... }
   }
   ```

## Order Execution Model

The trading engine simulates order execution with the following characteristics:

1. **Market Orders Only**: All orders are executed as market orders at the current price (close price from the candle).

2. **Instant Execution**: Orders are executed immediately when the strategy signals a trade, provided there is sufficient balance.

3. **No Slippage**: Orders are always filled exactly at the current market price with no slippage or price impact.

4. **No Partial Fills**: Orders are either completely filled (if enough balance is available) or completely rejected.

5. **Trading Fees**: Each transaction incurs a fee, applied as follows:
   - For buy orders: Total cost = Quantity × Price × (1 + fee)
   - For sell orders: Proceeds = Quantity × Price × (1 - fee)
   - Default fee is 2 basis points (0.02%), but can be customized

6. **Balance Verification**:
   - For buys: Requires sufficient quote currency (usually fiat) including fees
   - For sells: Requires sufficient base currency (token amount)

7. **No Order Book**: There is no simulated order book or limit orders - trades execute against current market prices.

## Strategy Development

### Single-Asset Strategies
Trading strategies for a single asset are implemented in the `strategy/` directory:

1. `strategy/main.py` - Strategy entry point with the required `on_tick` function
2. `strategy/basic.py` - Example mean-reversion strategy implementation

To implement your own single-asset strategy:
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

### Multi-Asset Strategies
For trading across multiple pairs (BTC/USDT, ETH/USDT, ETH/BTC), use the multi-asset framework:

1. `strategy/multi_main.py` - Entry point with the required `on_multi_tick` function
2. `strategy/multi_strategy.py` - Create this to implement custom multi-asset strategies

To implement a multi-asset strategy:
1. Create a `multi_strategy.py` file with a `MultiStrategy` class
2. Implement the `on_tick` method accepting a dictionary of market data for all pairs
3. Return trading signals specifying the trading pair:
   ```python
   # Buy BTC with USDT
   {"pair": "BTC/USDT", "side": "buy", "qty": 0.01}
   
   # Sell ETH for BTC
   {"pair": "ETH/BTC", "side": "sell", "qty": 0.1}
   
   # No action
   None
   ```

### Arbitrage Opportunities
The multi-asset framework enables triangular arbitrage strategies across three connected pairs:

```python
# Example arbitrage check
btc_price = market_data["BTC/USDT"]["close"]
eth_price = market_data["ETH/USDT"]["close"]
eth_btc_price = market_data["ETH/BTC"]["close"]

# Calculate implied ETH/BTC price
implied_eth_btc = eth_price / btc_price

# If actual ETH/BTC price is lower than implied (opportunity to buy ETH with BTC)
if eth_btc_price < implied_eth_btc * 0.995:
    return {"pair": "ETH/BTC", "side": "buy", "qty": 0.1}
```

## Configuration

Edit the `justfile` to customize:
- Trading pairs (e.g., "ETH/USDT", "BTC/USDT", "ETH/BTC")
- Time frame (default: "1m" for 1-minute candles)
- Date range for backtesting
- Team identifier for submissions
- Initial balances for each currency
- Trading fee (in basis points)

Run `just print` to view current configuration settings.

### Initial Balance and Fee Configuration
You can customize initial balances for each token and the trading fee (in basis points, where 1 basis point = 0.01%):

```shell
# Set custom initial balances
# Format: just score [team] [token1] [token2] [fiat] [token1_balance] [token2_balance] [fiat_balance]
just score myteam ETH BTC USDT 100 10 500000

# Set custom trading fee (5 basis points = 0.05%)
# Format: just score [team] [token1] [token2] [fiat] [token1_balance] [token2_balance] [fiat_balance] [fee]
just score myteam ETH BTC USDT 100 10 500000 5

# Set a higher trading fee (10 basis points = 0.1%)
just score myteam ETH BTC USDT 100 10 500000 10
```

Default values can be set in the justfile:
```
# Default balances
TOKEN_1_BALANCE := "100"     # Default ETH balance
TOKEN_2_BALANCE := "10"      # Default BTC balance
FIAT_BALANCE    := "500000"  # Default USDT balance

# Trading parameters
FEE := "2"  # Default fee in basis points (2 = 0.02%)
```

## Docker Support

Build and run the containerized environment:
```shell
just build
docker run -it junz
```

## License

See the [LICENSE](LICENSE) file for details.