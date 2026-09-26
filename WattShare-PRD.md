# WattShare — Product Requirements Document

**Status:** Active multi-month build (not a hackathon project)
**Owner:** Navendu Chaturvedi (solo)

---

## 1. Problem Statement

- Rooftop solar owners sell surplus power back to the grid at low feed-in tariffs
- Non-solar households pay full retail rates for grid electricity with no upside from nearby solar adoption
- Net metering disproportionately benefits wealthier homeowners who can afford panels
- Local distribution transformers face unpredictable load from uncoordinated solar injection

## 2. Solution

WattShare is a peer-to-peer solar energy trading simulator and dispatcher: neighbors with surplus rooftop solar trade directly with nearby households, matched and priced automatically by a dispatcher engine that accounts for local supply/demand and (eventually) transformer load.

## 3. Goals

- Simulate a realistic neighborhood microgrid using **real** consumption and solar generation data, not synthetic placeholders
- Match sellers and buyers with a clear, explainable algorithm
- Price trades dynamically based on local demand/supply and transformer load
- Present it through role-specific dashboards (seller and buyer), not a raw data table
- Build to a standard that's genuinely defensible — tested, documented, honestly scoped — since this is a serious multi-month project, not a weekend demo

## 4. Non-Goals (v1)

- No real hardware/IoT integration — data is real-sourced but simulated at the platform level
- No real payment processing
- No user authentication — single shared simulation view
- **No live commercial electricity trading.** Under India's Electricity Act 2003, trading electricity between consumers requires a license from the relevant State Electricity Regulatory Commission. WattShare is a matching/pricing engine, not a licensed trading operator. See ROADMAP.md for how this constraint shapes the realistic path forward.

## 5. Target Users (for framing)

- **Seller (prosumer):** a household with rooftop solar wanting to earn more than feed-in tariff rates from surplus generation
- **Buyer:** a household without solar (or with a temporary deficit) wanting cheaper clean power than grid retail

## 6. Core Features

### MVP
1. Household simulation using real consumption profiles + real solar irradiance data
2. Greedy matching engine (sellers sorted cheap→expensive, buyers by need, matched top-down)
3. Dynamic pricing: `price = base + α * (demand/supply − 1)`, clamped min/max. Balanced → base; surplus → cheaper (revised 2026-09-26 so the price floor is reachable)
4. FastAPI backend exposing household state, matching cycles, trade history
5. Seller Dashboard: surplus available, pricing mode (auto/manual), earnings summary, reliability score, lifetime impact stat
6. Buyer Dashboard: listing table (units, price, zone proximity, reliability), best-price/most-reliable highlights, Smart Match button, grid health indicator, price trend sparkline

### Stretch (post-MVP)
- Transformer load term in pricing: `+ β * (transformer_load / max_load)^2`
- Battery storage simulation (sell vs. store vs. use decisions)
- Tamper-evident trade ledger (hash-chained records)

## 7. Success Criteria

Since this is explicitly open-ended on outcome (per NV: "if it goes well, it goes well; if not, it's a strong showcase project"):

- **Minimum bar:** a well-built, well-documented, tested, deployed prototype using real data — genuinely portfolio-strong regardless of what happens next
- **Good outcome:** gets noticed through a legitimate channel (a sanctioned government/industry challenge, ISGF, or similar) and leads to a conversation, mentorship, or opportunity in the cleantech/energy-tech space
- **Best case, low probability:** some component of this gets referenced or adopted in an actual pilot context — understood as a long shot, not the plan

## 8. Stakeholders / Related Context

- Real-world regulatory precedent: DERC and UPERC approved six-month P2P solar trading pilots in Feb 2026 under the India Energy Stack framework, run by licensed DISCOMs (TP-DDL, BSES, PVVNL) with India Smart Grid Forum (ISGF) and Powerledger as technology partners — not independent platform operators. This is the real-world template WattShare is designed to be legible against.
