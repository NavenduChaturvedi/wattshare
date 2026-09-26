from dataclasses import dataclass


@dataclass
class Household:
    id: str
    name: str
    has_solar: bool
    capacity_kw: float
    baseline_kw: float
    zone_id: str = "Z1"
    size_class: str = "medium"  # picks the real load profile: small / medium / large
    current_generation_kwh: float = 0.0
    current_consumption_kwh: float = 0.0
    battery_stored_kwh: float = 0.0
    # Energy already traded this hour: + for kWh sold, - for kWh bought. Both the
    # dispatcher cycle and the marketplace settle against this, so the same kWh
    # can't be sold (or bought) twice in one hour. Reset on every tick.
    traded_kwh: float = 0.0

    @property
    def net_kwh(self) -> float:
        return round(self.current_generation_kwh - self.current_consumption_kwh, 3)

    @property
    def open_net_kwh(self) -> float:
        """Net position still untraded this hour: > 0 is surplus left to sell, < 0 is deficit left to cover."""
        return round(self.net_kwh - self.traded_kwh, 3)

    def record_sale(self, amount_kwh: float) -> None:
        self.traded_kwh = round(self.traded_kwh + amount_kwh, 3)

    def record_purchase(self, amount_kwh: float) -> None:
        self.traded_kwh = round(self.traded_kwh - amount_kwh, 3)
