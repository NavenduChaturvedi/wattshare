from typing import Optional, Tuple

from backend.market.models import Trade
from backend.simulation.models import Household

from .models import Listing
from .summary import effective_price


def resolve_deliverable(listing: Listing, seller_household: Household) -> float:
    """What the seller can actually hand over right now, which may be less than
    what the listing promised if their surplus has moved on since it was snapshotted."""
    actual_surplus = max(seller_household.net_kwh, 0.0)
    return round(max(min(listing.units_available_kwh, actual_surplus), 0.0), 3)


def execute_trade(
    listing: Listing,
    buyer_household_id: str,
    requested_kwh: float,
    seller_household: Household,
    current_clearing_price: Optional[float],
    current_hour: int,
    current_tick: int,
) -> Tuple[Trade, float]:
    """Attempts to buy up to `requested_kwh` from this listing. Always returns a
    Trade -- even a 0 kWh one if the seller has nothing deliverable -- because a
    real attempt happened and the seller's reliability history should reflect it,
    whether the trade came from a human clicking "buy" or from Smart Match picking
    this listing on their behalf.

    Returns (trade, remaining_deliverable_after) -- the caller re-snapshots the
    listing with the remainder so it doesn't stay stuck at its old, now-inflated
    advertised amount.
    """
    deliverable = resolve_deliverable(listing, seller_household)
    amount = round(min(requested_kwh, deliverable), 3)
    fulfilled_as_listed = deliverable >= listing.units_available_kwh

    trade = Trade(
        id=0,  # assigned by the database on insert
        seller_id=listing.seller_household_id,
        buyer_id=buyer_household_id,
        amount_kwh=amount,
        price_per_kwh=effective_price(listing, current_clearing_price),
        timestamp=current_hour,
        listing_id=listing.id,
        fulfilled_as_listed=fulfilled_as_listed,
        tick=current_tick,
    )
    remaining_after = round(max(deliverable - amount, 0.0), 3)
    return trade, remaining_after
