from collections import deque

WINDOW = 30  # minutes
THRESHOLD = 2.0  # std‑devs
prices = deque(maxlen=WINDOW)


def on_tick(market_data):
    price = market_data["close"]
    prices.append(price)
    if len(prices) < WINDOW:
        return None
    import numpy as np
    mu, sigma = np.mean(prices), np.std(prices)
    if price < mu - THRESHOLD * sigma:
        return {"side": "buy", "qty": 0.01}
    if price > mu + THRESHOLD * sigma:
        return {"side": "sell", "qty": 0.01}
    return None