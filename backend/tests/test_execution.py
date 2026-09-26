import pytest

from backend.marketplace.execution import execute_trade, resolve_deliverable

from .factories import household, listing


def run(lst, seller, requested, price=7.0):
    return execute_trade(lst, "B1", requested, seller, price, current_hour=12, current_tick=36)


def test_full_fill_from_an_accurate_listing():
    seller = household("S1", gen=3.0, cons=1.0)  # 2 kWh surplus
    trade, remaining = run(listing(units=2.0), seller, requested=1.5)
    assert trade.amount_kwh == 1.5
    assert trade.fulfilled_as_listed is True
    assert trade.price_per_kwh == 7.0
    assert (trade.listing_id, trade.tick, trade.timestamp) == (1, 36, 12)
    assert remaining == pytest.approx(0.5)


def test_request_larger_than_listing_is_capped_at_listing():
    seller = household("S1", gen=5.0, cons=1.0)  # 4 kWh surplus, but only 2 listed
    trade, remaining = run(listing(units=2.0), seller, requested=10.0)
    assert trade.amount_kwh == 2.0
    assert trade.fulfilled_as_listed is True
    assert remaining == 0.0


def test_stale_listing_partially_fills_and_counts_as_unfulfilled():
    seller = household("S1", gen=2.0, cons=1.0)  # surplus dropped to 1 kWh after listing 2
    trade, remaining = run(listing(units=2.0), seller, requested=2.0)
    assert trade.amount_kwh == 1.0
    assert trade.fulfilled_as_listed is False
    assert remaining == 0.0


def test_nothing_deliverable_still_records_a_zero_trade():
    seller = household("S1", gen=0.0, cons=1.0)  # now in deficit
    trade, remaining = run(listing(units=2.0), seller, requested=1.0)
    assert trade.amount_kwh == 0.0
    assert trade.fulfilled_as_listed is False
    assert remaining == 0.0


def test_energy_already_traded_this_hour_is_not_deliverable():
    seller = household("S1", gen=3.0, cons=1.0)
    seller.record_sale(1.5)
    assert resolve_deliverable(listing(units=2.0), seller) == pytest.approx(0.5)


def test_manual_ask_is_the_trade_price():
    seller = household("S1", gen=3.0, cons=1.0)
    trade, _ = run(listing(units=2.0, mode="manual", ask=5.0), seller, requested=1.0, price=9.0)
    assert trade.price_per_kwh == 5.0
