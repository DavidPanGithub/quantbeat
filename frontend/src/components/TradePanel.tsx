import type { Direction, GuessResponse } from "../types";

type Phase = "guessing" | "revealing" | "revealed";

interface TradePanelProps {
  phase: Phase;
  interval: string;
  horizonChoices: number[];
  selectedHorizon: number;
  onSelectHorizon: (h: number) => void;
  result: GuessResponse | null;
  onGuess: (d: Direction) => void;
  onNext: () => void;
}

function unit(interval: string, n: number): string {
  return n === 1 ? interval : `${interval}s`;
}

export default function TradePanel({
  phase,
  interval,
  horizonChoices,
  selectedHorizon,
  onSelectHorizon,
  result,
  onGuess,
  onNext,
}: TradePanelProps) {
  if (phase === "guessing") {
    return (
      <div className="trade-panel">
        <div className="horizon-picker">
          <span className="horizon-label">FORECAST HORIZON</span>
          <div className="horizon-choices">
            {horizonChoices.map((h) => (
              <button
                key={h}
                className={`horizon-chip ${h === selectedHorizon ? "active" : ""}`}
                onClick={() => onSelectHorizon(h)}
              >
                {h} {unit(interval, h)}
              </button>
            ))}
          </div>
        </div>
        <div className="trade-prompt">
          Where does TSLA close in{" "}
          <b>
            {selectedHorizon} {unit(interval, selectedHorizon)}
          </b>
          ?
        </div>
        <div className="trade-buttons">
          <button className="trade-btn long" onClick={() => onGuess("up")}>
            <span className="trade-btn-arrow">▲</span> LONG
            <span className="trade-btn-sub">price goes up</span>
          </button>
          <button className="trade-btn short" onClick={() => onGuess("down")}>
            <span className="trade-btn-arrow">▼</span> SHORT
            <span className="trade-btn-sub">price goes down</span>
          </button>
        </div>
      </div>
    );
  }

  if (phase === "revealing") {
    return (
      <div className="trade-panel">
        <div className="trade-prompt revealing">Revealing the market…</div>
      </div>
    );
  }

  // revealed
  const r = result!;
  const up = r.actual_direction === "up";
  return (
    <div className="trade-panel">
      <div className={`result-banner ${r.correct ? "win" : "loss"}`}>
        {r.correct ? "✓ YOU CALLED IT" : "✗ WRONG CALL"}
      </div>
      <div className="result-detail">
        <div>
          <span className="result-label">Your call</span>
          <span className="result-value">
            {r.your_direction === "up" ? "LONG" : "SHORT"}
          </span>
        </div>
        <div>
          <span className="result-label">
            Move / {r.horizon} {unit(interval, r.horizon)}
          </span>
          <span className={`result-value ${up ? "pos" : "neg"}`}>
            {up ? "▲" : "▼"} {r.pct_change >= 0 ? "+" : ""}
            {r.pct_change.toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="result-label">Close</span>
          <span className="result-value">
            ${r.start_close.toFixed(2)} → ${r.future_close.toFixed(2)}
          </span>
        </div>
      </div>
      <button className="next-btn" onClick={onNext}>
        NEXT ROUND →
      </button>
    </div>
  );
}
