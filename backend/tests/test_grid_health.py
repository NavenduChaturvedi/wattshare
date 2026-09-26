import pytest

from backend.market.grid_health import compute_grid_health


@pytest.mark.parametrize(
    "demand, supply, expected",
    [
        (1.0, 4.0, "green"),  # ratio 0.25
        (2.0, 4.0, "green"),  # ratio 0.5, boundary is inclusive
        (4.0, 4.0, "yellow"),  # ratio 1.0
        (6.0, 4.0, "yellow"),  # ratio 1.5, boundary is inclusive
        (8.0, 4.0, "red"),  # ratio 2.0
    ],
)
def test_bands(demand, supply, expected):
    assert compute_grid_health(demand, supply) == expected


def test_no_supply_with_demand_is_red():
    assert compute_grid_health(total_demand_kwh=3.0, total_supply_kwh=0.0) == "red"


def test_no_supply_and_no_demand_is_green():
    assert compute_grid_health(total_demand_kwh=0.0, total_supply_kwh=0.0) == "green"
