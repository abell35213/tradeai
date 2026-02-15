"""Tests for the MarketDataProvider interface and RegimeClassifier.should_trade."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from market_data_provider import MarketDataProvider, YFinanceDataProvider
from regime_classifier import RegimeClassifier


# ---------------------------------------------------------------
# MarketDataProvider ABC cannot be instantiated directly
# ---------------------------------------------------------------

class TestMarketDataProviderABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            MarketDataProvider()


# ---------------------------------------------------------------
# YFinanceDataProvider has all required methods
# ---------------------------------------------------------------

class TestYFinanceDataProviderInterface:
    """Verify the concrete class has every required method."""

    def test_has_get_spot(self):
        assert callable(getattr(YFinanceDataProvider, 'get_spot', None))

    def test_has_get_history(self):
        assert callable(getattr(YFinanceDataProvider, 'get_history', None))

    def test_has_get_options_chain(self):
        assert callable(getattr(YFinanceDataProvider, 'get_options_chain', None))

    def test_has_get_vix_history(self):
        assert callable(getattr(YFinanceDataProvider, 'get_vix_history', None))

    def test_has_get_calendar_events(self):
        assert callable(getattr(YFinanceDataProvider, 'get_calendar_events', None))


# ---------------------------------------------------------------
# Calendar events format
# ---------------------------------------------------------------

class TestCalendarEvents:
    def test_returns_list(self):
        provider = YFinanceDataProvider()
        events = provider.get_calendar_events()
        assert isinstance(events, list)

    def test_event_structure(self):
        provider = YFinanceDataProvider()
        events = provider.get_calendar_events()
        for evt in events:
            assert 'date' in evt
            assert 'event' in evt
            assert evt['event'] in ('FOMC', 'CPI', 'NFP')


# ---------------------------------------------------------------
# RegimeClassifier.should_trade
# ---------------------------------------------------------------

class TestRegimeShouldTrade:
    def test_allowed_when_compressed(self):
        rc = RegimeClassifier()
        classification = {
            'vol_regime': 'compressed',
            'details': {'macro_proximity': {'elevated': False}},
        }
        result = rc.should_trade(classification)
        assert result['allowed'] is True

    def test_blocked_when_stressed(self):
        rc = RegimeClassifier()
        classification = {
            'vol_regime': 'stressed',
            'details': {'macro_proximity': {'elevated': False}},
        }
        result = rc.should_trade(classification)
        assert result['allowed'] is False
        assert any('stressed' in r for r in result['reasons'])

    def test_blocked_when_macro_elevated(self):
        rc = RegimeClassifier()
        classification = {
            'vol_regime': 'expanding',
            'details': {'macro_proximity': {'elevated': True}},
        }
        result = rc.should_trade(classification)
        assert result['allowed'] is False
        assert any('Macro' in r for r in result['reasons'])

    def test_blocked_both_stressed_and_macro(self):
        rc = RegimeClassifier()
        classification = {
            'vol_regime': 'stressed',
            'details': {'macro_proximity': {'elevated': True}},
        }
        result = rc.should_trade(classification)
        assert result['allowed'] is False
        assert len(result['reasons']) == 2
