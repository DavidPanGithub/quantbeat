import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { newRound, submitGuess } from "./api";
import Chart, { type ChartHandle } from "./components/Chart";
import Header from "./components/Header";
import Scoreboard from "./components/Scoreboard";
import TradePanel from "./components/TradePanel";
import { estimatePremium } from "./format";
import type {
  GuessResponse,
  Instrument,
  NewRoundResponse,
  Tally,
} from "./types";

type Phase = "loading" | "guessing" | "revealing" | "revealed" | "error";

const DEFAULT_HORIZON = 10;
const DEFAULT_STAKE = 1000;
const STARTING_BALANCE = 10_000; // client fallback; server value is authoritative
const STORE_KEY = "quantbeat.v1";

function unit(interval: string, n: number): string {
  return n === 1 ? interval : `${interval}s`;
}

// Money + stats that survive a page reload.
interface MoneyState {
  balance: number;
  botBalances: Record<string, number>;
  you: Tally;
  streak: number;
  botTallies: Record<string, Tally>;
}

function freshMoney(): MoneyState {
  return {
    balance: STARTING_BALANCE,
    botBalances: {},
    you: { correct: 0, total: 0 },
    streak: 0,
    botTallies: {},
  };
}

function loadMoney(): MoneyState {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return { ...freshMoney(), ...JSON.parse(raw) };
  } catch {
    /* ignore corrupt storage */
  }
  return freshMoney();
}

function bump(t: Tally, correct: boolean): Tally {
  return { correct: t.correct + (correct ? 1 : 0), total: t.total + 1 };
}

export default function App() {
  const chartRef = useRef<ChartHandle>(null);

  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string>("");
  const [round, setRound] = useState<NewRoundResponse | null>(null);
  const [roundNumber, setRoundNumber] = useState(0);
  const [result, setResult] = useState<GuessResponse | null>(null);

  const [selectedHorizon, setSelectedHorizon] = useState(DEFAULT_HORIZON);
  const [instrument, setInstrument] = useState<Instrument>("long");
  const [stake, setStake] = useState(DEFAULT_STAKE);

  const [money, setMoney] = useState<MoneyState>(loadMoney);
  const [lastBotResults, setLastBotResults] = useState<
    Record<string, { direction: "up" | "down"; correct: boolean; pnl: number }>
  >({});
  const [youLast, setYouLast] = useState<
    { direction: "up" | "down"; correct: boolean; pnl: number } | undefined
  >();

  // Persist money/stats on every change.
  useEffect(() => {
    localStorage.setItem(STORE_KEY, JSON.stringify(money));
  }, [money]);

  const broke = money.balance < 1;

  const loadRound = useCallback(async () => {
    setPhase("loading");
    setResult(null);
    try {
      const data = await newRound();
      setRound(data);
      setRoundNumber((n) => n + 1);
      setPhase("guessing");
    } catch (e) {
      setError(String(e));
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    void loadRound();
  }, [loadRound]);

  // Keep the stake affordable: never let the selected stake exceed balance.
  const affordableStake = Math.min(stake, Math.max(0, Math.floor(money.balance)));

  const premiumPreview = useMemo(() => {
    if (!round) return 0;
    return estimatePremium(round.visible, round.start_close, selectedHorizon);
  }, [round, selectedHorizon]);

  const placeTrade = useCallback(async () => {
    if (!round || affordableStake < 1) return;
    try {
      const res = await submitGuess(
        round.round_id,
        instrument,
        affordableStake,
        selectedHorizon
      );
      setResult(res);
      setPhase("revealing");
      chartRef.current?.reveal(res.future, () => {
        setMoney((m) => {
          const botBalances = { ...m.botBalances };
          const botTallies = { ...m.botTallies };
          for (const br of res.bot_results) {
            botBalances[br.id] =
              (botBalances[br.id] ?? STARTING_BALANCE) + br.pnl;
            botTallies[br.id] = bump(
              botTallies[br.id] ?? { correct: 0, total: 0 },
              br.correct
            );
          }
          return {
            balance: m.balance + res.pnl,
            botBalances,
            you: bump(m.you, res.correct),
            streak: res.correct ? m.streak + 1 : 0,
            botTallies,
          };
        });
        setYouLast({
          direction: res.your_direction,
          correct: res.correct,
          pnl: res.pnl,
        });
        setLastBotResults(
          Object.fromEntries(
            res.bot_results.map((br) => [
              br.id,
              { direction: br.direction, correct: br.correct, pnl: br.pnl },
            ])
          )
        );
        setPhase("revealed");
      });
    } catch (e) {
      setError(String(e));
      setPhase("error");
    }
  }, [round, instrument, affordableStake, selectedHorizon]);

  const resetAccount = useCallback(() => {
    setMoney(freshMoney());
    setLastBotResults({});
    setYouLast(undefined);
    setStake(DEFAULT_STAKE);
    void loadRound();
  }, [loadRound]);

  if (phase === "error") {
    return (
      <div className="app error-screen">
        <div className="error-card">
          <h1>⚠ Can't reach the market</h1>
          <p>{error}</p>
          <p className="error-hint">
            Is the backend running? From <code>backend/</code>:
            <br />
            <code>uvicorn app.main:app --reload --port 8000</code>
            <br />
            (and <code>python prep.py</code> first, to build the data).
          </p>
          <button className="next-btn" onClick={() => void loadRound()}>
            RETRY
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header
        ticker={round?.ticker ?? "TSLA"}
        price={result?.future_close ?? round?.start_close ?? 0}
        balance={money.balance}
        startingBalance={round?.starting_balance ?? STARTING_BALANCE}
        roundNumber={roundNumber}
      />
      <main className="app-body">
        <section className="chart-col">
          {round && (
            <Chart
              ref={chartRef}
              visible={round.visible}
              startClose={round.start_close}
              horizonLabel={`${selectedHorizon} ${unit(
                round.interval,
                selectedHorizon
              )}`}
            />
          )}
          <TradePanel
            phase={phase === "loading" ? "guessing" : (phase as any)}
            interval={round?.interval ?? "day"}
            horizonChoices={round?.horizon_choices ?? []}
            selectedHorizon={selectedHorizon}
            onSelectHorizon={setSelectedHorizon}
            stakeChoices={round?.stake_choices ?? []}
            selectedStake={affordableStake}
            onSelectStake={setStake}
            balance={money.balance}
            instrument={instrument}
            onSelectInstrument={setInstrument}
            premiumPreview={premiumPreview}
            result={result}
            broke={broke}
            onPlaceTrade={() => void placeTrade()}
            onNext={() => void loadRound()}
            onReset={resetAccount}
          />
        </section>
        <Scoreboard
          you={money.you}
          youBalance={money.balance}
          streak={money.streak}
          bots={round?.bots ?? []}
          botBalances={money.botBalances}
          botTallies={money.botTallies}
          startingBalance={round?.starting_balance ?? STARTING_BALANCE}
          lastBotResults={lastBotResults}
          youLast={youLast}
        />
      </main>
    </div>
  );
}
