"""QuantBeat API.

Two endpoints drive the whole game:

* ``POST /api/round``            -> a fresh round (visible candles only)
* ``POST /api/round/{id}/guess`` -> scores the guess and reveals the future

A round stores the future for the longest supported horizon. The guess endpoint
slices that future to the horizon the player picked, computes the outcome, and
reveals only those bars — so the future can't be sniffed from network traffic,
and one round works for every horizon.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .bots import BOT_LABELS
from .config import DEFAULT_INTERVAL, DIRECTION_DOWN, DIRECTION_UP, HORIZON_CHOICES, TICKER
from .models import (
    BotInfo,
    BotResult,
    GuessRequest,
    GuessResponse,
    NewRoundResponse,
)

app = FastAPI(title="QuantBeat API", version="1.1.0")

# The Vite dev server runs on a different origin; allow it in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
def new_round() -> NewRoundResponse:
    with db.connect() as conn:
        db.init_db(conn)
        round_id = db.random_round_id(conn)
        if round_id is None:
            raise HTTPException(
                status_code=503,
                detail="No rounds available. Run `python prep.py` to build game data.",
            )
        r = db.get_round(conn, round_id)
        interval = _interval(conn)

    assert r is not None  # random_round_id just returned this id
    return NewRoundResponse(
        round_id=r.id,
        ticker=TICKER,
        interval=interval,
        horizon_choices=HORIZON_CHOICES,
        start_close=r.start_close,
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

    # Slice the stored future down to the chosen horizon and score that.
    revealed = r.future[: guess.horizon]
    future_close = revealed[-1]["close"]
    actual = DIRECTION_UP if future_close >= r.start_close else DIRECTION_DOWN
    pct_change = (future_close - r.start_close) / r.start_close * 100.0

    bot_results = [
        BotResult(
            id=bot_id,
            label=BOT_LABELS[bot_id],
            direction=direction,
            correct=direction == actual,
        )
        for bot_id, direction in r.bot_calls.items()
    ]

    return GuessResponse(
        round_id=r.id,
        horizon=guess.horizon,
        your_direction=guess.direction,
        actual_direction=actual,
        correct=guess.direction == actual,
        start_close=r.start_close,
        future_close=future_close,
        pct_change=pct_change,
        future=revealed,
        bot_results=bot_results,
    )
