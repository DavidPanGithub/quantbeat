"""QuantBeat API.

Two endpoints drive the whole game:

* ``POST /api/round``            -> a fresh round (visible candles only)
* ``POST /api/round/{id}/guess`` -> prices the trade, reveals the future, scores

A round stores the future for the longest supported horizon. The guess endpoint
slices that future to the chosen horizon, prices the chosen instrument off the
volatility of the visible window, and returns the player's P&L plus what each
bot would have made trading shares in its own direction at the same stake — so
the "you vs quants" board is a money contest, not just an accuracy one.

The future candles are returned only by the guess endpoint, so they can't be
sniffed from network traffic, and one round serves every horizon and instrument.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db, trading
from .bots import BOT_LABELS
from .config import (
    ALLOWED_ORIGINS,
    DEFAULT_INTERVAL,
    DIRECTION_DOWN,
    DIRECTION_UP,
    HORIZON_CHOICES,
    INSTRUMENT_LONG,
    INSTRUMENT_SHORT,
    STAKE_CHOICES,
    STARTING_BALANCE,
    TICKER,
)
from .models import (
    BotInfo,
    BotResult,
    GuessRequest,
    GuessResponse,
    NewRoundRequest,
    NewRoundResponse,
)

app = FastAPI(title="QuantBeat API", version="1.2.0")

# Allowed origins come from config (env-driven); localhost in dev, the deployed
# frontend URL in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bot_roster() -> list[BotInfo]:
    return [BotInfo(id=bot_id, label=label) for bot_id, label in BOT_LABELS.items()]


def _interval(conn) -> str:
    return db.get_meta(conn, "interval") or DEFAULT_INTERVAL


@app.get("/api/health")
def health() -> dict:
    with db.connect() as conn:
        db.init_db(conn)
        n = db.count_rounds(conn)
        interval = _interval(conn)
    return {"status": "ok", "ticker": TICKER, "rounds": n, "interval": interval}


@app.post("/api/round", response_model=NewRoundResponse)
def new_round(req: Optional[NewRoundRequest] = None) -> NewRoundResponse:
    req = req or NewRoundRequest()
    with db.connect() as conn:
        db.init_db(conn)
        round_id = db.random_round_id(conn, req.from_date, req.to_date)
        if round_id is None:
            # No round in the chosen era — fall back to the whole history.
            round_id = db.random_round_id(conn)
        if round_id is None:
            raise HTTPException(
                status_code=503,
                detail="No rounds available. Run `python prep.py` to build game data.",
            )
        r = db.get_round(conn, round_id)
        interval = _interval(conn)
        date_min = db.get_meta(conn, "date_min")
        date_max = db.get_meta(conn, "date_max")

    assert r is not None  # random_round_id just returned this id
    return NewRoundResponse(
        round_id=r.id,
        ticker=TICKER,
        interval=interval,
        horizon_choices=HORIZON_CHOICES,
        stake_choices=STAKE_CHOICES,
        starting_balance=STARTING_BALANCE,
        start_close=r.start_close,
        date_min=date_min,
        date_max=date_max,
        visible=r.visible,
        bots=_bot_roster(),
    )


@app.post("/api/round/{round_id}/guess", response_model=GuessResponse)
def submit_guess(round_id: int, guess: GuessRequest) -> GuessResponse:
    if guess.horizon not in HORIZON_CHOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported horizon {guess.horizon}. Choose one of {HORIZON_CHOICES}.",
        )

    with db.connect() as conn:
        db.init_db(conn)
        r = db.get_round(conn, round_id)

    if r is None:
        raise HTTPException(status_code=404, detail="Round not found.")

    # Slice the stored future down to the chosen horizon.
    revealed = r.future[: guess.horizon]
    future_close = revealed[-1]["close"]
    actual = DIRECTION_UP if future_close >= r.start_close else DIRECTION_DOWN
    pct_change = (future_close - r.start_close) / r.start_close * 100.0

    # Price the option off the volatility of the window the player actually saw.
    sigma = trading.historical_vol([c["close"] for c in r.visible])
    premium = trading.option_premium(r.start_close, sigma, guess.horizon)

    outcome = trading.evaluate_trade(
        guess.instrument, guess.stake, r.start_close, future_close, premium
    )
    your_direction = trading.direction_of(guess.instrument)

    # Each bot trades SHARES in its own direction at the same stake, so balances
    # are comparable across the board.
    bot_results = []
    for bot_id, direction in r.bot_calls.items():
        instrument = INSTRUMENT_LONG if direction == DIRECTION_UP else INSTRUMENT_SHORT
        bot_pnl = trading.evaluate_trade(
            instrument, guess.stake, r.start_close, future_close, premium
        ).pnl
        bot_results.append(
            BotResult(
                id=bot_id,
                label=BOT_LABELS[bot_id],
                direction=direction,
                correct=direction == actual,
                pnl=bot_pnl,
            )
        )

    return GuessResponse(
        round_id=r.id,
        horizon=guess.horizon,
        instrument=guess.instrument,
        stake=guess.stake,
        your_direction=your_direction,
        actual_direction=actual,
        correct=your_direction == actual,
        start_close=r.start_close,
        future_close=future_close,
        pct_change=pct_change,
        pnl=outcome.pnl,
        start_date=r.start_date,
        end_date=r.end_date,
        strike=outcome.strike,
        premium=outcome.premium,
        contracts=outcome.contracts,
        payoff=outcome.payoff,
        future=revealed,
        bot_results=bot_results,
    )
