from typing import Optional

BASE_PRICE = 6.0  # Rs/kWh
ALPHA = 2.0
PRICE_MIN = 4.0  # Rs/kWh
PRICE_MAX = 12.0  # Rs/kWh


def clearing_price(total_demand_kwh: float, total_supply_kwh: float) -> Optional[float]:
    """price = base_price + alpha * (demand / supply), clamped to [price_min, price_max].

    Returns None when there is no supply at all (no sellers this cycle -> no trades possible).
    """
    if total_supply_kwh <= 0:
        return None

    price = BASE_PRICE + ALPHA * (total_demand_kwh / total_supply_kwh)
    return round(min(max(price, PRICE_MIN), PRICE_MAX), 2)
