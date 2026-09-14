from typing import List

from backend.market.models import Trade

from .models import SellerStats
from .reliability import compute_reliability_score

TICKS_PER_DAY = 24
TICKS_PER_WEEK = 7 * 24


def compute_seller_stats(seller_id: str, trades: List[Trade], current_tick: int) -> SellerStats:
    """Earnings/volume count every trade the seller was ever part of (a seller
    doesn't care which mechanism matched them); reliability only looks at
    listing-based trades (see reliability.py). Trades with no absolute `tick`
    (the original dispatcher-cycle trades, predating this revision) count toward
    lifetime totals but can't be placed into today/this-week buckets.
    """
    seller_trades = [t for t in trades if t.seller_id == seller_id]
    current_day = current_tick // TICKS_PER_DAY

    def value(t: Trade) -> float:
        return t.amount_kwh * t.price_per_kwh

    earnings_today = sum(
        value(t) for t in seller_trades if t.tick is not None and t.tick // TICKS_PER_DAY == current_day
    )
    earnings_week = sum(
        value(t) for t in seller_trades if t.tick is not None and current_tick - t.tick < TICKS_PER_WEEK
    )

    return SellerStats(
        seller_household_id=seller_id,
        reliability_score=compute_reliability_score(seller_id, trades, current_tick),
        total_kwh_sold_lifetime=round(sum(t.amount_kwh for t in seller_trades), 3),
        earnings_today=round(earnings_today, 2),
        earnings_week=round(earnings_week, 2),
        earnings_lifetime=round(sum(value(t) for t in seller_trades), 2),
    )
