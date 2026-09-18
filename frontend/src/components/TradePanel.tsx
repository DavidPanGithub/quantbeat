import type { GuessResponse, Instrument } from "../types";
import { money, signedMoney } from "../format";

type Phase = "guessing" | "revealing" | "revealed";

interface InstrumentMeta {
  id: Instrument;
  label: string;
  sub: string;
  arrow: string;
  cls: string;
  option: boolean;
}

const INSTRUMENTS: InstrumentMeta[] = [
  { id: "long", label: "LONG", sub: "buy shares", arrow: "▲", cls: "long", option: false },
  { id: "short", label: "SHORT", sub: "short shares", arrow: "▼", cls: "short", option: false },
  { id: "call", label: "CALL", sub: "option · leveraged", arrow: "▲", cls: "long", option: true },
  { id: "put", label: "PUT", sub: "option · leveraged", arrow: "▼", cls: "short", option: true },
];

interface TradePanelProps {
  phase: Phase;
  interval: string;
  horizonChoices: number[];
  selectedHorizon: number;
  onSelectHorizon: (h: number) => void;
  stakeChoices: number[];
  selectedStake: number;
  onSelectStake: (s: number) => void;
  balance: number;
  instrument: Instrument;
  onSelectInstrument: (i: Instrument) => void;
  premiumPreview: number;
  result: GuessResponse | null;
  broke: boolean;
  onPlaceTrade: () => void;
  onNext: () => void;
  onReset: () => void;
}

function unit(interval: string, n: number): string {
  return n === 1 ? interval : `${interval}s`;
}

export default function TradePanel(props: TradePanelProps) {
  const {
    phase,
    interval,
    horizonChoices,
    selectedHorizon,
    onSelectHorizon,
    stakeChoices,
    selectedStake,
    onSelectStake,
    balance,
    instrument,
    onSelectInstrument,
    premiumPreview,
    result,
    broke,
    onPlaceTrade,
    onNext,
    onReset,
  } = props;

  if (phase === "guessing") {
    const meta = INSTRUMENTS.find((i) => i.id === instrument)!;
    const allIn = Math.floor(balance);
    const contracts =
      premiumPreview > 0 ? Math.floor(selectedStake / premiumPreview) : 0;

    return (
      <div className="trade-panel">
        <div className="picker-row">
          <span className="picker-label">HORIZON</span>
          <div className="chips">
            {horizonChoices.map((h) => (
              <button
                key={h}
                className={`chip ${h === selectedHorizon ? "active" : ""}`}
                onClick={() => onSelectHorizon(h)}
              >
                {h} {unit(interval, h)}
              </button>
            ))}
          </div>
        </div>

        <div className="instrument-grid">
          {INSTRUMENTS.map((i) => (
            <button
              key={i.id}
              className={`instrument-card ${i.cls} ${
                i.id === instrument ? "active" : ""
              }`}
              onClick={() => onSelectInstrument(i.id)}
            >
              <span className="instrument-top">
                <span className="instrument-arrow">{i.arrow}</span>
                {i.label}
              </span>
              <span className="instrument-sub">{i.sub}</span>
            </button>
          ))}
        </div>

        <div className="picker-row">
          <span className="picker-label">STAKE</span>
          <div className="chips">
            {stakeChoices.map((s) => (
              <button
                key={s}
                className={`chip ${s === selectedStake ? "active" : ""}`}
                disabled={s > balance}
                onClick={() => onSelectStake(s)}
              >
                {money(s)}
              </button>
            ))}
            {allIn > 0 && (
              <button
                className={`chip ${allIn === selectedStake ? "active" : ""}`}
                onClick={() => onSelectStake(allIn)}
              >
                All-in
              </button>
            )}
          </div>
        </div>

        {meta.option && (
          <div className="premium-preview">
            premium ≈ <b>${premiumPreview.toFixed(2)}</b>/contract · your{" "}
            {money(selectedStake)} buys <b>~{contracts}</b> contracts
            <span className="premium-note">
              max loss = your stake · upside is leveraged
            </span>
          </div>
        )}

        <button
          className={`place-btn ${meta.cls}`}
          onClick={onPlaceTrade}
          disabled={selectedStake < 1}
        >
          PLACE {meta.label} · {money(selectedStake)}
        </button>
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
  const win = r.pnl >= 0;
  const isOption = r.premium != null;

  if (broke) {
    return (
      <div className="trade-panel">
        <div className="result-banner loss">💥 BLOWN UP</div>
        <p className="broke-text">
          Your account is wiped out. Even beating the quants means surviving your
          own position sizing.
        </p>
        <button className="next-btn" onClick={onReset}>
          RESET ACCOUNT
        </button>
      </div>
    );
  }

  return (
    <div className="trade-panel">
      <div className={`result-banner ${win ? "win" : "loss"}`}>
        <span>{win ? "▲ PROFIT" : "▼ LOSS"}</span>
        <span className="result-pnl">{signedMoney(r.pnl)}</span>
      </div>
      <div className="result-detail">
        <div>
          <span className="result-label">Trade</span>
          <span className="result-value">{r.instrument.toUpperCase()}</span>
        </div>
        <div>
          <span className="result-label">
            Move / {r.horizon} {unit(interval, r.horizon)}
          </span>
          <span className={`result-value ${r.pct_change >= 0 ? "pos" : "neg"}`}>
            {r.pct_change >= 0 ? "▲ +" : "▼ "}
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

      <div className="window-dates">
        📅 this window was <b>{r.start_date}</b> → <b>{r.end_date}</b>
      </div>

      {isOption && (
        <div className="option-breakdown">
          <span>
            strike <b>${r.strike!.toFixed(2)}</b>
          </span>
          <span>
            premium <b>${r.premium!.toFixed(2)}</b>
          </span>
          <span>
            contracts <b>{r.contracts!.toFixed(1)}</b>
          </span>
          <span>
            payoff <b>${r.payoff!.toFixed(2)}</b>/ct
          </span>
        </div>
      )}

      <button className="next-btn" onClick={onNext}>
        NEXT ROUND →
      </button>
    </div>
  );
}
