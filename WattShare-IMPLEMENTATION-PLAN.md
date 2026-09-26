# WattShare — Implementation Plan

*Drafted 2026-09-25 against commit `1f72f50`. Measures the code against PRD / ARCHITECTURE / ROADMAP and lays out the remaining work in order.*

> **Progress (2026-09-26):** Phases **A0** and **A1** are done. There are 107 pytest tests (unit tests plus API smoke tests against a temp DB), GitHub Actions CI, and `WATTSHARE_DB_PATH`. `market/matching.py` is a pure two-pointer greedy matcher that sorts by ask price with id tie-breaks, and `/match/smart` uses it too. Three bugs found along the way were also fixed: trade-ID collisions between dispatcher and marketplace trades, energy being sold twice in the same hour, and buyers purchasing beyond their deficit. 
>
> **Progress (2026-09-26, later): A2 is done.** The three §5 decisions went with the recommended defaults: a **JSON** config, **loop one real day**, and the **demo preset** stays the default (`"households": "generated"` is also available). Solar comes from Open-Meteo, with three committed Lucknow 2019 fixture days. Load comes from a **real dataset**, so the synthetic fallback wasn't needed: CEEW's Mathura (UP) smart meters, CC0 (see `backend/data/SOURCES.md`). There is also `GET /config`, a provenance line in the dashboard header, and `--config` / `--step` on the CLIs. The suite is at 138 tests, all offline.
>
> **A2.5 finding:** prices now move properly. They sit at ₹12 around dawn and dusk, about ₹6.5 at midday, and there is no supply at night, so nothing is flat or pinned. But `base + α·(D/S)` can never go **below** `base` (₹6), so `PRICE_MIN = 4` is unreachable, and a midday glut with 4× more supply than demand still only reaches ₹6.46. Retuning is a product decision and hasn't been made yet (see §5).
>
> **Phase B (in progress):**
> - Done:
>   - README: regulatory context, why not blockchain, data sources, CI badge, Python version.
>   - `WATTSHARE_CORS_ORIGINS` and a Render health check.
>   - Cold-start "waking up" state with retries.
>   - Boilerplate SVGs removed.
>   - CI actions moved to v7 and Node 22.
> - Also done:
>   - **Deployed and verified.** Render (`wattshare-api-wfjq.onrender.com`) and Vercel (`wattshare-eta.vercel.app`) were already wired to auto-deploy from `main`. CORS is locked to the Vercel origin.
>   - README screenshots (`docs/screenshots/`).
>   - Mobile check at 390px: no horizontal overflow on any page.
>   - Fixed clipped y-axis labels on the generation chart.
>   - **Hour flow reordered:** the marketplace trades while an hour is open, and the dispatcher clears the leftovers when it closes. Before this, dispatching as soon as an hour opened (after the double-sell fix) left the marketplace permanently empty.
>
> **Phase B is done**, apart from setting the health-check path on the existing Render service, which the API tools can't change; it's a one-field change in the dashboard. **Next: Phase C** (stretch), plus the open pricing decision below.

---

## 1. Where the code stands

| Roadmap phase | Status | Notes |
|---|---|---|
| 1 — Household simulation (real data) | ✅ **Done (A2)** — was ⚠️ Partial | Engine and ticks work, but the curves in `backend/simulation/curves.py` are **synthetic** (a sine bell for solar, Gaussian bumps for load). The 10 households are hard-coded in `simulation/engine.py`. No location/config input. |
| 2 — Matching + pricing | ✅ **Done (A1)** — was ⚠️ Partial | The pricing formula matches the spec. **The matching algorithm does not** (see §2.1). There are **no tests at all**. |
| 3 — API layer | ⚠️ **Mostly done** | All 10 endpoints from ARCHITECTURE.md exist, plus `GET /listings/{id}` and `POST /listings/{id}/buy`. There is no CI, no API tests, and the DB path is hard-coded. |
| 4 — Seller & Buyer dashboards | ✅ **Done** | `/seller` and `/buyer` pages, Smart Match, reliability, sparkline and grid health badge are all in place. |
| 5 — Polish & deployment | ⚠️ **Partial** | `render.yaml` and deploy instructions exist. The README has **no regulatory context section**, which ROADMAP asks for explicitly. Deployment has not been confirmed as live. |
| Stretch | ❌ Not started | Transformer load term, battery storage, hash-chained ledger. |

