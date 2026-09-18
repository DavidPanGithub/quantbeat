import { useCallback, useEffect, useRef, useState } from "react";
import { newRound, submitGuess } from "./api";
import Chart, { type ChartHandle } from "./components/Chart";
import Header from "./components/Header";
import Scoreboard from "./components/Scoreboard";
import TradePanel from "./components/TradePanel";
import type {
  Direction,
  GuessResponse,
  NewRoundResponse,
  Tally,
} from "./types";

type Phase = "loading" | "guessing" | "revealing" | "revealed" | "error";

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

  const [you, setYou] = useState<Tally>({ correct: 0, total: 0 });
  const [streak, setStreak] = useState(0);
  const [botTallies, setBotTallies] = useState<Record<string, Tally>>({});
  const [lastBotResults, setLastBotResults] = useState<
    Record<string, { direction: Direction; correct: boolean }>
  >({});
  const [youLast, setYouLast] = useState<
    { direction: Direction; correct: boolean } | undefined
  >();

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

  const onGuess = useCallback(
    async (direction: Direction) => {
      if (!round) return;
      try {
        const res = await submitGuess(round.round_id, direction);
        setResult(res);
        setPhase("revealing");
        chartRef.current?.reveal(res.future, () => {
          // Tally once the animation completes.
          setYou((t) => bump(t, res.correct));
          setStreak((s) => (res.correct ? s + 1 : 0));
          setYouLast({ direction, correct: res.correct });
          setBotTallies((prev) => {
            const next = { ...prev };
            for (const br of res.bot_results) {
              const cur = next[br.id] ?? { correct: 0, total: 0 };
              next[br.id] = bump(cur, br.correct);
            }
            return next;
          });
          setLastBotResults(
            Object.fromEntries(
              res.bot_results.map((br) => [
                br.id,
                { direction: br.direction, correct: br.correct },
              ])
            )
          );
          setPhase("revealed");
        });
      } catch (e) {
        setError(String(e));
        setPhase("error");
      }
    },
    [round]
  );

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

  const price = result?.future_close ?? round?.start_close ?? 0;

  return (
    <div className="app">
      <Header
        ticker={round?.ticker ?? "TSLA"}
        price={price}
        roundNumber={roundNumber}
      />
      <main className="app-body">
        <section className="chart-col">
          {round && (
            <Chart
              ref={chartRef}
              visible={round.visible}
              startClose={round.start_close}
              horizonDays={round.horizon_days}
            />
          )}
          <TradePanel
            phase={phase === "loading" ? "guessing" : (phase as any)}
            horizonDays={round?.horizon_days ?? 0}
            result={result}
            onGuess={onGuess}
            onNext={() => void loadRound()}
          />
        </section>
        <Scoreboard
          you={you}
          streak={streak}
          bots={round?.bots ?? []}
          botTallies={botTallies}
          lastBotResults={lastBotResults}
          youLast={youLast}
        />
      </main>
    </div>
  );
}
