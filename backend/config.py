"""Simulation config: config/default.json, optionally replaced by the file named in
WATTSHARE_CONFIG, then individual env overrides on top (WATTSHARE_SEED,
WATTSHARE_DATA_SOURCE, WATTSHARE_SIM_DATE, WATTSHARE_CLOCK, WATTSHARE_CLOCK_SPEED)."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.json"


class Location(BaseModel):
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "Asia/Kolkata"


class SimConfig(BaseModel):
    location: Location
    sim_date: date  # the real day whose weather/season drives the simulation; each sim day replays it
    # "real": Open-Meteo irradiance + CEEW load profiles. "synthetic": the original
    # made-up curves, kept for offline experiments and as a clearly labelled fallback.
    data_source: Literal["real", "synthetic"] = "real"
    # "demo": the 10 named households the dashboards were designed around.
    # "generated": n_households built from n_households / solar_ratio / seed.
    households: Literal["demo", "generated"] = "demo"
    n_households: int = Field(default=10, ge=2, le=200)
    solar_ratio: float = Field(default=0.4, gt=0, lt=1)
    seed: Optional[int] = None
    # The neighbourhood's share of its distribution transformer, per home. An
    # assumption for the simulation (Indian LV transformers serve dozens to hundreds
    # of homes; this sizes a slice of one), not a measured value.
    transformer_kw_per_home: float = Field(default=1.2, gt=0)
    # Home batteries: the given share of solar homes get one, biggest arrays first.
    battery_share: float = Field(default=0.5, ge=0, le=1)
    battery_kwh: float = Field(default=5.0, gt=0)  # usable capacity
    # Max charge/discharge per hour. 1.5 kW spreads a full battery over ~3 evening hours;
    # faster rates dump it in one hour, overshoot local demand and export the rest.
    battery_kw: float = Field(default=1.5, gt=0)
    # Rs/kWh: store below, release at/above. Just above the balanced-market price (6), so
    # batteries fill while the market is in surplus and release once it turns scarce.
    battery_threshold_price: float = Field(default=6.5, gt=0)
    # "live": the simulated hour follows real time in location.timezone (the API
    # catches the simulation up on every request). "manual": hours only advance
    # via POST /match + /simulate/tick -- the original step-through mode.
    clock: Literal["live", "manual"] = "live"
    # Simulated hours per real hour in live mode. 1 = real time; 60 = one simulated
    # hour per real minute (for demos).
    clock_speed: float = Field(default=1.0, gt=0, le=3600)


def load_config(path: Optional[Union[str, Path]] = None) -> SimConfig:
    path = Path(path or os.environ.get("WATTSHARE_CONFIG") or DEFAULT_CONFIG_PATH)
    data = json.loads(path.read_text())

    if os.environ.get("WATTSHARE_SEED"):
        data["seed"] = int(os.environ["WATTSHARE_SEED"])
    if os.environ.get("WATTSHARE_DATA_SOURCE"):
        data["data_source"] = os.environ["WATTSHARE_DATA_SOURCE"]
    if os.environ.get("WATTSHARE_SIM_DATE"):
        data["sim_date"] = os.environ["WATTSHARE_SIM_DATE"]
    if os.environ.get("WATTSHARE_CLOCK"):
        data["clock"] = os.environ["WATTSHARE_CLOCK"]
    if os.environ.get("WATTSHARE_CLOCK_SPEED"):
        data["clock_speed"] = float(os.environ["WATTSHARE_CLOCK_SPEED"])

    return SimConfig.model_validate(data)
