"""API request/response schemas."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .config import DIRECTION_DOWN, DIRECTION_UP


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
    start_close: float
    visible: List[Candle]
    bots: List[BotInfo]


class GuessRequest(BaseModel):
    direction: str = Field(..., pattern=f"^({DIRECTION_UP}|{DIRECTION_DOWN})$")
    horizon: int = Field(..., gt=0)


class BotResult(BaseModel):
    id: str
    label: str
    direction: str
    correct: bool


class GuessResponse(BaseModel):
    round_id: int
    horizon: int
    your_direction: str
    actual_direction: str
    correct: bool
    start_close: float
    future_close: float
    pct_change: float
    future: List[Candle]
    bot_results: List[BotResult]
