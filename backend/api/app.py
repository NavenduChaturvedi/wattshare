import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.market.engine import MarketEngine
from backend.market.grid_health import compute_grid_health
from backend.marketplace.execution import execute_trade
from backend.marketplace.models import Listing
from backend.marketplace.reliability import compute_reliability_score
from backend.marketplace.stats import compute_seller_stats
from backend.marketplace.summary import compute_listing_price_stats, effective_price
from backend.simulation.engine import SimulationEngine

from . import db
from .schemas import (
    BuyerListingOut,
    BuyFromListingRequest,
    HouseholdOut,
    ListingCreate,
    ListingOut,
    MarketStateOut,
    MarketSummaryOut,
    MatchResponse,
    PricePointOut,
    SellerStatsOut,
    SmartMatchRequest,
    SmartMatchResponseOut,
    TickResponse,
    TradeExecutionOut,
    TradeOut,
)

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


def _find_household(household_id: str):
    return next((h for h in sim_engine.households if h.id == household_id), None)


def _current_clearing_price(conn) -> Optional[float]:
    latest_state = db.fetch_latest_market_state(conn)
    return latest_state["clearing_price"] if latest_state else None


@app.post("/listings", response_model=ListingOut)
def create_or_update_listing(payload: ListingCreate, conn=Depends(get_db)):
    household = _find_household(payload.seller_household_id)
    if household is None:
        raise HTTPException(status_code=404, detail="household not found")
    if not household.has_solar:
        raise HTTPException(status_code=400, detail="only solar households can list surplus for sale")
    if payload.pricing_mode == "manual" and (
        payload.asking_price_per_kwh is None or payload.asking_price_per_kwh <= 0
    ):
        raise HTTPException(status_code=400, detail="manual pricing requires a positive asking_price_per_kwh")

    listing = Listing(
        id=0,  # assigned by the database on insert
        seller_household_id=household.id,
        units_available_kwh=max(household.net_kwh, 0.0),
        pricing_mode=payload.pricing_mode,
        asking_price_per_kwh=payload.asking_price_per_kwh if payload.pricing_mode == "manual" else None,
        created_at_tick=sim_engine.total_ticks,
    )
    listing.id = db.insert_listing(conn, listing)
    conn.commit()
    return ListingOut(**listing.__dict__)


@app.get("/listings/{seller_household_id}", response_model=Optional[ListingOut])
def get_seller_listing(seller_household_id: str, conn=Depends(get_db)):
    return db.fetch_latest_listing_for_seller(conn, seller_household_id)


@app.get("/listings", response_model=list[BuyerListingOut])
def get_active_listings(conn=Depends(get_db)):
    listings = [Listing(**row) for row in db.fetch_active_listings(conn)]
    if not listings:
        return []

    current_clearing_price = _current_clearing_price(conn)
    trades = db.fetch_trades_for_marketplace(conn)

    out = []
    for listing in listings:
        household = _find_household(listing.seller_household_id)
        if household is None:
            continue  # defensive -- shouldn't happen, a listing always comes from a real household
        out.append(
            BuyerListingOut(
                id=listing.id,
                seller_household_id=listing.seller_household_id,
                seller_name=household.name,
                zone_id=household.zone_id,
                units_available_kwh=listing.units_available_kwh,
                price_per_kwh=effective_price(listing, current_clearing_price),
                reliability_score=compute_reliability_score(listing.seller_household_id, trades, sim_engine.total_ticks),
            )
        )
    return out


def _refresh_listing_after_sale(conn, listing: Listing, remaining_kwh: float) -> None:
    """A sale is also the moment we learn the seller's true current surplus, so
    re-snapshot the listing with what's actually left -- this both prevents
    over-selling the same stale listing repeatedly and naturally "un-stales" it."""
    db.insert_listing(
        conn,
        Listing(
            id=0,
            seller_household_id=listing.seller_household_id,
            units_available_kwh=remaining_kwh,
            pricing_mode=listing.pricing_mode,
            asking_price_per_kwh=listing.asking_price_per_kwh,
            created_at_tick=sim_engine.total_ticks,
        ),
    )


