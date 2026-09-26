import pytest

from backend.marketplace.stats import TICKS_PER_DAY, compute_seller_stats

from .factories import dispatcher_trade, listing_trade


def test_today_week_and_lifetime_buckets():
    now = 10 * TICKS_PER_DAY + 5  # day 10, hour 5
    trades = [
        listing_trade(tick=now - 1, amount=1.0, price=6.0),  # today: Rs 6
        listing_trade(tick=now - 24, amount=2.0, price=5.0),  # yesterday, still this week: Rs 10
        listing_trade(tick=now - 200, amount=1.0, price=8.0),  # older than a week: Rs 8
    ]
    stats = compute_seller_stats("S1", trades, current_tick=now)
    assert stats.earnings_today == pytest.approx(6.0)
    assert stats.earnings_week == pytest.approx(16.0)
    assert stats.earnings_lifetime == pytest.approx(24.0)
    assert stats.total_kwh_sold_lifetime == pytest.approx(4.0)


def test_today_is_the_calendar_day_not_the_last_24_ticks():
    now = 3 * TICKS_PER_DAY + 1  # 01:00 on day 3
    trades = [listing_trade(tick=now - 2)]  # 23:00 on day 2
    assert compute_seller_stats("S1", trades, current_tick=now).earnings_today == 0.0


def test_trades_without_tick_count_only_toward_lifetime():
    trades = [dispatcher_trade("S1", amount=2.0, price=7.0, tick=None)]
    stats = compute_seller_stats("S1", trades, current_tick=5)
    assert stats.earnings_today == 0.0
    assert stats.earnings_week == 0.0
    assert stats.earnings_lifetime == pytest.approx(14.0)
    assert stats.total_kwh_sold_lifetime == pytest.approx(2.0)


def test_other_sellers_trades_are_excluded():
    stats = compute_seller_stats("S1", [listing_trade(seller="S2", tick=0)], current_tick=0)
    assert stats.earnings_lifetime == 0.0
