import argparse

from backend.config import load_config
from backend.simulation.engine import SimulationEngine


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=None, help="Path to a config JSON (default: config/default.json)")
    parser.add_argument("--step", action="store_true", help="Pause after each hour; press Enter to advance")


def build_engine(args: argparse.Namespace) -> SimulationEngine:
    return SimulationEngine(seed=args.seed, config=load_config(args.config))


def print_provenance(engine: SimulationEngine) -> None:
    cfg = engine.config
    if cfg.data_source == "real":
        print(f"Real data: {cfg.location.name} on {cfg.sim_date} ({engine.season}) -- Open-Meteo irradiance, CEEW load profiles")
    else:
        print("Synthetic data: made-up solar and load curves")


def wait_for_step(args: argparse.Namespace) -> None:
    if args.step:
        try:
            input("-- Enter for the next hour --")
        except EOFError:  # stdin closed (piped/CI): finish the day without pausing
            args.step = False


def battery_cell(h) -> str:
    if h.battery_capacity_kwh <= 0:
        return "-"
    arrow = "+" if h.battery_flow_kwh > 0 else ("-" if h.battery_flow_kwh < 0 else " ")
    return f"{arrow}{abs(h.battery_flow_kwh):.1f} [{h.battery_stored_kwh:.1f}]"


def print_household_snapshot(engine: SimulationEngine) -> None:
    print(f"\n=== Hour {engine.current_hour:02d}:00 ===")
    header = f"{'ID':<5}{'Name':<16}{'Solar':<7}{'Gen(kWh)':>10}{'Cons(kWh)':>11}{'Batt':>12}{'Net(kWh)':>10}"
    print(header)
    print("-" * len(header))

    total_gen = total_cons = total_net = 0.0
    for h in engine.households:
        print(
            f"{h.id:<5}{h.name:<16}{'Yes' if h.has_solar else 'No':<7}"
            f"{h.current_generation_kwh:>10.2f}{h.current_consumption_kwh:>11.2f}{battery_cell(h):>12}{h.net_kwh:>10.2f}"
        )
        total_gen += h.current_generation_kwh
        total_cons += h.current_consumption_kwh
        total_net += h.net_kwh

    print("-" * len(header))
    print(f"{'TOTAL':<28}{total_gen:>10.2f}{total_cons:>11.2f}{'':>12}{total_net:>10.2f}")
