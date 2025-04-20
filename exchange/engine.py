"""CLI: python -m exchange.engine path/to/submission.tgz"""
import argparse, importlib.util, time, tarfile, tempfile, sys, json, os
from pathlib import Path
import numpy as np
import pandas as pd

# --- Helpers -------------------------------------------------------------

def sharpe(returns: np.ndarray, risk_free: float = 0.0):
    excess = returns - risk_free / (365 * 24 * 60)  # per‑minute rf
    return np.sqrt(525600) * excess.mean() / (excess.std(ddof=1) + 1e-9)

def max_drawdown(equity: np.ndarray):
    cummax = np.maximum.accumulate(equity)
    dd = (equity - cummax) / cummax
    return dd.min()

# --- Core Engine ---------------------------------------------------------

def run_multi_backtest(submission_dir: Path, data_dict: dict, broker=None):
    """Run a backtest with multiple trading pairs.
    
    Args:
        submission_dir: Path to the strategy directory
        data_dict: Dictionary of {pair: dataframe} containing market data for each pair
        broker: Optional custom broker instance with initial balances
    """
    sys.path.insert(0, str(submission_dir))
    strat_mod = importlib.import_module("strategy.main")
    
    # Initialize multi-asset broker if not provided
    if broker is None:
        broker = MultiBroker(initial_balance=10_000)  # USD
    
    # Record initial balances for display
    initial_balances = broker.balances.copy()
    
    # Initialize prices with first data point for each pair
    first_prices = {}
    for pair, df in data_dict.items():
        if not df.empty:
            first_prices[pair] = df.iloc[0]['close']
    
    # Calculate true initial portfolio value including all assets
    initial_portfolio_value = initial_balances["fiat"]
    if "token_1/fiat" in first_prices and initial_balances["token_1"] > 0:
        initial_portfolio_value += initial_balances["token_1"] * first_prices["token_1/fiat"]
    if "token_2/fiat" in first_prices and initial_balances["token_2"] > 0:
        initial_portfolio_value += initial_balances["token_2"] * first_prices["token_2/fiat"]
    
    # Start equity history with correct initial portfolio value
    broker.equity_history = [initial_portfolio_value]
    
    # Combine all dataframes and sort by timestamp
    all_data = []
    for pair, df in data_dict.items():
        df = df.copy()
        df['pair'] = pair
        all_data.append(df)
    
    combined_data = pd.concat(all_data)
    combined_data = combined_data.sort_values('timestamp')
    
    # Process data timestamp by timestamp
    for timestamp, group in combined_data.groupby('timestamp'):
        # Update prices for each pair in this timestamp
        market_data = {}
        for _, row in group.iterrows():
            pair = row['pair']
            broker.update_market(pair, row.to_dict())
            data_dict = row.to_dict()
            # Add fee information to market data so strategies can access it
            data_dict["fee"] = broker.fee
            market_data[pair] = data_dict
        
        # Get strategy decision based on all available market data and current balances
        action = strat_mod.on_data(market_data, broker.balances)
        
        # Execute action if any
        if action:
            broker.execute(action)
    
    # Calculate performance metrics
    equity_curve = np.array(broker.equity_history)
    rets = np.diff(equity_curve) / equity_curve[:-1]
    initial_equity = equity_curve[0]
    final_equity = equity_curve[-1]
    absolute_pnl = final_equity - initial_equity
    percentage_pnl = (absolute_pnl / initial_equity) * 100
    
    # Initial and final fiat values are now correctly calculated in the equity curve
    initial_fiat_value = initial_equity
    final_fiat_value = final_equity
    
    # Store current prices for result reporting
    current_prices = {
        "token_1/fiat": broker.prices.get("token_1/fiat"),
        "token_2/fiat": broker.prices.get("token_2/fiat"),
        "token_1/token_2": broker.prices.get("token_1/token_2")
    }
    
    # Calculate what the value would be if we had simply held the initial assets
    hodl_value = initial_balances["fiat"]
    if broker.prices["token_1/fiat"] is not None and initial_balances["token_1"] > 0:
        hodl_value += initial_balances["token_1"] * broker.prices["token_1/fiat"]
    if broker.prices["token_2/fiat"] is not None and initial_balances["token_2"] > 0:
        hodl_value += initial_balances["token_2"] * broker.prices["token_2/fiat"]
    
    # Calculate HODL performance
    hodl_absolute_pnl = hodl_value - initial_equity
    hodl_percentage_pnl = (hodl_absolute_pnl / initial_equity) * 100
    
    # Return results
    return {
        "sharpe": sharpe(rets),
        "max_dd": max_drawdown(equity_curve),
        "turnover": broker.turnover,
        "absolute_pnl": absolute_pnl,
        "percentage_pnl": percentage_pnl,
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "initial_balances": initial_balances,
        "final_balances": broker.balances,
        "initial_fiat_value": initial_fiat_value,
        "final_fiat_value": final_fiat_value,
        "total_fees_paid": broker.total_fees_paid,
        "trade_count": broker.trade_count,
        "current_prices": current_prices,
        "hodl_absolute_pnl": hodl_absolute_pnl,
        "hodl_percentage_pnl": hodl_percentage_pnl,
        "hodl_value": hodl_value,
        "equity_curve": equity_curve.tolist(),
    }

