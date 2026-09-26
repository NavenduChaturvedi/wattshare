import pytest

from backend.market.engine import MarketEngine
from backend.market.pricing import clearing_price

from .factories import household


def neighborhood():
    # 4 sellers with plenty of surplus (10 kWh), 6 buyers needing 6 kWh in total.
    sellers = [household(f"S{i}", gen=3.5, cons=1.0) for i in range(1, 5)]
    buyers = [household(f"B{i}", gen=0.0, cons=1.0) for i in range(1, 7)]
    return sellers + buyers


def test_every_buyer_is_served_when_supply_is_plentiful():
    # The old index-aligned zip left B5 and B6 unserved here.
    state, trades = MarketEngine().run_cycle(neighborhood(), hour=12)
    assert {t.buyer_id for t in trades} == {f"B{i}" for i in range(1, 7)}
    assert sum(t.amount_kwh for t in trades) == pytest.approx(state.total_demand_kwh)


def test_all_trades_settle_at_the_clearing_price():
    state, trades = MarketEngine().run_cycle(neighborhood(), hour=12)
    assert state.clearing_price == clearing_price(6.0, 10.0)
    assert {t.price_per_kwh for t in trades} == {state.clearing_price}


def test_manual_asks_decide_who_sells_first():
    hh = [household("S1", gen=3.0, cons=1.0), household("S2", gen=3.0, cons=1.0), household("B1", cons=2.0)]
    _, trades = MarketEngine().run_cycle(hh, hour=12, ask_prices={"S1": 10.0, "S2": 5.0})
    assert [(t.seller_id, t.amount_kwh) for t in trades] == [("S2", 2.0)]


def test_auto_sellers_ask_the_clearing_price():
    # S2 asks above the clearing price (6 + 2*(2/4) = 7), so auto-priced S1 goes first.
    hh = [household("S1", gen=3.0, cons=1.0), household("S2", gen=3.0, cons=1.0), household("B1", cons=2.0)]
    _, trades = MarketEngine().run_cycle(hh, hour=12, ask_prices={"S2": 9.0})
    assert [t.seller_id for t in trades] == ["S1"]


def test_energy_already_traded_this_hour_is_not_rematched():
    hh = [household("S1", gen=3.0, cons=1.0), household("B1", cons=2.0)]
    hh[0].record_sale(2.0)
    hh[1].record_purchase(2.0)
    state, trades = MarketEngine().run_cycle(hh, hour=12)
    assert trades == []
    assert state.clearing_price is None


def test_no_supply_means_no_price_and_no_trades():
    state, trades = MarketEngine().run_cycle([household("B1", cons=1.0)], hour=21)
    assert (state.clearing_price, trades) == (None, [])
    assert state.total_demand_kwh == 1.0
