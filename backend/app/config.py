"""Central game configuration.

Kept in one place so the data-prep step and the API agree on the same window
sizes, and so there are no magic numbers scattered across the codebase.

The engine forecasts a number of *bars* ahead, not a hardcoded number of days.
A bar is whatever the loaded data is (daily, hourly, minute) — the human-facing
unit label is stored alongside the data at prep time.
"""
from pathlib import Path

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

# --- Prediction outcomes ---------------------------------------------------
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
