# Data sources

WattShare's simulation runs on real, public data. The platform itself is still a simulation: households, trades and prices are modelled, but the physical inputs are measured.

## Solar generation: Open-Meteo Historical Weather API

- **What:** hourly `shortwave_radiation`, the global horizontal irradiance in W/m², for the configured location and date.
- **Source:** [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). It is free, needs no key, and is licensed [CC BY 4.0](https://open-meteo.com/en/licence) (reanalysis data from ERA5 and others).
- **Model:** `kWh per hour = capacity_kWp × (GHI / 1000 W/m²) × 0.78`. The 0.78 is the performance ratio, covering inverter, wiring, temperature and soiling losses. Each home also gets a fixed 0.93 to 1.00 derate for orientation and shading. This is a deliberately simple model, not a PVsyst-grade one.
- **Timing:** Open-Meteo labels each value with the *end* of its hour, so the 10:00 to 11:00 interval uses the value labelled 11:00.
- **Cached days:** these are committed under `cache/solar/`, so tests and deploys never need the network.

  | Date | Character | Daily irradiation |
  |---|---|---|
  | 2019-05-29 | Clearest pre-monsoon day of May 2019 (the default) | 24.95 MJ/m² |
  | 2019-07-11 | Heavily overcast monsoon day | 5.36 MJ/m² |
  | 2019-12-22 | Typical winter day (December median) | 12.21 MJ/m² |

  Any other day is fetched once and cached automatically. All three are for Lucknow (26.85, 80.95).

## Household consumption: CEEW smart-meter data (Mathura, Uttar Pradesh)

- **Source:** Council on Energy, Environment and Water (CEEW). *High frequency smart meter data from two districts in India (Mathura and Bareilly)*. Harvard Dataverse, [doi:10.7910/DVN/GOCHJH](https://doi.org/10.7910/DVN/GOCHJH).
- **Authors:** Shalu Agrawal, Sunil Mani, Abhishek Jain and Karthik Ganesan. The companion report is [*What Smart Meters Can Tell Us*](https://www.ceew.in/publications/what-smart-meters-can-tell-us).
- **Licence:** CC0 1.0 (public domain).
- **What's used:** the file *Mathura 2019* holds 3-minute readings (kWh, voltage, current) from 38 urban households, May to December 2019. Mathura is in Uttar Pradesh, the same state as the default Lucknow location. The 2020 data was skipped because of lockdown distortion.
- **Derived file:** `load_profiles.csv`, with columns season, size class, hour and kWh. It is built by `build_load_profiles.py`:
  1. Readings with voltage 0 are dropped. They are supply outages (6–11% of readings, depending on the month), not low demand.
  2. For each meter and hour of the day, the mean kWh per powered reading × 20 gives the typical kWh consumed in that hour.
  3. Meters need at least 200 powered readings in every hour-of-day slot (about 10 days) and at least 1 kWh/day. The rest are split into small, medium and large by tercile of daily use.
  4. Each class profile is the mean of its members' profiles.

  | Season (months used) | Meters kept | Small | Medium | Large |
  |---|---|---|---|---|
  | Summer (May–Jun) | 32 / 38 | 4.6 kWh/day | 11.9 kWh/day | 25.7 kWh/day |
  | Monsoon (Jul–Sep) | 38 / 38 | 4.3 | 9.7 | 23.6 |
  | Winter (Dec) | 24 / 37 | 2.2 | 3.7 | 7.4 |

- **In the simulation:** each household uses its size class's profile for the season of `sim_date` (Mar–Jun summer, Jul–Sep monsoon, Oct–Feb winter). A fixed per-home scale of 0.8–1.2× and ±10% hourly noise keep neighbours from being identical.
- **Worth knowing:** in summer and monsoon, real load peaks *overnight* when coolers and ACs run, not in the morning and evening. That is why there is no local solar supply to trade against when demand is highest.

## Rebuilding

```bash
python -m backend.data.build_load_profiles   # downloads the 175 MB source into backend/data/raw/ (gitignored)
```

The synthetic curves from the original prototype still exist (`data_source: "synthetic"` in the config) and are labelled as synthetic wherever they're shown.
