"""Tests for the IndexVolEngine module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from index_vol_engine import IndexVolEngine


# ------------------------------------------------------------------
# Mock data (mirrors demo_data vol surface / regime structures)
# ------------------------------------------------------------------

MOCK_VOL_DATA = {
    'symbol': 'SPY',
    'term_structure': {
        'shape': 'contango',
        'expirations': ['2026-03-20', '2026-04-17'],
        'atm_ivs': [0.16, 0.18],
        'distortion_detected': False,
        'signal': 'Contango — normal term structure',
    },
    'skew': {
        'put_skew_iv': 0.20,
        'call_skew_iv': 0.14,
        'skew_spread': 0.06,
        'signal': 'Normal skew',
    },
    'forward_vol': {
        'spot_vol': 0.16,
        'forward_vol': 0.20,
        'ratio': 1.25,
        'signal': 'Forward vol elevated',
    },
    'sector_iv_comparison': {
        'symbol_iv': 0.16,
        'sector_etf': 'SPY',
        'sector_iv': 0.16,
        'iv_premium': 1.0,
        'signal': 'Symbol IV in line with sector',
    },
    'skew_percentile': {
        'current_skew': -0.10,
        'percentile': 45.0,
        'signal': 'Skew within normal range',
    },
}

MOCK_REGIME_FAVORABLE = {
    'vol_regime': 'compressed',
    'correlation_regime': 'medium',
    'risk_appetite': 'risk_on',
    'details': {
        'volatility': {'regime': 'compressed', 'vix_current': 14.5,
                       'vix_percentile': 22.0, 'vix_sma_20': 15.2},
        'correlation': {'regime': 'medium', 'avg_correlation': 0.42,
                        'sector_count': 9},
        'gamma_exposure': {'gamma_direction': 'positive',
                           'put_call_oi_ratio': 0.72, 'total_oi': 12500000},
        'macro_proximity': {'elevated': False, 'signals': []},
    },
    'timestamp': '2026-02-14T16:45:00',
}

MOCK_REGIME_STRESSED = {
    'vol_regime': 'stressed',
    'correlation_regime': 'high',
    'risk_appetite': 'risk_off',
    'details': {
        'volatility': {'regime': 'stressed', 'vix_current': 32.0,
                       'vix_percentile': 88.0, 'vix_sma_20': 28.5},
        'correlation': {'regime': 'high', 'avg_correlation': 0.72,
                        'sector_count': 9},
        'gamma_exposure': {'gamma_direction': 'negative',
                           'put_call_oi_ratio': 1.35, 'total_oi': 15000000},
        'macro_proximity': {'elevated': True,
                            'signals': ['TLT volatility spike']},
    },
    'timestamp': '2026-02-14T16:45:00',
}


# ------------------------------------------------------------------
# Component scoring tests
# ------------------------------------------------------------------

class TestComponentScoring:
    def setup_method(self):
        self.engine = IndexVolEngine()

    def test_score_components_returns_all_keys(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        expected_keys = {
            'iv_rv_spread', 'term_structure', 'skew_dislocation',
            'dealer_gamma', 'event_proximity',
        }
        assert set(components.keys()) == expected_keys

    def test_all_scores_between_0_and_1(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        for key, val in components.items():
            assert 0.0 <= val <= 1.0, f'{key} out of range: {val}'

    def test_contango_term_structure_score_high(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        assert components['term_structure'] >= 0.70

    def test_backwardation_term_structure_score_low(self):
        vol_data = {**MOCK_VOL_DATA, 'term_structure': {
            'shape': 'backwardation', 'distortion_detected': False,
        }}
        components = self.engine._score_components(vol_data, MOCK_REGIME_FAVORABLE)
        assert components['term_structure'] <= 0.30

    def test_positive_gamma_high_score(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        assert components['dealer_gamma'] >= 0.75

    def test_negative_gamma_low_score(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_STRESSED)
        assert components['dealer_gamma'] <= 0.25

    def test_event_proximity_safe_high(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        assert components['event_proximity'] >= 0.70

    def test_event_proximity_elevated_low(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_STRESSED)
        assert components['event_proximity'] <= 0.20

    def test_iv_rv_spread_rich(self):
        """When forward/spot ratio > 1.15, score should be above neutral."""
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        assert components['iv_rv_spread'] > 0.5


# ------------------------------------------------------------------
# Composite edge tests
# ------------------------------------------------------------------

class TestCompositeEdge:
    def setup_method(self):
        self.engine = IndexVolEngine()

    def test_favorable_regime_edge_above_threshold(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        edge = self.engine._composite_edge(components)
        assert edge >= self.engine.EDGE_PASS_THRESHOLD

    def test_stressed_regime_edge_below_threshold(self):
        """Stressed regime + unfavorable vol data should produce low edge."""
        stressed_vol = {
            **MOCK_VOL_DATA,
            'term_structure': {'shape': 'backwardation', 'distortion_detected': False},
            'forward_vol': {'spot_vol': 0.30, 'forward_vol': 0.25, 'ratio': 0.83,
                            'signal': 'Forward vol depressed'},
            'skew': {'skew_spread': -0.05, 'signal': 'Inverted skew'},
            'skew_percentile': {'percentile': 15.0},
        }
        components = self.engine._score_components(stressed_vol, MOCK_REGIME_STRESSED)
        edge = self.engine._composite_edge(components)
        assert edge < self.engine.EDGE_PASS_THRESHOLD

    def test_edge_between_0_and_1(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        edge = self.engine._composite_edge(components)
        assert 0.0 <= edge <= 1.0


# ------------------------------------------------------------------
# Gate evaluation tests
# ------------------------------------------------------------------

class TestGateEvaluation:
    def setup_method(self):
        self.engine = IndexVolEngine()

    def test_favorable_passes(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_FAVORABLE)
        edge = self.engine._composite_edge(components)
        trade_gate = {'allowed': True, 'reasons': []}
        gate = self.engine._evaluate_gate(edge, trade_gate, components)
        assert gate['passed'] is True
        assert gate['reasons'] == []

    def test_stressed_fails(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_STRESSED)
        edge = self.engine._composite_edge(components)
        trade_gate = {'allowed': False, 'reasons': ['Volatility regime is stressed']}
        gate = self.engine._evaluate_gate(edge, trade_gate, components)
        assert gate['passed'] is False
        assert len(gate['reasons']) > 0

    def test_low_edge_fails_even_if_regime_allows(self):
        components = {
            'iv_rv_spread': 0.1,
            'term_structure': 0.1,
            'skew_dislocation': 0.1,
            'dealer_gamma': 0.5,
            'event_proximity': 0.75,
        }
        edge = self.engine._composite_edge(components)
        trade_gate = {'allowed': True, 'reasons': []}
        gate = self.engine._evaluate_gate(edge, trade_gate, components)
        assert gate['passed'] is False
        assert any('Edge score' in r for r in gate['reasons'])


# ------------------------------------------------------------------
# Edge-to-confidence mapping
# ------------------------------------------------------------------

class TestEdgeToConfidence:
    def test_zero_edge(self):
        assert IndexVolEngine._edge_to_confidence(0.0) == 1.0

    def test_full_edge(self):
        assert IndexVolEngine._edge_to_confidence(1.0) == 5.0

    def test_mid_edge(self):
        assert IndexVolEngine._edge_to_confidence(0.5) == 3.0

    def test_below_zero_clamps(self):
        assert IndexVolEngine._edge_to_confidence(-0.5) == 1.0

    def test_above_one_clamps(self):
        assert IndexVolEngine._edge_to_confidence(1.5) == 5.0

    def test_quarter_edge(self):
        assert IndexVolEngine._edge_to_confidence(0.25) == 2.0


# ------------------------------------------------------------------
# Spread params builder
# ------------------------------------------------------------------

class TestBuildSpreadParams:
    def setup_method(self):
        self.engine = IndexVolEngine()

    def test_returns_required_keys(self):
        analysis = {
            'components': {},
            'regime_snapshot': {'details': {'volatility': {}}},
        }
        params = self.engine._build_spread_params('SPY', analysis)
        required = {'strategy', 'expiry', 'strikes', 'wing_width',
                    'credit', 'max_loss', 'pop_estimate',
                    'estimated_delta', 'estimated_vega', 'estimated_gamma'}
        assert required.issubset(set(params.keys()))

    def test_strategy_is_credit_spread(self):
        analysis = {
            'components': {},
            'regime_snapshot': {'details': {'volatility': {}}},
        }
        params = self.engine._build_spread_params('SPY', analysis)
        assert 'credit spread' in params['strategy'].lower()
