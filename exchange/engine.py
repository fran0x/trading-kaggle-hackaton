"""CLI: python -m exchange.engine path/to/submission.tgz"""
import argparse, importlib.util, runpy, time, tarfile, tempfile, sys, json
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

def run_backtest(submission_dir: Path, data: pd.DataFrame):
    """Import submission.strategy.main.entrypoint and stream data row by row."""
    sys.path.insert(0, str(submission_dir))
    strat_mod = importlib.import_module("strategy.main")
    broker = SimpleBroker(initial_balance=10_000)  # USD
    for _, row in data.iterrows():
        price = row["close"]
        broker.update_market(price)
        action = strat_mod.on_tick(row.to_dict())
        if action:
            broker.execute(action)
    equity_curve = np.array(broker.equity_history)
    rets = np.diff(equity_curve) / equity_curve[:-1]
    initial_equity = equity_curve[0]
    final_equity = equity_curve[-1]
    absolute_pnl = final_equity - initial_equity
    percentage_pnl = (absolute_pnl / initial_equity) * 100
    
    return {
        "sharpe": sharpe(rets),
        "max_dd": max_drawdown(equity_curve),
        "turnover": broker.turnover,
        "absolute_pnl": absolute_pnl,
        "percentage_pnl": percentage_pnl,
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "equity_curve": equity_curve.tolist(),
    }

class SimpleBroker:
    def __init__(self, initial_balance: float):
        self.cash = initial_balance
        self.pos = 0.0  # asset units
        self.equity_history = [initial_balance]
        self.turnover = 0.0
    def update_market(self, price):
        self.price = price
        self.equity_history.append(self.cash + self.pos * price)
    def execute(self, order):
        side, qty = order["side"], float(order["qty"])
        if side == "buy":
            cost = qty * self.price * 1.0002  # 2 bps fee
            if self.cash >= cost:
                self.cash -= cost
                self.pos += qty
                self.turnover += cost
        elif side == "sell":
            if self.pos >= qty:
                proceeds = qty * self.price * 0.9998
                self.cash += proceeds
                self.pos -= qty
                self.turnover += qty * self.price

# --- CLI --------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("submission")
    p.add_argument("--data", default="data/btcusdt_1m.parquet")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as td:
        with tarfile.open(args.submission) as tar:
            tar.extractall(path=td)
        res = run_backtest(Path(td) / "submission", pd.read_parquet(args.data))
        
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
            
            # PnL metrics
            "pnl": {
                "absolute": display_res.pop("absolute_pnl"),
                "percentage": display_res.pop("percentage_pnl"),
                "initial_equity": display_res.pop("initial_equity"),
                "final_equity": display_res.pop("final_equity")
            },
            
            # Risk-adjusted return
            "sharpe": display_res.pop("sharpe"),
            
            # Risk metric
            "max_drawdown": display_res.pop("max_dd"),
            
            # Trading activity
            "turnover": display_res.pop("turnover"),
            
            # Score breakdown
            "score_components": display_res.pop("score_components")
        }
        
        print(json.dumps(ordered_res, indent=2))

if __name__ == "__main__":
    main()
