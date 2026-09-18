import type { Candle } from "./types";

export function money(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })}`;
}

export function signedMoney(n: number): string {
  return `${n >= 0 ? "+" : "-"}$${Math.abs(n).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })}`;
}

// Mirrors backend/app/trading.py so options can show a live premium preview
// before the trade is placed. Keep in sync with ATM_PREMIUM_FACTOR /
// MIN_PREMIUM_FRACTION on the server.
const ATM_PREMIUM_FACTOR = 0.4;
const MIN_PREMIUM_FRACTION = 0.005;

export function estimatePremium(
  visible: Candle[],
  price: number,
  horizon: number
): number {
  const closes = visible.map((c) => c.close);
  const rets: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    if (closes[i - 1] > 0) rets.push(Math.log(closes[i] / closes[i - 1]));
  }
  let sigma = 0;
  if (rets.length >= 2) {
    const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
    const varc =
      rets.reduce((a, r) => a + (r - mean) ** 2, 0) / (rets.length - 1);
    sigma = Math.sqrt(varc);
  }
  return Math.max(
    ATM_PREMIUM_FACTOR * price * sigma * Math.sqrt(horizon),
    price * MIN_PREMIUM_FRACTION
  );
}
