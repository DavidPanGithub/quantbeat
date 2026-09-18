"""Central game configuration.

Kept in one place so the data-prep step and the API agree on the same window
sizes, and so there are no magic numbers scattered across the codebase.

The engine forecasts a number of *bars* ahead, not a hardcoded number of days.
A bar is whatever the loaded data is (daily, hourly, minute) — the human-facing
unit label is stored alongside the data at prep time.
"""
import os
from pathlib import Path

# --- CORS ------------------------------------------------------------------
# Comma-separated origins allowed to call the API. Defaults to the local Vite
# dev server; set ALLOWED_ORIGINS in production to your deployed frontend URL.
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if o.strip()
]

# --- Data source -----------------------------------------------------------
TICKER = "TSLA"
STOOQ_URL = "https://stooq.com/q/d/l/?s=tsla.us&i=d"

# --- Storage ---------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "quantbeat.db"

# --- Round geometry --------------------------------------------------------
# How many bars of history the player sees before guessing.
VISIBLE_BARS = 90
# The horizons (in bars) a player may choose to forecast over.
HORIZON_CHOICES = [1, 5, 10, 20, 60]
# The longest horizon; each round stores this many future bars so any choice
# can be scored from the same precomputed round.
MAX_HORIZON = max(HORIZON_CHOICES)
# Upper bound on how many rounds to precompute (sliding windows over history).
MAX_ROUNDS = 1200
# Bars to step between consecutive precomputed windows. Larger = fewer, more-
# distinct rounds; smaller = more overlap.
WINDOW_STRIDE = 3
# Human-facing unit for one bar, used when the data doesn't specify one.
DEFAULT_INTERVAL = "day"

# --- Trading account -------------------------------------------------------
# Everyone (player + bots) starts with this cash balance.
STARTING_BALANCE = 10_000.0
# Stake presets the player can risk on a single trade.
STAKE_CHOICES = [100, 500, 1_000, 5_000]

# --- Instruments -----------------------------------------------------------
INSTRUMENT_LONG = "long"     # buy shares  — profit if price rises (linear)
INSTRUMENT_SHORT = "short"   # short shares — profit if price falls (linear)
INSTRUMENT_CALL = "call"     # ATM call option — leveraged bullish, risk = premium
INSTRUMENT_PUT = "put"       # ATM put option  — leveraged bearish, risk = premium
INSTRUMENTS = [INSTRUMENT_LONG, INSTRUMENT_SHORT, INSTRUMENT_CALL, INSTRUMENT_PUT]

# --- Option pricing (simplified ATM approximation) -------------------------
# At-the-money Black-Scholes reduces to roughly 0.4 * S * sigma * sqrt(T).
# Good enough for a game; real pricing is not the point here.
ATM_PREMIUM_FACTOR = 0.4
# Floor the premium at this fraction of spot so it's never ~0 on calm windows.
MIN_PREMIUM_FRACTION = 0.005

# --- Prediction outcomes ---------------------------------------------------
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
