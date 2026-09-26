from typing import Optional

BASE_PRICE = 6.0  # Rs/kWh
ALPHA = 2.0
# Transformer congestion premium: + BETA * (import load / transformer capacity)^2.
# Quadratic, so it's negligible at light load and bites as the transformer nears capacity.
BETA = 4.0
PRICE_MIN = 4.0  # Rs/kWh
PRICE_MAX = 12.0  # Rs/kWh


def clearing_price(
    total_demand_kwh: float,
    total_supply_kwh: float,
    transformer_import_ratio: float = 0.0,
) -> Optional[float]:
    """price = base_price + alpha * (demand / supply) + beta * (import_load / max_load)^2,
    clamped to [price_min, price_max].

    `transformer_import_ratio` is how hard the neighbourhood is drawing on the grid
    through its transformer (0 = not importing, 1 = at capacity). Export (midday
    reverse flow) adds no premium: pricing local energy higher then would only
    discourage the local consumption that relieves it.

    Returns None when there is no supply at all (no sellers this cycle -> no trades possible).
    """
    if total_supply_kwh <= 0:
        return None

    congestion = BETA * max(transformer_import_ratio, 0.0) ** 2
    price = BASE_PRICE + ALPHA * (total_demand_kwh / total_supply_kwh) + congestion
    return round(min(max(price, PRICE_MIN), PRICE_MAX), 2)
