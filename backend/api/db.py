import sqlite3
from pathlib import Path
from typing import List, Optional

from backend.market.models import MarketState, Trade
from backend.marketplace.models import Listing
from backend.simulation.models import Household

DB_PATH = Path(__file__).resolve().parent.parent / "wattshare.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    has_solar INTEGER NOT NULL,
    zone_id TEXT NOT NULL,
    current_generation_kwh REAL NOT NULL,
    current_consumption_kwh REAL NOT NULL,
    battery_stored_kwh REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id TEXT NOT NULL,
    buyer_id TEXT NOT NULL,
    amount_kwh REAL NOT NULL,
    price_per_kwh REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    listing_id INTEGER,
    fulfilled_as_listed INTEGER,
    tick INTEGER
);

CREATE TABLE IF NOT EXISTS market_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    total_supply_kwh REAL NOT NULL,
    total_demand_kwh REAL NOT NULL,
    clearing_price REAL
);

-- Append-only, like trades/market_states: each save is a new row rather than an
-- update, so a listing's snapshot (units_available_kwh, created_at_tick) is
-- preserved even after the seller's live surplus moves on. "A seller's current
-- listing" = the most recent row for that seller_household_id. This is what lets
-- the marketplace later detect a stale listing (promised more than the seller
-- can actually deliver by the time a trade executes against it).
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_household_id TEXT NOT NULL,
    units_available_kwh REAL NOT NULL,
    pricing_mode TEXT NOT NULL,
    asking_price_per_kwh REAL,
    created_at_tick INTEGER NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI's sync dependencies and route handlers can
    # run on different threadpool threads within the same request. Safe here since
    # every connection is opened fresh per request (via the get_db dependency) and
    # closed at the end of that same request -- never shared across concurrent requests.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    """Drop and recreate all tables -- used to start each fresh app run from a clean slate."""
    conn = get_connection()
    try:
        conn.executescript(
            "DROP TABLE IF EXISTS households; "
            "DROP TABLE IF EXISTS trades; "
            "DROP TABLE IF EXISTS market_states; "
            "DROP TABLE IF EXISTS listings;"
        )
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def upsert_households(conn: sqlite3.Connection, households: List[Household]) -> None:
    conn.executemany(
        """
        INSERT INTO households (id, name, has_solar, zone_id, current_generation_kwh, current_consumption_kwh, battery_stored_kwh)
        VALUES (:id, :name, :has_solar, :zone_id, :current_generation_kwh, :current_consumption_kwh, :battery_stored_kwh)
        ON CONFLICT(id) DO UPDATE SET
            current_generation_kwh = excluded.current_generation_kwh,
            current_consumption_kwh = excluded.current_consumption_kwh,
            battery_stored_kwh = excluded.battery_stored_kwh
        """,
        [
            {
                "id": h.id,
                "name": h.name,
                "has_solar": int(h.has_solar),
                "zone_id": h.zone_id,
                "current_generation_kwh": h.current_generation_kwh,
                "current_consumption_kwh": h.current_consumption_kwh,
                "battery_stored_kwh": h.battery_stored_kwh,
            }
            for h in households
        ],
    )


def fetch_households(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute("SELECT * FROM households ORDER BY id").fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "has_solar": bool(r["has_solar"]),
            "zone_id": r["zone_id"],
            "current_generation_kwh": r["current_generation_kwh"],
            "current_consumption_kwh": r["current_consumption_kwh"],
            "battery_stored_kwh": r["battery_stored_kwh"],
        }
        for r in rows
    ]


def insert_single_trade(conn: sqlite3.Connection, trade: Trade) -> int:
    """Like insert_trades, but for a single marketplace-originated trade whose id
    isn't pre-assigned by an in-memory counter (MarketEngine assigns its own ids
    for dispatcher-cycle trades; this lets SQLite's AUTOINCREMENT assign one
    instead -- safe to mix, since AUTOINCREMENT always ratchets past the highest
    id it has ever seen, explicit or automatic)."""
    cursor = conn.execute(
        """
        INSERT INTO trades (seller_id, buyer_id, amount_kwh, price_per_kwh, timestamp,
                             listing_id, fulfilled_as_listed, tick)
        VALUES (:seller_id, :buyer_id, :amount_kwh, :price_per_kwh, :timestamp,
                :listing_id, :fulfilled_as_listed, :tick)
        """,
        {
            "seller_id": trade.seller_id,
            "buyer_id": trade.buyer_id,
            "amount_kwh": trade.amount_kwh,
            "price_per_kwh": trade.price_per_kwh,
            "timestamp": trade.timestamp,
            "listing_id": trade.listing_id,
            "fulfilled_as_listed": None if trade.fulfilled_as_listed is None else int(trade.fulfilled_as_listed),
            "tick": trade.tick,
        },
    )
    return cursor.lastrowid


