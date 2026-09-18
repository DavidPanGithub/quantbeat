import type { BotInfo, Direction, Tally } from "../types";

interface Competitor {
  id: string;
  label: string;
  tally: Tally;
  lastCall?: Direction;
  lastCorrect?: boolean;
  isYou?: boolean;
}

interface ScoreboardProps {
  you: Tally;
  streak: number;
  bots: BotInfo[];
  botTallies: Record<string, Tally>;
  lastBotResults: Record<string, { direction: Direction; correct: boolean }>;
  youLast?: { direction: Direction; correct: boolean };
}

function pct(t: Tally): number {
  return t.total === 0 ? 0 : (t.correct / t.total) * 100;
}

export default function Scoreboard({
  you,
  streak,
  bots,
  botTallies,
  lastBotResults,
  youLast,
}: ScoreboardProps) {
  const competitors: Competitor[] = [
    {
      id: "you",
      label: "YOU",
      tally: you,
      lastCall: youLast?.direction,
      lastCorrect: youLast?.correct,
      isYou: true,
    },
    ...bots.map((b) => ({
      id: b.id,
      label: b.label,
      tally: botTallies[b.id] ?? { correct: 0, total: 0 },
      lastCall: lastBotResults[b.id]?.direction,
      lastCorrect: lastBotResults[b.id]?.correct,
    })),
  ];

  // Rank by accuracy so the leader floats to the top.
  const ranked = [...competitors].sort((a, b) => pct(b.tally) - pct(a.tally));
  const leaderId = you.total > 0 ? ranked[0].id : null;

  return (
    <aside className="scoreboard">
      <div className="scoreboard-head">
        <h2>YOU vs THE QUANTS</h2>
        <div className="streak">
          🔥 streak <b>{streak}</b>
        </div>
      </div>
      <div className="leaderboard">
        {ranked.map((c) => (
          <div
            key={c.id}
            className={`lb-row ${c.isYou ? "is-you" : ""} ${
              c.id === leaderId ? "is-leader" : ""
            }`}
          >
            <div className="lb-name">
              {c.id === leaderId && <span className="crown">♛</span>}
              {c.label}
              {c.lastCall && (
                <span
                  className={`lb-call ${c.lastCorrect ? "ok" : "bad"}`}
                  title="last call"
                >
                  {c.lastCall === "up" ? "▲" : "▼"}
                </span>
              )}
            </div>
            <div className="lb-bar-track">
              <div
                className={`lb-bar-fill ${c.isYou ? "you" : ""}`}
                style={{ width: `${pct(c.tally)}%` }}
              />
            </div>
            <div className="lb-stat">
              {pct(c.tally).toFixed(0)}%
              <span className="lb-stat-sub">
                {c.tally.correct}/{c.tally.total}
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="scoreboard-foot">
        Beat the coin flip and you're ahead of chance. Beat all four and you're
        officially better than the bots.
      </p>
    </aside>
  );
}