**In short:** the product shell (API + dashboards) is ahead of the foundations. The two headline claims in the PRD, *real data* and *tested*, are the parts that are missing. The plan below fixes the foundations before adding anything new.

---

## 2. Gaps found in existing code

### 2.1 Matching engine diverges from spec (correctness bug)
`backend/market/engine.py` `run_cycle`:
- Sellers are sorted by `h.id`. The spec says **ask price ascending**.
- Pairing uses `zip(sellers, buyers)`. That makes at most `min(len(sellers), len(buyers))` trades, each seller trades **once**, and leftover surplus is dropped. With 4 sellers and 6 buyers, 2 buyers are never served even when supply is plentiful. The spec says to match top-down **until one list is exhausted**.

**Fix:** use a two-pointer greedy with remaining-quantity tracking. Keep the engine pure: it takes households plus optional per-seller ask prices and returns trades without mutating anything.

### 2.2 Synthetic data where the PRD promises real data
See Phase A below.

### 2.3 Hard-coded configuration
The household list, solar ratio, location and DB path are all constants. ARCHITECTURE requires "location, number of households, solar-adoption ratio should be parameters."

### 2.4 Missing CLI flag
ARCHITECTURE lists a `--step` debug flag for tick-by-tick inspection. Only `--seed` exists.

---

## 3. Work plan

The order is deliberate: **tests first**, so the matching rewrite and the data swap have a safety net; **real data second**, because it is the biggest credibility gap; **deploy and docs third**; **stretch last**.

### Phase A0 — Test harness + CI (≈ 3–4 days)
*Done when:* `pytest` runs green locally and in GitHub Actions on every push.

