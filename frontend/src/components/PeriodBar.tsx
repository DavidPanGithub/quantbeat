export interface Period {
  id: string;
  label: string;
  from?: string;
  to?: string;
}

interface PeriodBarProps {
  periods: Period[];
  selectedId: string;
  onSelect: (p: Period) => void;
}

export default function PeriodBar({
  periods,
  selectedId,
  onSelect,
}: PeriodBarProps) {
  if (periods.length <= 1) return null; // nothing to pick between
  return (
    <div className="period-bar">
      <span className="period-label">MARKET ERA</span>
      <div className="period-chips">
        {periods.map((p) => (
          <button
            key={p.id}
            className={`period-chip ${p.id === selectedId ? "active" : ""}`}
            onClick={() => onSelect(p)}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
