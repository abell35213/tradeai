"""Tests for the IndexVolEngine module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from index_vol_engine import IndexVolEngine
from trade_ticket import TradeTicket, Exits


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
        trade_gate = {'pass_trade': True, 'reasons': []}
        gate = self.engine._evaluate_gate(edge, trade_gate, components)
        assert gate['passed'] is True
        assert gate['reasons'] == []

    def test_stressed_fails(self):
        components = self.engine._score_components(MOCK_VOL_DATA, MOCK_REGIME_STRESSED)
        edge = self.engine._composite_edge(components)
        trade_gate = {'pass_trade': False, 'reasons': ['Volatility regime is stressed']}
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
        trade_gate = {'pass_trade': True, 'reasons': []}
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


# ------------------------------------------------------------------
# Iron Condor ticket generation tests
# ------------------------------------------------------------------


def _make_option_df(strikes, bids, asks):
    """Create a minimal option-chain DataFrame for testing."""
    return pd.DataFrame({'strike': strikes, 'bid': bids, 'ask': asks})


def _mock_ticker(current_price, expirations, puts_by_exp, calls_by_exp):
    """Return a mock yfinance Ticker object."""
    ticker = MagicMock()
    ticker.info = {'currentPrice': current_price}
    ticker.options = expirations

    def option_chain(exp):
        chain = MagicMock()
        chain.puts = puts_by_exp.get(exp, pd.DataFrame())
        chain.calls = calls_by_exp.get(exp, pd.DataFrame())
        return chain

    ticker.option_chain = option_chain
    return ticker


class TestIronCondorTickets:
    """Tests for ``generate_iron_condor_tickets`` and its helpers."""

    def setup_method(self):
        self.engine = IndexVolEngine()

    # -- Helper tests ---------------------------------------------------

    def test_estimate_implied_move(self):
        puts = _make_option_df([498, 500, 502], [3.0, 5.0, 7.0], [3.5, 5.5, 7.5])
        calls = _make_option_df([498, 500, 502], [7.0, 5.0, 3.0], [7.5, 5.5, 3.5])
        move = IndexVolEngine._estimate_implied_move(puts, calls, 500.0)
        # ATM put mid=5.25, ATM call mid=5.25, straddle=10.5
        assert move == pytest.approx(10.5, abs=0.01)

    def test_estimate_implied_move_empty(self):
        empty = pd.DataFrame(columns=['strike', 'bid', 'ask'])
        assert IndexVolEngine._estimate_implied_move(empty, empty, 500.0) is None

    def test_nearest_strike(self):
        df = _make_option_df([490, 495, 500, 505, 510], [0]*5, [0]*5)
        strike, idx = IndexVolEngine._nearest_strike(df, 497)
        assert strike == 495.0
        assert df.loc[idx, 'strike'] == 495.0

    def test_nearest_strike_empty(self):
        empty = pd.DataFrame(columns=['strike', 'bid', 'ask'])
        strike, idx = IndexVolEngine._nearest_strike(empty, 500)
        assert strike is None
        assert idx is None

    def test_spread_credit(self):
        df = _make_option_df([490, 495, 500], [1.0, 2.0, 3.0], [1.5, 2.5, 3.5])
        # sell idx=2 (bid=3.0), buy idx=0 (ask=1.5) → credit = 1.5
        credit = IndexVolEngine._spread_credit(df, 2, df, 0)
        assert credit == pytest.approx(1.5)

    def test_spread_credit_negative_clamped(self):
        df = _make_option_df([490, 500], [0.5, 1.0], [2.0, 3.0])
        # sell idx=0 (bid=0.5), buy idx=1 (ask=3.0) → -2.5 → clamped to 0
        credit = IndexVolEngine._spread_credit(df, 0, df, 1)
        assert credit == 0.0

    # -- _build_iron_condor_ticket tests --------------------------------

    def test_build_ticket_returns_trade_ticket(self):
        """A valid chain should produce a TradeTicket."""
        # SPY at 500, implied move ~10 → short strikes ~488 / ~512
        put_strikes = list(range(475, 506))
        call_strikes = list(range(495, 526))
        puts = _make_option_df(
            put_strikes,
            [max(0, 500 - s - 2) * 0.3 for s in put_strikes],
            [max(0.05, 500 - s) * 0.35 for s in put_strikes],
        )
        calls = _make_option_df(
            call_strikes,
            [max(0, s - 500 - 2) * 0.3 for s in call_strikes],
            [max(0.05, s - 500) * 0.35 for s in call_strikes],
        )
        # Ensure ATM options have meaningful bid/ask for straddle calc
        atm_put_idx = puts.index[puts['strike'] == 500].tolist()[0]
        puts.loc[atm_put_idx, 'bid'] = 4.0
        puts.loc[atm_put_idx, 'ask'] = 4.5
        atm_call_idx = calls.index[calls['strike'] == 500].tolist()[0]
        calls.loc[atm_call_idx, 'bid'] = 4.0
        calls.loc[atm_call_idx, 'ask'] = 4.5

        # Set up bid/ask on wings to generate a credit
        for df in [puts, calls]:
            for i in df.index:
                if df.loc[i, 'bid'] < 0.10:
                    df.loc[i, 'bid'] = 0.30
                    df.loc[i, 'ask'] = 0.50

        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker,
            symbol='SPY',
            current_price=500.0,
            expiry='2026-02-23',
            dte=7,
            wing_width=5.0,
            min_credit_pct=0.0,    # accept any credit for this test
            implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is not None
        assert isinstance(ticket, TradeTicket)

    def test_ticket_has_four_legs(self):
        """An iron condor ticket must have exactly 4 legs."""
        puts = _make_option_df(
            list(range(480, 506)),
            [2.0] * 26,
            [2.5] * 26,
        )
        calls = _make_option_df(
            list(range(495, 521)),
            [2.0] * 26,
            [2.5] * 26,
        )
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker,
            symbol='SPY',
            current_price=500.0,
            expiry='2026-02-23',
            dte=7,
            wing_width=5.0,
            min_credit_pct=0.0,
            implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is not None
        assert len(ticket.legs) == 4
        sides = [(l.type, l.side) for l in ticket.legs]
        assert ('put', 'buy') in sides
        assert ('put', 'sell') in sides
        assert ('call', 'sell') in sides
        assert ('call', 'buy') in sides

    def test_ticket_strategy_is_iron_condor(self):
        puts = _make_option_df(list(range(480, 506)), [2.0]*26, [2.5]*26)
        calls = _make_option_df(list(range(495, 521)), [2.0]*26, [2.5]*26)
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker, symbol='SPY', current_price=500.0,
            expiry='2026-02-23', dte=8, wing_width=5.0,
            min_credit_pct=0.0, implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is not None
        assert 'iron condor' in ticket.strategy.lower()

    def test_ticket_exit_rules(self):
        """Exits must match IC defaults: 65% TP, 2× stop, 2 DTE time stop."""
        puts = _make_option_df(list(range(480, 506)), [2.0]*26, [2.5]*26)
        calls = _make_option_df(list(range(495, 521)), [2.0]*26, [2.5]*26)
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker, symbol='SPY', current_price=500.0,
            expiry='2026-02-23', dte=7, wing_width=5.0,
            min_credit_pct=0.0, implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is not None
        assert ticket.exits.take_profit_pct == 65.0
        assert ticket.exits.stop_loss_multiple == 2.0
        assert ticket.exits.time_stop_days == 2

    def test_ticket_has_credit_and_max_loss(self):
        """Each ticket must carry credit and max_loss fields."""
        puts = _make_option_df(list(range(480, 506)), [2.0]*26, [2.5]*26)
        calls = _make_option_df(list(range(495, 521)), [2.0]*26, [2.5]*26)
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker, symbol='SPY', current_price=500.0,
            expiry='2026-02-23', dte=7, wing_width=5.0,
            min_credit_pct=0.0, implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is not None
        assert ticket.mid_credit >= 0
        assert ticket.max_loss >= 0
        assert ticket.width > 0

    def test_credit_threshold_filters_ticket(self):
        """When credit is below threshold, no ticket is returned."""
        # Low-credit chain: bid = 0.01, ask = 5.0 → near-zero credit
        puts = _make_option_df(list(range(480, 506)), [0.01]*26, [5.0]*26)
        calls = _make_option_df(list(range(495, 521)), [0.01]*26, [5.0]*26)
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = puts
        chain.calls = calls
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker, symbol='SPY', current_price=500.0,
            expiry='2026-02-23', dte=7, wing_width=5.0,
            min_credit_pct=0.25,  # require >=25%
            implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is None

    def test_empty_chain_returns_none(self):
        ticker = MagicMock()
        chain = MagicMock()
        chain.puts = pd.DataFrame()
        chain.calls = pd.DataFrame()
        ticker.option_chain = MagicMock(return_value=chain)

        ticket = self.engine._build_iron_condor_ticket(
            ticker=ticker, symbol='SPY', current_price=500.0,
            expiry='2026-02-23', dte=7, wing_width=5.0,
            min_credit_pct=0.25, implied_move_mult=1.2,
            existing_positions=[],
        )
        assert ticket is None

    # -- generate_iron_condor_tickets integration tests -----------------

    @patch('index_vol_engine.yf')
    def test_returns_list(self, mock_yf):
        """Return type is always a list."""
        ticker = MagicMock()
        ticker.info = {'currentPrice': 500.0}
        ticker.options = []  # no expirations
        mock_yf.Ticker.return_value = ticker

        result = self.engine.generate_iron_condor_tickets('SPY')
        assert isinstance(result, list)

    @patch('index_vol_engine.yf')
    def test_no_expirations_returns_empty(self, mock_yf):
        """No expirations in range → 0 tickets."""
        ticker = MagicMock()
        ticker.info = {'currentPrice': 500.0}
        ticker.options = ['2026-06-19']  # far out
        mock_yf.Ticker.return_value = ticker

        result = self.engine.generate_iron_condor_tickets('SPY')
        assert result == []

    @patch('index_vol_engine.yf')
    def test_no_price_returns_empty(self, mock_yf):
        ticker = MagicMock()
        ticker.info = {}
        ticker.options = ['2026-02-23']
        mock_yf.Ticker.return_value = ticker

        result = self.engine.generate_iron_condor_tickets('SPY')
        assert result == []

    @patch('index_vol_engine.yf')
    def test_dte_filtering(self, mock_yf):
        """Only expirations in 7-10 DTE range are considered."""
        today = date.today()
        in_range = (today + timedelta(days=8)).strftime('%Y-%m-%d')
        out_range = (today + timedelta(days=30)).strftime('%Y-%m-%d')

        puts = _make_option_df(list(range(480, 506)), [2.0]*26, [2.5]*26)
        calls = _make_option_df(list(range(495, 521)), [2.0]*26, [2.5]*26)

        ticker = _mock_ticker(500.0, [in_range, out_range],
                              {in_range: puts}, {in_range: calls})
        mock_yf.Ticker.return_value = ticker

        result = self.engine.generate_iron_condor_tickets('SPY')
        # Should process the in_range expiry; out_range skipped
        assert isinstance(result, list)
        # Each returned ticket (if any) must be in DTE range
        for t in result:
            assert 7 <= t.dte <= 10

    def test_class_constants(self):
        """Verify default class constants match spec."""
        assert self.engine.IC_DTE_MIN == 7
        assert self.engine.IC_DTE_MAX == 10
        assert self.engine.IC_IMPLIED_MOVE_MULT == 1.2
        assert self.engine.IC_WING_WIDTH == 5.0
        assert 0.25 <= self.engine.IC_MIN_CREDIT_PCT <= 0.30
        assert 60.0 <= self.engine.IC_TAKE_PROFIT_PCT <= 70.0
        assert self.engine.IC_STOP_LOSS_MULTIPLE == 2.0
        assert self.engine.IC_TIME_STOP_DTE == 2
