import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.simulation import clock as clock_module
from backend.simulation.clock import LiveClock

IST = timezone(timedelta(hours=5, minutes=30))


class FrozenTime:
    def __init__(self, at: datetime):
        self.now = at

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta):
        self.now += timedelta(**delta)


@pytest.fixture
def frozen(monkeypatch):
    t = FrozenTime(datetime(2026, 9, 26, 15, 20, tzinfo=IST))
    monkeypatch.setattr(clock_module, "utc_now", t)
    return t


# --- the clock itself -----------------------------------------------------------


def test_real_time_follows_the_local_hour(frozen):
    c = LiveClock("Asia/Kolkata")
    assert c.target_ticks() == 15
    assert c.seconds_to_next_hour() == pytest.approx(40 * 60)
    frozen.advance(minutes=39, seconds=59)
    assert c.target_ticks() == 15
    frozen.advance(seconds=1)
    assert c.target_ticks() == 16
    assert c.seconds_to_next_hour() == pytest.approx(3600)


def test_days_keep_counting(frozen):
    c = LiveClock("Asia/Kolkata")
    frozen.advance(days=1, hours=2)
    assert c.target_ticks() == 24 + 17
    assert c.local_time().hour == 17


def test_speed_runs_simulated_hours_faster(frozen):
    c = LiveClock("Asia/Kolkata", speed=60)  # one simulated hour per real minute
    assert c.target_ticks() == 15
    assert c.seconds_to_next_hour() == pytest.approx(40)  # 40 simulated minutes / 60
    frozen.advance(seconds=40)
    assert c.target_ticks() == 16
    frozen.advance(minutes=10)
    assert c.target_ticks() == 26


def test_other_timezones(frozen):
    assert LiveClock("UTC").target_ticks() == 9  # 15:20 IST == 09:50 UTC


def test_speed_must_be_positive():
    with pytest.raises(ValueError):
        LiveClock("Asia/Kolkata", speed=0)


# --- through the API -------------------------------------------------------------


@pytest.fixture
def live_client(tmp_path, monkeypatch, frozen):
    monkeypatch.setenv("WATTSHARE_DB_PATH", str(tmp_path / "live.db"))
    monkeypatch.setenv("WATTSHARE_SEED", "42")
    monkeypatch.setenv("WATTSHARE_CLOCK", "live")
    monkeypatch.delenv("WATTSHARE_CLOCK_SPEED", raising=False)
    with TestClient(app) as c:
        yield c


def test_startup_lands_on_the_current_hour_with_today_replayed(live_client):
    status = live_client.get("/simulation").json()
    assert (status["hour"], status["total_ticks"], status["clock"]) == (15, 15, "live")
    assert status["seconds_to_next_hour"] == pytest.approx(40 * 60)
    assert status["local_time"].startswith("2026-09-26T15:20")

    # 00:00-14:00 were dispatched: the last cleared hour is 14:00, with trades and a price trend.
    assert live_client.get("/market-state").json()["timestamp"] == 14
    assert len(live_client.get("/trades").json()) > 0
    assert len(live_client.get("/market/summary").json()["price_trend"]) > 0
    assert live_client.get("/ledger/verify").json()["valid"] is True


def test_hours_advance_on_their_own(live_client, frozen):
    frozen.advance(hours=2)
    assert live_client.get("/simulation").json()["hour"] == 17
    frozen.advance(hours=8)  # past midnight
    status = live_client.get("/simulation").json()
    assert (status["hour"], status["total_ticks"]) == (1, 25)
    assert live_client.get("/market-state").json()["timestamp"] == 0


def test_any_request_catches_the_clock_up(live_client, frozen):
    frozen.advance(hours=1)
    live_client.get("/households")  # not /simulation
    assert live_client.get("/market-state").json()["timestamp"] == 15


def test_manual_stepping_is_refused_while_live(live_client):
    assert live_client.post("/match").status_code == 409
    assert live_client.post("/simulate/tick").status_code == 409
    assert live_client.get("/simulation").json()["hour"] == 15


def test_concurrent_requests_dispatch_each_hour_once(live_client, frozen):
    frozen.advance(hours=3)
    threads = [threading.Thread(target=live_client.get, args=("/households",)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    trend = live_client.get("/market/summary").json()["price_trend"]
    hours = [p["hour"] for p in trend]
    assert len(hours) == len(set(hours)), f"an hour was dispatched twice: {hours}"
    assert live_client.get("/simulation").json()["total_ticks"] == 18
    assert live_client.get("/ledger/verify").json()["valid"] is True


def test_config_reports_the_clock(live_client):
    cfg = live_client.get("/config").json()
    assert (cfg["clock"], cfg["clock_speed"], cfg["timezone"]) == ("live", 1.0, "Asia/Kolkata")
