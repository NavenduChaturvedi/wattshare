from dataclasses import dataclass
from typing import Literal, Optional

PricingMode = Literal["auto", "manual"]


@dataclass
class Listing:
    id: int
    seller_household_id: str
    units_available_kwh: float  # snapshot of the seller's surplus when created/updated
    pricing_mode: PricingMode
    asking_price_per_kwh: Optional[float]  # None when pricing_mode == "auto"
    created_at_tick: int  # SimulationEngine.total_ticks at creation/last update


@dataclass
class SellerStats:
    """Derived from trade history -- never stored raw, always recomputed."""

    seller_household_id: str
    reliability_score: float
    total_kwh_sold_lifetime: float
    earnings_today: float
    earnings_week: float
    earnings_lifetime: float
