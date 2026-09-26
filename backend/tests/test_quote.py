import pytest

from backend.marketplace.quote import build_quote

from .api_helpers import households, midday_market
from .factories import household, listing

# --- pure quote logic ---------------------------------------------------------


def test_default_quote_is_the_most_you_can_buy():
    seller = household("S1", gen=4.0, cons=1.0)  # 3 kWh surplus, 2 listed
    q = build_quote(listing(units=2.0), seller, buyer_need_kwh=1.2, requested_kwh=None, current_clearing_price=5.0)
    assert (q.max_kwh, q.amount_kwh, q.total_cost) == (1.2, 1.2, 6.0)
    assert q.stale is False


def test_request_is_capped_by_listing_and_need():
    seller = household("S1", gen=4.0, cons=1.0)
    capped_by_need = build_quote(listing(units=2.0), seller, 0.5, requested_kwh=1.5, current_clearing_price=5.0)
    assert (capped_by_need.requested_kwh, capped_by_need.amount_kwh) == (1.5, 0.5)
    capped_by_listing = build_quote(listing(units=2.0), seller, 9.0, requested_kwh=5.0, current_clearing_price=5.0)
    assert capped_by_listing.amount_kwh == 2.0


def test_smaller_request_is_honoured_and_priced():
    seller = household("S1", gen=4.0, cons=1.0)
    q = build_quote(listing(units=2.0, mode="manual", ask=4.4), seller, 3.0, requested_kwh=0.75, current_clearing_price=9.0)
    assert (q.amount_kwh, q.price_per_kwh, q.total_cost) == (0.75, 4.4, 3.3)


def test_stale_listing_quotes_only_what_the_seller_can_deliver():
    seller = household("S1", gen=1.5, cons=1.0)  # only 0.5 kWh left, listing says 2
    q = build_quote(listing(units=2.0), seller, 3.0, requested_kwh=None, current_clearing_price=5.0)
    assert q.stale is True
    assert (q.advertised_kwh, q.deliverable_kwh, q.max_kwh) == (2.0, 0.5, 0.5)


def test_no_need_quotes_zero():
    seller = household("S1", gen=4.0, cons=1.0)
    q = build_quote(listing(units=2.0), seller, 0.0, requested_kwh=1.0, current_clearing_price=5.0)
    assert (q.max_kwh, q.amount_kwh, q.total_cost) == (0.0, 0.0, 0.0)


# --- through the API -------------------------------------------------------------


def quote(client, listing_id, buyer_id, amount=None):
    params = {"buyer_household_id": buyer_id}
    if amount is not None:
        params["amount_kwh"] = amount
    return client.get(f"/listings/{listing_id}/quote", params=params)


def test_quote_then_buy_gives_exactly_the_quoted_trade(client):
    seller, buyer, lst = midday_market(client)
    amount = round(min(-buyer["open_net_kwh"], lst["units_available_kwh"]) / 2, 3)
    q = quote(client, lst["id"], buyer["id"], amount).json()
    assert q["amount_kwh"] == pytest.approx(amount)

    res = client.post(
        f"/listings/{lst['id']}/buy",
        json={"buyer_household_id": buyer["id"], "amount_kwh": q["amount_kwh"], "max_price_per_kwh": q["price_per_kwh"]},
    )
    assert res.status_code == 200, res.json()
    trade = res.json()["trade"]
    assert trade["amount_kwh"] == pytest.approx(q["amount_kwh"])
    assert trade["price_per_kwh"] == q["price_per_kwh"]
    assert round(trade["amount_kwh"] * trade["price_per_kwh"], 2) == pytest.approx(q["total_cost"])


def test_quote_is_read_only(client):
    _, buyer, lst = midday_market(client)
    before = (client.get("/trades").json(), households(client), client.get("/listings").json())
    for _ in range(3):
        assert quote(client, lst["id"], buyer["id"], 0.2).status_code == 200
    assert (client.get("/trades").json(), households(client), client.get("/listings").json()) == before


def test_default_quote_covers_the_whole_need(client):
    _, buyer, lst = midday_market(client)
    q = quote(client, lst["id"], buyer["id"]).json()
    assert q["max_kwh"] == pytest.approx(min(-buyer["open_net_kwh"], lst["units_available_kwh"]))
    assert q["amount_kwh"] == q["max_kwh"]


def test_price_guard_refuses_and_changes_nothing(client):
    _, buyer, lst = midday_market(client)
    price = quote(client, lst["id"], buyer["id"]).json()["price_per_kwh"]
    before = client.get("/trades").json()
    res = client.post(
        f"/listings/{lst['id']}/buy",
        json={"buyer_household_id": buyer["id"], "amount_kwh": 0.1, "max_price_per_kwh": price - 0.5},
    )
    assert res.status_code == 409
    assert "price moved" in res.json()["detail"].lower()
    assert client.get("/trades").json() == before


def test_quote_validation(client):
    seller, buyer, lst = midday_market(client)
    assert quote(client, 99999, buyer["id"]).status_code == 404
    assert quote(client, lst["id"], "NOPE").status_code == 404
    assert quote(client, lst["id"], seller["id"]).status_code == 400  # own listing
    assert quote(client, lst["id"], buyer["id"], -1).status_code == 400
