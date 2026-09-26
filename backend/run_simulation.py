import argparse

from backend.display import add_common_args, build_engine, print_household_snapshot, print_provenance, wait_for_step

HOURS_PER_DAY = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WattShare Phase 1: household simulation")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible household data (default: random each run)",
    )
    add_common_args(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = build_engine(args)
    solar_count = sum(h.has_solar for h in engine.households)

    print("WattShare -- Phase 1: Household Simulation")
    print(f"{len(engine.households)} households ({solar_count} with solar, {len(engine.households) - solar_count} without)")
    print_provenance(engine)
    if args.seed is not None:
        print(f"(seed={args.seed})")

    print_household_snapshot(engine)
    for _ in range(HOURS_PER_DAY - 1):
        wait_for_step(args)
        engine.tick()
        print_household_snapshot(engine)


if __name__ == "__main__":
    main()
