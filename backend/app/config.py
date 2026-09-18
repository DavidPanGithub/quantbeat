"""Central game configuration.

Kept in one place so the data-prep step and the API agree on the same window
sizes, and so there are no magic numbers scattered across the codebase.
"""
from pathlib import Path

# --- Data source -----------------------------------------------------------
TICKER = "TSLA"
STOOQ_URL = "https://stooq.com/q/d/l/?s=tsla.us&i=d"

# --- Storage ---------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "quantbeat.db"

# --- Round geometry --------------------------------------------------------
# How many trading days of history the player sees before guessing.
VISIBLE_DAYS = 90
# How many trading days into the future the prediction covers.
HORIZON_DAYS = 10
# Upper bound on how many rounds to precompute (sliding windows over history).
MAX_ROUNDS = 1200
# Trading days to step between consecutive precomputed windows. Larger = fewer,
# more-distinct rounds; smaller = more overlap.
WINDOW_STRIDE = 3

# --- Prediction outcomes ---------------------------------------------------
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
