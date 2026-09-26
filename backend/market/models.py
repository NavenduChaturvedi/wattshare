from dataclasses import dataclass
from typing import Optional


@dataclass
class Trade:
    id: int
    seller_id: str
    buyer_id: str
    amount_kwh: float
    price_per_kwh: float
    timestamp: int  # simulated hour of day (0-23) -- for display, unchanged since Phase 2

    # Marketplace fields (Phase 4 revision). Left None for trades produced by the
    # original neighborhood-wide dispatcher cycle (POST /match), which isn't tied
    # to any listing and isn't part of a seller's reliability history.
    listing_id: Optional[int] = None
    fulfilled_as_listed: Optional[bool] = None
    tick: Optional[int] = None  # absolute tick at execution time (see SimulationEngine.total_ticks)


@dataclass
class MarketState:
    timestamp: int  # simulated hour (0-23)
    total_supply_kwh: float
    total_demand_kwh: float
    clearing_price: Optional[float]
    # Net flow through the distribution transformer this hour: + importing from
    # the grid, - exporting to it. Local P2P trades stay on the LV feeder; only
    # the neighbourhood's residual imbalance crosses the transformer.
    transformer_load_kw: float = 0.0
    transformer_load_pct: Optional[float] = None  # |load| / capacity; None if capacity unknown
