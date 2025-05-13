"""CLI: python -m exchange.engine path/to/submission.tgz"""
import argparse, importlib.util, time, tarfile, tempfile, sys, json, os
import uuid
from pathlib import Path
import pandas as pd

# --- Core Engine ---------------------------------------------------------

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

        # Get strategy decision based on all available market data and current balances
        actions: list[dict] | None = strat_mod.on_data(market_data, balances)

        if actions is None:
            continue

        # Add action dictionary to result DataFrame
        for action in actions:
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