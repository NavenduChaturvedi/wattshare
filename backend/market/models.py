from dataclasses import dataclass
from typing import Optional


@dataclass
class Trade:
    id: int
    seller_id: str
    buyer_id: str
    amount_kwh: float
    price_per_kwh: float
    timestamp: int  # simulated hour (0-23)


@dataclass
class MarketState:
    timestamp: int  # simulated hour (0-23)
    total_supply_kwh: float
    total_demand_kwh: float
    clearing_price: Optional[float]
