from backend.simulation.engine import SimulationEngine


def print_household_snapshot(engine: SimulationEngine) -> None:
    print(f"\n=== Hour {engine.current_hour:02d}:00 ===")
    header = f"{'ID':<5}{'Name':<16}{'Solar':<7}{'Gen(kWh)':>10}{'Cons(kWh)':>11}{'Net(kWh)':>10}"
    print(header)
    print("-" * len(header))

    total_gen = total_cons = 0.0
    for h in engine.households:
        print(
            f"{h.id:<5}{h.name:<16}{'Yes' if h.has_solar else 'No':<7}"
            f"{h.current_generation_kwh:>10.2f}{h.current_consumption_kwh:>11.2f}{h.net_kwh:>10.2f}"
        )
        total_gen += h.current_generation_kwh
        total_cons += h.current_consumption_kwh

    print("-" * len(header))
    print(f"{'TOTAL':<28}{total_gen:>10.2f}{total_cons:>11.2f}{(total_gen - total_cons):>10.2f}")