@app.post("/listings/{listing_id}/buy", response_model=TradeExecutionOut)
def buy_from_listing(listing_id: int, payload: BuyFromListingRequest, conn=Depends(get_db)):
    listing_row = db.fetch_listing_by_id(conn, listing_id)
    if listing_row is None:
        raise HTTPException(status_code=404, detail="listing not found")
    listing = Listing(**listing_row)

    buyer = _find_household(payload.buyer_household_id)
    if buyer is None:
        raise HTTPException(status_code=404, detail="buyer household not found")
    if buyer.id == listing.seller_household_id:
        raise HTTPException(status_code=400, detail="can't buy from your own listing")
    if payload.amount_kwh <= 0:
        raise HTTPException(status_code=400, detail="amount_kwh must be positive")

    seller = _find_household(listing.seller_household_id)

    trade, remaining = execute_trade(
        listing,
        buyer.id,
        payload.amount_kwh,
        seller,
        _current_clearing_price(conn),
        sim_engine.current_hour,
        sim_engine.total_ticks,
    )
    trade.id = db.insert_single_trade(conn, trade)
    _refresh_listing_after_sale(conn, listing, remaining)
    conn.commit()

    if trade.amount_kwh >= payload.amount_kwh - 1e-9:
        message = f"Bought {trade.amount_kwh:.2f} kWh at Rs {trade.price_per_kwh:.2f}/kWh."
    elif trade.fulfilled_as_listed:
        message = f"Bought {trade.amount_kwh:.2f} kWh -- that's all this listing had (you asked for {payload.amount_kwh:.2f})."
    elif trade.amount_kwh > 0:
        message = (
            f"Only {trade.amount_kwh:.2f} kWh came through -- the seller's surplus dropped "
            f"since they listed {listing.units_available_kwh:.2f} kWh."
        )
    else:
        message = "The seller has nothing deliverable right now -- their listing was stale."

    return TradeExecutionOut(
        trade=TradeOut(**trade.__dict__),
        fulfilled_as_listed=trade.fulfilled_as_listed,
        message=message,
    )


@app.post("/match/smart", response_model=SmartMatchResponseOut)
def smart_match(payload: SmartMatchRequest, conn=Depends(get_db)):
    buyer = _find_household(payload.buyer_household_id)
    if buyer is None:
        raise HTTPException(status_code=404, detail="buyer household not found")
    if payload.desired_kwh <= 0:
        raise HTTPException(status_code=400, detail="desired_kwh must be positive")

    current_clearing_price = _current_clearing_price(conn)

    # Optimal = cheapest first, same principle as the dispatcher's matching engine,
    # applied here to one buyer's specific request rather than the whole neighborhood.
    candidates = [
        Listing(**row) for row in db.fetch_active_listings(conn) if row["seller_household_id"] != buyer.id
    ]
    candidates.sort(key=lambda listing: effective_price(listing, current_clearing_price))

    remaining = payload.desired_kwh
    executed: list = []
    for listing in candidates:
        if remaining <= 0:
            break
        seller = _find_household(listing.seller_household_id)
        if seller is None:
            continue

        trade, leftover = execute_trade(
            listing, buyer.id, remaining, seller, current_clearing_price, sim_engine.current_hour, sim_engine.total_ticks
        )
        trade.id = db.insert_single_trade(conn, trade)
        _refresh_listing_after_sale(conn, listing, leftover)
        executed.append(trade)
        remaining = round(remaining - trade.amount_kwh, 3)

    conn.commit()

    total_kwh = round(sum(t.amount_kwh for t in executed), 3)
    total_cost = round(sum(t.amount_kwh * t.price_per_kwh for t in executed), 2)

    return SmartMatchResponseOut(
        trades=[TradeOut(**t.__dict__) for t in executed],
        total_kwh_matched=total_kwh,
        total_cost=total_cost,
        fully_matched=remaining <= 1e-9,
    )


@app.get("/sellers/{seller_household_id}/stats", response_model=SellerStatsOut)
def get_seller_stats(seller_household_id: str, conn=Depends(get_db)):
    if _find_household(seller_household_id) is None:
        raise HTTPException(status_code=404, detail="household not found")
    trades = db.fetch_trades_for_marketplace(conn)
    stats = compute_seller_stats(seller_household_id, trades, sim_engine.total_ticks)
    return SellerStatsOut(**stats.__dict__)


@app.get("/market-state", response_model=MarketStateOut)
def get_market_state(conn=Depends(get_db)):
    state = db.fetch_latest_market_state(conn)
    if state is None:
        return MarketStateOut(timestamp=None, total_supply_kwh=0.0, total_demand_kwh=0.0, clearing_price=None)
    return state


@app.get("/market/summary", response_model=MarketSummaryOut)
def get_market_summary(conn=Depends(get_db)):
    latest_state = db.fetch_latest_market_state(conn)
    current_clearing_price = latest_state["clearing_price"] if latest_state else None
    total_supply = latest_state["total_supply_kwh"] if latest_state else 0.0
    total_demand = latest_state["total_demand_kwh"] if latest_state else 0.0

    active_listings = [Listing(**row) for row in db.fetch_active_listings(conn)]
    average_price, best_price = compute_listing_price_stats(active_listings, current_clearing_price)

    trend_rows = db.fetch_recent_market_states(conn)
    price_trend = [
        PricePointOut(hour=r["timestamp"], clearing_price=r["clearing_price"])
        for r in trend_rows
        if r["clearing_price"] is not None
    ]

    return MarketSummaryOut(
        current_clearing_price=current_clearing_price,
        average_listing_price=average_price,
        best_listing_price=best_price,
        grid_health=compute_grid_health(total_demand, total_supply),
        price_trend=price_trend,
    )
