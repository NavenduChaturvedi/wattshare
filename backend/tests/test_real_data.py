import json
import random
import urllib.request
from datetime import date

import pytest
from pydantic import ValidationError

from backend.config import DEFAULT_CONFIG_PATH, load_config
from backend.data.load import SIZE_CLASSES, hourly_profile, season_for
from backend.data.solar import (
    CACHE_DIR,
    PERFORMANCE_RATIO,
    IrradianceUnavailable,
    generation_kwh,
    hourly_irradiance,
)
from backend.simulation.engine import SimulationEngine
from backend.simulation.households import generate_households

LUCKNOW = (26.85, 80.95)
CLEAR_DAY = date(2019, 5, 29)
FIXTURE_DAYS = [CLEAR_DAY, date(2019, 7, 11), date(2019, 12, 22)]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Everything here must run from committed data."""

    def refuse(*args, **kwargs):
        raise OSError("network disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    for var in ("WATTSHARE_CONFIG", "WATTSHARE_SEED", "WATTSHARE_DATA_SOURCE", "WATTSHARE_SIM_DATE"):
        monkeypatch.delenv(var, raising=False)


# --- config ---------------------------------------------------------------


def test_default_config_loads():
    cfg = load_config()
    assert cfg.location.name == "Lucknow"
    assert cfg.data_source == "real"
    assert cfg.households == "demo"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("WATTSHARE_SEED", "7")
    monkeypatch.setenv("WATTSHARE_DATA_SOURCE", "synthetic")
    monkeypatch.setenv("WATTSHARE_SIM_DATE", "2019-12-22")
    cfg = load_config()
    assert (cfg.seed, cfg.data_source, cfg.sim_date) == (7, "synthetic", date(2019, 12, 22))


def test_invalid_config_is_rejected(tmp_path):
    data = json.loads(DEFAULT_CONFIG_PATH.read_text())
    data["solar_ratio"] = 1.5
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        load_config(path)


# --- solar ----------------------------------------------------------------


@pytest.mark.parametrize("day", FIXTURE_DAYS)
def test_fixture_days_are_committed_and_parse(day):
    assert (CACHE_DIR / f"{LUCKNOW[0]:.2f}_{LUCKNOW[1]:.2f}_{day.isoformat()}.json").exists()
    values = hourly_irradiance(*LUCKNOW, day)
    assert len(values) == 24
    assert all(v >= 0 for v in values)


def test_irradiance_is_zero_at_night_and_peaks_near_solar_noon():
    values = hourly_irradiance(*LUCKNOW, CLEAR_DAY)
    assert all(values[h] == 0 for h in (0, 1, 2, 3, 20, 21, 22, 23))
    assert values.index(max(values)) in (11, 12)  # solar noon in Lucknow is ~12:05 IST
    assert max(values) > 800  # a clear pre-monsoon day


def test_uncached_day_without_network_fails_clearly():
    with pytest.raises(IrradianceUnavailable, match="No cached irradiance"):
        hourly_irradiance(*LUCKNOW, date(2001, 1, 1))


def test_generation_model():
    assert generation_kwh(1000.0, 4.0) == pytest.approx(4.0 * PERFORMANCE_RATIO)
    assert generation_kwh(500.0, 4.0) == pytest.approx(generation_kwh(500.0, 2.0) * 2, abs=1e-3)  # linear in capacity
    assert generation_kwh(0.0, 4.0) == 0.0
    assert generation_kwh(800.0, 0.0) == 0.0


# --- load profiles ----------------------------------------------------------


@pytest.mark.parametrize(
    "month, expected",
    [(1, "winter"), (3, "summer"), (6, "summer"), (7, "monsoon"), (9, "monsoon"), (10, "winter"), (12, "winter")],
)
def test_season_mapping(month, expected):
    assert season_for(date(2019, month, 15)) == expected


@pytest.mark.parametrize("season", ["summer", "monsoon", "winter"])
def test_profiles_exist_and_scale_with_size(season):
    daily = []
    for size in SIZE_CLASSES:
        profile = hourly_profile(season, size)
        assert len(profile) == 24
        assert all(v > 0 for v in profile)
        daily.append(sum(profile))
    assert daily == sorted(daily)  # small < medium < large


def test_summer_load_is_heavier_than_winter():
    assert sum(hourly_profile("summer", "large")) > 2 * sum(hourly_profile("winter", "large"))


# --- generated households ---------------------------------------------------


@pytest.mark.parametrize("n, ratio", [(10, 0.4), (25, 0.3), (3, 0.5), (50, 0.2)])
def test_generated_neighborhood_shape(n, ratio):
    hh = generate_households(n, ratio, random.Random(1))
    assert len(hh) == n
    assert len({h.id for h in hh}) == n
    assert sum(h.has_solar for h in hh) == max(1, round(n * ratio))
    for zone in {h.zone_id for h in hh}:
        assert any(h.has_solar for h in hh if h.zone_id == zone), f"{zone} has no seller"
    assert all(2.0 <= h.capacity_kw <= 5.0 for h in hh if h.has_solar)


def test_generation_is_deterministic_per_seed():
    a = generate_households(12, 0.4, random.Random(5))
    b = generate_households(12, 0.4, random.Random(5))
    assert a == b


# --- simulation engine ------------------------------------------------------


def run_day(engine):
    days = []
    for _ in range(24):
        days.append([(h.current_generation_kwh, h.current_consumption_kwh) for h in engine.households])
        engine.tick()
    return days


def test_real_day_has_no_solar_at_night_and_surplus_at_noon():
    engine = SimulationEngine(seed=1, config=load_config())
    day = run_day(engine)
    assert sum(g for g, _ in day[22]) == 0
    assert sum(g for g, _ in day[11]) > sum(c for _, c in day[11])
    assert all(c > 0 for hour in day for _, c in hour)


def test_real_day_replays_after_midnight():
    engine = SimulationEngine(seed=1, config=load_config())
    first_day_gen = [sum(g for g, _ in hour) for hour in run_day(engine)]
    second_day_gen = [sum(g for g, _ in hour) for hour in run_day(engine)]
    assert first_day_gen == second_day_gen  # same weather; only load noise differs
    assert engine.total_ticks == 48 and engine.current_hour == 0


def test_same_seed_same_simulation():
    assert run_day(SimulationEngine(seed=3, config=load_config())) == run_day(SimulationEngine(seed=3, config=load_config()))


def test_synthetic_mode_still_works(monkeypatch):
    monkeypatch.setenv("WATTSHARE_DATA_SOURCE", "synthetic")
    day = run_day(SimulationEngine(seed=1, config=load_config()))
    assert sum(g for g, _ in day[12]) > 0 and sum(g for g, _ in day[0]) == 0


def test_generated_households_mode(tmp_path):
    data = json.loads(DEFAULT_CONFIG_PATH.read_text())
    data.update(households="generated", n_households=20, solar_ratio=0.3)
    path = tmp_path / "gen.json"
    path.write_text(json.dumps(data))
    engine = SimulationEngine(seed=2, config=load_config(path))
    assert len(engine.households) == 20
    assert sum(h.has_solar for h in engine.households) == 6
