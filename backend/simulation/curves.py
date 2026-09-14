import math
import random

DAYLIGHT_START = 6
DAYLIGHT_END = 18


def solar_generation_kwh(hour: int, capacity_kw: float, rng: random.Random) -> float:
    """Bell-shaped output over daylight hours, peaking at solar noon, with occasional cloud dips."""
    if capacity_kw <= 0 or hour < DAYLIGHT_START or hour >= DAYLIGHT_END:
        return 0.0

    daylight_span = DAYLIGHT_END - DAYLIGHT_START
    x = (hour - DAYLIGHT_START) / daylight_span * math.pi
    base = capacity_kw * math.sin(x)

    if rng.random() < 0.15:
        weather_factor = rng.uniform(0.5, 0.85)
    else:
        weather_factor = rng.uniform(0.92, 1.05)

    return round(max(0.0, base * weather_factor), 3)


def _gaussian_bump(hour: float, peak: float, width: float, amplitude: float) -> float:
    return amplitude * math.exp(-((hour - peak) ** 2) / (2 * width ** 2))


def consumption_kwh(hour: int, baseline_kw: float, rng: random.Random) -> float:
    """Baseline load plus morning and evening peaks, with random noise."""
    morning_peak = _gaussian_bump(hour, peak=7.5, width=1.3, amplitude=baseline_kw * 1.8)
    evening_peak = _gaussian_bump(hour, peak=19.5, width=2.0, amplitude=baseline_kw * 2.2)
    load = baseline_kw + morning_peak + evening_peak
    noise = rng.uniform(0.9, 1.1)
    return round(max(0.05, load * noise), 3)
