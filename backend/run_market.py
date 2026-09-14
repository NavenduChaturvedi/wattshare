import argparse
from typing import List

from backend.display import print_household_snapshot
from backend.market.engine import MarketEngine
from backend.market.models import MarketState, Trade
from backend.simulation.engine import SimulationEngine

HOURS_PER_DAY = 24


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WattShare Phase 2: matching engine + dynamic pricing")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible household data (default: random each run)",
    )
    return parser.parse_args()


def print_market_state(state: MarketState) -> None:
    if state.clearing_price is None:
        print(f"Market: no sellers available -> no trades this hour (demand={state.total_demand_kwh:.2f} kWh)")
    else:
        print(
            f"Market: supply={state.total_supply_kwh:.2f} kWh, demand={state.total_demand_kwh:.2f} kWh, "
            f"clearing price=Rs {state.clearing_price:.2f}/kWh"
        )


def print_trades(trades: List[Trade]) -> None:
    if not trades:
        print("No trades executed this hour.")
        return
    print(f"{len(trades)} trade(s):")
    for t in trades:
        print(f"  #{t.id:03d}  {t.seller_id} -> {t.buyer_id}   {t.amount_kwh:>5.2f} kWh @ Rs {t.price_per_kwh:.2f}/kWh")


def main() -> None:
    args = parse_args()
    sim = SimulationEngine(seed=args.seed)
    market = MarketEngine()

    solar_count = sum(h.has_solar for h in sim.households)
    print("WattShare -- Phase 2: Matching Engine + Dynamic Pricing")
    print(f"{len(sim.households)} households ({solar_count} with solar, {len(sim.households) - solar_count} without)")
    if args.seed is not None:
        print(f"(seed={args.seed})")

    for hour in range(HOURS_PER_DAY):
        print_household_snapshot(sim)
        state, trades = market.run_cycle(sim.households, sim.current_hour)
        print_market_state(state)
        print_trades(trades)

        if hour < HOURS_PER_DAY - 1:
            sim.tick()

    total_volume = round(sum(t.amount_kwh for t in market.trades), 2)
    total_value = round(sum(t.amount_kwh * t.price_per_kwh for t in market.trades), 2)
    print("\n=== Day Summary ===")
    print(f"Total trades: {len(market.trades)}")
    print(f"Total volume: {total_volume:.2f} kWh")
    print(f"Total value:  Rs {total_value:.2f}")


if __name__ == "__main__":
    main()
