"""Regression tests for regime classification given fixed data.

These tests use deterministic inputs to ensure that regime labels
remain stable as the codebase evolves.  They do NOT depend on live
market data — instead they exercise ``_determine_risk_appetite``
and ``should_trade`` with pre-built sub-signal dicts.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

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
        assert result['allowed'] is True
        assert result['reasons'] == []

    def test_blocked_stressed(self, classifier):
        classification = {
            'vol_regime': 'stressed',
            'details': {
                'macro_proximity': {'elevated': False},
            },
        }
        result = classifier.should_trade(classification)
        assert result['allowed'] is False
        assert any('stressed' in r.lower() for r in result['reasons'])

    def test_blocked_macro_elevated(self, classifier):
        classification = {
            'vol_regime': 'expanding',
            'details': {
                'macro_proximity': {'elevated': True},
            },
        }
        result = classifier.should_trade(classification)
        assert result['allowed'] is False
        assert any('macro' in r.lower() for r in result['reasons'])

    def test_blocked_both_stressed_and_macro(self, classifier):
        classification = {
            'vol_regime': 'stressed',
            'details': {
                'macro_proximity': {'elevated': True},
            },
        }
        result = classifier.should_trade(classification)
        assert result['allowed'] is False
        assert len(result['reasons']) == 2
