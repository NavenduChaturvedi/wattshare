import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.market.engine import MarketEngine
from backend.simulation.engine import SimulationEngine

from . import db
from .schemas import HouseholdOut, MarketStateOut, MatchResponse, TickResponse, TradeOut

sim_engine: Optional[SimulationEngine] = None
market_engine: Optional[MarketEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sim_engine, market_engine

    # Each server run starts from a fresh, consistent simulation at hour 0 --
    # old trade/household rows from a previous run would no longer line up with it.
    db.reset_db()

    seed_env = os.environ.get("WATTSHARE_SEED")
    sim_engine = SimulationEngine(seed=int(seed_env) if seed_env else None)
    market_engine = MarketEngine()

    conn = db.get_connection()
    try:
        db.upsert_households(conn, sim_engine.households)
        conn.commit()
    finally:
        conn.close()

    yield


app = FastAPI(title="WattShare API", lifespan=lifespan)

# Local demo, no auth/cookies -- wildcard is fine and sidesteps origin quirks
# from whatever dev proxy fronts the frontend during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_db():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/households", response_model=list[HouseholdOut])
def get_households(conn=Depends(get_db)):
    return db.fetch_households(conn)


@app.post("/simulate/tick", response_model=TickResponse)
def simulate_tick(conn=Depends(get_db)):
    sim_engine.tick()
    db.upsert_households(conn, sim_engine.households)
    conn.commit()
    return TickResponse(hour=sim_engine.current_hour, households=db.fetch_households(conn))


@app.post("/match", response_model=MatchResponse)
def run_match(conn=Depends(get_db)):
    state, trades = market_engine.run_cycle(sim_engine.households, sim_engine.current_hour)
    db.insert_market_state(conn, state)
    db.insert_trades(conn, trades)
    conn.commit()
    return MatchResponse(
        market_state=MarketStateOut(**state.__dict__),
        trades=[TradeOut(**t.__dict__) for t in trades],
    )


@app.get("/trades", response_model=list[TradeOut])
def get_trades(conn=Depends(get_db)):
    return db.fetch_trades(conn)


@app.get("/market-state", response_model=MarketStateOut)
def get_market_state(conn=Depends(get_db)):
    state = db.fetch_latest_market_state(conn)
    if state is None:
        return MarketStateOut(timestamp=None, total_supply_kwh=0.0, total_demand_kwh=0.0, clearing_price=None)
    return state
