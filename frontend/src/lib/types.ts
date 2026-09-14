export interface Household {
  id: string;
  name: string;
  has_solar: boolean;
  current_generation_kwh: number;
  current_consumption_kwh: number;
  battery_stored_kwh: number;
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
