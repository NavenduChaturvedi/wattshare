"""Household consumption from real smart-meter load profiles (see SOURCES.md).

load_profiles.csv holds a typical 24-hour profile per season and household size
class, built by build_load_profiles.py from CEEW's Mathura (Uttar Pradesh) data.
"""

import csv
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Literal, Tuple

PROFILES_PATH = Path(__file__).resolve().parent / "load_profiles.csv"

Season = Literal["summer", "monsoon", "winter"]
SizeClass = Literal["small", "medium", "large"]
SIZE_CLASSES: Tuple[SizeClass, ...] = ("small", "medium", "large")


def season_for(day: date) -> Season:
    """North-Indian seasons, matched to the months each profile was built from:
    Mar-Jun hot pre-monsoon, Jul-Sep monsoon, Oct-Feb cooler months."""
    if 3 <= day.month <= 6:
        return "summer"
    if 7 <= day.month <= 9:
        return "monsoon"
    return "winter"


@lru_cache(maxsize=1)
def _profiles() -> Dict[Tuple[str, str], List[float]]:
    out: Dict[Tuple[str, str], List[float]] = {}
    with PROFILES_PATH.open(newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault((row["season"], row["size_class"]), [0.0] * 24)[int(row["hour"])] = float(row["kwh"])
    return out


def hourly_profile(season: Season, size_class: SizeClass) -> List[float]:
    """Typical kWh consumed in each hour 0..23 for this season and household size."""
    return list(_profiles()[(season, size_class)])
