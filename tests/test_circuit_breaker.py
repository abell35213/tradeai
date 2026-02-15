"""Tests for the circuit breaker module."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import datetime, timedelta
import pytest
from circuit_breaker import CircuitBreaker


class TestWeeklyDrawdown:
    def test_no_drawdown_allowed(self):
        cb = CircuitBreaker(weekly_drawdown_pct=5.0)
        assert cb.check_weekly_drawdown(0.0) is False

    def test_small_loss_allowed(self):
        cb = CircuitBreaker(weekly_drawdown_pct=5.0)
        assert cb.check_weekly_drawdown(-3.0) is False

    def test_exceeds_threshold_blocked(self):
        cb = CircuitBreaker(weekly_drawdown_pct=5.0)
        assert cb.check_weekly_drawdown(-6.0) is True


class TestVixPercentile:
    def test_normal_allowed(self):
        cb = CircuitBreaker(vix_percentile_limit=80.0)
        assert cb.check_vix_percentile(50.0) is False

    def test_at_limit_blocked(self):
        cb = CircuitBreaker(vix_percentile_limit=80.0)
        assert cb.check_vix_percentile(80.0) is True

    def test_above_limit_blocked(self):
        cb = CircuitBreaker(vix_percentile_limit=80.0)
        assert cb.check_vix_percentile(90.0) is True


class TestVixSpike:
    def test_small_move_allowed(self):
        cb = CircuitBreaker(vix_spike_pct=20.0)
        assert cb.check_vix_spike(5.0) is False

    def test_large_spike_blocked(self):
        cb = CircuitBreaker(vix_spike_pct=20.0)
        assert cb.check_vix_spike(25.0) is True


class TestMacroProximity:
    def test_no_events_allowed(self):
        cb = CircuitBreaker(macro_blackout_days=1)
        assert cb.check_macro_proximity([]) is False

    def test_event_today_blocked(self):
        cb = CircuitBreaker(macro_blackout_days=1)
        today = datetime.now().date().isoformat()
        events = [{'date': today, 'event': 'FOMC'}]
        assert cb.check_macro_proximity(events) is True

    def test_event_tomorrow_blocked(self):
        cb = CircuitBreaker(macro_blackout_days=1)
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        events = [{'date': tomorrow, 'event': 'CPI'}]
        assert cb.check_macro_proximity(events) is True

    def test_event_far_away_allowed(self):
        cb = CircuitBreaker(macro_blackout_days=1)
        far = (datetime.now().date() + timedelta(days=30)).isoformat()
        events = [{'date': far, 'event': 'NFP'}]
        assert cb.check_macro_proximity(events) is False


class TestCheckAll:
    def test_all_clear(self):
        cb = CircuitBreaker()
        result = cb.check_all(
            weekly_pnl_pct=0.0,
            vix_percentile=50.0,
            vix_day_change_pct=2.0,
            calendar_events=[],
        )
        assert result['trading_allowed'] is True
        assert result['reasons'] == []

    def test_multiple_blocks(self):
        cb = CircuitBreaker(weekly_drawdown_pct=3.0, vix_percentile_limit=70.0)
        result = cb.check_all(
            weekly_pnl_pct=-5.0,
            vix_percentile=75.0,
            vix_day_change_pct=1.0,
            calendar_events=[],
        )
        assert result['trading_allowed'] is False
        assert len(result['reasons']) == 2

    def test_regime_stressed_blocks(self):
        cb = CircuitBreaker()
        result = cb.check_all(
            weekly_pnl_pct=0.0,
            vix_percentile=40.0,
            vix_day_change_pct=0.0,
            calendar_events=[],
            regime_label='stressed',
        )
        assert result['trading_allowed'] is False
        assert any('stressed' in r for r in result['reasons'])

    def test_macro_proximity_elevated_blocks(self):
        cb = CircuitBreaker()
        result = cb.check_all(
            weekly_pnl_pct=0.0,
            vix_percentile=40.0,
            vix_day_change_pct=0.0,
            calendar_events=[],
            macro_proximity_elevated=True,
        )
        assert result['trading_allowed'] is False
        assert any('Macro proximity' in r for r in result['reasons'])
