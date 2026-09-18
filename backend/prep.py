"""Build the QuantBeat game data.

Run once (or whenever you want fresh data):

    python prep.py                      # fetch real TSLA daily data (Stooq)
    python prep.py --csv my_tsla.csv    # use your own OHLCV CSV
    python prep.py --synthetic          # force a synthetic series (offline)

It loads a daily OHLCV series, slides a window across history to carve out game
rounds, precomputes each bot's directional call and the ground-truth outcome,
and writes everything to SQLite. Real calendar dates are used only to sort the
series and are then discarded — rounds carry a sequential day index instead, so
players can't identify (and look up) the window.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import random
import urllib.request
from typing import List, Optional

from app import db
from app.bots import run_all_bots
from app.config import (
    DIRECTION_DOWN,
    DIRECTION_UP,
    HORIZON_DAYS,
    MAX_ROUNDS,
    STOOQ_URL,
    VISIBLE_DAYS,
    WINDOW_STRIDE,
)

# Minimum bars we need before any round can be built.
_MIN_BARS = VISIBLE_DAYS + HORIZON_DAYS + 1


# --------------------------------------------------------------------------- #
# Data sources
# --------------------------------------------------------------------------- #
def _parse_ohlcv(rows: List[dict]) -> List[dict]:
    """Normalise CSV rows (case-insensitive headers) into sorted OHLCV bars."""
    bars: List[dict] = []
    for row in rows:
        lower = {k.lower(): v for k, v in row.items() if k}
        try:
            bars.append(
                {
                    "date": lower["date"],
                    "open": float(lower["open"]),
                    "high": float(lower["high"]),
                    "low": float(lower["low"]),
                    "close": float(lower["close"]),
                    "volume": float(lower.get("volume", 0) or 0),
                }
            )
        except (KeyError, ValueError):
            continue  # skip malformed / header-repeat lines
    bars.sort(key=lambda b: b["date"])
    return bars


def load_from_csv(path: str) -> List[dict]:
    with open(path, newline="") as fh:
        return _parse_ohlcv(list(csv.DictReader(fh)))


def fetch_from_stooq() -> Optional[List[dict]]:
    """Fetch TSLA daily bars from Stooq's free CSV endpoint."""
    req = urllib.request.Request(STOOQ_URL, headers={"User-Agent": "quantbeat/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - network is best-effort here
        print(f"  ! Stooq fetch failed ({exc}); will fall back to synthetic.")
        return None
    bars = _parse_ohlcv(list(csv.DictReader(io.StringIO(text))))
    return bars if len(bars) >= _MIN_BARS else None


def synthesize(n_days: int = 2600, seed: int = 42) -> List[dict]:
    """Generate a TSLA-flavoured series via geometric Brownian motion.

    Not real data — a believable stand-in so the game runs fully offline. Uses a
    daily drift and volatility in TSLA's rough historical ballpark.
    """
    rng = random.Random(seed)
    daily_drift = 0.0007  # ~18%/yr
    daily_vol = 0.035  # TSLA is famously volatile
    price = 20.0
    bars: List[dict] = []
    for i in range(n_days):
        shock = rng.gauss(0.0, 1.0)
        ret = daily_drift + daily_vol * shock
        open_ = price
        close = max(0.5, price * math.exp(ret))
        high = max(open_, close) * (1 + abs(rng.gauss(0, 0.01)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, 0.01)))
        volume = rng.uniform(2e7, 1.5e8)
        bars.append(
            {
                "date": f"{i:05d}",  # synthetic ordinal; discarded downstream
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": round(volume),
            }
        )
        price = close
    return bars


# --------------------------------------------------------------------------- #
# Round construction
# --------------------------------------------------------------------------- #
def _candle(index: int, bar: dict) -> dict:
    """A dateless candle keyed by sequential index for the chart library."""
    return {
        "t": index,
        "open": bar["open"],
        "high": bar["high"],
        "low": bar["low"],
        "close": bar["close"],
        "volume": bar["volume"],
    }


def build_rounds(bars: List[dict]) -> List[db.Round]:
    rounds: List[db.Round] = []
    last_start = len(bars) - (VISIBLE_DAYS + HORIZON_DAYS)
    round_id = 1
    for start in range(0, last_start + 1, WINDOW_STRIDE):
        window = bars[start : start + VISIBLE_DAYS + HORIZON_DAYS]
        visible_bars = window[:VISIBLE_DAYS]
        future_bars = window[VISIBLE_DAYS:]

        visible = [_candle(i, b) for i, b in enumerate(visible_bars)]
        future = [
            _candle(VISIBLE_DAYS + i, b) for i, b in enumerate(future_bars)
        ]

        start_close = visible_bars[-1]["close"]
        future_close = future_bars[-1]["close"]
        actual = DIRECTION_UP if future_close >= start_close else DIRECTION_DOWN

        visible_closes = [b["close"] for b in visible_bars]
        bot_calls = run_all_bots(visible_closes, round_seed=round_id)

        rounds.append(
            db.Round(
                id=round_id,
                visible=visible,
                future=future,
                start_close=start_close,
                future_close=future_close,
                actual_direction=actual,
                bot_calls=bot_calls,
            )
        )
        round_id += 1

    random.Random(7).shuffle(rounds)
    return rounds[:MAX_ROUNDS]


def load_bars(args: argparse.Namespace) -> tuple[List[dict], str]:
    if args.csv:
        return load_from_csv(args.csv), f"CSV ({args.csv})"
    if not args.synthetic:
        bars = fetch_from_stooq()
        if bars:
            return bars, "Stooq (real TSLA daily)"
    return synthesize(), "synthetic (GBM)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build QuantBeat game data.")
    parser.add_argument("--csv", help="Path to an OHLCV CSV to use instead of fetching.")
    parser.add_argument(
        "--synthetic", action="store_true", help="Force a synthetic offline series."
    )
    args = parser.parse_args()

    print("QuantBeat data prep")
    bars, source = load_bars(args)
    print(f"  source : {source}")
    print(f"  bars   : {len(bars)}")

    if len(bars) < _MIN_BARS:
        raise SystemExit(
            f"Need at least {_MIN_BARS} bars to build a round "
            f"(VISIBLE_DAYS={VISIBLE_DAYS} + HORIZON_DAYS={HORIZON_DAYS}); got {len(bars)}."
        )

    rounds = build_rounds(bars)
    print(f"  rounds : {len(rounds)}")

    with db.connect() as conn:
        db.init_db(conn)
        db.reset_rounds(conn)
        for r in rounds:
            db.insert_round(conn, r)
        db.set_meta(conn, "source", source)
        conn.commit()

    print(f"  wrote  : {db.DB_PATH}")
    print("Done. Start the API with: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
