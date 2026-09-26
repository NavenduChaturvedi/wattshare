"""Home battery policy: a simple, explainable price-threshold rule with hysteresis.

- Sun's up and local energy is cheap (last clearing price below the threshold)
  -> store the home's solar surplus instead of selling it.
- Local energy is expensive, or there was no local supply at all last hour
  (the scarcest case) -> start releasing: cover the home's own load first, and
  whatever exceeds that becomes surplus to sell.
- Once releasing, keep going until the battery is empty or the sun is back.
  Without that hysteresis the battery chases its own tail: its evening sales
  pull the next clearing price under the threshold, it stops, the price jumps
  back up, it restarts -- idling in alternate hours through the evening peak.

The signal is the price the *previous* hour cleared at -- the only price anyone
knows when an hour opens.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

ROUND_TRIP_EFFICIENCY = 0.9  # applied on charging: 1 kWh in stores 0.9 kWh


@dataclass(frozen=True)
class BatterySpec:
    capacity_kwh: float
    max_rate_kw: float  # max kWh in or out over one hour
    threshold_price: float  # Rs/kWh


def decide_flow(
    generation_kwh: float,
    consumption_kwh: float,
    stored_kwh: float,
    spec: BatterySpec,
    price_signal: Optional[float],
    releasing: bool,
) -> Tuple[float, bool]:
    """(kWh the battery takes this hour, whether it's now in releasing mode).
    Flow > 0 is charging from the home's own surplus, < 0 is discharging."""
    surplus = generation_kwh - consumption_kwh
    cheap = price_signal is not None and price_signal < spec.threshold_price

    if surplus > 0 and cheap:
        room = (spec.capacity_kwh - stored_kwh) / ROUND_TRIP_EFFICIENCY
        return round(max(min(surplus, spec.max_rate_kw, room), 0.0), 3), False

    if not cheap:
        releasing = True
    if releasing and stored_kwh > 0:
        return -round(min(spec.max_rate_kw, stored_kwh), 3), True
    return 0.0, False  # empty (or holding for a pricier hour)


def apply_flow(stored_kwh: float, flow_kwh: float, spec: BatterySpec) -> float:
    """New state of charge after this hour's flow."""
    if flow_kwh > 0:
        stored_kwh += flow_kwh * ROUND_TRIP_EFFICIENCY
    else:
        stored_kwh += flow_kwh
    return round(min(max(stored_kwh, 0.0), spec.capacity_kwh), 3)
