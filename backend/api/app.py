import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_config
from backend.market.engine import MarketEngine
from backend.market.grid_health import compute_grid_health
from backend.market.matching import Bid, Offer, match
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
    ConfigOut,
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

    sim_engine = SimulationEngine(config=load_config())
    market_engine = MarketEngine()

    conn = db.get_connection()
    try:
        db.upsert_households(conn, sim_engine.households)
        conn.commit()
    finally:
        conn.close()

    yield


app = FastAPI(title="WattShare API", lifespan=lifespan)


def cors_origins() -> list:
    """WATTSHARE_CORS_ORIGINS: comma-separated allowed origins, e.g. the Vercel URL in
    production. Unset means "*" -- fine for local dev (no auth/cookies), and it
    sidesteps origin quirks from whatever dev proxy fronts the frontend."""
    raw = os.environ.get("WATTSHARE_CORS_ORIGINS", "").strip()
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()] if raw else ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def get_db():
    conn = db.get_connection()
    try:
        yield conn
    finally:
        conn.close()


SOLAR_SOURCE = "Open-Meteo Historical Weather API (hourly shortwave radiation)"
LOAD_SOURCE = "CEEW smart-meter data, Mathura, Uttar Pradesh, 2019 (CC0)"


@app.get("/config", response_model=ConfigOut)
def get_config():
    """Read-only data provenance, so the dashboard can say where its numbers come from."""
    cfg = sim_engine.config
    real = cfg.data_source == "real"
    return ConfigOut(
        location=cfg.location.name,
        latitude=cfg.location.latitude,
        longitude=cfg.location.longitude,
        sim_date=cfg.sim_date,
        season=sim_engine.season if real else None,
        data_source=cfg.data_source,
        households=cfg.households,
        solar_source=SOLAR_SOURCE if real else "synthetic bell curve",
        load_source=LOAD_SOURCE if real else "synthetic morning/evening peaks",
    )


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
    state, trades = market_engine.run_cycle(
        sim_engine.households, sim_engine.current_hour, ask_prices=_manual_ask_prices(conn)
    )
    db.insert_market_state(conn, state)
    for trade in trades:
        trade.id = db.insert_trade(conn, trade)
        _settle(trade)
    for seller_id in {t.seller_id for t in trades}:
        _shrink_listing_to_open_surplus(conn, seller_id)
    db.upsert_households(conn, sim_engine.households)
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


def _manual_ask_prices(conn) -> dict:
    """Seller id -> asking price, for sellers whose current listing sets its own price."""
    asks = {}
    for h in sim_engine.households:
        if not h.has_solar:
            continue
        row = db.fetch_latest_listing_for_seller(conn, h.id)
        if row and row["pricing_mode"] == "manual" and row["asking_price_per_kwh"] is not None:
            asks[h.id] = row["asking_price_per_kwh"]
    return asks


def _settle(trade) -> None:
    """Books a trade against both households' positions for this hour, so neither
    the dispatcher nor the marketplace can trade the same kWh again."""
    if trade.amount_kwh <= 0:
        return
    _find_household(trade.seller_id).record_sale(trade.amount_kwh)
    _find_household(trade.buyer_id).record_purchase(trade.amount_kwh)


def _open_need_kwh(household) -> float:
    """How much this household still has to cover this hour (0 if it's in surplus or already covered)."""
    return max(-household.open_net_kwh, 0.0)


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
        units_available_kwh=max(household.open_net_kwh, 0.0),
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


def _shrink_listing_to_open_surplus(conn, seller_id: str) -> None:
    """After the dispatcher sells some of a seller's surplus, their listing can't
    still advertise that energy. Re-snapshot it (same as after a marketplace sale)
    so buyers see what's really left, and the seller isn't marked unreliable for
    energy the dispatcher sold on their behalf."""
    row = db.fetch_latest_listing_for_seller(conn, seller_id)
    if row is None or row["units_available_kwh"] <= 0:
        return
    listing = Listing(**row)
    seller = _find_household(seller_id)
    remaining = round(min(listing.units_available_kwh, max(seller.open_net_kwh, 0.0)), 3)
    if remaining < listing.units_available_kwh:
        _refresh_listing_after_sale(conn, listing, remaining)


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
    need = _open_need_kwh(buyer)
    if need <= 0:
        raise HTTPException(status_code=400, detail=f"{buyer.name} has no deficit to cover this hour")
    requested = round(min(payload.amount_kwh, need), 3)

    seller = _find_household(listing.seller_household_id)

    trade, remaining = execute_trade(
        listing,
        buyer.id,
        requested,
        seller,
        _current_clearing_price(conn),
        sim_engine.current_hour,
        sim_engine.total_ticks,
    )
    trade.id = db.insert_trade(conn, trade)
    _settle(trade)
    _refresh_listing_after_sale(conn, listing, remaining)
    db.upsert_households(conn, sim_engine.households)
    conn.commit()

    if trade.amount_kwh >= payload.amount_kwh - 1e-9:
        message = f"Bought {trade.amount_kwh:.2f} kWh at Rs {trade.price_per_kwh:.2f}/kWh."
    elif trade.amount_kwh >= requested - 1e-9:
        message = (
            f"Bought {trade.amount_kwh:.2f} kWh -- that covers your whole deficit this hour "
            f"(you asked for {payload.amount_kwh:.2f})."
        )
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
    need = _open_need_kwh(buyer)
    if need <= 0:
        raise HTTPException(status_code=400, detail=f"{buyer.name} has no deficit to cover this hour")
    if payload.desired_kwh > need + 1e-9:
        raise HTTPException(
            status_code=400, detail=f"{buyer.name} only needs {need:.2f} kWh this hour -- ask for that much or less"
        )

    current_clearing_price = _current_clearing_price(conn)

    # Same matching algorithm as the dispatcher (matching.match), run for one buyer
    # against the advertised listings. Listings are one per seller, so offers key by seller.
    candidates = {
        row["seller_household_id"]: Listing(**row)
        for row in db.fetch_active_listings(conn)
        if row["seller_household_id"] != buyer.id and _find_household(row["seller_household_id"]) is not None
    }
    offers = [
        Offer(seller_id, effective_price(listing, current_clearing_price), listing.units_available_kwh)
        for seller_id, listing in candidates.items()
    ]

    remaining = payload.desired_kwh
    executed: list = []
    while remaining > 0:
        pairings = match(offers, [Bid(buyer.id, remaining)])
        if not pairings:
            break
        # Execute only the first pairing, then re-match: if that listing turns out
        # stale and delivers short, the shortfall rolls on to the next-cheapest seller.
        pairing = pairings[0]
        offers = [o for o in offers if o.household_id != pairing.seller_id]
        listing = candidates[pairing.seller_id]
        seller = _find_household(pairing.seller_id)

        trade, leftover = execute_trade(
            listing,
            buyer.id,
            pairing.amount_kwh,
            seller,
            current_clearing_price,
            sim_engine.current_hour,
            sim_engine.total_ticks,
        )
        trade.id = db.insert_trade(conn, trade)
        _settle(trade)
        _refresh_listing_after_sale(conn, listing, leftover)
        executed.append(trade)
        remaining = round(remaining - trade.amount_kwh, 3)

    db.upsert_households(conn, sim_engine.households)
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
