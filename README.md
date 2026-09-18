# QuantBeat 📈

**Can you beat the quants at predicting Tesla?**

QuantBeat is a stock-prediction game built on *real historical TSLA data*. You're
shown a live-trading-style chart up to a hidden point in history, you call the
next move — **LONG or SHORT** — and the market reveals what actually happened.
Every round, you're scored head-to-head against a panel of algorithmic trading
bots (momentum, mean-reversion, moving-average crossover, and a coin flip).

TSLA is the perfect subject: it's the most-traded stock by retail investors and
notoriously hard to predict. If a human can consistently beat the bots on TSLA,
that's a real story. (Spoiler: it's harder than it looks.)

> All data is **historical replay** — no live market feed, no market-data
> licensing, and every outcome is verifiable ground truth. Dates are stripped
> from the visible chart so you can't just look it up.

---

## Architecture

```
quantbeat/
├── backend/          FastAPI + SQLite
│   ├── prep.py       one-time: fetch/clean TSLA data, precompute game rounds
│   └── app/          the API (new round, submit guess, reveal + bot scoring)
└── frontend/         Vite + React + TypeScript + TradingView Lightweight Charts
    └── src/          the trading-terminal UI
```

**Why it's built this way**

- **Future data never leaves the server** until you lock in a guess — no cheating.
- **Rounds are precomputed** at prep time (visible window, hidden future, and each
  bot's answer), so the API is stateless and fast.
- **Bots run the same backtest logic** on the same window you see, so the
  "you vs quant" scoreboard is honest.

---

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Build the game data. Tries to fetch real TSLA daily data from Stooq;
# falls back to a synthetic series if offline. Drop in your own CSV with --csv.
python prep.py                       # auto-fetch (or synthetic fallback)
python prep.py --csv path/to/tsla.csv   # use your own OHLCV CSV

# Run the API
uvicorn app.main:app --reload --port 8000
```

Your CSV just needs columns: `Date, Open, High, Low, Close, Volume`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The frontend proxies `/api` to the backend on port 8000.

---

## How scoring works

Each round shows `VISIBLE_DAYS` of candles. You predict whether the close
`HORIZON` trading days later is **higher (LONG)** or **lower (SHORT)** than the
last visible close. The bots predict the same thing from the same data:

| Bot            | Strategy                                            |
|----------------|-----------------------------------------------------|
| Momentum       | Trend-following: recent up-move → bet up            |
| Mean-Reversion | Fade extremes: above its average → bet down         |
| MA Crossover   | Fast SMA above slow SMA → bet up                    |
| Coin Flip      | 50/50 baseline (the bar everyone should clear)      |

Your accuracy and current streak are tracked per session, alongside each bot's
running accuracy — so you can see, in real time, whether you're actually beating
the quants.

## Roadmap (v2 ideas)

- Magnitude guesses (`±%`) and "draw the next 5 candles"
- Persistent accounts + global leaderboard
- More bots (RSI, Bollinger, a tiny ML model) to beat
- Multiple tickers / difficulty tiers
