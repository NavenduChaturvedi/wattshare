"""Helpers for driving the API in tests (the `client` fixture lives in conftest.py)."""


def open_net(h: dict) -> float:
    return round(h["current_generation_kwh"] - h["current_consumption_kwh"] - h["traded_kwh"], 3)


def households(client) -> dict:
    return {h["id"]: h for h in client.get("/households").json()}


def advance(client, hours: int, match: bool = True) -> None:
    for _ in range(hours):
        assert client.post("/simulate/tick").status_code == 200
        if match:
            assert client.post("/match").status_code == 200


def midday_market(client):
    """Advance to 11:00 without dispatching, so both surplus and deficit are still open."""
    advance(client, 11, match=False)
    hh = households(client)
    seller = max((h for h in hh.values() if h["has_solar"]), key=open_net)
    buyer = min(hh.values(), key=open_net)
    assert open_net(seller) > 0 and open_net(buyer) < 0
    listing = client.post("/listings", json={"seller_household_id": seller["id"], "pricing_mode": "auto"}).json()
    return seller, buyer, listing
