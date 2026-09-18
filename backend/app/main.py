"""QuantBeat API.

Two endpoints drive the whole game:

* ``POST /api/round``            -> a fresh round (visible candles only)
* ``POST /api/round/{id}/guess`` -> scores the guess and reveals the future

The future candles and the ground-truth direction live only in the database and
are returned exclusively by the guess endpoint, so a player can't peek ahead by
inspecting network traffic.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .bots import BOT_LABELS
from .config import HORIZON_DAYS, TICKER
from .models import (
    BotInfo,
    BotResult,
    GuessRequest,
    GuessResponse,
    NewRoundResponse,
)

app = FastAPI(title="QuantBeat API", version="1.0.0")

# The Vite dev server runs on a different origin; allow it in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bot_roster() -> list[BotInfo]:
    return [BotInfo(id=bot_id, label=label) for bot_id, label in BOT_LABELS.items()]


@app.get("/api/health")
def health() -> dict:
    with db.connect() as conn:
        db.init_db(conn)
        n = db.count_rounds(conn)
    return {"status": "ok", "ticker": TICKER, "rounds": n}


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

    assert r is not None  # random_round_id just returned this id
    return NewRoundResponse(
        round_id=r.id,
        ticker=TICKER,
        horizon_days=HORIZON_DAYS,
        start_close=r.start_close,
        visible=r.visible,
        bots=_bot_roster(),
    )


@app.post("/api/round/{round_id}/guess", response_model=GuessResponse)
def submit_guess(round_id: int, guess: GuessRequest) -> GuessResponse:
    with db.connect() as conn:
        db.init_db(conn)
        r = db.get_round(conn, round_id)

    if r is None:
        raise HTTPException(status_code=404, detail="Round not found.")

    pct_change = (r.future_close - r.start_close) / r.start_close * 100.0
    bot_results = [
        BotResult(
            id=bot_id,
            label=BOT_LABELS[bot_id],
            direction=direction,
            correct=direction == r.actual_direction,
        )
        for bot_id, direction in r.bot_calls.items()
    ]

    return GuessResponse(
        round_id=r.id,
        your_direction=guess.direction,
        actual_direction=r.actual_direction,
        correct=guess.direction == r.actual_direction,
        start_close=r.start_close,
        future_close=r.future_close,
        pct_change=pct_change,
        future=r.future,
        bot_results=bot_results,
    )
