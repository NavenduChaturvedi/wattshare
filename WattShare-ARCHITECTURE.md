# WattShare — Architecture

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic
- **Frontend:** Next.js (App Router) + Tailwind CSS — same stack as NV's portfolio site
- **Data storage:** SQLite for local dev; can move to Postgres if deployment needs grow
- **Testing:** pytest for backend logic (matching engine and pricing formula are pure functions — high-value, low-effort to test)
- **CI:** GitHub Actions — run tests on every push
- **Deployment:** Backend on Render, frontend on Vercel

## Real Data Sources (replaces earlier synthetic/randomized data)

- **Solar generation:** NASA POWER API or Open-Meteo — real solar irradiance data for a real location (e.g. Lucknow/UP), converted to expected generation via a simple panel-capacity model
- **Household consumption:** public Indian residential load profile datasets (e.g. data.gov.in or academic energy datasets) instead of randomized curves
- Config-driven: location, number of households, solar-adoption ratio should be parameters, not hardcoded — enables demoing different neighborhood scenarios

## System Components

```
[ Real Solar Irradiance Data ] --> [ Generation Model ] --\
                                                            \
[ Real Consumption Profiles ]  -------------------------->  [ Household State ]
                                                            /
                                                           /
                                              [ Simulation Engine ]
                                                      |
                                                      v
                                            [ Matching Engine ]
                                                      |
                                                      v
                                          [ Pricing Calculator ]
                                                      |
                                                      v
                                            [ Trade Ledger (DB) ]
                                                      |
                                                      v
                                        [ FastAPI REST endpoints ]
                                                      |
                                                      v
                                    [ Next.js Seller/Buyer Dashboards ]
```

## Data Models

**Household**
- `id`, `name`, `has_solar` (bool), `zone_id` (for proximity grouping)
- `current_generation_kwh`, `current_consumption_kwh`
- `battery_stored_kwh` (0 for v1)

**Trade**
- `id`, `seller_id`, `buyer_id`, `amount_kwh`, `price_per_kwh`, `timestamp`

**MarketState** (snapshot per matching cycle)
- `timestamp`, `total_supply_kwh`, `total_demand_kwh`, `clearing_price`, `transformer_load_pct` (stretch)

**Listing**
- `id`, `seller_household_id`, `units_available_kwh`, `asking_price_per_kwh` (nullable = auto), `pricing_mode` (auto/manual), `created_at_tick`

**SellerStats** (derived)
- `seller_household_id`, `reliability_score` (0–1), `total_kwh_sold_lifetime`, `earnings_today/week/lifetime`

## Simulation Parameters

- **Tick = 1 simulated hour**, 24 ticks per day — chosen for clean, eyeballable daily cycles over unnecessary 15-min granularity
- **Solar households: minority (e.g. 4 of 10)** — deliberately not 50/50, so genuine scarcity drives the pricing model instead of supply roughly matching demand all day
- Full day runs in one execution by default (no real-time sleep delays); optional `--step` debug flag for manual tick-by-tick inspection
- `--seed` flag for reproducible runs during development; default random for demo realism

## Matching Algorithm (v1)

1. Filter households into sellers (surplus > 0) and buyers (deficit > 0)
2. Sort sellers by ask price ascending, buyers by need descending
3. Match top-down, min(seller_surplus, buyer_deficit) kWh per pair
4. Continue until one list exhausted
5. All matches in a cycle settle at the cycle's clearing price (not per-trade negotiated)

## Pricing Formula (v1)

```
clearing_price = base_price + alpha * (total_demand_kwh / total_supply_kwh - 1)
               + beta * (transformer_import / transformer_capacity)^2
clamped between price_min and price_max
```
*Revised 2026-09-26:* the formula is centred on balance (demand = supply → base_price), so a surplus prices below base. The original `base + α·(D/S)` could never go below ₹6, which left the ₹4 floor unreachable. The β transformer term (stretch) is implemented and applies on import only.
Placeholder constants: base_price ≈ ₹6/kWh, alpha ≈ 2, price_min ≈ ₹4, price_max ≈ ₹12 — plausible and explainable, not claimed to be economically rigorous.

**Reliability score:** `trades_fulfilled_as_listed / total_trades_attempted`, rolling window (last 20 trades or 7 sim-days). New sellers default to a neutral 0.85 until 5+ trades of history exist.

## API Endpoints

- `GET /households` — current state of all households
- `POST /simulate/tick` — advance simulation one hour
- `POST /match` — run one matching cycle
- `GET /trades` — trade history
- `GET /market-state` — latest price, supply/demand snapshot
- `POST /listings` — seller creates/updates a listing
- `GET /listings` — active listings (buyer dashboard)
- `GET /sellers/{id}/stats` — reliability + earnings (seller dashboard)
- `POST /match/smart` — buyer-initiated auto-match for a desired kWh amount
- `GET /market/summary` — average price, best price, price trend

## UI — Seller Dashboard

- Current surplus card with auto/manual pricing toggle
- Reliability badge (not a star rating — electricity has no subjective quality)
- Earnings: today / week / lifetime
- Impact stat: lifetime kWh sold + rough CO₂-offset estimate (labeled as an estimate)

## UI — Buyer Dashboard

- Listing table: seller, units, price, zone proximity ("same block"/"nearby"), reliability score
- Best price / most reliable highlights + live market average
- **Smart Match button:** one-click auto-optimal match via the real matching algorithm — both a good demo moment and honest proof the engine works
- Grid health indicator (green/yellow/red, tied to transformer load once that term is added)
- Price trend sparkline for the day

## Why Not Blockchain (design decision, stated explicitly)

Real DERC/UPERC pilots settle through blockchain-*enabled* ledgers integrated with DISCOM billing systems, not public gas-fee chains. WattShare's v1 trade ledger is a normal database; a tamper-evident hash-chain (blockchain-*inspired*, not a deployed smart contract) is a stretch feature, not core scope. This keeps the build honest about what it actually is: a matching/pricing engine, not a blockchain product wearing a solar costume.
