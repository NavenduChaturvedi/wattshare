from dataclasses import dataclass
from typing import Optional

from backend.simulation.models import Household

from .execution import resolve_deliverable
from .models import Listing
from .summary import effective_price


@dataclass
class Quote:
    """What buying from a listing would actually do right now -- the same caps the
    purchase itself applies, so a preview and the real trade can't disagree."""

    listing_id: int
    seller_household_id: str
    price_per_kwh: float
    advertised_kwh: float  # what the listing says
    deliverable_kwh: float  # what the seller can hand over right now
    buyer_need_kwh: float  # the buyer's remaining deficit this hour
    max_kwh: float  # min(deliverable, need): the most this purchase can be
    requested_kwh: float
    amount_kwh: float  # requested, capped at max_kwh
    total_cost: float
    stale: bool  # the seller can't deliver everything the listing advertises


def build_quote(
    listing: Listing,
    seller: Household,
    buyer_need_kwh: float,
    requested_kwh: Optional[float],
    current_clearing_price: Optional[float],
) -> Quote:
    """`requested_kwh=None` quotes the maximum."""
    deliverable = resolve_deliverable(listing, seller)
    need = round(max(buyer_need_kwh, 0.0), 3)
    max_kwh = round(min(deliverable, need), 3)
    requested = max_kwh if requested_kwh is None else round(max(requested_kwh, 0.0), 3)
    amount = round(min(requested, max_kwh), 3)
    price = effective_price(listing, current_clearing_price)
    return Quote(
        listing_id=listing.id,
        seller_household_id=listing.seller_household_id,
        price_per_kwh=price,
        advertised_kwh=listing.units_available_kwh,
        deliverable_kwh=deliverable,
        buyer_need_kwh=need,
        max_kwh=max_kwh,
        requested_kwh=requested,
        amount_kwh=amount,
        total_cost=round(amount * price, 2),
        stale=deliverable < listing.units_available_kwh - 1e-9,
    )
