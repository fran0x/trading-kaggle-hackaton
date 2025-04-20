"""Required by the exchange engine."""
import importlib
from pathlib import Path

# Plug‑n‑play: chooses STRATEGY env‑var or defaults to example.
STRATEGY = importlib.import_module(
    "strategy.basic"  # Use fully qualified package name
)

def on_tick(market_data):
    """API guaranteed by the rulebook. Return dict {side, qty} or None."""
    return STRATEGY.on_tick(market_data)