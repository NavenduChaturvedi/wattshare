import type {
  BuyerListing,
  Household,
  LedgerCheck,
  Listing,
  MarketState,
  MarketSummary,
  MatchResponse,
  PricingMode,
  SellerStats,
  SimConfig,
  SimulationStatus,
  SmartMatchResult,
  TickResponse,
  Trade,
  TradeExecutionResult,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  if (res.status === 204) return null as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

export const api = {
  getSimulationStatus: () => request<SimulationStatus>("/simulation"),
  getConfig: () => request<SimConfig>("/config"),
  getHouseholds: () => request<Household[]>("/households"),
  tick: () => request<TickResponse>("/simulate/tick", { method: "POST" }),
  match: () => request<MatchResponse>("/match", { method: "POST" }),
  getTrades: () => request<Trade[]>("/trades"),
  verifyLedger: () => request<LedgerCheck>("/ledger/verify"),
  getMarketState: () => request<MarketState>("/market-state"),

  getSellerListing: (sellerId: string) => request<Listing | null>(`/listings/${sellerId}`),
  getActiveListings: () => request<BuyerListing[]>("/listings"),
  saveListing: (sellerId: string, pricingMode: PricingMode, askingPricePerKwh: number | null) =>
    request<Listing>("/listings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        seller_household_id: sellerId,
        pricing_mode: pricingMode,
        asking_price_per_kwh: askingPricePerKwh,
      }),
    }),
  getSellerStats: (sellerId: string) => request<SellerStats>(`/sellers/${sellerId}/stats`),
  getMarketSummary: () => request<MarketSummary>("/market/summary"),

  buyFromListing: (listingId: number, buyerId: string, amountKwh: number) =>
    request<TradeExecutionResult>(`/listings/${listingId}/buy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buyer_household_id: buyerId, amount_kwh: amountKwh }),
    }),
  smartMatch: (buyerId: string, desiredKwh: number) =>
    request<SmartMatchResult>("/match/smart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buyer_household_id: buyerId, desired_kwh: desiredKwh }),
    }),
};