class MultiBroker:
    """Broker supporting multiple trading pairs and currencies."""
    def __init__(self, initial_balance: float = 10_000):
        # Initialize balances for each currency
        self.balances = {
            "fiat": initial_balance,  # Base currency (quote currency)
            "token_1": 0.0,           # Primary token
            "token_2": 0.0            # Secondary token
        }
        
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
        self.equity_history = [initial_balance]
        self.turnover = 0.0
        self.trade_count = 0
        self.total_fees_paid = 0.0  # Track total fees paid
        
        # Trading fee (2 bps = 0.0002 = 0.02%)
        self.fee = 0.0002
    
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

# --- CLI --------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("submission")
    p.add_argument("--token1fiat", help="Path to token_1/fiat data", default="data/token1fiat_1m.parquet")
    p.add_argument("--token2fiat", help="Path to token_2/fiat data", default="data/token2fiat_1m.parquet")
    p.add_argument("--token1token2", help="Path to token_1/token_2 data", default="data/token1token2_1m.parquet")
    p.add_argument("--token1_balance", help="Initial token_1 balance", type=float, default=0.0)
    p.add_argument("--token2_balance", help="Initial token_2 balance", type=float, default=0.0)
    p.add_argument("--fiat_balance", help="Initial fiat balance", type=float, default=10000.0)
    p.add_argument("--fee", help="Trading fee (in basis points, e.g., 2 = 0.02%)", type=float, default=2.0)
    args = p.parse_args()
    
    # Load data for each available pair
    data_dict = {}
    
    if os.path.exists(args.token1fiat):
        data_dict["token_1/fiat"] = pd.read_parquet(args.token1fiat)
    
    if os.path.exists(args.token2fiat):
        data_dict["token_2/fiat"] = pd.read_parquet(args.token2fiat)
    
    if os.path.exists(args.token1token2):
        data_dict["token_1/token_2"] = pd.read_parquet(args.token1token2)
    
    if not data_dict:
        print("Error: No data files found. Please provide at least one valid data file.")
        sys.exit(1)
    
    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(args.submission) as tar:
            tar.extractall(path=td)
            
        # Create MultiBroker with custom initial balances and fee
        broker = MultiBroker(initial_balance=args.fiat_balance)
        broker.balances = {
            "fiat": args.fiat_balance,
            "token_1": args.token1_balance,
            "token_2": args.token2_balance
        }
        # Convert fee from basis points to decimal (e.g., 2 basis points = 0.0002)
        broker.fee = args.fee / 10000
        
        # Reset the equity history - it will be properly initialized in run_multi_backtest
        broker.equity_history = []
        
        # Update the run_multi_backtest function to use our custom broker
        res = run_multi_backtest(Path(td) / "submission", data_dict, broker=broker)
        
        # Calculate score components
        sharpe_component = 0.7 * res["sharpe"]
        drawdown_component = 0.2 * abs(res["max_dd"])
        turnover_component = 0.1 * (res["turnover"] / 1e6)
        
        # Calculate final score
        score = sharpe_component - drawdown_component - turnover_component
        
        # Add score components to the results
        res["score_components"] = {
            "sharpe_contribution": sharpe_component,
            "drawdown_penalty": drawdown_component,
            "turnover_penalty": turnover_component
        }
        res["score"] = score
        
        # Create a copy of results without the equity curve for display
        display_res = res.copy()
        display_res.pop("equity_curve", None)
        
        # Create ordered dictionary with a logical grouping of metrics
        ordered_res = {
            # Top-level performance metric
            "score": display_res.pop("score"),
            
            # PnL metrics - keeping a copy of initial_equity for HODL
            "pnl": {
                "absolute": display_res.pop("absolute_pnl"),
                "percentage": display_res.pop("percentage_pnl"),
                "initial_equity": display_res["initial_equity"],
                "final_equity": display_res.pop("final_equity")
            },
            
            # Balances
            "balances": {
                "initial": {
                    **display_res.pop("initial_balances"),
                    "total_in_fiat": display_res.pop("initial_fiat_value")
                },
                "final": {
                    **display_res.pop("final_balances"),
                    "total_in_fiat": display_res.pop("final_fiat_value")
                }
            },
            
            # Market prices
            "prices": {
                "initial": {
                    "token_1/fiat": broker.first_prices.get("token_1/fiat"),
                    "token_2/fiat": broker.first_prices.get("token_2/fiat"),
                    "token_1/token_2": broker.first_prices.get("token_1/token_2")
                },
                "final": display_res.pop("current_prices")
            },
            
            # Trading activity and performance metrics
            "trading": {
                "sharpe": display_res.pop("sharpe"),
                "max_drawdown": display_res.pop("max_dd"),
                "turnover": display_res.pop("turnover"),
                "trade_count": display_res.pop("trade_count"),
                "total_fees_paid": display_res.pop("total_fees_paid"),
            },
            
            # HODL comparison
            "hodl_pnl": {
                "absolute": display_res.pop("hodl_absolute_pnl"),
                "percentage": display_res.pop("hodl_percentage_pnl"),
                "initial_equity": display_res.pop("initial_equity"),
                "final_equity": display_res.pop("hodl_value")
            },
            
            # Score breakdown
            "score_components": display_res.pop("score_components")
        }
        
        # Format all numeric values to 4 decimal places
        def format_numbers(obj):
            if isinstance(obj, dict):
                return {k: format_numbers(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [format_numbers(item) for item in obj]
            elif isinstance(obj, float):
                # Round to 4 decimal places
                return round(obj, 4)
            else:
                return obj
        
        formatted_res = format_numbers(ordered_res)
        print(json.dumps(formatted_res, indent=2))

if __name__ == "__main__":
    main()