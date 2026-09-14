import random
from typing import List, Optional

from .curves import consumption_kwh, solar_generation_kwh
from .models import Household

# id, name, has_solar, solar capacity (kW), baseline consumption (kW), zone id
# Zones are a simple grouping (no real geo) used for "same block" vs "nearby"
# proximity in the marketplace -- every zone has at least one solar seller.
HOUSEHOLD_SEED_DATA = [
    ("H01", "Aditi Sharma", True, 4.5, 0.5, "Z1"),
    ("H02", "Rohan Mehta", False, 0.0, 0.9, "Z1"),
    ("H03", "Fatima Khan", True, 3.8, 0.6, "Z1"),
    ("H04", "Vikram Nair", False, 0.0, 1.1, "Z1"),
    ("H05", "Sara Iyer", False, 0.0, 0.7, "Z2"),
    ("H06", "Aditya Rao", True, 5.2, 0.8, "Z2"),
    ("H07", "Priya Desai", False, 0.0, 1.3, "Z2"),
    ("H08", "Karan Malhotra", False, 0.0, 0.6, "Z3"),
    ("H09", "Neha Kapoor", True, 4.0, 0.5, "Z3"),
    ("H10", "Arjun Singh", False, 0.0, 1.0, "Z3"),
]


class SimulationEngine:
    """Advances a neighborhood of households through hourly ticks (0-23, wrapping daily)."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.current_hour = 0
        # Monotonic count of ticks since startup -- unlike current_hour (which wraps
        # at 24 for display/curve purposes), this never resets. It's what lets the
        # marketplace layer reason about elapsed time: "is this listing stale",
        # "what trades happened today/this week".
        self.total_ticks = 0
        self.households: List[Household] = [
            Household(id=hid, name=name, has_solar=has_solar, capacity_kw=cap, baseline_kw=base, zone_id=zone)
            for hid, name, has_solar, cap, base, zone in HOUSEHOLD_SEED_DATA
        ]
        self._update_all()

    def _update_all(self) -> None:
        for h in self.households:
            h.current_generation_kwh = solar_generation_kwh(self.current_hour, h.capacity_kw, self.rng)
            h.current_consumption_kwh = consumption_kwh(self.current_hour, h.baseline_kw, self.rng)

    def tick(self) -> None:
        self.current_hour = (self.current_hour + 1) % 24
        self.total_ticks += 1
        self._update_all()
