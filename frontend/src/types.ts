// Types mirror the backend API contract (backend/app/models.py).

export type Direction = "up" | "down";
export type Instrument = "long" | "short" | "call" | "put";

export interface Candle {
  t: number; // sequential bar index, NOT a real date
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BotInfo {
  id: string;
  label: string;
}

export interface NewRoundResponse {
  round_id: number;
  ticker: string;
  interval: string; // human unit for one bar: "day", "minute", ...
  horizon_choices: number[];
  stake_choices: number[];
  starting_balance: number;
  start_close: number;
  date_min: string | null;
  date_max: string | null;
  visible: Candle[];
  bots: BotInfo[];
}

export interface BotResult {
  id: string;
  label: string;
  direction: Direction;
  correct: boolean;
  pnl: number;
}

export interface GuessResponse {
  round_id: number;
  horizon: number;
  instrument: Instrument;
  stake: number;
  your_direction: Direction;
  actual_direction: Direction;
  correct: boolean;
  start_close: number;
  future_close: number;
  pct_change: number;
  pnl: number;
  start_date: string;
  end_date: string;
  strike: number | null;
  premium: number | null;
  contracts: number | null;
  payoff: number | null;
  future: Candle[];
  bot_results: BotResult[];
}

// Per-player running tally kept for the session (you + each bot).
export interface Tally {
  correct: number;
  total: number;
}
