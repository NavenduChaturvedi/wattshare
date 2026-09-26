"""Rooftop solar generation from real hourly irradiance (Open-Meteo Historical Weather API).

Days are cached as JSON under backend/data/cache/solar/, and the fixture days used
by the default config are committed -- so tests and deployments never need the
network. A day that isn't cached is fetched once and then cached.
"""

import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import List

CACHE_DIR = Path(__file__).resolve().parent / "cache" / "solar"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Share of nameplate output a real rooftop system delivers after inverter, wiring,
# temperature and soiling losses. 0.75-0.80 is the usual range; a simple model,
# not a PVsyst-grade one.
PERFORMANCE_RATIO = 0.78
STC_IRRADIANCE_W_M2 = 1000.0  # panels are rated (kWp) at 1000 W/m2


class IrradianceUnavailable(RuntimeError):
    pass


def _cache_path(latitude: float, longitude: float, day: date) -> Path:
    return CACHE_DIR / f"{latitude:.2f}_{longitude:.2f}_{day.isoformat()}.json"


def _fetch(latitude: float, longitude: float, day: date, timezone: str) -> dict:
    query = urllib.parse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "hourly": "shortwave_radiation",
            "timezone": timezone,
        }
    )
    try:
        with urllib.request.urlopen(f"{OPEN_METEO_ARCHIVE_URL}?{query}", timeout=30) as res:
            return json.load(res)
    except OSError as e:
        raise IrradianceUnavailable(
            f"No cached irradiance for {latitude:.2f},{longitude:.2f} on {day} and Open-Meteo is unreachable ({e}). "
            "Pick a cached day (backend/data/cache/solar/) or run once with network access."
        ) from e


def hourly_irradiance(latitude: float, longitude: float, day: date, timezone: str = "Asia/Kolkata") -> List[float]:
    """Mean global horizontal irradiance (W/m2) for each hour-long interval h:00-h+1:00, h = 0..23.

    Open-Meteo labels each value with the END of its hour (the 11:00 value is the
    10:00-11:00 mean), so interval h takes the value labelled h+1. The 23:00-24:00
    interval is night in India and is set to 0.
    """
    path = _cache_path(latitude, longitude, day)
    if path.exists():
        payload = json.loads(path.read_text())
    else:
        payload = _fetch(latitude, longitude, day, timezone)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=1))

    labelled = payload["hourly"]["shortwave_radiation"]
    if len(labelled) != 24:
        raise IrradianceUnavailable(f"Expected 24 hourly values for {day}, got {len(labelled)}")
    values = [float(v or 0.0) for v in labelled]
    return values[1:] + [0.0]


def generation_kwh(irradiance_w_m2: float, capacity_kwp: float, performance_ratio: float = PERFORMANCE_RATIO) -> float:
    """kWh produced over one hour: capacity x (GHI / 1000 W/m2) x performance ratio."""
    if capacity_kwp <= 0 or irradiance_w_m2 <= 0:
        return 0.0
    return round(capacity_kwp * (irradiance_w_m2 / STC_IRRADIANCE_W_M2) * performance_ratio, 3)
