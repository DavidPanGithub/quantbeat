import type { GuessResponse, Instrument, NewRoundResponse } from "./types";

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
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
