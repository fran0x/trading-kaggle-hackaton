"""Grabs Binance 1‑minute OHLCV via CCXT and saves as Parquet."""
import ccxt
import pandas as pd
import time
import os
import argparse
from datetime import datetime, timedelta, UTC
from pyrate_limiter import Rate, Limiter

ONE_MINUTE_IN_MILLIS = 60_000

def fetch(symbol: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """Fetch OHLCV between timestamps (inclusive) in milliseconds."""
    exchange = ccxt.binance()
    rate_limiter = Limiter(Rate(exchange.rateLimit, 1), max_delay=1000)
    frames = []
    since_ts = start_ts
    while since_ts < end_ts:
        since_datetime = datetime.utcfromtimestamp(since_ts / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"Fetching {symbol} market data from {since_datetime}...")
        
        remaining_minutes = (end_ts - since_ts) // ONE_MINUTE_IN_MILLIS
        if remaining_minutes == 0:
            break
        limit_minutes = min(1000, remaining_minutes)
        rate_limiter.try_acquire('fetch_ohclv')
        batch = exchange.fetch_ohlcv(symbol, timeframe="1m", since=since_ts, limit=limit_minutes)
        if not batch:
            break
        frames.append(pd.DataFrame(batch, columns=["timestamp", "open", "high", "low", "close", "volume"]))

        since_ts = batch[-1][0] + ONE_MINUTE_IN_MILLIS
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["symbol"] = symbol
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", help="Token pair")
    parser.add_argument("--start", type=int, help="UNIX‑ms", default=int((datetime.now(UTC) - timedelta(days=1)).timestamp() * 1e3))
    parser.add_argument("--end", type=int, help="UNIX‑ms", default=int(datetime.now(UTC).timestamp() * 1e3))
    parser.add_argument("--output", help="Output csv file path")
    args = parser.parse_args()

    df = fetch(args.symbol, args.start, args.end)
    os.makedirs("../data", exist_ok=True)
    
    # Use provided output path or generate default
    if args.output:
        out_path = args.output
    else:
        out_path = f"../data/{args.symbol.replace('/', '').lower()}.csv"
    
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df):,} rows to {out_path}")