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
    return {
        "sharpe": sharpe(rets),
        "max_dd": max_drawdown(equity_curve),
        "turnover": broker.turnover,
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
        score = 0.7 * res["sharpe"] - 0.2 * abs(res["max_dd"]) - 0.1 * (res["turnover"] / 1e6)
        print(json.dumps({**res, "score": score}, indent=2))

if __name__ == "__main__":
    main()
