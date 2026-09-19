# QuantBeat 📈

**Can you beat the quants at predicting Tesla?**

🎮 **[Play the live demo →](https://quantbeat.davidusinggithub.workers.dev)**

> Hosted free on Cloudflare Workers (frontend) + Render (backend). The API sleeps
> after idle, so the first round may take ~50s to cold-start, then it's instant.


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

Each round shows `VISIBLE_BARS` of candles. You pick a **forecast horizon**
(1 / 5 / 10 / 20 / 60 bars) and predict whether the close that many bars later
is **higher (LONG)** or **lower (SHORT)** than the last visible close. The bots
predict the same thing from the same data:

| Bot            | Strategy                                            |
|----------------|-----------------------------------------------------|
| Momentum       | Trend-following: recent up-move → bet up            |
| Mean-Reversion | Fade extremes: above its average → bet down         |
| MA Crossover   | Fast SMA above slow SMA → bet up                    |
| Coin Flip      | 50/50 baseline (the bar everyone should clear)      |

Each round stores the future for the *longest* horizon; the API slices it to the
horizon you chose and scores against that. The bots read only the visible
window, so their calls don't depend on the horizon — one round serves them all.

Your accuracy and current streak are tracked per session, alongside each bot's
running accuracy — so you can see, in real time, whether you're beating the quants.

## Trade with real money (and real leverage)

You start with a **$10,000 account** and stake cash on each round. Pick your
instrument:

| Instrument | Payoff                                                          |
|------------|-----------------------------------------------------------------|
| **Long**   | Buy shares — linear P&L, `stake × return`                       |
| **Short**  | Short shares — linear, profits when price falls                 |
| **Call**   | ATM call option — capped loss (the premium), leveraged upside   |
| **Put**    | ATM put option — capped loss, leveraged downside bet            |

Options are priced off the **volatility of the visible window** using the ATM
Black-Scholes approximation `premium ≈ 0.4 · S · σ · √T` (see
`backend/app/trading.py`). Your stake buys `stake / premium` contracts, so a
correct option call can multiply your money — and a wrong one loses the whole
premium. That asymmetry is the point.

Every bot trades **shares in its signal's direction at your stake**, so the
scoreboard is a live **P&L leaderboard**: out-earn all four to win. Blow up your
account and you can reset. Balances persist in `localStorage`.

## Pick your era (without cheating)

A **market-era picker** lets you choose which slice of history to play — All-time
or a specific year. To keep the anti-cheat intact, the server picks a **random
window within** the era you chose and still hides the dates while you trade; the
**actual dates are revealed only after you guess** ("this window was 2020-02-03
→ 2020-05-14"). You steer the regime, but you can't look up the specific answer.

## Days, minutes, whatever you load

The engine forecasts **N bars ahead** — a bar is whatever data you loaded. Feed
it daily bars and horizons mean days; feed it 1-minute bars and the identical
game becomes minute-level, UI labels included. `--interval` sets only the
human-facing unit:

```bash
python prep.py --csv tsla_1min.csv --interval minute   # minute-level game
python prep.py --csv tsla_daily.csv --interval day      # daily (default)
```

> The bundled Stooq/synthetic data is **daily**, so minute-level play needs an
> intraday (1-min) OHLCV CSV — that data isn't included.

## Deploy (free)

Frontend on **Cloudflare Pages** + backend on **Render** — both free, no card.
The backend is read-only (rounds are baked into the image; player balances live
in the browser), so there's no database to run, and no AI/LLM cost at runtime.

**1. Backend → Render**
- Push this repo to GitHub.
- Render dashboard → **New → Blueprint** → pick the repo. `render.yaml` provisions
  a free Docker web service from `backend/Dockerfile` (which runs `prep.py` at
  build to bake real TSLA data).
- Note the service URL, e.g. `https://quantbeat-api.onrender.com`.
- (Free services sleep after ~15 min idle; first request then cold-starts ~30s.)

**2. Frontend → Cloudflare Pages**
- Cloudflare dashboard → **Workers & Pages → Create → Pages** → connect the repo.
- Build settings: **root** `frontend`, **build command** `npm run build`,
  **output** `dist`.
- Add an environment variable **`VITE_API_BASE`** = your Render URL (from step 1).
- Deploy. You'll get `https://quantbeat.pages.dev` (or a custom domain / a
  `quantbeat.hoiinpan.com` subdomain).

**3. Connect them**
- Back in Render, set the env var **`ALLOWED_ORIGINS`** to your Pages URL
  (e.g. `https://quantbeat.pages.dev`) so the API accepts browser requests from it.

**Refresh the data** later by triggering a redeploy on Render (rebuilds the image
and re-runs `prep.py`), or automate it with a scheduled GitHub Action.

## Roadmap (v2 ideas)

- Magnitude guesses (`±%`) and "draw the next 5 candles"
- Persistent accounts + global leaderboard
- More bots (RSI, Bollinger, a tiny ML model) to beat
- Multiple tickers / difficulty tiers
