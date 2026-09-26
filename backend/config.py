"""Simulation config: config/default.json, optionally replaced by the file named in
WATTSHARE_CONFIG, then individual env overrides on top (WATTSHARE_SEED,
WATTSHARE_DATA_SOURCE, WATTSHARE_SIM_DATE)."""

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


def load_config(path: Optional[Union[str, Path]] = None) -> SimConfig:
    path = Path(path or os.environ.get("WATTSHARE_CONFIG") or DEFAULT_CONFIG_PATH)
    data = json.loads(path.read_text())

    if os.environ.get("WATTSHARE_SEED"):
        data["seed"] = int(os.environ["WATTSHARE_SEED"])
    if os.environ.get("WATTSHARE_DATA_SOURCE"):
        data["data_source"] = os.environ["WATTSHARE_DATA_SOURCE"]
    if os.environ.get("WATTSHARE_SIM_DATE"):
        data["sim_date"] = os.environ["WATTSHARE_SIM_DATE"]

    return SimConfig.model_validate(data)
