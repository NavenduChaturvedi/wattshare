import itertools
import random

import pytest

from backend.market.matching import Bid, Offer, match


def totals_by(pairings, attr):
    out = {}
    for p in pairings:
        key = getattr(p, attr)
        out[key] = round(out.get(key, 0.0) + p.amount_kwh, 3)
    return out


def test_one_big_seller_serves_several_buyers():
    pairings = match([Offer("S1", ask_price=6.0, kwh=10.0)], [Bid("B1", 2.0), Bid("B2", 3.0), Bid("B3", 4.0)])
    assert len(pairings) == 3
    assert totals_by(pairings, "buyer_id") == {"B1": 2.0, "B2": 3.0, "B3": 4.0}
    assert sum(p.amount_kwh for p in pairings) == pytest.approx(9.0)  # 1 kWh of surplus left over


def test_several_small_sellers_serve_one_big_buyer():
    offers = [Offer("S1", 6.0, 1.0), Offer("S2", 6.0, 1.5), Offer("S3", 6.0, 2.0)]
    pairings = match(offers, [Bid("B1", 10.0)])
    assert len(pairings) == 3
    assert totals_by(pairings, "seller_id") == {"S1": 1.0, "S2": 1.5, "S3": 2.0}


def test_cheapest_seller_is_consumed_first():
    offers = [Offer("S1", 9.0, 2.0), Offer("S2", 5.0, 2.0), Offer("S3", 7.0, 2.0)]
    pairings = match(offers, [Bid("B1", 3.0)])
    assert [(p.seller_id, p.amount_kwh) for p in pairings] == [("S2", 2.0), ("S3", 1.0)]


def test_neediest_buyer_is_served_first():
    pairings = match([Offer("S1", 6.0, 3.0)], [Bid("B1", 1.0), Bid("B2", 2.5), Bid("B3", 1.5)])
    assert [(p.buyer_id, p.amount_kwh) for p in pairings] == [("B2", 2.5), ("B3", 0.5)]


def test_ties_break_by_id_so_results_are_deterministic():
    offers = [Offer("S3", 6.0, 1.0), Offer("S1", 6.0, 1.0), Offer("S2", 6.0, 1.0)]
    bids = [Bid("B2", 1.0), Bid("B1", 1.0)]
    pairings = match(offers, bids)
    assert [(p.seller_id, p.buyer_id) for p in pairings] == [("S1", "B1"), ("S2", "B2")]
    # Input order doesn't matter.
    for perm_offers in itertools.permutations(offers):
        for perm_bids in itertools.permutations(bids):
            assert match(list(perm_offers), list(perm_bids)) == pairings


def test_exact_balance_exhausts_both_sides_without_zero_trades():
    offers = [Offer("S1", 6.0, 2.0), Offer("S2", 6.0, 1.0)]
    bids = [Bid("B1", 1.5), Bid("B2", 1.5)]
    pairings = match(offers, bids)
    assert all(p.amount_kwh > 0 for p in pairings)
    assert sum(p.amount_kwh for p in pairings) == pytest.approx(3.0)


def test_empty_or_non_positive_sides_produce_nothing():
    assert match([], [Bid("B1", 1.0)]) == []
    assert match([Offer("S1", 6.0, 1.0)], []) == []
    assert match([Offer("S1", 6.0, 0.0)], [Bid("B1", 1.0)]) == []
    assert match([Offer("S1", 6.0, 1.0)], [Bid("B1", -1.0)]) == []


@pytest.mark.parametrize("seed", range(50))
def test_conservation_on_random_markets(seed):
    rng = random.Random(seed)
    offers = [Offer(f"S{i}", round(rng.uniform(4, 12), 2), round(rng.uniform(0.001, 5), 3)) for i in range(rng.randint(0, 6))]
    bids = [Bid(f"B{i}", round(rng.uniform(0.001, 5), 3)) for i in range(rng.randint(0, 8))]
    pairings = match(offers, bids)

    supply = sum(o.kwh for o in offers)
    demand = sum(b.kwh for b in bids)
    traded = sum(p.amount_kwh for p in pairings)

    # Greedy two-pointer clears the whole short side.
    assert traded == pytest.approx(min(supply, demand), abs=1e-6)
    assert all(p.amount_kwh > 0 for p in pairings)
    sold = totals_by(pairings, "seller_id")
    bought = totals_by(pairings, "buyer_id")
    assert all(sold.get(o.household_id, 0) <= o.kwh + 1e-9 for o in offers)
    assert all(bought.get(b.household_id, 0) <= b.kwh + 1e-9 for b in bids)