1. Add a `backend/requirements-dev.txt` containing `pytest` and `httpx` (FastAPI's `TestClient` needs `httpx`).
2. Add `backend/tests/` with unit tests for the pure functions that exist today:
   - `pricing.clearing_price`: zero supply → `None`; clamping at both bounds; monotonic in demand/supply.
   - `grid_health.compute_grid_health`: all three bands and the zero-supply edge cases.
   - `reliability.compute_reliability_score`: default under 5 trades, the 20-trade window, the 7-day window, and the rule that dispatcher trades are excluded.
   - `stats.compute_seller_stats`: day/week bucketing and trades with `tick=None`.
   - `summary.effective_price` / `compute_listing_price_stats`.
   - `execution.execute_trade`: partial fulfilment, zero-deliverable attempts, and `fulfilled_as_listed`.
3. Make the DB path configurable with a `WATTSHARE_DB_PATH` env var, defaulting to the current path. Add API smoke tests using `TestClient` against a temp DB: tick → match → listings → buy → stats.
4. Add `.github/workflows/ci.yml` with two jobs:
   - Backend: Python 3.11 and 3.12 → `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` → `pytest`.
   - Frontend: Node 20 → `npm ci` → `npm run lint` → `npm run build` (working-directory `frontend`).
5. Pin `pytest` config in `pyproject.toml` or `pytest.ini` with `pythonpath = .` so `backend.*` imports resolve.

### Phase A1 — Fix the matching engine (≈ 2 days)
*Done when:* the new matching tests pass and the dashboards still work.

1. Write the failing tests first:
   - 1 seller with 10 kWh against 3 buyers needing 2, 3 and 4 kWh → 3 trades, 1 kWh of surplus left.
   - 3 small sellers against 1 large buyer → 3 trades.
   - Sellers are consumed in ask-price order, and ties break by id so results are deterministic.
   - Supply equals demand exactly → both lists exhausted, no zero-kWh trades.
   - Conservation: Σ traded ≤ min(total supply, total demand), and no seller or buyer goes over their net.
2. Rewrite `MarketEngine.run_cycle` as a two-pointer greedy. For each seller's ask price, use the manual listing price when one exists and the clearing price otherwise. All trades in a cycle still **settle at the clearing price**, per spec.
3. Pull the pure `match(sellers, buyers) -> list[Pairing]` out of the class so it can be tested without a DB or ID counter.
4. Check that `/match/smart` uses the same core algorithm. ARCHITECTURE describes it as "honest proof the engine works," so it must not be a separate code path.

### Phase A2 — Real data (≈ 2–3 weeks; the main piece of work)
*Done when:* a full simulated day for a configured location produces generation and consumption curves you can trace back to a named public source, and tests pass offline.

**A2.1 Config layer**
- Add `backend/config.py` using a Pydantic model loaded from `config/default.yaml` (or JSON) plus env overrides. It holds `location` (name, lat, lon, default Lucknow ≈ 26.85, 80.95), `sim_date`, `n_households`, `solar_ratio` (default 0.4), `seed`, `data_source` (`real` | `synthetic`), and the pricing constants.
- Replace `HOUSEHOLD_SEED_DATA` with a generator that builds N households from the config: solar capacity drawn from a realistic 2–5 kW rooftop range, zones assigned round-robin so each zone keeps at least one seller, and names from a list. Keep the current 10 as a `demo` preset so the dashboard demo stays stable.

**A2.2 Solar generation from real irradiance**
- Add `backend/data/solar.py` to fetch hourly GHI (`shortwave_radiation`, W/m²) from the **Open-Meteo Historical Weather API**. It is free and needs no key. **NASA POWER** (`ALLSKY_SFC_SW_DWN`, hourly) is the documented fallback.
- Generation model: `kWh = capacity_kWp × (GHI / 1000) × performance_ratio`, with PR ≈ 0.75–0.80 as a named constant. Optionally add a temperature derate later. Document it as a simple model.
- **Cache fetched days to disk** (`backend/data/cache/<lat>_<lon>_<date>.json`) and **commit one or two fixture days**, for example a clear pre-monsoon day and a cloudy monsoon day in Lucknow. Tests and the Render deploy then never depend on the network.
- Tests: the model is zero at night, peaks near local solar noon, and scales linearly with capacity. The fixture loader parses correctly.

**A2.3 Consumption from real load profiles**
- **Research spike first (time-box to 2–3 days):** find a public Indian residential hourly load dataset (data.gov.in, published academic smart-meter datasets, and similar). Record the source URL, licence, region, season and household count in `backend/data/SOURCES.md`.
- Normalise it into a small committed CSV of 24-hour per-household-class shapes (e.g. small / medium / large). Scale each household by its class and apply mild seeded noise so neighbours are not identical.
- **If no usable dataset turns up:** keep the current curve, but rename it `synthetic_profile`, label it as synthetic in the README and the API response (`data_source` field), and note the gap in the README. The honest fallback is better than overclaiming.

**A2.4 Wiring + CLI**
- `SimulationEngine(config)` pulls hour *h* of the loaded day. Wrapping past hour 23 advances to the next cached day, or loops the same day, depending on config.
- Add `--step` (press Enter to advance) and `--config path.yaml` to `run_simulation.py` and `run_market.py`.
- Expose `GET /config` (read-only) so the dashboard can show "Lucknow · 2026-05-14 · Open-Meteo" as a data-provenance line.

**A2.5 Re-validate Phase 2 against real data**
- Run a full day and check that prices actually move. With a 40% solar ratio, midday should be supply-heavy (cheap, green) and evenings should have zero supply (no trades, red). If the curve is flat or pinned at `PRICE_MAX` all day, retune α and the band limits, and write down why.

### Phase B — Polish & deployment (≈ 1–2 weeks)
*Done when:* both services are live, the README tells the full story, and a stranger can clone the repo and run it in under 5 minutes.

1. **README:**
   - Add a **Regulatory Context** section (Electricity Act 2003, SERC licensing, the Feb 2026 DERC/UPERC pilots, and WattShare as a matching/pricing engine rather than a trading operator), taken from ROADMAP.
   - Add a **Why not blockchain** paragraph from ARCHITECTURE.
   - Add a **Data sources** section linking `SOURCES.md`.
   - Update Non-goals: "all household data is simulated" becomes "simulated at the platform level from real-sourced data."
   - Add screenshots or a GIF of both dashboards and a CI status badge.
2. **Deploy:**
   - Render (backend) from `render.yaml` and Vercel (frontend, root `frontend`, `NEXT_PUBLIC_API_URL`).
   - Note: the Render free tier has an ephemeral disk and cold starts. Since the DB resets on boot anyway, that is fine; document it.
   - Consider narrowing CORS to the Vercel domain via an env var, keeping `*` for local use.
3. **Frontend polish:** a data-provenance line, loading and error states for when the Render cold start takes 30+ seconds, and a check of mobile layout on both dashboards.
4. **Tidy:** delete the unused Next.js boilerplate SVGs in `frontend/public/`, and state the Python version once (the spec says 3.11+, Render pins 3.12.7).

### Phase C — Stretch (only after A and B are solid)
Each item needs tests, and each can ship on its own.

1. **Transformer load term:**
   - Add `transformer_load_kw = Σ net injection + Σ grid draw` per zone (or neighbourhood) against a configured `max_load_kw`.
   - Pricing becomes `+ β·(load/max)²`, keeping the existing clamp.
   - Feed `transformer_load_pct` into `MarketState`, and switch `grid_health` to use load % instead of the demand/supply ratio. The badge's meaning then matches what ARCHITECTURE says it should.
2. **Battery storage:** a per-household `battery_capacity_kwh`, plus a simple rule-based policy (store when the price is below a threshold, sell when above). Surface the charge level on the seller dashboard.
3. **Hash-chained ledger:**
   - Each trade row stores `prev_hash` and `hash = sha256(prev_hash ‖ canonical trade fields)`.
   - Add `GET /ledger/verify`.
   - Label it "tamper-evident, blockchain-inspired," following the ARCHITECTURE wording.

---

## 4. Suggested schedule

This follows ROADMAP's "steady side project" pacing, starting now (late Sept 2026) and adjusting around the Diploma term load.

| Weeks | Phase | Milestone |
|---|---|---|
| 1 | A0 | CI green, core unit tests in place |
| 2 | A1 | Matching engine matches spec, conservation tests pass |
| 3–5 | A2 | Config layer, Open-Meteo solar, load-profile spike + integration |
| 6 | A2.5 | Pricing retuned against real curves |
| 7–8 | B | README + regulatory section, live on Render + Vercel |
| 9+ | C | Stretch features, one at a time |

That lands a complete, deployed, real-data v1 at roughly **2 months**, well inside ROADMAP's 3–4 month target, with slack for term workload.

---

## 5. Risks & decisions

| Risk / open question | Mitigation |
|---|---|
| No clean public Indian hourly residential load dataset | Time-boxed spike; fall back to a synthetic profile that is **clearly labelled** as synthetic |
| External API rate limits or downtime (Open-Meteo / NASA POWER) | Disk cache + committed fixtures; the app never fetches at request time in production |
| Real curves make pricing degenerate (pinned at max all evening) | That is realistic, since there's no solar at night. Show it honestly in the UI ("no local supply — grid only") rather than tuning it away |
| Matching rewrite changes numbers the dashboards display | Phase A0 API smoke tests catch contract breaks; the response schemas stay the same |
| Render free tier cold starts hurt the demo | A loading state in the frontend; mention it in the README |

**Open decision from A2.5:** should an oversupplied market price below `base`? For example, `price = base · (D/S)^γ` clamped to the band, or `base + α·(D/S − 1)`. Either would make the ₹4 floor reachable and midday solar noticeably cheap.

**Decisions to confirm before starting A2** (resolved, see Progress):
1. Config format: YAML (needs `pyyaml`) or JSON (no new dependency).
2. Whether a sim day loops the same real day or walks through consecutive days.
3. Whether the `demo` preset (today's 10 named households) stays the dashboard default, or the dashboard switches to config-generated households.
