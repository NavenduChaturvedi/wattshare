import json

import pytest

from backend.config import DEFAULT_CONFIG_PATH, load_config
from backend.market.engine import MarketEngine
from backend.simulation.battery import ROUND_TRIP_EFFICIENCY, BatterySpec, apply_flow, decide_flow
from backend.simulation.engine import SimulationEngine

from .api_helpers import advance, households

SPEC = BatterySpec(capacity_kwh=5.0, max_rate_kw=1.5, threshold_price=8.0)


def flow(gen, cons, stored, price, releasing=False):
    return decide_flow(gen, cons, stored, SPEC, price, releasing)


# --- policy ------------------------------------------------------------------


def test_cheap_hour_with_surplus_charges_up_to_rate():
    assert flow(gen=4.0, cons=1.0, stored=0.0, price=6.5) == (1.5, False)
    assert flow(gen=1.8, cons=1.0, stored=0.0, price=6.5) == (pytest.approx(0.8), False)


def test_charging_stops_at_capacity():
    room = (5.0 - 4.55) / ROUND_TRIP_EFFICIENCY
    assert flow(gen=4.0, cons=1.0, stored=4.55, price=6.5)[0] == pytest.approx(room, abs=1e-3)
    assert flow(gen=4.0, cons=1.0, stored=5.0, price=6.5) == (0.0, False)


def test_expensive_hour_starts_releasing():
    assert flow(gen=0.0, cons=1.0, stored=5.0, price=9.0) == (-1.5, True)


def test_no_local_supply_counts_as_expensive():
    assert flow(gen=0.0, cons=1.0, stored=5.0, price=None) == (-1.5, True)


def test_cheap_hour_without_sun_holds_charge():
    assert flow(gen=0.0, cons=1.0, stored=5.0, price=7.0) == (0.0, False)


def test_hysteresis_keeps_releasing_after_its_own_sales_pull_the_price_down():
    assert flow(gen=0.0, cons=1.0, stored=3.5, price=7.0, releasing=True) == (-1.5, True)


def test_releasing_ends_when_empty_or_sun_returns():
    assert flow(gen=0.0, cons=1.0, stored=0.0, price=7.0, releasing=True) == (0.0, False)
    assert flow(gen=3.0, cons=1.0, stored=2.0, price=6.5, releasing=True) == (1.5, False)


def test_last_partial_discharge():
    assert flow(gen=0.0, cons=1.0, stored=0.4, price=None) == (-0.4, True)


def test_state_of_charge_accounting():
    assert apply_flow(0.0, 1.5, SPEC) == pytest.approx(1.5 * ROUND_TRIP_EFFICIENCY)
    assert apply_flow(3.0, -1.5, SPEC) == pytest.approx(1.5)
    assert apply_flow(4.9, 1.5, SPEC) == 5.0  # never above capacity
    assert apply_flow(0.2, -1.5, SPEC) == 0.0  # never below empty


# --- in the simulation ---------------------------------------------------------


def config_with(tmp_path, **overrides):
    data = json.loads(DEFAULT_CONFIG_PATH.read_text())
    data.update(overrides)
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(data))
    return load_config(path)


def simulate_day2(cfg):
    """Hour-by-hour (state, households snapshot) for the second simulated day, dispatching each hour."""
    sim, market = SimulationEngine(seed=42, config=cfg), MarketEngine()
    day2 = []
    for tick in range(48):
        state, _ = market.run_cycle(sim.households, sim.current_hour, transformer_capacity_kw=sim.transformer_capacity_kw)
        sim.observe_price(state.clearing_price)
        if tick >= 24:
            day2.append((state, [(h.id, h.battery_flow_kwh, h.battery_stored_kwh) for h in sim.households]))
        sim.tick()
    return sim, day2


def test_default_demo_gives_batteries_to_the_biggest_arrays(tmp_path):
    sim = SimulationEngine(seed=1, config=config_with(tmp_path))
    assert sorted(h.id for h in sim.households if h.battery_capacity_kwh > 0) == ["H01", "H06"]


def test_no_batteries_when_share_is_zero(tmp_path):
    sim = SimulationEngine(seed=1, config=config_with(tmp_path, battery_share=0))
    assert all(h.battery_capacity_kwh == 0 for h in sim.households)


def test_batteries_charge_at_midday_and_release_in_the_evening(tmp_path):
    _, day2 = simulate_day2(config_with(tmp_path))
    by_hour = {state.timestamp: snap for state, snap in day2}
    charging = {h: sum(f for _, f, _ in by_hour[h] if f > 0) for h in range(24)}
    discharging = {h: sum(-f for _, f, _ in by_hour[h] if f < 0) for h in range(24)}
    assert sum(charging[h] for h in range(8, 14)) > 5
    assert sum(discharging[h] for h in range(16, 22)) > 5
    assert sum(charging[h] for h in range(18, 24)) == 0  # no charging after dark


def test_batteries_bring_local_supply_to_evenings_that_had_none(tmp_path):
    _, without = simulate_day2(config_with(tmp_path, battery_share=0))
    _, with_ = simulate_day2(config_with(tmp_path))
    priced = lambda day: sum(s.clearing_price is not None for s, _ in day)
    assert priced(with_) > priced(without)
    evening = lambda day: sum(abs(s.transformer_load_kw) for s, _ in day if 17 <= s.timestamp <= 19)
    assert evening(with_) < evening(without) / 2


def test_api_exposes_battery_state(client):
    advance(client, 11)  # through the morning, with dispatch
    hh = households(client)
    batt = [h for h in hh.values() if h["battery_capacity_kwh"] > 0]
    assert len(batt) == 2
    assert all(h["battery_stored_kwh"] > 0 for h in batt)  # charged from the morning sun
    for h in hh.values():
        gen_minus_cons = h["current_generation_kwh"] - h["current_consumption_kwh"]
        assert h["net_kwh"] == pytest.approx(gen_minus_cons - h["battery_flow_kwh"], abs=1e-3)