def insert_trades(conn: sqlite3.Connection, trades: List[Trade]) -> None:
    if not trades:
        return
    conn.executemany(
        """
        INSERT INTO trades (id, seller_id, buyer_id, amount_kwh, price_per_kwh, timestamp,
                             listing_id, fulfilled_as_listed, tick)
        VALUES (:id, :seller_id, :buyer_id, :amount_kwh, :price_per_kwh, :timestamp,
                :listing_id, :fulfilled_as_listed, :tick)
        """,
        [
            {
                "id": t.id,
                "seller_id": t.seller_id,
                "buyer_id": t.buyer_id,
                "amount_kwh": t.amount_kwh,
                "price_per_kwh": t.price_per_kwh,
                "timestamp": t.timestamp,
                "listing_id": t.listing_id,
                "fulfilled_as_listed": None if t.fulfilled_as_listed is None else int(t.fulfilled_as_listed),
                "tick": t.tick,
            }
            for t in trades
        ],
    )


def fetch_trades(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    return [
        {
            "id": r["id"],
            "seller_id": r["seller_id"],
            "buyer_id": r["buyer_id"],
            "amount_kwh": r["amount_kwh"],
            "price_per_kwh": r["price_per_kwh"],
            "timestamp": r["timestamp"],
        }
        for r in rows
    ]


def fetch_trades_for_marketplace(conn: sqlite3.Connection) -> List[Trade]:
    """Full Trade objects (including the marketplace fields) for reliability/earnings
    calculations -- unlike fetch_trades(), which only returns the original Phase 3
    columns for the unchanged GET /trades response shape."""
    rows = conn.execute("SELECT * FROM trades ORDER BY id").fetchall()
    return [
        Trade(
            id=r["id"],
            seller_id=r["seller_id"],
            buyer_id=r["buyer_id"],
            amount_kwh=r["amount_kwh"],
            price_per_kwh=r["price_per_kwh"],
            timestamp=r["timestamp"],
            listing_id=r["listing_id"],
            fulfilled_as_listed=None if r["fulfilled_as_listed"] is None else bool(r["fulfilled_as_listed"]),
            tick=r["tick"],
        )
        for r in rows
    ]


def insert_market_state(conn: sqlite3.Connection, state: MarketState) -> None:
    conn.execute(
        """
        INSERT INTO market_states (timestamp, total_supply_kwh, total_demand_kwh, clearing_price)
        VALUES (:timestamp, :total_supply_kwh, :total_demand_kwh, :clearing_price)
        """,
        {
            "timestamp": state.timestamp,
            "total_supply_kwh": state.total_supply_kwh,
            "total_demand_kwh": state.total_demand_kwh,
            "clearing_price": state.clearing_price,
        },
    )


def fetch_latest_market_state(conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute("SELECT * FROM market_states ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return {
        "timestamp": row["timestamp"],
        "total_supply_kwh": row["total_supply_kwh"],
        "total_demand_kwh": row["total_demand_kwh"],
        "clearing_price": row["clearing_price"],
    }


def fetch_recent_market_states(conn: sqlite3.Connection, limit: int = 24) -> List[dict]:
    """The most recent cycles, oldest first -- a stand-in for "today" (one row per
    hourly cycle, so the last 24 approximate a simulated day) without needing an
    absolute-tick column on this table."""
    rows = conn.execute("SELECT * FROM market_states ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [
        {
            "timestamp": r["timestamp"],
            "clearing_price": r["clearing_price"],
        }
        for r in reversed(rows)
    ]


def _row_to_listing(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "seller_household_id": r["seller_household_id"],
        "units_available_kwh": r["units_available_kwh"],
        "pricing_mode": r["pricing_mode"],
        "asking_price_per_kwh": r["asking_price_per_kwh"],
        "created_at_tick": r["created_at_tick"],
    }


def insert_listing(conn: sqlite3.Connection, listing: Listing) -> int:
    """Always inserts a new row (see the listings table comment) and returns its id."""
    cursor = conn.execute(
        """
        INSERT INTO listings (seller_household_id, units_available_kwh, pricing_mode,
                               asking_price_per_kwh, created_at_tick)
        VALUES (:seller_household_id, :units_available_kwh, :pricing_mode,
                :asking_price_per_kwh, :created_at_tick)
        """,
        {
            "seller_household_id": listing.seller_household_id,
            "units_available_kwh": listing.units_available_kwh,
            "pricing_mode": listing.pricing_mode,
            "asking_price_per_kwh": listing.asking_price_per_kwh,
            "created_at_tick": listing.created_at_tick,
        },
    )
    return cursor.lastrowid


def fetch_latest_listing_for_seller(conn: sqlite3.Connection, seller_household_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM listings WHERE seller_household_id = ? ORDER BY id DESC LIMIT 1",
        (seller_household_id,),
    ).fetchone()
    return None if row is None else _row_to_listing(row)


def fetch_listing_by_id(conn: sqlite3.Connection, listing_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    return None if row is None else _row_to_listing(row)


def fetch_active_listings(conn: sqlite3.Connection) -> List[dict]:
    """The latest listing per seller, excluding ones with nothing left to sell."""
    rows = conn.execute(
        """
        SELECT l.* FROM listings l
        INNER JOIN (
            SELECT seller_household_id, MAX(id) AS max_id
            FROM listings
            GROUP BY seller_household_id
        ) latest ON l.id = latest.max_id
        WHERE l.units_available_kwh > 0
        ORDER BY l.seller_household_id
        """
    ).fetchall()
    return [_row_to_listing(r) for r in rows]
