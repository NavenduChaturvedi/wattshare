import type {
  Household,
  MarketState,
  MatchResponse,
  TickResponse,
  Trade,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getHouseholds: () => request<Household[]>("/households"),
  tick: () => request<TickResponse>("/simulate/tick", { method: "POST" }),
  match: () => request<MatchResponse>("/match", { method: "POST" }),
  getTrades: () => request<Trade[]>("/trades"),
  getMarketState: () => request<MarketState>("/market-state"),
};
