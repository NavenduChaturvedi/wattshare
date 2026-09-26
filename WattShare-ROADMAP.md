# WattShare — Roadmap & Regulatory Context

## Regulatory Context (state this plainly in the repo README too)

Under India's Electricity Act, 2003, the sale and purchase of electricity between consumers is not recognised — any entity distributing or trading electricity must hold a license from the relevant State Electricity Regulatory Commission. WattShare is built as a **matching and dynamic-pricing engine**, designed to be legible against the model already used in India's live pilots (DERC and UPERC approved six-month P2P solar trading pilots in Feb 2026 under the India Energy Stack framework), where a licensed DISCOM operates the pilot and a technology partner (e.g. ISGF + Powerledger in the UP pilot) supplies the platform. WattShare is not a commercial trading platform and does not intend to become one without that kind of institutional partnership.

Stating this directly in the docs is a credibility signal, not a limitation — it shows the project understands the domain rather than ignoring the legal reality.

## Build Phases

**Phase 1 — Household simulation (real data)**
- Integrate real solar irradiance (NASA POWER / Open-Meteo) and real consumption profiles
- Config-driven household count, solar ratio, location
- *Done when:* a full simulated day produces realistic, verifiable generation/consumption curves

**Phase 2 — Matching + pricing engine**
- Greedy matching algorithm, dynamic pricing formula
- pytest coverage for both — these are pure functions, cheap to test thoroughly
- *Done when:* trades execute correctly against real data and prices respond sensibly to supply/demand shifts

**Phase 3 — API layer**
- FastAPI endpoints, SQLite persistence
- GitHub Actions CI running the test suite on every push
- *Done when:* the full API surface from ARCHITECTURE.md is live and tested

**Phase 4 — Seller & Buyer Dashboards**
- Next.js + Tailwind, both role-specific views per ARCHITECTURE.md spec
- Listing + SellerStats models, reliability score, Smart Match flow
- *Done when:* it looks and feels like a real product, not a debug console

**Phase 5 — Polish & deployment**
- README with problem statement, architecture summary, and the regulatory context section above
- Deploy live (Render + Vercel)
- Stretch features (transformer load term, battery storage) only after Phases 1–4 are solid

## Suggested Pacing

Given the Diploma in Programming starting in October and a lighter 7-term pacing to manage course load: treat WattShare as a **steady side project, not a sprint.** Rough shape — one phase roughly every 2–3 weeks depending on term workload, aiming for a complete, deployed v1 within 3–4 months rather than rushing it around a new academic term. Adjust freely; the point of doing this outside a hackathon is exactly that there's no artificial deadline forcing corners to be cut.

## Path to "Going Somewhere" (realistic expectations)

- **Not** cold-emailing DERC/UPERC/Ministry of Power directly — near-zero odds of traction at that level for an individual
- **Better:** India Smart Grid Forum (ISGF) — public-private-academia forum, the actual technology-partner precedent in the UP pilot; a polished, well-documented prototype is a reasonable thing to share with them, though a reply/feedback is the realistic outcome, not adoption
- **Best concrete channel:** sanctioned government/industry challenges built for exactly this kind of crossover — e.g. the Blockchain India Challenge (C-DAC), which lists Power as a problem-statement sector and explicitly offers winners the chance to collaborate with user agencies on deployment. Worth checking for open cycles. Solar-specific hackathons (e.g. past India Solar Hackathon by New Energy Nexus) are another category to watch for.
- **Most likely genuine payoff:** not a deployed pilot, but a conversation, mentorship, or an opening into the cleantech/energy-tech space — treat that as a real win, not a consolation prize
