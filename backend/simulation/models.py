from dataclasses import dataclass


@dataclass
class Household:
    id: str
    name: str
    has_solar: bool
    capacity_kw: float
    baseline_kw: float
    zone_id: str = "Z1"
    current_generation_kwh: float = 0.0
    current_consumption_kwh: float = 0.0
    battery_stored_kwh: float = 0.0

    @property
    def net_kwh(self) -> float:
        return round(self.current_generation_kwh - self.current_consumption_kwh, 3)
