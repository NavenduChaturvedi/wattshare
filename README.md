# WattShare

A peer-to-peer solar energy trading simulator for a residential neighborhood.
Households with rooftop solar sell surplus energy directly to nearby neighbors
instead of feeding it back to the grid at low tariffs. A dispatcher engine
matches buyers and sellers and prices trades dynamically based on local
supply and demand.

This is a portfolio project demonstrating system design, algorithmic thinking
(matching + dynamic pricing), and full-stack delivery. All data is simulated
-- there's no real hardware, blockchain, or payment processing involved (see
[Non-goals](#non-goals)).

## How it works

**1. Household simulation.** 10 households, 4 with rooftop solar and 6 pure
consumers. Each simulated hour, solar generation follows a bell curve peaking
near noon (with occasional random "cloud" dips), and consumption follows
morning and evening peaks -- both with a bit of random noise layered on top so
the neighborhood feels organic rather than mechanical.

**2. Matching.** Every cycle:
1. Households are split into sellers (generation > consumption this hour) and
   buyers (consumption > generation).
2. Sellers are sorted by ask price ascending (everyone shares the same base
   ask in v1); buyers are sorted by need (deficit) descending.
3. The two lists are walked top-down and paired index-for-index -- seller `i`
   trades with buyer `i` for `min(seller's surplus, buyer's deficit)` kWh --
   stopping as soon as either list runs out.

This is deliberately simple (no auction, no partial re-matching of leftover
surplus/deficit) -- it's meant to be an explainable v1, not a clearing-price
auction engine.

**3. Pricing.** Once per cycle, from the *aggregate* supply and demand (not
per trade):

```
clearing_price = base_price + alpha * (total_demand_kwh / total_supply_kwh)
clamped to [price_min, price_max]
```

With `base_price = 6`, `alpha = 2`, `price_min = 4`, `price_max = 12` (Rs/kWh)
-- placeholder constants chosen to be plausible and easy to explain, not
economically rigorous. Every trade executed in a cycle settles at that
cycle's single clearing price.

## Architecture

```
[ Simulation Engine ] --generates--> [ Household State ]
                                              |
                                              v
                                    [ Matching Engine ]
                                              |
                                              v
                                    [ Pricing Calculator ]
                                              |
                                              v
                                    [ Trade Ledger (SQLite) ]
                                              |
                                              v
                                    [ FastAPI REST endpoints ]
                                              |
                                              v
                                    [ Next.js Dashboard ]
```

| Layer | Tech |
|---|---|
| Simulation + matching + pricing | Python 3 (stdlib only) |
| API | FastAPI + Pydantic |
| Persistence | SQLite (`sqlite3`, no ORM) |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS |
| Charts | Recharts |

## Project layout

This was built in five phases, and each phase's entry point still works
standalone:

```
backend/
  simulation/          Phase 1 -- household generation/consumption curves
    curves.py
    engine.py
    models.py
  run_simulation.py     Phase 1 CLI -- prints a full simulated day to console

  market/               Phase 2 -- matching engine + dynamic pricing
    pricing.py
    engine.py
    models.py
  run_market.py          Phase 2 CLI -- simulation + matching, console output

  api/                  Phase 3 -- FastAPI + SQLite
    app.py               routes
    db.py                SQLite schema + queries (raw sqlite3, no ORM)
    schemas.py           Pydantic response models
  display.py             shared console table printer (Phases 1 & 2)
  requirements.txt

frontend/               Phase 4 -- Next.js dashboard
  src/
    app/                 page + layout + global styles
    components/          Controls, HouseholdTable, PriceChart, GenerationChart, TradeFeed
    lib/                 typed API client
```

## Running it locally

### Backend

```bash
python -m venv .venv
./.venv/Scripts/activate       # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
```

Phase 1 -- household simulation only (console):
```bash
python -m backend.run_simulation --seed 42   # --seed is optional; omit for fresh randomness each run
```

Phase 2 -- adds matching + pricing (console):
```bash
python -m backend.run_market --seed 42
```

Phase 3/4 -- the API server the dashboard talks to:
```bash
uvicorn backend.api.app:app --port 8000
```
Interactive API docs: http://127.0.0.1:8000/docs

An optional `WATTSHARE_SEED` env var seeds the API's simulation the same way
`--seed` does for the CLIs, for reproducible testing.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000 with the backend running. Click **Advance Hour**
to step the simulation one hour and run a matching cycle, or **Auto-play** to
let it run continuously.

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/households` | GET | Current state of all households |
| `/simulate/tick` | POST | Advance the simulation by one hour |
| `/match` | POST | Run one matching cycle at the current hour |
| `/trades` | GET | Full trade history |
| `/market-state` | GET | Latest clearing price / supply / demand snapshot |

The database resets on every server start, so the in-memory simulation clock
and the persisted trade history always stay consistent with each other.

## Deployment

**Backend -> Render.** `render.yaml` at the repo root is a ready-to-use
Blueprint (build: `pip install -r backend/requirements.txt`, start:
`uvicorn backend.api.app:app --host 0.0.0.0 --port $PORT`). Either connect
the repo as a Blueprint, or create a Python web service manually with those
same two commands.

**Frontend -> Vercel.** Import the repo, set the project's **Root Directory**
to `frontend`, and set `NEXT_PUBLIC_API_URL` to your deployed Render URL in
the project's environment variables.

The two services are independent -- CORS on the backend is left permissive
(`allow_origins=["*"]`) since there's no auth or cookies involved, so the
frontend can point at any backend URL without extra configuration.

## Non-goals

Deliberately out of scope for this project:
- No real hardware/IoT -- all household data is simulated.
- No real blockchain/smart contracts -- the trade ledger is a plain SQLite
  table.
- No user accounts -- single shared simulation view.
- No real payments.

## Possible future work

Not implemented, but the data model leaves room for them:
- Transformer load term in the pricing formula (`+ beta * (load/max_load)^2`).
- Battery storage (households store surplus instead of always selling).
- Hash-chained trade ledger for a tamper-evident history.
- Swap SQLite for Postgres if this ever needs real concurrent persistence.
