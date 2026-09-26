"""End-to-end smoke tests through the real FastAPI app, against a throwaway SQLite file."""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WATTSHARE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("WATTSHARE_SEED", "42")
    with TestClient(app) as c:  # the context manager runs the lifespan (DB reset + fresh simulation)
        yield c


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


def test_fresh_start(client):
    hh = households(client)
    assert len(hh) == 10
    assert sum(h["has_solar"] for h in hh.values()) == 4
    assert client.get("/trades").json() == []
    assert client.get("/market-state").json()["clearing_price"] is None


def test_config_reports_data_provenance(client):
    cfg = client.get("/config").json()
    assert cfg["location"] == "Lucknow"
    assert cfg["data_source"] == "real"
    assert cfg["season"] == "summer"
    assert "Open-Meteo" in cfg["solar_source"] and "CEEW" in cfg["load_source"]


def test_tick_then_match_records_state_and_trades(client):
    advance(client, 12)
    state = client.get("/market-state").json()
    assert state["timestamp"] == 12
    assert state["clearing_price"] is not None
    assert len(client.get("/trades").json()) > 0
    summary = client.get("/market/summary").json()
    assert summary["grid_health"] in {"green", "yellow", "red"}
    assert len(summary["price_trend"]) > 0


def test_dispatch_clears_the_short_side_of_the_market(client):
    advance(client, 12, match=False)
    state = client.post("/match").json()["market_state"]
    after = households(client)
    open_supply = sum(max(open_net(h), 0) for h in after.values())
    open_demand = sum(max(-open_net(h), 0) for h in after.values())
    # Whichever side was smaller is fully used up.
    assert min(open_supply, open_demand) == pytest.approx(0, abs=1e-3)
    traded = sum(t["amount_kwh"] for t in client.get("/trades").json())
    assert traded == pytest.approx(min(state["total_supply_kwh"], state["total_demand_kwh"]), abs=1e-3)


def test_no_household_ever_trades_past_its_own_net(client):
    for _ in range(24):
        advance(client, 1)
        client.post("/match")  # a second cycle in the same hour must find nothing left to double-sell
        for h in households(client).values():
            net = round(h["current_generation_kwh"] - h["current_consumption_kwh"], 3)
            assert abs(h["traded_kwh"]) <= abs(net) + 1e-6
            assert h["traded_kwh"] * net >= 0  # sellers only sell, buyers only buy


def test_listing_buy_and_seller_stats(client):
    seller, buyer, listing = midday_market(client)
    assert listing["units_available_kwh"] == pytest.approx(open_net(seller))

    amount = round(min(0.5, -open_net(buyer), listing["units_available_kwh"]), 3)
    res = client.post(f"/listings/{listing['id']}/buy", json={"buyer_household_id": buyer["id"], "amount_kwh": amount})
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["trade"]["amount_kwh"] == pytest.approx(amount)
    assert body["fulfilled_as_listed"] is True

    stats = client.get(f"/sellers/{seller['id']}/stats").json()
    assert stats["total_kwh_sold_lifetime"] == pytest.approx(amount)
    assert stats["earnings_today"] > 0

    # The listing was re-snapshotted with what's left.
    active = {l["seller_household_id"]: l for l in client.get("/listings").json()}
    assert active[seller["id"]]["units_available_kwh"] == pytest.approx(listing["units_available_kwh"] - amount)


def test_buy_is_capped_at_the_buyers_deficit(client):
    _, buyer, listing = midday_market(client)
    need = -open_net(buyer)
    res = client.post(f"/listings/{listing['id']}/buy", json={"buyer_household_id": buyer["id"], "amount_kwh": 999})
    assert res.status_code == 200
    assert res.json()["trade"]["amount_kwh"] <= need + 1e-6


def test_household_in_surplus_cannot_buy(client):
    seller, _, listing = midday_market(client)
    other_seller = next(
        h for h in households(client).values() if h["has_solar"] and h["id"] != seller["id"] and open_net(h) > 0
    )
    res = client.post(f"/listings/{listing['id']}/buy", json={"buyer_household_id": other_seller["id"], "amount_kwh": 1})
    assert res.status_code == 400


def test_smart_match_rejects_more_than_the_buyer_needs(client):
    _, buyer, _ = midday_market(client)
    res = client.post("/match/smart", json={"buyer_household_id": buyer["id"], "desired_kwh": -open_net(buyer) + 5})
    assert res.status_code == 400
    assert "only needs" in res.json()["detail"]


def test_smart_match_buys_cheapest_first(client):
    _, buyer, _ = midday_market(client)
    sellers = [h for h in households(client).values() if h["has_solar"] and open_net(h) > 0]
    assert len(sellers) >= 2
    cheap, pricey = sellers[0], sellers[1]
    client.post("/listings", json={"seller_household_id": pricey["id"], "pricing_mode": "manual", "asking_price_per_kwh": 11})
    client.post("/listings", json={"seller_household_id": cheap["id"], "pricing_mode": "manual", "asking_price_per_kwh": 4.5})

    desired = round(min(-open_net(buyer), open_net(cheap)), 3)
    res = client.post("/match/smart", json={"buyer_household_id": buyer["id"], "desired_kwh": desired})
    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["fully_matched"] is True
    assert [t["seller_id"] for t in body["trades"]] == [cheap["id"]]
    assert body["total_cost"] == pytest.approx(desired * 4.5, abs=0.01)


def test_trade_ids_stay_unique_across_dispatcher_and_marketplace(client):
    _, buyer, listing = midday_market(client)
    client.post(f"/listings/{listing['id']}/buy", json={"buyer_household_id": buyer["id"], "amount_kwh": 0.1})
    advance(client, 3)  # dispatcher cycles after a marketplace trade used to collide on id
    ids = [t["id"] for t in client.get("/trades").json()]
    assert len(ids) == len(set(ids))


def test_validation_errors(client):
    assert client.post("/listings", json={"seller_household_id": "NOPE", "pricing_mode": "auto"}).status_code == 404
    non_solar = next(h for h in households(client).values() if not h["has_solar"])
    assert client.post("/listings", json={"seller_household_id": non_solar["id"], "pricing_mode": "auto"}).status_code == 400
    solar = next(h for h in households(client).values() if h["has_solar"])
    assert client.post("/listings", json={"seller_household_id": solar["id"], "pricing_mode": "manual"}).status_code == 400
    assert client.post("/listings/999/buy", json={"buyer_household_id": "H02", "amount_kwh": 1}).status_code == 404
    assert client.get("/sellers/NOPE/stats").status_code == 404


def test_cors_defaults_to_wildcard(monkeypatch):
    from backend.api.app import cors_origins

    monkeypatch.delenv("WATTSHARE_CORS_ORIGINS", raising=False)
    assert cors_origins() == ["*"]


def test_cors_origins_from_env(monkeypatch):
    from backend.api.app import cors_origins

    monkeypatch.setenv("WATTSHARE_CORS_ORIGINS", "https://wattshare.vercel.app/, http://localhost:3000")
    assert cors_origins() == ["https://wattshare.vercel.app", "http://localhost:3000"]
