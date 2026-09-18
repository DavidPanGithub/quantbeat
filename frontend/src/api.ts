import type { Direction, GuessResponse, NewRoundResponse } from "./types";

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

export function newRound(): Promise<NewRoundResponse> {
  return post<NewRoundResponse>("/api/round");
}

export function submitGuess(
  roundId: number,
  direction: Direction,
  horizon: number
): Promise<GuessResponse> {
  return post<GuessResponse>(`/api/round/${roundId}/guess`, { direction, horizon });
}
