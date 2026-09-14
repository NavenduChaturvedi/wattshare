from typing import List, Optional

from pydantic import BaseModel


class HouseholdOut(BaseModel):
    id: str
    name: str
    has_solar: bool
    current_generation_kwh: float
    current_consumption_kwh: float
    battery_stored_kwh: float


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


class TickResponse(BaseModel):
    hour: int
    households: List[HouseholdOut]


class MatchResponse(BaseModel):
    market_state: MarketStateOut
    trades: List[TradeOut]
