"""Build the QuantBeat game data.

Run once (or whenever you want fresh data):

    python prep.py                          # fetch real TSLA daily data (Stooq)
    python prep.py --csv my_tsla.csv        # use your own OHLCV CSV
    python prep.py --synthetic              # force a synthetic series (offline)
    python prep.py --csv 1min.csv --interval minute   # intraday data

It loads an OHLCV series, slides a window across history to carve out game
rounds, precomputes each bot's directional call, and writes everything to
SQLite. Each round stores the future for the *longest* supported horizon; the
API slices it to whatever horizon a player picks.

A bar is whatever the data is. ``--interval`` only sets the human-facing unit
label (day/minute/hour) — load minute bars and the same game becomes
minute-level. Real timestamps are used only to sort the series and are then
discarded; rounds carry a sequential bar index instead, so players can't
identify (and look up) the window.
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
    DEFAULT_INTERVAL,
    MAX_HORIZON,
    MAX_ROUNDS,
    STOOQ_URL,
    TICKER,
    VISIBLE_BARS,
    WINDOW_STRIDE,
)

# Minimum bars we need before any round can be built.
_MIN_BARS = VISIBLE_BARS + MAX_HORIZON


# --------------------------------------------------------------------------- #
# Data sources
# --------------------------------------------------------------------------- #
def _parse_ohlcv(rows: List[dict]) -> List[dict]:
    """Normalise CSV rows (case-insensitive headers) into sorted OHLCV bars."""
    bars: List[dict] = []
    for row in rows:
        lower = {k.lower(): v for k, v in row.items() if k}
        # Accept either a combined datetime column or a date column.
        stamp = lower.get("datetime") or lower.get("date") or lower.get("time")
        try:
            bars.append(
                {
                    "stamp": stamp,
                    "open": float(lower["open"]),
                    "high": float(lower["high"]),
                    "low": float(lower["low"]),
                    "close": float(lower["close"]),
                    "volume": float(lower.get("volume", 0) or 0),
                }
            )
        except (KeyError, ValueError, TypeError):
            continue  # skip malformed / header-repeat lines
    bars.sort(key=lambda b: b["stamp"] or "")
    return bars


def load_from_csv(path: str) -> List[dict]:
    with open(path, newline="") as fh:
        return _parse_ohlcv(list(csv.DictReader(fh)))


def fetch_from_yahoo() -> Optional[List[dict]]:
    """Fetch real daily TSLA bars from Yahoo's v8 chart API (no key required).

    The ``quote`` OHLC arrays are split-adjusted, which is what we want: prices
    stay continuous across TSLA's 2020 (5:1) and 2022 (3:1) splits.
    """
    import json
    import time
    from datetime import datetime, timezone

    start = 1262304000  # 2010-01-01, before TSLA's 2010 IPO
    end = int(time.time())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}"
        f"?period1={start}&period2={end}&interval=1d"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - network is best-effort here
        print(f"  ! Yahoo fetch failed ({exc}); trying next source.")
        return None

    result = (data.get("chart") or {}).get("result")
    if not result:
        return None
    r = result[0]
    stamps = r.get("timestamp") or []
    quote = (r.get("indicators") or {}).get("quote", [{}])[0]

    bars: List[dict] = []
    for i, t in enumerate(stamps):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        v = quote["volume"][i]
        if None in (o, h, l, c):
            continue  # Yahoo leaves gaps as nulls
        bars.append(
            {
                "stamp": datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
                "volume": round(v or 0),
            }
        )
    return bars if len(bars) >= _MIN_BARS else None


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


def synthesize(n_bars: int = 2600, seed: int = 42) -> List[dict]:
    """Generate a TSLA-flavoured series via geometric Brownian motion.

    Not real data — a believable stand-in so the game runs fully offline. Uses a
    per-bar drift and volatility in TSLA's rough historical daily ballpark, and
    real business-day dates so the era picker works out of the box.
    """
    from datetime import date, timedelta

    rng = random.Random(seed)
    drift = 0.0007  # ~18%/yr on daily bars
    vol = 0.035  # TSLA is famously volatile
    price = 20.0

    # Sequential business days (skip weekends) starting from a fixed date.
    dates: List[str] = []
    d = date(2015, 1, 2)
    while len(dates) < n_bars:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)

    bars: List[dict] = []
    for i in range(n_bars):
        shock = rng.gauss(0.0, 1.0)
        ret = drift + vol * shock
        open_ = price
        close = max(0.5, price * math.exp(ret))
        high = max(open_, close) * (1 + abs(rng.gauss(0, 0.01)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, 0.01)))
        volume = rng.uniform(2e7, 1.5e8)
        bars.append(
            {
                "stamp": dates[i],
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
    """A timestamp-free candle keyed by sequential index for the chart."""
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
    last_start = len(bars) - (VISIBLE_BARS + MAX_HORIZON)
    round_id = 1
    for start in range(0, last_start + 1, WINDOW_STRIDE):
        window = bars[start : start + VISIBLE_BARS + MAX_HORIZON]
        visible_bars = window[:VISIBLE_BARS]
        future_bars = window[VISIBLE_BARS:]

        visible = [_candle(i, b) for i, b in enumerate(visible_bars)]
        future = [_candle(VISIBLE_BARS + i, b) for i, b in enumerate(future_bars)]

        start_close = visible_bars[-1]["close"]
        visible_closes = [b["close"] for b in visible_bars]
        bot_calls = run_all_bots(visible_closes, round_seed=round_id)

        rounds.append(
            db.Round(
                id=round_id,
                visible=visible,
                future=future,
                start_close=start_close,
                bot_calls=bot_calls,
                start_date=visible_bars[-1]["stamp"],
                end_date=future_bars[-1]["stamp"],
            )
        )
        round_id += 1

    random.Random(7).shuffle(rounds)
    return rounds[:MAX_ROUNDS]


def load_bars(args: argparse.Namespace) -> tuple[List[dict], str]:
    if args.csv:
        return load_from_csv(args.csv), f"CSV ({args.csv})"
    if not args.synthetic:
        bars = fetch_from_yahoo()
        if bars:
            return bars, "Yahoo (real TSLA daily, split-adjusted)"
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
    parser.add_argument(
        "--interval",
        default=DEFAULT_INTERVAL,
        help="Human unit for one bar (day/minute/hour). Labels the UI only.",
    )
    args = parser.parse_args()

    print("QuantBeat data prep")
    bars, source = load_bars(args)
    print(f"  source  : {source}")
    print(f"  interval: {args.interval}")
    print(f"  bars    : {len(bars)}")

    if len(bars) < _MIN_BARS:
        raise SystemExit(
            f"Need at least {_MIN_BARS} bars to build a round "
            f"(VISIBLE_BARS={VISIBLE_BARS} + MAX_HORIZON={MAX_HORIZON}); got {len(bars)}."
        )

    rounds = build_rounds(bars)
    print(f"  rounds  : {len(rounds)}")

    with db.connect() as conn:
        db.init_db(conn)
        db.reset_rounds(conn)
        for r in rounds:
            db.insert_round(conn, r)
        db.set_meta(conn, "source", source)
        db.set_meta(conn, "interval", args.interval)
        db.set_meta(conn, "date_min", bars[0]["stamp"])
        db.set_meta(conn, "date_max", bars[-1]["stamp"])
        conn.commit()

    print(f"  wrote   : {db.DB_PATH}")
    print("Done. Start the API with: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
