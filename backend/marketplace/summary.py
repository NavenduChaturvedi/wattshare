from typing import List, Optional, Tuple

from backend.market.pricing import BASE_PRICE

from .models import Listing


def effective_price(listing: Listing, current_clearing_price: Optional[float]) -> float:
    """What a buyer would actually pay for this listing right now: the seller's own
    asking price in manual mode, or the live clearing price in auto mode (falling
    back to the base price if no market cycle has run yet)."""
    if listing.pricing_mode == "manual" and listing.asking_price_per_kwh is not None:
        return listing.asking_price_per_kwh
    return current_clearing_price if current_clearing_price is not None else BASE_PRICE


def compute_listing_price_stats(
    listings: List[Listing], current_clearing_price: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """(average, best/lowest) effective price across active listings, or (None, None)
    when there's nothing on offer right now."""
    if not listings:
        return None, None

    prices = [effective_price(listing, current_clearing_price) for listing in listings]
    return round(sum(prices) / len(prices), 2), round(min(prices), 2)
