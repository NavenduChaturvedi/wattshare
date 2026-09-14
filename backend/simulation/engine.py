import random
from typing import List, Optional

from .curves import consumption_kwh, solar_generation_kwh
from .models import Household

# id, name, has_solar, solar capacity (kW), baseline consumption (kW)
HOUSEHOLD_SEED_DATA = [
    ("H01", "Aditi Sharma", True, 4.5, 0.5),
    ("H02", "Rohan Mehta", False, 0.0, 0.9),
    ("H03", "Fatima Khan", True, 3.8, 0.6),
    ("H04", "Vikram Nair", False, 0.0, 1.1),
    ("H05", "Sara Iyer", False, 0.0, 0.7),
    ("H06", "Aditya Rao", True, 5.2, 0.8),
    ("H07", "Priya Desai", False, 0.0, 1.3),
    ("H08", "Karan Malhotra", False, 0.0, 0.6),
    ("H09", "Neha Kapoor", True, 4.0, 0.5),
    ("H10", "Arjun Singh", False, 0.0, 1.0),
]


class SimulationEngine:
    """Advances a neighborhood of households through hourly ticks (0-23)."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.current_hour = 0
        self.households: List[Household] = [
            Household(id=hid, name=name, has_solar=has_solar, capacity_kw=cap, baseline_kw=base)
            for hid, name, has_solar, cap, base in HOUSEHOLD_SEED_DATA
        ]
        self._update_all()

    def _update_all(self) -> None:
        for h in self.households:
            h.current_generation_kwh = solar_generation_kwh(self.current_hour, h.capacity_kw, self.rng)
            h.current_consumption_kwh = consumption_kwh(self.current_hour, h.baseline_kw, self.rng)

    def tick(self) -> None:
        self.current_hour = (self.current_hour + 1) % 24
        self._update_all()
