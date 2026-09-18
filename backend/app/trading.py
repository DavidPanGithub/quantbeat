"""Instrument pricing and P&L.

Pure functions, no I/O — so both the player's trade and each bot's trade are
scored through the same code, and the maths can be unit-tested in isolation.

Options use a deliberately simplified at-the-money approximation of
Black-Scholes (premium ~= 0.4 * S * sigma * sqrt(T)). This is a game, not a
pricing desk: the goal is believable, asymmetric option payoffs (capped
downside = premium, leveraged upside), not exact fair value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from .config import (
    ATM_PREMIUM_FACTOR,
    DIRECTION_DOWN,
    DIRECTION_UP,
    INSTRUMENT_CALL,
    INSTRUMENT_LONG,
    INSTRUMENT_PUT,
    INSTRUMENT_SHORT,
    MIN_PREMIUM_FRACTION,
)


@dataclass
class TradeOutcome:
    pnl: float
    # Option-only fields (None for shares).
    strike: Optional[float] = None
    premium: Optional[float] = None
    contracts: Optional[float] = None
    payoff: Optional[float] = None


def direction_of(instrument: str) -> str:
    """The bullish/bearish stance an instrument expresses."""
    return DIRECTION_UP if instrument in (INSTRUMENT_LONG, INSTRUMENT_CALL) else DIRECTION_DOWN


def historical_vol(closes: List[float]) -> float:
    """Per-bar volatility: sample stdev of log returns over the window."""
    rets = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var)


def option_premium(price: float, sigma: float, horizon: int) -> float:
    """ATM option premium for the given horizon, floored so it's never ~0."""
    approx = ATM_PREMIUM_FACTOR * price * sigma * math.sqrt(horizon)
    return max(approx, price * MIN_PREMIUM_FRACTION)


def evaluate_trade(
    instrument: str,
    stake: float,
    start_close: float,
    future_close: float,
    premium: float,
) -> TradeOutcome:
    """P&L for staking ``stake`` dollars on ``instrument`` this round.

    Shares are linear in the return. Options spend the whole stake on premiums
    (contracts = stake / premium) for a capped-loss, leveraged-gain payoff.
    """
    ret = (future_close - start_close) / start_close

    if instrument == INSTRUMENT_LONG:
        return TradeOutcome(pnl=stake * ret)
    if instrument == INSTRUMENT_SHORT:
        return TradeOutcome(pnl=stake * -ret)

    # Options are struck at-the-money (strike = entry price).
    strike = start_close
    contracts = stake / premium
    if instrument == INSTRUMENT_CALL:
        payoff = max(0.0, future_close - strike)
    elif instrument == INSTRUMENT_PUT:
        payoff = max(0.0, strike - future_close)
    else:  # pragma: no cover - guarded by request validation
        raise ValueError(f"Unknown instrument: {instrument}")

    pnl = contracts * payoff - stake  # premium already paid = the stake
    return TradeOutcome(
        pnl=pnl,
        strike=strike,
        premium=premium,
        contracts=contracts,
        payoff=payoff,
    )
