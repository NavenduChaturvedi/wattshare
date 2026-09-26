"""Builds backend/data/load_profiles.csv from the CEEW Mathura smart-meter data.

Source: CEEW, "High frequency smart meter data from two districts in India
(Mathura and Bareilly)", Harvard Dataverse, doi:10.7910/DVN/GOCHJH (CC0 1.0).
See backend/data/SOURCES.md for the full write-up.

Method, per season:
  1. Drop outage readings (voltage == 0). Those are supply cuts, not demand, and
     would drag every profile down.
  2. For each meter and hour of day, mean kWh per 3-minute reading x 20
     = typical kWh consumed in that hour while powered.
  3. Keep meters with enough powered readings in every hour and a plausible
     daily total, then split them into small / medium / large by daily-kWh terciles.
  4. Each class profile is the mean of its members' 24-hour profiles.

Only needs to run when the method changes -- the output CSV is committed.

    python -m backend.data.build_load_profiles [path/to/Mathura_2019.csv]
"""

import csv
import statistics
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

DATAVERSE_FILE_URL = "https://dataverse.harvard.edu/api/access/datafile/5425311?format=original"  # Mathura 2019
RAW_PATH = Path(__file__).resolve().parent / "raw" / "ceew_mathura_2019.csv"
OUT_PATH = Path(__file__).resolve().parent / "load_profiles.csv"

READINGS_PER_HOUR = 20  # 3-minute interval
SEASON_MONTHS = {
    "summer": {"2019-05", "2019-06"},  # pre-monsoon heat: coolers/ACs
    "monsoon": {"2019-07", "2019-08", "2019-09"},
    "winter": {"2019-12"},
}
MIN_READINGS_PER_HOUR_SLOT = 200  # ~10 powered days in each hour of the day
MIN_DAILY_KWH = 1.0  # below this the home is effectively vacant
SIZE_CLASSES = ("small", "medium", "large")


def ensure_raw(path: Path) -> Path:
    if path.exists():
        return path
    print(f"Downloading CEEW Mathura 2019 (~175 MB) to {path} ...")
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATAVERSE_FILE_URL, path)
    return path


def season_of(timestamp: str):
    month = timestamp[:7]
    return next((s for s, months in SEASON_MONTHS.items() if month in months), None)


def build(raw: Path):
    # (season, meter, hour) -> [sum_kwh, powered_readings]
    acc = defaultdict(lambda: [0.0, 0])
    with raw.open(newline="") as f:
        for row in csv.DictReader(f):
            season = season_of(row["x_Timestamp"])
            if season is None or float(row["z_Avg Voltage (Volt)"] or 0) == 0:
                continue
            slot = acc[(season, row["meter"], int(row["x_Timestamp"][11:13]))]
            slot[0] += float(row["t_kWh"] or 0)
            slot[1] += 1

    rows, summary = [], {}
    for season in SEASON_MONTHS:
        meters = sorted({m for (s, m, _) in acc if s == season})
        profiles = {}
        for meter in meters:
            slots = [acc.get((season, meter, h)) for h in range(24)]
            if any(s is None or s[1] < MIN_READINGS_PER_HOUR_SLOT for s in slots):
                continue
            profile = [s[0] / s[1] * READINGS_PER_HOUR for s in slots]
            if sum(profile) >= MIN_DAILY_KWH:
                profiles[meter] = profile

        ranked = sorted(profiles, key=lambda m: sum(profiles[m]))
        n = len(ranked)
        groups = {cls: ranked[i * n // 3 : (i + 1) * n // 3] for i, cls in enumerate(SIZE_CLASSES)}
        summary[season] = {"meters_used": n, "meters_seen": len(meters)}
        for cls, members in groups.items():
            mean_profile = [statistics.fmean(profiles[m][h] for m in members) for h in range(24)]
            summary[season][cls] = (len(members), round(sum(mean_profile), 2))
            rows += [(season, cls, h, round(mean_profile[h], 4)) for h in range(24)]
    return rows, summary


def main() -> None:
    raw = ensure_raw(Path(sys.argv[1]) if len(sys.argv) > 1 else RAW_PATH)
    rows, summary = build(raw)
    with OUT_PATH.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["season", "size_class", "hour", "kwh"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    for season, info in summary.items():
        classes = ", ".join(f"{c}: {info[c][0]} homes, {info[c][1]} kWh/day" for c in SIZE_CLASSES)
        print(f"  {season}: {info['meters_used']}/{info['meters_seen']} meters kept -- {classes}")


if __name__ == "__main__":
    main()
