from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel


class ConfigOut(BaseModel):
    location: str
    latitude: float
    longitude: float
    sim_date: date
    season: Optional[str] = None  # None in synthetic mode
    data_source: Literal["real", "synthetic"]
    households: Literal["demo", "generated"]
    solar_source: str
    load_source: str


class HouseholdOut(BaseModel):
    id: str
    name: str
    has_solar: bool
    zone_id: str
    current_generation_kwh: float
    current_consumption_kwh: float
    battery_stored_kwh: float
    battery_capacity_kwh: float  # 0 = no battery
    battery_flow_kwh: float  # this hour: + charging, - discharging
    traded_kwh: float  # already traded this hour: + sold, - bought
    net_kwh: float  # generation - consumption - battery flow: + offering, - needing
    open_net_kwh: float  # net_kwh not yet traded this hour


class TradeOut(BaseModel):
    id: int
    seller_id: str
    buyer_id: str
    amount_kwh: float
    price_per_kwh: float
    timestamp: int


class MarketStateOut(BaseModel):
    timestamp: Optional[int] = None
    total_supply_kwh: float
    total_demand_kwh: float
    clearing_price: Optional[float] = None
    transformer_load_kw: float = 0.0  # + importing from the grid, - exporting
    transformer_load_pct: Optional[float] = None


class LedgerVerifyOut(BaseModel):
    valid: bool
    trades_checked: int  # rows verified before the first break (all of them when valid)
    head_hash: str  # hash of the last verified trade -- the chain's current tip
    first_invalid_trade_id: Optional[int] = None


class SimulationStatusOut(BaseModel):
    hour: int  # the hour currently open for trading (0-23)
    total_ticks: int


class TickResponse(BaseModel):
    hour: int
    households: List[HouseholdOut]


class MatchResponse(BaseModel):
    market_state: MarketStateOut
    trades: List[TradeOut]


class ListingCreate(BaseModel):
    seller_household_id: str
    pricing_mode: Literal["auto", "manual"]
    asking_price_per_kwh: Optional[float] = None


class ListingOut(BaseModel):
    id: int
    seller_household_id: str
    units_available_kwh: float
    pricing_mode: str
    asking_price_per_kwh: Optional[float] = None
    created_at_tick: int


class BuyerListingOut(BaseModel):
    """GET /listings, enriched with what the buyer dashboard actually needs to
    render a row -- resolving pricing_mode into one real number, and pulling in
    the seller's name/zone/reliability so the frontend doesn't have to cross-
    reference three other endpoints per row."""

    id: int
    seller_household_id: str
    seller_name: str
    zone_id: str
    units_available_kwh: float
    price_per_kwh: float
    reliability_score: float


class SellerStatsOut(BaseModel):
    seller_household_id: str
    reliability_score: float
    total_kwh_sold_lifetime: float
    earnings_today: float
    earnings_week: float
    earnings_lifetime: float


class PricePointOut(BaseModel):
    hour: int
    clearing_price: float


class MarketSummaryOut(BaseModel):
    current_clearing_price: Optional[float] = None
    average_listing_price: Optional[float] = None
    best_listing_price: Optional[float] = None
    grid_health: Literal["green", "yellow", "red"]
    transformer_load_pct: Optional[float] = None
    price_trend: List[PricePointOut]


class BuyFromListingRequest(BaseModel):
    buyer_household_id: str
    amount_kwh: float


class TradeExecutionOut(BaseModel):
    trade: TradeOut
    fulfilled_as_listed: bool
    message: str


class SmartMatchRequest(BaseModel):
    buyer_household_id: str
    desired_kwh: float


class SmartMatchResponseOut(BaseModel):
    trades: List[TradeOut]
    total_kwh_matched: float
    total_cost: float
    fully_matched: bool
