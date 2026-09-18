import type { GuessResponse, Instrument, NewRoundResponse } from "./types";

// In dev this is empty and requests hit the Vite proxy (same origin). In
// production set VITE_API_BASE to the deployed backend URL at build time.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export function newRound(
  fromDate?: string,
  toDate?: string
): Promise<NewRoundResponse> {
  return post<NewRoundResponse>("/api/round", {
    from_date: fromDate ?? null,
    to_date: toDate ?? null,
  });
}

export function submitGuess(
  roundId: number,
  instrument: Instrument,
  stake: number,
  horizon: number
): Promise<GuessResponse> {
  return post<GuessResponse>(`/api/round/${roundId}/guess`, {
    instrument,
    stake,
    horizon,
  });
}
