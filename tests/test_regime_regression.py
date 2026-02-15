"""Regression tests for regime classification given fixed data.

These tests use deterministic inputs to ensure that regime labels
remain stable as the codebase evolves.  They do NOT depend on live
market data — instead they exercise ``_determine_risk_appetite``
and ``should_trade`` with pre-built sub-signal dicts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from datetime import datetime, timedelta

import pytest
from regime_classifier import RegimeClassifier


@pytest.fixture
def classifier():
    return RegimeClassifier()


# ------------------------------------------------------------------
# Risk-appetite determination regression
# ------------------------------------------------------------------

class TestRiskAppetiteRegression:
    """Deterministic inputs → deterministic risk-appetite label."""

    def test_risk_off_when_stressed_high_corr_negative_gamma_macro(self, classifier):
        vol = {'regime': 'stressed'}
        corr = {'regime': 'high'}
        gamma = {'gamma_direction': 'negative'}
        macro = {'elevated': True}
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'risk_off'

    def test_risk_on_when_compressed_low_corr_positive_gamma(self, classifier):
        vol = {'regime': 'compressed'}
        corr = {'regime': 'low'}
        gamma = {'gamma_direction': 'positive'}
        macro = {'elevated': False}
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'risk_on'

    def test_neutral_when_expanding_medium_corr_neutral_gamma(self, classifier):
        vol = {'regime': 'expanding'}
        corr = {'regime': 'medium'}
        gamma = {'gamma_direction': 'neutral'}
        macro = {'elevated': False}
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'neutral'

    def test_risk_off_stressed_only(self, classifier):
        """Stressed vol alone contributes 2 risk-off signals."""
        vol = {'regime': 'stressed'}
        corr = {'regime': 'medium'}
        gamma = {'gamma_direction': 'neutral'}
        macro = {'elevated': True}
        # 2 (stressed) + 1 (macro) = 3 → risk_off
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'risk_off'

    def test_risk_on_compressed_low_no_gamma(self, classifier):
        """Compressed + low correlation = 3 risk-on → risk_on."""
        vol = {'regime': 'compressed'}
        corr = {'regime': 'low'}
        gamma = {'gamma_direction': 'positive'}
        macro = {'elevated': False}
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'risk_on'

    def test_neutral_when_mixed_signals(self, classifier):
        vol = {'regime': 'compressed'}  # +2 risk_on
        corr = {'regime': 'high'}        # +1 risk_off
        gamma = {'gamma_direction': 'negative'}  # +1 risk_off
        macro = {'elevated': False}
        # risk_on=2, risk_off=2 → neither ≥ 3 → neutral
        assert classifier._determine_risk_appetite(vol, corr, gamma, macro) == 'neutral'


# ------------------------------------------------------------------
# should_trade regression
# ------------------------------------------------------------------

class TestShouldTradeRegression:
    """Deterministic classification → deterministic trade gate."""

    def test_allowed_compressed_no_macro(self, classifier):
        classification = {
            'vol_regime': 'compressed',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is True
        assert result['reasons'] == []

    def test_blocked_stressed(self, classifier):
        classification = {
            'vol_regime': 'stressed',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert any('stressed' in r.lower() for r in result['reasons'])

    def test_blocked_macro_elevated(self, classifier):
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': True},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert any('macro' in r.lower() for r in result['reasons'])

    def test_blocked_both_stressed_and_macro(self, classifier):
        classification = {
            'vol_regime': 'stressed',
            'details': {
                'macro_proximity': {'elevated': True},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert len(result['reasons']) == 2


# ------------------------------------------------------------------
# SPY-specific gating (v1) regression
# ------------------------------------------------------------------

class TestSPYGatingRegression:
    """Deterministic classification → SPY-specific gate checks."""

    def test_vix_spike_blocks_trade(self, classifier):
        """VIX day-over-day >10% should block."""
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
                'volatility': {
                    'vix_current': 22.0,
                    'vix_prev_close': 19.0,
                    'vix_change_pct': 15.79,
                },
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert any('VIX spike' in r for r in result['reasons'])

    def test_vix_spike_below_threshold_passes(self, classifier):
        """VIX change under 10% should not trigger spike block."""
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
                'volatility': {
                    'vix_current': 20.0,
                    'vix_prev_close': 19.0,
                    'vix_change_pct': 5.26,
                },
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is True

    def test_vix_hard_ceiling_blocks_trade(self, classifier):
        """VIX above 35 hard ceiling should block."""
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
                'volatility': {
                    'vix_current': 38.5,
                    'vix_prev_close': 34.0,
                    'vix_change_pct': 5.0,
                },
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert any('ceiling' in r.lower() for r in result['reasons'])

    def test_vix_below_ceiling_passes(self, classifier):
        """VIX under the ceiling should not trigger block."""
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
                'volatility': {
                    'vix_current': 28.0,
                    'vix_prev_close': 27.0,
                    'vix_change_pct': 3.7,
                },
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is True

    def test_macro_event_within_48h_blocks(self, classifier):
        """A scheduled macro event within 48 h should block."""
        future = (datetime.now() + timedelta(hours=12)).isoformat()
        classifier.MACRO_EVENT_CALENDAR = [(future, 'FOMC')]

        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        assert any('FOMC' in r for r in result['reasons'])

    def test_macro_event_beyond_48h_passes(self, classifier):
        """A macro event more than 48 h out should not block."""
        future = (datetime.now() + timedelta(hours=72)).isoformat()
        classifier.MACRO_EVENT_CALENDAR = [(future, 'CPI')]

        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is True

    def test_output_has_pass_trade_and_reasons(self, classifier):
        """should_trade must always return pass_trade (bool) and reasons (list)."""
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert 'pass_trade' in result
        assert isinstance(result['pass_trade'], bool)
        assert 'reasons' in result
        assert isinstance(result['reasons'], list)

    def test_multiple_spy_blocks_accumulate_reasons(self, classifier):
        """Multiple SPY blocks should all appear in reasons."""
        future = (datetime.now() + timedelta(hours=6)).isoformat()
        classifier.MACRO_EVENT_CALENDAR = [(future, 'NFP')]

        classification = {
            'vol_regime': 'stressed',
            'details': {
                'macro_proximity': {'elevated': True},
                'volatility': {
                    'vix_current': 40.0,
                    'vix_prev_close': 30.0,
                    'vix_change_pct': 33.33,
                },
            },
        }
        result = classifier.should_trade(classification)
        assert result['pass_trade'] is False
        # stressed + macro elevated + VIX spike + VIX ceiling + macro calendar = 5
        assert len(result['reasons']) >= 5
