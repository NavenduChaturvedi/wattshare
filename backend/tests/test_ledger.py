import sqlite3

import pytest

from backend.market.ledger import GENESIS_HASH, canonical, trade_hash, verify_chain

from .api_helpers import households, open_net


def make_trade(tid, amount=1.0):
    return {
        "id": tid,
        "seller_id": "S1",
        "buyer_id": "B1",
        "amount_kwh": amount,
        "price_per_kwh": 6.5,
        "timestamp": 12,
        "listing_id": None,
        "fulfilled_as_listed": None,
        "tick": 12,
    }


def chain(n):
    rows, prev = [], GENESIS_HASH
    for i in range(1, n + 1):
        row = make_trade(i, amount=i / 10)
        row["prev_hash"], row["hash"] = prev, trade_hash(prev, row)
        prev = row["hash"]
        rows.append(row)
    return rows


# --- pure chain logic -------------------------------------------------------


def test_canonical_form_is_order_independent_and_normalises_bools():
    a = make_trade(1)
    b = dict(reversed(list(a.items())))
    assert canonical(a) == canonical(b)
    assert canonical({**a, "fulfilled_as_listed": True}) == canonical({**a, "fulfilled_as_listed": 1})


def test_hash_depends_on_every_field_and_the_predecessor():
    base = make_trade(1)
    h = trade_hash(GENESIS_HASH, base)
    assert trade_hash("f" * 64, base) != h
    for field, value in [("amount_kwh", 1.01), ("price_per_kwh", 7.0), ("buyer_id", "B2"), ("id", 2)]:
        assert trade_hash(GENESIS_HASH, {**base, field: value}) != h


def test_empty_chain_is_valid():
    check = verify_chain([])
    assert (check.valid, check.trades_checked, check.head_hash) == (True, 0, GENESIS_HASH)


def test_intact_chain_verifies():
    rows = chain(5)
    check = verify_chain(rows)
    assert check.valid and check.trades_checked == 5 and check.head_hash == rows[-1]["hash"]


def test_edited_trade_is_caught_at_that_trade():
    rows = chain(5)
    rows[2]["amount_kwh"] = 99.0
    check = verify_chain(rows)
    assert (check.valid, check.first_invalid_trade_id, check.trades_checked) == (False, 3, 2)


def test_deleted_trade_breaks_the_next_link():
    rows = chain(5)
    del rows[1]
    assert verify_chain(rows).first_invalid_trade_id == 3


def test_rehashing_one_edited_row_still_breaks_the_chain_after_it():
    rows = chain(5)
    rows[2]["amount_kwh"] = 99.0
    rows[2]["hash"] = trade_hash(rows[2]["prev_hash"], rows[2])  # a forger fixes up row 3...
    assert verify_chain(rows).first_invalid_trade_id == 4  # ...but row 4 still points at the old hash


# --- through the API ----------------------------------------------------------


def test_api_ledger_verifies_after_mixed_trading(client):
    for _ in range(11):
        client.post("/simulate/tick")
    hh = households(client)
    seller = max((h for h in hh.values() if h["has_solar"]), key=open_net)
    buyer = min(hh.values(), key=open_net)
    listing = client.post("/listings", json={"seller_household_id": seller["id"], "pricing_mode": "auto"}).json()
    client.post(f"/listings/{listing['id']}/buy", json={"buyer_household_id": buyer["id"], "amount_kwh": 0.1})
    client.post("/match")
    client.post("/simulate/tick")
    client.post("/match")

    n_trades = len(client.get("/trades").json())
    check = client.get("/ledger/verify").json()
    assert n_trades > 3
    assert check == {
        "valid": True,
        "trades_checked": n_trades,
        "head_hash": check["head_hash"],
        "first_invalid_trade_id": None,
    }
    assert len(check["head_hash"]) == 64


def test_api_detects_a_tampered_row(client, tmp_path):
    for _ in range(12):
        client.post("/simulate/tick")
        client.post("/match")
    victim = client.get("/trades").json()[3]["id"]

    conn = sqlite3.connect(tmp_path / "test.db")  # same file the client fixture points the API at
    conn.execute("UPDATE trades SET amount_kwh = amount_kwh * 2 WHERE id = ?", (victim,))
    conn.commit()
    conn.close()

    check = client.get("/ledger/verify").json()
    assert check["valid"] is False
    assert check["first_invalid_trade_id"] == victim


@pytest.mark.parametrize("n_hours", [0, 3])
def test_api_ledger_valid_from_the_start(client, n_hours):
    for _ in range(n_hours):
        client.post("/match")
        client.post("/simulate/tick")
    assert client.get("/ledger/verify").json()["valid"] is True
