"""CLI: python -m exchange.engine path/to/submission.tgz"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

# --- Helpers -------------------------------------------------------------

MINUTES_PER_YEAR = 365 * 24 * 60
ANNUALIZATION_FACTOR = np.sqrt(MINUTES_PER_YEAR)
EPSILON = 1e-9
DEFAULT_RISK_FREE = 0.0
DEFAULT_FEE = 0.0002  # 2 bps = 0.0002 = 0.02%


def sharpe(returns: np.ndarray, risk_free: float = DEFAULT_RISK_FREE):
    excess = returns - risk_free / MINUTES_PER_YEAR  # per‑minute rf
    return ANNUALIZATION_FACTOR * excess.mean() / (excess.std(ddof=1) + EPSILON)


def max_drawdown(equity: np.ndarray):
    cummax = np.maximum.accumulate(equity)
    dd = (equity - cummax) / cummax
    return dd.min()


# --- Core Engine ---------------------------------------------------------

class Trader:
    """Trader supporting multiple trading pairs and currencies."""

    def __init__(self):
        # Initialize balances for each currency
        self.balances = {"fiat": 0.0, "token_1": 0.0, "token_2": 0.0}

        # Track market prices for each pair
        self.prices = {
            "token_1/fiat": None,
            "token_2/fiat": None,
            "token_1/token_2": None
        }

        # First and last prices for reporting
        self.first_prices = {
            "token_1/fiat": None,
            "token_2/fiat": None,
            "token_1/token_2": None
        }

        # Store the first update timestamp for each pair
        self.first_update = {
            "token_1/fiat": False,
            "token_2/fiat": False,
            "token_1/token_2": False
        }

        # Track portfolio value history
        self.equity_history = 0.0
        self.turnover = 0.0
        self.trade_count = 0
        self.total_fees_paid = 0.0  # Track total fees paid

        # Trading fee
        self.fee = DEFAULT_FEE

    def update_market(self, pair, price_data):
        """Update market prices for a specific trading pair"""
        # Store the updated price
        self.prices[pair] = price_data["close"]

        # Store first price for each pair (for reporting)
        if not self.first_update[pair]:
            self.first_prices[pair] = price_data["close"]
            self.first_update[pair] = True

        # Calculate total portfolio value (in fiat)
        equity = self.calculate_portfolio_value()
        self.equity_history.append(equity)

    def calculate_portfolio_value(self):
        """Calculate total portfolio value in fiat currency"""
        value = self.balances["fiat"]

        # Add token_1 value if we have price data
        if self.prices["token_1/fiat"] is not None:
            value += self.balances["token_1"] * self.prices["token_1/fiat"]

        # Add token_2 value if we have price data
        if self.prices["token_2/fiat"] is not None:
            value += self.balances["token_2"] * self.prices["token_2/fiat"]
        # If token_2/fiat price not available but token_1/fiat and token_1/token_2 are available
        elif self.prices["token_1/fiat"] is not None and self.prices["token_1/token_2"] is not None:
            token2_value_in_token1 = self.balances["token_2"] / self.prices["token_1/token_2"]
            value += token2_value_in_token1 * self.prices["token_1/fiat"]

        return value

    def execute(self, order):
        """Execute a trading order across any supported pair"""
        pair = order["pair"]  # e.g., "token_1/fiat"
        side = order["side"]  # "buy" or "sell"
        qty = float(order["qty"])

        # Split the pair into base and quote currencies
        base, quote = pair.split("/")

        # Get current price for the pair
        price = self.prices[pair]
        if price is None:
            return  # Can't trade without a price

        executed = False

        if side == "buy":
            # Calculate total cost including fee
            base_cost = qty * price
            fee_amount = base_cost * self.fee
            total_cost = base_cost + fee_amount

            # Check if we have enough of the quote currency
            if self.balances[quote] >= total_cost:
                # Deduct quote currency (e.g., fiat)
                self.balances[quote] -= total_cost

                # Add base currency (e.g., token_1)
                self.balances[base] += qty

                # Track turnover and fees
                self.turnover += total_cost
                self.total_fees_paid += fee_amount
                executed = True

        elif side == "sell":
            # Check if we have enough of the base currency
            if self.balances[base] >= qty:
                # Calculate proceeds after fee
                base_proceeds = qty * price
                fee_amount = base_proceeds * self.fee
                net_proceeds = base_proceeds - fee_amount

                # Add quote currency (e.g., fiat)
                self.balances[quote] += net_proceeds

                # Deduct base currency (e.g., token_1)
                self.balances[base] -= qty

                # Track turnover and fees
                self.turnover += base_proceeds
                self.total_fees_paid += fee_amount
                executed = True

        # Count successful trades
        if executed:
            self.trade_count += 1

def score(solution: pd.DataFrame, submission: pd.DataFrame, row_id_column_name: str, fee: float, fiat_balance: float, token1_balance: float, token2_balance: float) -> float:
    """Score trading strategy"""
    # Initialize multi-asset trader
    trader = Trader()  # USD
    trader.balances = {
        "fiat": fiat_balance,
        "token_1": token1_balance,
        "token_2": token2_balance,
    }
    trader.fee = fee / 10000

    # Record initial balances for display
    initial_balances = trader.balances.copy()

    # Initialize prices with first data point for each pair
    solution.sort_values("timestamp", inplace=True)
    first_prices = {k: df.iloc[0]['close'] for k, df in solution.groupby("symbol")}

    # Calculate true initial portfolio value including all assets
    initial_portfolio_value = initial_balances["fiat"]
    if "token_1/fiat" in first_prices and initial_balances["token_1"] > 0:
        initial_portfolio_value += initial_balances["token_1"] * first_prices["token_1/fiat"]
    if "token_2/fiat" in first_prices and initial_balances["token_2"] > 0:
        initial_portfolio_value += initial_balances["token_2"] * first_prices["token_2/fiat"]

    # Start equity history with correct initial portfolio value
    trader.equity_history = [initial_portfolio_value]

    # Process data timestamp by timestamp
    for timestamp, group in solution.groupby('timestamp'):
        for _, row in group.iterrows():
            trader.update_market(row["symbol"], row.to_dict())

        # Get strategy decision based on all available market data and current balances
        for _, row in submission.iterrows():
            trader.execute(row.to_dict())

    # Calculate performance metrics
    equity_curve = np.array(trader.equity_history)
    rets = np.diff(equity_curve) / equity_curve[:-1]

    # Return results
    res = {
        "sharpe": sharpe(rets),
        "max_dd": max_drawdown(equity_curve),
        "turnover": trader.turnover,
    }

    # Calculate score components
    sharpe_component = 0.7 * res["sharpe"]
    drawdown_component = 0.2 * abs(res["max_dd"])
    turnover_component = 0.1 * (res["turnover"] / 1e6)

    # Calculate final score
    score = sharpe_component - drawdown_component - turnover_component

    return score


# --- CLI --------------------------------------------------------------

def main(args: argparse.Namespace):
    if not os.path.exists(args.data):
        print(f"Error: {args.data} file doesn't exist.")
        sys.exit(1)

    data_df = pd.read_csv(args.data)

    if not os.path.exists(args.submission):
        print(f"Error: {args.submission} file doesn't exist.")
        sys.exit(1)

    submission_df = pd.read_csv(args.submission)

    res = score(data_df, submission_df, "", args.fee, args.fiat_balance, args.token1_balance, args.token2_balance)

    print(f"score: {res}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("submission", help="Path to submission file")
    p.add_argument("--data", help="Path to data file", default="test.csv")
    p.add_argument("--token1_balance", help="Initial token_1 balance", type=float, default=0.0)
    p.add_argument("--token2_balance", help="Initial token_2 balance", type=float, default=0.0)
    p.add_argument("--fiat_balance", help="Initial fiat balance", type=float, default=10000.0)
    p.add_argument("--fee", help="Trading fee (in basis points, e.g., 2 = 0.02%)", type=float, default=2.0)
    args = p.parse_args()

    main(args)