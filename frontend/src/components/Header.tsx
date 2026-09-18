import { money } from "../format";

interface HeaderProps {
  ticker: string;
  price: number;
  balance: number;
  startingBalance: number;
  roundNumber: number;
}

export default function Header({
  ticker,
  price,
  balance,
  startingBalance,
  roundNumber,
}: HeaderProps) {
  const pnl = balance - startingBalance;
  const up = pnl >= 0;
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-mark">◆</span> QUANT<span className="brand-accent">BEAT</span>
      </div>
      <div className="ticker-tape">
        <span className="live-dot" />
        <span className="ticker-symbol">{ticker}</span>
        <span className="ticker-price">{price ? `$${price.toFixed(2)}` : "—"}</span>
        <span className="ticker-tag">HISTORICAL REPLAY</span>
      </div>
      <div className="account">
        <div className="account-balance">
          <span className="account-label">ACCOUNT</span>
          <span className={`account-value ${up ? "pos" : "neg"}`}>
            {money(balance)}
          </span>
        </div>
        <div className={`account-pnl ${up ? "pos" : "neg"}`}>
          {up ? "▲" : "▼"} {money(Math.abs(pnl))}
        </div>
      </div>
      <div className="round-badge">ROUND #{roundNumber}</div>
    </header>
  );
}
