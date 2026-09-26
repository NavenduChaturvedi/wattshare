export interface Household {
  id: string;
  name: string;
  has_solar: boolean;
  zone_id: string;
  current_generation_kwh: number;
  current_consumption_kwh: number;
  battery_stored_kwh: number;
  battery_capacity_kwh: number; // 0 = no battery
  battery_flow_kwh: number; // this hour: + charging, - discharging
  traded_kwh: number; // already traded this hour: + sold, - bought
  net_kwh: number; // generation - consumption - battery flow: + offering, - needing
  open_net_kwh: number; // net_kwh not yet traded this hour
}

export interface SimConfig {
  location: string;
  latitude: number;
  longitude: number;
  sim_date: string; // ISO date
  season: string | null;
  data_source: "real" | "synthetic";
  households: "demo" | "generated";
  solar_source: string;
  load_source: string;
  clock: "live" | "manual";
  clock_speed: number; // simulated hours per real hour
  timezone: string; // IANA, e.g. Asia/Kolkata
}

export interface Trade {
  id: number;
  seller_id: string;
  buyer_id: string;
  amount_kwh: number;
  price_per_kwh: number;
  timestamp: number;
}

export interface MarketState {
  timestamp: number | null;
  total_supply_kwh: number;
  total_demand_kwh: number;
  clearing_price: number | null;
  transformer_load_kw: number; // + importing from the grid, - exporting
  transformer_load_pct: number | null;
}

export interface LedgerCheck {
  valid: boolean;
  trades_checked: number;
  head_hash: string;
  first_invalid_trade_id: number | null;
}

export interface SimulationStatus {
  hour: number; // the hour currently open for trading
  total_ticks: number;
  clock: "live" | "manual";
  seconds_to_next_hour: number | null; // live clock only
  local_time: string | null; // live clock only, ISO 8601
}

export interface TickResponse {
  hour: number;
  households: Household[];
}

export interface MatchResponse {
  market_state: MarketState;
  trades: Trade[];
}

export type PricingMode = "auto" | "manual";

export interface Listing {
  id: number;
  seller_household_id: string;
  units_available_kwh: number;
  pricing_mode: PricingMode;
  asking_price_per_kwh: number | null;
  created_at_tick: number;
}

export interface SellerStats {
  seller_household_id: string;
  reliability_score: number;
  total_kwh_sold_lifetime: number;
  earnings_today: number;
  earnings_week: number;
  earnings_lifetime: number;
}

export interface BuyerListing {
  id: number;
  seller_household_id: string;
  seller_name: string;
  zone_id: string;
  units_available_kwh: number;
  price_per_kwh: number;
  reliability_score: number;
}

export type GridHealth = "green" | "yellow" | "red";

export interface MarketTrendPoint {
  hour: number;
  clearing_price: number;
}

export interface MarketSummary {
  current_clearing_price: number | null;
  average_listing_price: number | null;
  best_listing_price: number | null;
  grid_health: GridHealth;
  transformer_load_pct: number | null;
  price_trend: MarketTrendPoint[];
}

/** GET /listings/{id}/quote -- what a purchase would actually do right now. */
export interface PurchaseQuote {
  listing_id: number;
  seller_household_id: string;
  price_per_kwh: number;
  advertised_kwh: number;
  deliverable_kwh: number; // what the seller can hand over right now
  buyer_need_kwh: number;
  max_kwh: number; // min(deliverable, need)
  requested_kwh: number;
  amount_kwh: number; // requested, capped at max_kwh
  total_cost: number;
  stale: boolean; // seller can't deliver everything the listing advertises
}

export interface TradeExecutionResult {
  trade: Trade;
  fulfilled_as_listed: boolean;
  message: string;
}

export interface SmartMatchResult {
  trades: Trade[];
  total_kwh_matched: number;
  total_cost: number;
  fully_matched: boolean;
}
