"""API request/response schemas."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .config import INSTRUMENTS


class Candle(BaseModel):
    # ``t`` is a sequential bar index, NOT a real date/time. Real timestamps are
    # deliberately withheld so players can't look up the outcome.
    t: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class BotInfo(BaseModel):
    id: str
    label: str


class NewRoundResponse(BaseModel):
    round_id: int
    ticker: str
    interval: str  # human unit for one bar: "day", "minute", ...
    horizon_choices: List[int]
    stake_choices: List[int]
    starting_balance: float
    start_close: float
    visible: List[Candle]
    bots: List[BotInfo]


class GuessRequest(BaseModel):
    instrument: str = Field(..., pattern=f"^({'|'.join(INSTRUMENTS)})$")
    stake: float = Field(..., gt=0)
    horizon: int = Field(..., gt=0)


class BotResult(BaseModel):
    id: str
    label: str
    direction: str
    correct: bool
    pnl: float  # P&L if the bot had traded shares in its direction at the same stake


class GuessResponse(BaseModel):
    round_id: int
    horizon: int
    instrument: str
    stake: float
    your_direction: str
    actual_direction: str
    correct: bool
    start_close: float
    future_close: float
    pct_change: float
    pnl: float
    # Option-only breakdown (null for share trades).
    strike: Optional[float] = None
    premium: Optional[float] = None
    contracts: Optional[float] = None
    payoff: Optional[float] = None
    future: List[Candle]
    bot_results: List[BotResult]
