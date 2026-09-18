interface HeaderProps {
  ticker: string;
  price: number;
  roundNumber: number;
}

export default function Header({ ticker, price, roundNumber }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="brand">
        <span className="brand-mark">◆</span> QUANT<span className="brand-accent">BEAT</span>
      </div>
      <div className="ticker-tape">
        <span className="live-dot" />
        <span className="ticker-symbol">{ticker}</span>
        <span className="ticker-price">
          {price ? `$${price.toFixed(2)}` : "—"}
        </span>
        <span className="ticker-tag">HISTORICAL REPLAY</span>
      </div>
      <div className="round-badge">ROUND #{roundNumber}</div>
    </header>
  );
}
