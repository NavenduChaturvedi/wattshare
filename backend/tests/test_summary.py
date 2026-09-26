from backend.market.pricing import BASE_PRICE
from backend.marketplace.summary import compute_listing_price_stats, effective_price

from .factories import listing


def test_manual_listing_uses_its_own_ask():
    assert effective_price(listing(mode="manual", ask=5.5), current_clearing_price=9.0) == 5.5


def test_auto_listing_follows_clearing_price():
    assert effective_price(listing(mode="auto"), current_clearing_price=9.0) == 9.0


def test_auto_listing_falls_back_to_base_before_any_cycle():
    assert effective_price(listing(mode="auto"), current_clearing_price=None) == BASE_PRICE


def test_price_stats_empty():
    assert compute_listing_price_stats([], current_clearing_price=7.0) == (None, None)


def test_price_stats_average_and_best():
    listings = [listing(mode="manual", ask=5.0), listing(mode="auto"), listing(mode="manual", ask=9.0)]
    assert compute_listing_price_stats(listings, current_clearing_price=7.0) == (7.0, 5.0)
