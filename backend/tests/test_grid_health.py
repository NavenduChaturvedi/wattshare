import pytest

from backend.market.grid_health import compute_grid_health


@pytest.mark.parametrize(
    "load_pct, expected",
    [
        (0.0, "green"),
        (49.9, "green"),
        (50.0, "yellow"),  # boundaries belong to the higher band
        (79.9, "yellow"),
        (80.0, "red"),
        (130.0, "red"),  # overloaded
    ],
)
def test_bands(load_pct, expected):
    assert compute_grid_health(load_pct) == expected


def test_no_reading_yet_is_green():
    assert compute_grid_health(None) == "green"
