from typing import List, Tuple

from backend.simulation.models import Household

from .models import MarketState, Trade
from .pricing import clearing_price


class MarketEngine:
    """Runs one matching cycle per call: filter sellers/buyers, pair them index-aligned, price the cycle once."""

    def __init__(self):
        self.trades: List[Trade] = []
        self._next_trade_id = 1

    def run_cycle(self, households: List[Household], hour: int) -> Tuple[MarketState, List[Trade]]:
        sellers = sorted((h for h in households if h.net_kwh > 0), key=lambda h: h.id)
        buyers = sorted((h for h in households if h.net_kwh < 0), key=lambda h: h.net_kwh)

        total_supply = round(sum(h.net_kwh for h in sellers), 3)
        total_demand = round(sum(-h.net_kwh for h in buyers), 3)
        price = clearing_price(total_demand, total_supply)

        new_trades: List[Trade] = []
        if price is not None:
            for seller, buyer in zip(sellers, buyers):
                amount = round(min(seller.net_kwh, -buyer.net_kwh), 3)
                if amount <= 0:
                    continue
                trade = Trade(
                    id=self._next_trade_id,
                    seller_id=seller.id,
                    buyer_id=buyer.id,
                    amount_kwh=amount,
                    price_per_kwh=price,
                    timestamp=hour,
                )
                new_trades.append(trade)
                self._next_trade_id += 1

        self.trades.extend(new_trades)

        state = MarketState(
            timestamp=hour,
            total_supply_kwh=total_supply,
            total_demand_kwh=total_demand,
            clearing_price=price,
        )
        return state, new_trades
