import pytest

from backend.market.pricing import ALPHA, BASE_PRICE, PRICE_MAX, PRICE_MIN, clearing_price


def test_no_supply_means_no_price():
    assert clearing_price(total_demand_kwh=5.0, total_supply_kwh=0.0) is None
    assert clearing_price(total_demand_kwh=0.0, total_supply_kwh=0.0) is None


def test_formula_inside_band():
    # 6 + 2 * (2 / 4) = 7
    assert clearing_price(total_demand_kwh=2.0, total_supply_kwh=4.0) == pytest.approx(BASE_PRICE + ALPHA * 0.5)


def test_clamped_at_max_when_demand_swamps_supply():
    assert clearing_price(total_demand_kwh=100.0, total_supply_kwh=1.0) == PRICE_MAX


def test_zero_demand_sits_at_base_price():
    # The formula never goes below BASE_PRICE, so PRICE_MIN only bites if the constants change.
    assert clearing_price(total_demand_kwh=0.0, total_supply_kwh=10.0) == BASE_PRICE
    assert PRICE_MIN <= BASE_PRICE <= PRICE_MAX


def test_monotonic_in_demand_over_supply():
    ratios = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 10.0]
    prices = [clearing_price(total_demand_kwh=r, total_supply_kwh=1.0) for r in ratios]
    assert prices == sorted(prices)
