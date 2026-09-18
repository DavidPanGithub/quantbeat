import type { BotInfo, Direction, Tally } from "../types";
import { money, signedMoney } from "../format";

interface ScoreboardProps {
  you: Tally;
  youBalance: number;
  streak: number;
  bots: BotInfo[];
  botBalances: Record<string, number>;
  botTallies: Record<string, Tally>;
  startingBalance: number;
  lastBotResults: Record<string, { direction: Direction; correct: boolean; pnl: number }>;
  youLast?: { direction: Direction; correct: boolean; pnl: number };
}

interface Row {
  id: string;
  label: string;
  balance: number;
  tally: Tally;
  lastCall?: Direction;
  lastPnl?: number;
  isYou?: boolean;
}

function acc(t: Tally): number {
  return t.total === 0 ? 0 : (t.correct / t.total) * 100;
}

export default function Scoreboard({
  you,
  youBalance,
  streak,
  bots,
  botBalances,
  botTallies,
  startingBalance,
  lastBotResults,
  youLast,
}: ScoreboardProps) {
  const rows: Row[] = [
    {
      id: "you",
      label: "YOU",
      balance: youBalance,
      tally: you,
      lastCall: youLast?.direction,
      lastPnl: youLast?.pnl,
      isYou: true,
    },
    ...bots.map((b) => ({
      id: b.id,
      label: b.label,
      balance: botBalances[b.id] ?? startingBalance,
      tally: botTallies[b.id] ?? { correct: 0, total: 0 },
      lastCall: lastBotResults[b.id]?.direction,
      lastPnl: lastBotResults[b.id]?.pnl,
    })),
  ];

  const ranked = [...rows].sort((a, b) => b.balance - a.balance);
  const maxBalance = Math.max(...ranked.map((r) => r.balance), 1);
  const played = you.total > 0;
  const leaderId = played ? ranked[0].id : null;

  return (
    <aside className="scoreboard">
      <div className="scoreboard-head">
        <h2>YOU vs THE QUANTS</h2>
        <div className="streak">🔥 <b>{streak}</b></div>
      </div>
      <div className="leaderboard">
        {ranked.map((c) => {
          const pnl = c.balance - startingBalance;
          return (
            <div
              key={c.id}
              className={`lb-row ${c.isYou ? "is-you" : ""} ${
                c.id === leaderId ? "is-leader" : ""
              }`}
            >
              <div className="lb-top">
                <span className="lb-name">
                  {c.id === leaderId && <span className="crown">♛</span>}
                  {c.label}
                  {c.lastCall && (
                    <span className={`lb-call ${(c.lastPnl ?? 0) >= 0 ? "ok" : "bad"}`}>
                      {c.lastCall === "up" ? "▲" : "▼"}
                    </span>
                  )}
                </span>
                <span className={`lb-balance ${pnl >= 0 ? "pos" : "neg"}`}>
                  {money(c.balance)}
                </span>
              </div>
              <div className="lb-bar-track">
                <div
                  className={`lb-bar-fill ${c.isYou ? "you" : ""}`}
                  style={{ width: `${(c.balance / maxBalance) * 100}%` }}
                />
              </div>
              <div className="lb-sub">
                <span className={pnl >= 0 ? "pos" : "neg"}>{signedMoney(pnl)}</span>
                <span className="lb-acc">
                  {acc(c.tally).toFixed(0)}% · {c.tally.correct}/{c.tally.total}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="scoreboard-foot">
        Bots trade shares in their signal's direction at your stake. You've got
        options — literally. Out-earn all four to win.
      </p>
    </aside>
  );
}
