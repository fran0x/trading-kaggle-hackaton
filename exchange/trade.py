"""CLI: python -m exchange.engine path/to/submission.tgz"""
import argparse, importlib.util, time, tarfile, tempfile, sys, json, os
import uuid
from pathlib import Path
import pandas as pd

# --- Core Engine ---------------------------------------------------------

class Trader:
    """Trader supporting multiple trading pairs and currencies."""

    def __init__(self, balances, fee):
        # Initialize balances for each currency
        self.balances = balances
        self.fee = fee

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
        self.equity_history = []
        self.turnover = 0.0
        self.trade_count = 0
        self.total_fees_paid = 0.0  # Track total fees paid

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

def run_backtest(submission_dir: Path, combined_data: pd.DataFrame, fee: float, balances: dict[str, float]) -> pd.DataFrame:
    """Run a backtest with multiple trading pairs.

    Args:
        submission_dir: Path to the strategy directory
        combined_data: DataFrame containing market data for multiple pairs
        fee: Trading fee (in basis points, e.g., 2 = 0.02%)
        balances: Dictionary of {pair: amount} containing initial balances
    """
    sys.path.insert(0, str(submission_dir))
    strat_mod = importlib.import_module("strategy.main")

    trader = Trader(balances, fee)

    # Record initial balances for display
    initial_balances = balances.copy()

    # Initialize prices with first data point for each pair
    combined_data.sort_values("timestamp", inplace=True)
    first_prices = {k: df.iloc[0]['close'] for k, df in combined_data.groupby("symbol")}

    # Calculate true initial portfolio value including all assets
    initial_portfolio_value = initial_balances["fiat"]
    if "token_1/fiat" in first_prices and initial_balances["token_1"] > 0:
        initial_portfolio_value += initial_balances["token_1"] * first_prices["token_1/fiat"]
    if "token_2/fiat" in first_prices and initial_balances["token_2"] > 0:
        initial_portfolio_value += initial_balances["token_2"] * first_prices["token_2/fiat"]

    trader.equity_history = [initial_portfolio_value]
    result = pd.DataFrame(
        columns=["id", "timestamp", "pair", "side", "qty"],
    )

    # Process data timestamp by timestamp
    for timestamp, group in combined_data.groupby('timestamp'):
        # Update prices for each pair in this timestamp
        market_data = {
            "fee": fee
        }
        for _, row in group.iterrows():
            pair = row['symbol']
            data_dict = row.to_dict()
            # Add fee information to market data so strategies can access it
            market_data[pair] = data_dict
            trader.update_market(pair, data_dict)

        # Get strategy decision based on all available market data and current balances
        actions: list[dict] | None = strat_mod.on_data(market_data, balances)

        if actions is None:
            continue

        # Add action dictionary to result DataFrame
        for action in actions:
            trader.execute(action)
            action["timestamp"] = timestamp
            action["id"] = str(uuid.uuid4())
            result = pd.concat([result, pd.DataFrame([action])], ignore_index=True)

    return result


# --- CLI --------------------------------------------------------------

def main(args: argparse.Namespace):
    if not os.path.exists(args.data):
        print(f"Error: {args.data} file doesn't exist.")
        sys.exit(1)

    data_df = pd.read_csv(args.data)

    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(args.submission) as tar:
            tar.extractall(path=td)

        # Run backtest
        res = run_backtest(Path(td) / "submission", data_df, args.fee / 10000, {
            "fiat": args.fiat_balance,
            "token_1": args.token1_balance,
            "token_2": args.token2_balance,
        })

        # Save resulting trades to csv
        res.to_csv(args.output, index=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("submission", help="Path to submission file")
    p.add_argument("--data", help="Path to data file", default="test.csv")
    p.add_argument("--output", help="Path to output file", default="submission.csv")
    p.add_argument("--token1_balance", help="Initial token_1 balance", type=float, default=0.0)
    p.add_argument("--token2_balance", help="Initial token_2 balance", type=float, default=0.0)
    p.add_argument("--fiat_balance", help="Initial fiat balance", type=float, default=10000.0)
    p.add_argument("--fee", help="Trading fee (in basis points, e.g., 2 = 0.02%)", type=float, default=2.0)
    args = p.parse_args()

    main(args)