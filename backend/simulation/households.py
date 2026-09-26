"""Who lives in the simulated neighbourhood: the fixed demo preset, or N households
generated from the config."""

import math
import random
from typing import List

from .models import Household

# id, name, has_solar, solar capacity (kWp), synthetic baseline load (kW), zone id, size class
# Zones are a simple grouping (no real geo) used for "same block" vs "nearby"
# proximity in the marketplace -- every zone has at least one solar seller.
# baseline_kw drives the synthetic curves; size_class picks the real load profile.
DEMO_HOUSEHOLDS = [
    ("H01", "Aditi Sharma", True, 4.5, 0.5, "Z1", "small"),
    ("H02", "Rohan Mehta", False, 0.0, 0.9, "Z1", "medium"),
    ("H03", "Fatima Khan", True, 3.8, 0.6, "Z1", "small"),
    ("H04", "Vikram Nair", False, 0.0, 1.1, "Z1", "large"),
    ("H05", "Sara Iyer", False, 0.0, 0.7, "Z2", "medium"),
    ("H06", "Aditya Rao", True, 5.2, 0.8, "Z2", "medium"),
    ("H07", "Priya Desai", False, 0.0, 1.3, "Z2", "large"),
    ("H08", "Karan Malhotra", False, 0.0, 0.6, "Z3", "small"),
    ("H09", "Neha Kapoor", True, 4.0, 0.5, "Z3", "small"),
    ("H10", "Arjun Singh", False, 0.0, 1.0, "Z3", "large"),
]

FIRST_NAMES = [
    "Aarav", "Ananya", "Deepak", "Divya", "Farhan", "Gauri", "Harsh", "Isha", "Jatin", "Kavya",
    "Manish", "Meera", "Nikhil", "Pooja", "Rahul", "Riya", "Sameer", "Sneha", "Tanvi", "Varun",
]
SURNAMES = [
    "Agarwal", "Bansal", "Chauhan", "Dubey", "Gupta", "Joshi", "Mishra", "Pandey", "Saxena", "Srivastava",
    "Tiwari", "Verma", "Yadav", "Siddiqui", "Rastogi",
]
SIZE_CLASSES = ("small", "medium", "large")
SYNTHETIC_BASELINE_KW = {"small": 0.55, "medium": 0.8, "large": 1.15}
ROOFTOP_KWP_RANGE = (2.0, 5.0)  # typical Indian residential rooftop systems
HOMES_PER_ZONE = 3.5


def demo_households() -> List[Household]:
    return [
        Household(id=hid, name=name, has_solar=solar, capacity_kw=cap, baseline_kw=base, zone_id=zone, size_class=size)
        for hid, name, solar, cap, base, zone, size in DEMO_HOUSEHOLDS
    ]


def generate_households(n: int, solar_ratio: float, rng: random.Random) -> List[Household]:
    """n households, round(n * solar_ratio) of them with solar (at least 1). Zones are
    filled round-robin, solar homes first, so every zone has at least one seller."""
    n_solar = min(n, max(1, round(n * solar_ratio)))
    n_zones = max(1, min(n_solar, math.ceil(n / HOMES_PER_ZONE)))

    names = rng.sample([f"{f} {s}" for f in FIRST_NAMES for s in SURNAMES], n)
    households = []
    for i in range(n):
        has_solar = i < n_solar
        size = rng.choice(SIZE_CLASSES)
        households.append(
            Household(
                id=f"H{i + 1:02d}",
                name=names[i],
                has_solar=has_solar,
                capacity_kw=round(rng.uniform(*ROOFTOP_KWP_RANGE), 1) if has_solar else 0.0,
                baseline_kw=SYNTHETIC_BASELINE_KW[size],
                zone_id=f"Z{i % n_zones + 1}",
                size_class=size,
            )
        )
    # Interleave so solar homes aren't all H01..Hk -- purely cosmetic, zones already assigned.
    rng.shuffle(households)
    for i, h in enumerate(households):
        h.id = f"H{i + 1:02d}"
    return sorted(households, key=lambda h: h.id)
