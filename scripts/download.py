"""Grabs Binance 1‑minute OHLCV via CCXT and saves as Parquet."""
import ccxt
import pandas as pd
import time
import os
import argparse
from datetime import datetime

ONE_MINUTE_IN_MILLIS = 60_000

def fetch(symbol: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """Fetch OHLCV between timestamps (inclusive) in milliseconds."""
    exchange = ccxt.binance()
    frames = []
    since_ts = start_ts
    while since_ts < end_ts:
        since_datetime = datetime.utcfromtimestamp(since_ts / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"Fetching {symbol} market data from {since_datetime}...")
        
        remaining_minutes = (end_ts - since_ts) // ONE_MINUTE_IN_MILLIS
        limit_minutes = min(1000, remaining_minutes)
        batch = exchange.fetch_ohlcv(symbol, timeframe="1m", since=since_ts, limit=limit_minutes)
        if not batch:
            break
        frames.append(pd.DataFrame(batch, columns=["timestamp", "open", "high", "low", "close", "volume"]))

        since_ts = batch[-1][0] + ONE_MINUTE_IN_MILLIS
        time.sleep(exchange.rateLimit / 1000)
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="e.g. BTC/USDT")
    parser.add_argument("--start", type=int, required=True, help="UNIX‑ms")
    parser.add_argument("--end", type=int, required=True, help="UNIX‑ms")
    args = parser.parse_args()

    df = fetch(args.symbol, args.start, args.end)
    os.makedirs("data", exist_ok=True)
    out_path = f"data/{args.symbol.replace('/','').lower()}_1m.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Saved {len(df):,} rows to {out_path}")