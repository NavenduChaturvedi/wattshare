import pytest

from backend.market.pricing import ALPHA, BASE_PRICE, BETA, PRICE_MAX, PRICE_MIN, clearing_price


def test_no_supply_means_no_price():
    assert clearing_price(total_demand_kwh=5.0, total_supply_kwh=0.0) is None
    assert clearing_price(total_demand_kwh=0.0, total_supply_kwh=0.0) is None


def test_formula_inside_band():
    # 6 + 2 * (6 / 4 - 1) = 7
    assert clearing_price(total_demand_kwh=6.0, total_supply_kwh=4.0) == pytest.approx(BASE_PRICE + ALPHA * 0.5)


def test_balanced_market_clears_at_base_price():
    assert clearing_price(total_demand_kwh=3.0, total_supply_kwh=3.0) == BASE_PRICE


def test_surplus_prices_below_base():
    # A midday glut (demand a quarter of supply): 6 + 2 * (0.25 - 1) = 4.5
    assert clearing_price(total_demand_kwh=1.0, total_supply_kwh=4.0) == pytest.approx(4.5)
    assert clearing_price(total_demand_kwh=1.0, total_supply_kwh=4.0) < BASE_PRICE


def test_clamped_at_max_when_demand_swamps_supply():
    assert clearing_price(total_demand_kwh=100.0, total_supply_kwh=1.0) == PRICE_MAX


def test_zero_demand_reaches_the_floor():
    # 6 + 2 * (0 - 1) = 4 == PRICE_MIN: the floor is reachable, but only with no demand at all.
    assert clearing_price(total_demand_kwh=0.0, total_supply_kwh=10.0) == PRICE_MIN
    assert PRICE_MIN <= BASE_PRICE <= PRICE_MAX


def test_transformer_import_adds_a_quadratic_premium():
    no_load = clearing_price(2.0, 4.0)
    assert clearing_price(2.0, 4.0, transformer_import_ratio=0.5) == pytest.approx(no_load + BETA * 0.25)
    assert clearing_price(2.0, 4.0, transformer_import_ratio=1.0) == pytest.approx(no_load + BETA)


def test_export_adds_no_premium():
    assert clearing_price(2.0, 4.0, transformer_import_ratio=-0.8) == clearing_price(2.0, 4.0)


def test_congested_price_still_clamps_at_max():
    assert clearing_price(3.0, 4.0, transformer_import_ratio=3.0) == PRICE_MAX


def test_monotonic_in_demand_over_supply():
    ratios = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 10.0]
    prices = [clearing_price(total_demand_kwh=r, total_supply_kwh=1.0) for r in ratios]
    assert prices == sorted(prices)
