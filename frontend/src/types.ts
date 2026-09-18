// Types mirror the backend API contract (backend/app/models.py).

export type Direction = "up" | "down";

export interface Candle {
  t: number; // sequential day index, NOT a real date
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
  start_close: number;
  visible: Candle[];
  bots: BotInfo[];
}

export interface BotResult {
  id: string;
  label: string;
  direction: Direction;
  correct: boolean;
}

export interface GuessResponse {
  round_id: number;
  horizon: number;
  your_direction: Direction;
  actual_direction: Direction;
  correct: boolean;
  start_close: number;
  future_close: number;
  pct_change: number;
  future: Candle[];
  bot_results: BotResult[];
}

// Per-player running tally kept for the session (you + each bot).
export interface Tally {
  correct: number;
  total: number;
}
