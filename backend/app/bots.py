"""The quant bots the player duels against.

Each bot is a pure function of the *visible* closing prices (the same data the
player sees) and returns a directional call: DIRECTION_UP or DIRECTION_DOWN.
They deliberately never see the future — that keeps the "you vs quant"
scoreboard honest.

Bots are registered in ``BOTS`` (id -> callable). Add a strategy by writing a
function and appending it; nothing else needs to change.
"""
from __future__ import annotations

import random
from typing import Callable, Dict, List

from .config import DIRECTION_DOWN, DIRECTION_UP

# A bot maps a list of closing prices to a direction string.
BotStrategy = Callable[[List[float]], str]


def _sma(values: List[float], window: int) -> float:
    """Simple moving average of the last ``window`` values."""
    window = min(window, len(values))
    return sum(values[-window:]) / window


def momentum(closes: List[float], lookback: int = 20) -> str:
    """Trend-following: if price rose over the lookback, bet it keeps rising."""
    reference = closes[-min(lookback, len(closes))]
    return DIRECTION_UP if closes[-1] >= reference else DIRECTION_DOWN


def mean_reversion(closes: List[float], window: int = 20) -> str:
    """Fade extremes: above the moving average, bet on a pull-back down."""
    return DIRECTION_DOWN if closes[-1] > _sma(closes, window) else DIRECTION_UP


def ma_crossover(closes: List[float], fast: int = 10, slow: int = 30) -> str:
    """Classic crossover: fast average above slow average signals up."""
    return DIRECTION_UP if _sma(closes, fast) > _sma(closes, slow) else DIRECTION_DOWN


def coin_flip(closes: List[float], *, seed: int = 0) -> str:
    """A 50/50 baseline. Seeded so a given round is reproducible on reveal."""
    rng = random.Random(seed if seed else int(closes[-1] * 100))
    return DIRECTION_UP if rng.random() >= 0.5 else DIRECTION_DOWN


# Display metadata lives with the strategy so the frontend can render a label
# without hardcoding it. Order here is the order shown on the scoreboard.
BOTS: Dict[str, BotStrategy] = {
    "momentum": momentum,
    "mean_reversion": mean_reversion,
    "ma_crossover": ma_crossover,
    "coin_flip": coin_flip,
}

BOT_LABELS: Dict[str, str] = {
    "momentum": "Momentum",
    "mean_reversion": "Mean-Reversion",
    "ma_crossover": "MA Crossover",
    "coin_flip": "Coin Flip",
}


def run_all_bots(closes: List[float], round_seed: int) -> Dict[str, str]:
    """Return every bot's directional call for one round's visible closes."""
    calls: Dict[str, str] = {}
    for bot_id, strategy in BOTS.items():
        if bot_id == "coin_flip":
            calls[bot_id] = coin_flip(closes, seed=round_seed)
        else:
            calls[bot_id] = strategy(closes)
    return calls
