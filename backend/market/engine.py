from typing import List, Mapping, Optional, Tuple

from backend.simulation.models import Household

from .matching import Bid, Offer, match
from .models import MarketState, Trade
from .pricing import clearing_price


class MarketEngine:
    """Runs one matching cycle per call: price the cycle from aggregate supply/demand,
    greedily match sellers to buyers (see matching.match), settle every trade at that price."""

    def __init__(self):
        self.trades: List[Trade] = []
        self._next_trade_id = 1  # display ids for the console CLI; the API uses database ids instead

    def run_cycle(
        self,
        households: List[Household],
        hour: int,
        ask_prices: Optional[Mapping[str, float]] = None,
        transformer_capacity_kw: Optional[float] = None,
    ) -> Tuple[MarketState, List[Trade]]:
        """`ask_prices` maps seller id -> their own asking price (manual listings).
        Sellers without one ask the clearing price. Asks only decide who sells first;
        every trade still settles at the single clearing price."""
        # open_net_kwh, not net_kwh: anything already sold/bought on the marketplace
        # this hour is spoken for and must not be matched again here.
        sellers = [h for h in households if h.open_net_kwh > 0]
        buyers = [h for h in households if h.open_net_kwh < 0]

        total_supply = round(sum(h.open_net_kwh for h in sellers), 3)
        total_demand = round(sum(-h.open_net_kwh for h in buyers), 3)
        # Physical, not open, positions: the transformer carries the neighbourhood's
        # whole imbalance for the hour regardless of who has traded with whom.
        transformer_load = round(-sum(h.net_kwh for h in households), 3)  # kWh over 1 h = average kW
        import_ratio = 0.0
        load_pct = None
        if transformer_capacity_kw:
            import_ratio = max(transformer_load, 0.0) / transformer_capacity_kw
            load_pct = round(abs(transformer_load) / transformer_capacity_kw * 100, 1)
        price = clearing_price(total_demand, total_supply, import_ratio)

        new_trades: List[Trade] = []
        if price is not None:
            asks = ask_prices or {}
            offers = [Offer(h.id, asks.get(h.id, price), h.open_net_kwh) for h in sellers]
            bids = [Bid(h.id, -h.open_net_kwh) for h in buyers]
            for pairing in match(offers, bids):
                new_trades.append(
                    Trade(
                        id=self._next_trade_id,
                        seller_id=pairing.seller_id,
                        buyer_id=pairing.buyer_id,
                        amount_kwh=pairing.amount_kwh,
                        price_per_kwh=price,
                        timestamp=hour,
                    )
                )
                self._next_trade_id += 1

        self.trades.extend(new_trades)

        state = MarketState(
            timestamp=hour,
            total_supply_kwh=total_supply,
            total_demand_kwh=total_demand,
            clearing_price=price,
            transformer_load_kw=transformer_load,
            transformer_load_pct=load_pct,
        )
        return state, new_trades
