from typing import Literal

GridHealth = Literal["green", "yellow", "red"]

# Same demand/supply ratio that drives clearing_price (see pricing.py) -- no new
# simulated quantity, just a traffic-light bucketing of a signal that already exists.
LOW_STRESS_RATIO = 0.5
HIGH_STRESS_RATIO = 1.5


def compute_grid_health(total_demand_kwh: float, total_supply_kwh: float) -> GridHealth:
    """Green: plenty of local supply relative to demand. Yellow: roughly balanced.
    Red: demand well exceeds local supply (or there's no supply at all to meet it)."""
    if total_supply_kwh <= 0:
        return "red" if total_demand_kwh > 0 else "green"

    ratio = total_demand_kwh / total_supply_kwh
    if ratio <= LOW_STRESS_RATIO:
        return "green"
    if ratio <= HIGH_STRESS_RATIO:
        return "yellow"
    return "red"
