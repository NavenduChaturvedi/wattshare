from backend.marketplace.reliability import (
    DEFAULT_RELIABILITY_SCORE,
    MAX_WINDOW_TICKS,
    MAX_WINDOW_TRADES,
    MIN_TRADES_FOR_SCORE,
    compute_reliability_score,
)

from .factories import dispatcher_trade, listing_trade


def test_new_seller_gets_neutral_default():
    assert compute_reliability_score("S1", [], current_tick=0) == DEFAULT_RELIABILITY_SCORE


def test_default_until_enough_history():
    trades = [listing_trade(tick=t, fulfilled=False) for t in range(MIN_TRADES_FOR_SCORE - 1)]
    assert compute_reliability_score("S1", trades, current_tick=10) == DEFAULT_RELIABILITY_SCORE


def test_fulfilment_ratio_once_history_exists():
    trades = [listing_trade(tick=t, fulfilled=t % 5 != 0) for t in range(10)]  # 2 of 10 failed
    assert compute_reliability_score("S1", trades, current_tick=10) == 0.8


def test_only_the_last_20_trades_count():
    old_failures = [listing_trade(tick=t, fulfilled=False) for t in range(10)]
    recent_successes = [listing_trade(tick=10 + t, fulfilled=True) for t in range(MAX_WINDOW_TRADES)]
    assert compute_reliability_score("S1", old_failures + recent_successes, current_tick=40) == 1.0


def test_trades_older_than_7_days_drop_out():
    now = MAX_WINDOW_TICKS + 100
    stale_failures = [listing_trade(tick=t, fulfilled=False) for t in range(10)]
    recent = [listing_trade(tick=now - t, fulfilled=True) for t in range(MIN_TRADES_FOR_SCORE)]
    assert compute_reliability_score("S1", stale_failures + recent, current_tick=now) == 1.0


def test_dispatcher_trades_and_other_sellers_are_ignored():
    trades = [dispatcher_trade("S1", tick=t) for t in range(10)]
    trades += [listing_trade(seller="S2", tick=t, fulfilled=False) for t in range(10)]
    assert compute_reliability_score("S1", trades, current_tick=10) == DEFAULT_RELIABILITY_SCORE
