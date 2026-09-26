"""Small builders so tests read as scenarios rather than constructor noise."""

from typing import Optional

from backend.market.models import Trade
from backend.marketplace.models import Listing
from backend.simulation.models import Household


def household(hid: str, gen: float = 0.0, cons: float = 0.0, zone: str = "Z1") -> Household:
    h = Household(
        id=hid,
        name=f"House {hid}",
        has_solar=gen > 0,
        capacity_kw=5.0 if gen > 0 else 0.0,
        baseline_kw=0.5,
        zone_id=zone,
    )
    h.current_generation_kwh = gen
    h.current_consumption_kwh = cons
    return h


def listing(
    seller: str = "S1",
    units: float = 2.0,
    mode: str = "auto",
    ask: Optional[float] = None,
    lid: int = 1,
    tick: int = 0,
) -> Listing:
    return Listing(
        id=lid,
        seller_household_id=seller,
        units_available_kwh=units,
        pricing_mode=mode,
        asking_price_per_kwh=ask,
        created_at_tick=tick,
    )


def listing_trade(
    seller: str = "S1",
    tick: int = 0,
    fulfilled: bool = True,
    amount: float = 1.0,
    price: float = 6.0,
) -> Trade:
    return Trade(
        id=1,
        seller_id=seller,
        buyer_id="B1",
        amount_kwh=amount,
        price_per_kwh=price,
        timestamp=tick % 24,
        listing_id=1,
        fulfilled_as_listed=fulfilled,
        tick=tick,
    )


def dispatcher_trade(seller: str = "S1", amount: float = 1.0, price: float = 6.0, tick: Optional[int] = None) -> Trade:
    return Trade(id=1, seller_id=seller, buyer_id="B1", amount_kwh=amount, price_per_kwh=price, timestamp=0, tick=tick)
