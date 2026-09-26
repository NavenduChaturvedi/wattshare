export interface Household {
  id: string;
  name: string;
  has_solar: boolean;
  zone_id: string;
  current_generation_kwh: number;
  current_consumption_kwh: number;
  battery_stored_kwh: number;
  traded_kwh: number; // already traded this hour: + sold, - bought
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
  price_trend: MarketTrendPoint[];
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
