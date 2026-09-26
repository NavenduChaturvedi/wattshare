import random
from typing import Dict, List, Optional

from backend.config import SimConfig, load_config
from backend.data.load import hourly_profile, season_for
from backend.data.solar import generation_kwh, hourly_irradiance

from .battery import BatterySpec, apply_flow, decide_flow
from .curves import consumption_kwh, solar_generation_kwh
from .households import demo_households, generate_households
from .models import Household

# Real-data mode keeps neighbours from being identical copies of their size class:
# a fixed per-home appetite (bigger fridge, more fans...), plus hour-to-hour jitter.
HOUSEHOLD_LOAD_SCALE = (0.8, 1.2)
HOURLY_LOAD_NOISE = (0.9, 1.1)
# Fixed per-home solar derate (panel orientation, shading, soiling) on top of the shared weather.
PANEL_DERATE = (0.93, 1.0)


class SimulationEngine:
    """Advances a neighborhood of households through hourly ticks (0-23, wrapping daily).

    In "real" mode every simulated day replays config.sim_date: that day's measured
    irradiance at config.location, and the season's measured household load profiles.
    """

    def __init__(self, seed: Optional[int] = None, config: Optional[SimConfig] = None):
        self.config = config or load_config()
        self.rng = random.Random(seed if seed is not None else self.config.seed)
        self.current_hour = 0
        # Monotonic count of ticks since startup -- unlike current_hour (which wraps
        # at 24 for display/curve purposes), this never resets. It's what lets the
        # marketplace layer reason about elapsed time: "is this listing stale",
        # "what trades happened today/this week".
        self.total_ticks = 0

        if self.config.households == "demo":
            self.households: List[Household] = demo_households()
        else:
            self.households = generate_households(self.config.n_households, self.config.solar_ratio, self.rng)

        self.transformer_capacity_kw = round(self.config.transformer_kw_per_home * len(self.households), 2)

        self.battery_spec = BatterySpec(
            capacity_kwh=self.config.battery_kwh,
            max_rate_kw=self.config.battery_kw,
            threshold_price=self.config.battery_threshold_price,
        )
        solar_by_size = sorted((h for h in self.households if h.has_solar), key=lambda h: (-h.capacity_kw, h.id))
        for h in solar_by_size[: round(len(solar_by_size) * self.config.battery_share)]:
            h.battery_capacity_kwh = self.battery_spec.capacity_kwh
            h.battery_max_kw = self.battery_spec.max_rate_kw
        # Last clearing price the batteries have seen (None = no local supply). Fed by
        # observe_price() after each dispatch; used when the next hour opens.
        self.price_signal: Optional[float] = None
        self._releasing: Dict[str, bool] = {}  # battery hysteresis state, see battery.py

        self.real_data = self.config.data_source == "real"
        if self.real_data:
            loc = self.config.location
            self.irradiance = hourly_irradiance(loc.latitude, loc.longitude, self.config.sim_date, loc.timezone)
            self.season = season_for(self.config.sim_date)
            self._load_scale: Dict[str, float] = {h.id: self.rng.uniform(*HOUSEHOLD_LOAD_SCALE) for h in self.households}
            self._derate: Dict[str, float] = {h.id: self.rng.uniform(*PANEL_DERATE) for h in self.households}
            self._profiles = {h.id: hourly_profile(self.season, h.size_class) for h in self.households}

        self._update_all()

    def _update_all(self) -> None:
        hour = self.current_hour
        for h in self.households:
            if self.real_data:
                h.current_generation_kwh = round(
                    generation_kwh(self.irradiance[hour], h.capacity_kw) * self._derate[h.id], 3
                )
                h.current_consumption_kwh = round(
                    self._profiles[h.id][hour] * self._load_scale[h.id] * self.rng.uniform(*HOURLY_LOAD_NOISE), 3
                )
            else:
                h.current_generation_kwh = solar_generation_kwh(hour, h.capacity_kw, self.rng)
                h.current_consumption_kwh = consumption_kwh(hour, h.baseline_kw, self.rng)
            if h.battery_capacity_kwh > 0:
                h.battery_flow_kwh, self._releasing[h.id] = decide_flow(
                    h.current_generation_kwh,
                    h.current_consumption_kwh,
                    h.battery_stored_kwh,
                    self.battery_spec,
                    self.price_signal,
                    self._releasing.get(h.id, False),
                )
                h.battery_stored_kwh = apply_flow(h.battery_stored_kwh, h.battery_flow_kwh, self.battery_spec)
            h.traded_kwh = 0.0  # a new hour opens a fresh position

    def observe_price(self, clearing_price: Optional[float]) -> None:
        """The clearing price of the hour that just closed -- the batteries' signal for the next one."""
        self.price_signal = clearing_price

    def tick(self) -> None:
        self.current_hour = (self.current_hour + 1) % 24
        self.total_ticks += 1
        self._update_all()
