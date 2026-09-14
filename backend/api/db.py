import sqlite3
from pathlib import Path
from typing import List, Optional

from backend.market.models import MarketState, Trade
from backend.simulation.models import Household

DB_PATH = Path(__file__).resolve().parent.parent / "wattshare.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    has_solar INTEGER NOT NULL,
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
    timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS market_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    total_supply_kwh REAL NOT NULL,
    total_demand_kwh REAL NOT NULL,
    clearing_price REAL
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
            "DROP TABLE IF EXISTS market_states;"
        )
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def upsert_households(conn: sqlite3.Connection, households: List[Household]) -> None:
    conn.executemany(
        """
        INSERT INTO households (id, name, has_solar, current_generation_kwh, current_consumption_kwh, battery_stored_kwh)
        VALUES (:id, :name, :has_solar, :current_generation_kwh, :current_consumption_kwh, :battery_stored_kwh)
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
            "current_generation_kwh": r["current_generation_kwh"],
            "current_consumption_kwh": r["current_consumption_kwh"],
            "battery_stored_kwh": r["battery_stored_kwh"],
        }
        for r in rows
    ]


def insert_trades(conn: sqlite3.Connection, trades: List[Trade]) -> None:
    if not trades:
        return
    conn.executemany(
        """
        INSERT INTO trades (id, seller_id, buyer_id, amount_kwh, price_per_kwh, timestamp)
        VALUES (:id, :seller_id, :buyer_id, :amount_kwh, :price_per_kwh, :timestamp)
        """,
        [
            {
                "id": t.id,
                "seller_id": t.seller_id,
                "buyer_id": t.buyer_id,
                "amount_kwh": t.amount_kwh,
                "price_per_kwh": t.price_per_kwh,
                "timestamp": t.timestamp,
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
