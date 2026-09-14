from typing import List

from backend.market.models import Trade

DEFAULT_RELIABILITY_SCORE = 0.85
MIN_TRADES_FOR_SCORE = 5
MAX_WINDOW_TRADES = 20
MAX_WINDOW_TICKS = 7 * 24  # 7 simulated days


def compute_reliability_score(seller_id: str, trades: List[Trade], current_tick: int) -> float:
    """trades_fulfilled_as_listed / total_trades_attempted, over a rolling window of
    at most 20 trades or 7 simulated days (whichever is smaller). Sellers with fewer
    than MIN_TRADES_FOR_SCORE listing-based trades get a neutral default so a new
    seller with zero history isn't shown as unreliable.

    Only trades tied to a listing (listing_id is not None) count as "attempted" --
    a listing is the seller's promise, so only listing-based trades can be judged
    against it. Trades from the original neighborhood-wide dispatcher cycle carry
    no such promise and are excluded.
    """
    attempted = sorted(
        (t for t in trades if t.seller_id == seller_id and t.listing_id is not None and t.tick is not None),
        key=lambda t: t.tick,
    )
    within_window = [t for t in attempted if current_tick - t.tick <= MAX_WINDOW_TICKS]
    windowed = within_window[-MAX_WINDOW_TRADES:]

    if len(windowed) < MIN_TRADES_FOR_SCORE:
        return DEFAULT_RELIABILITY_SCORE

    fulfilled = sum(1 for t in windowed if t.fulfilled_as_listed)
    return round(fulfilled / len(windowed), 3)
