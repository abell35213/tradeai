"""Tests for the derivatives calculator – Black-Scholes with dividend yield,
vega_per_1pct / rho_per_1pct naming, and IV solver consistency."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import math
import pytest
from derivatives_calculator import DerivativesCalculator

dc = DerivativesCalculator()


# ---------------------------------------------------------------
# Black-Scholes pricing with q = 0 should match original behavior
# ---------------------------------------------------------------

class TestBlackScholesBasic:
    def test_call_price_positive(self):
        price = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'call')
        assert price > 0

    def test_put_price_positive(self):
        price = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'put')
        assert price > 0

    def test_expired_call_itm(self):
        assert dc.black_scholes_price(110, 100, 0, 0.05, 0.2, 'call') == 10

    def test_expired_put_itm(self):
        assert dc.black_scholes_price(90, 100, 0, 0.05, 0.2, 'put') == 10

    def test_put_call_parity_no_div(self):
        S, K, T, r, sigma = 100, 105, 0.5, 0.05, 0.25
        call = dc.black_scholes_price(S, K, T, r, sigma, 'call')
        put = dc.black_scholes_price(S, K, T, r, sigma, 'put')
        # C - P = S - K*exp(-rT)
        assert abs((call - put) - (S - K * math.exp(-r * T))) < 1e-8

    def test_put_call_parity_with_dividend(self):
        S, K, T, r, sigma, q = 100, 105, 0.5, 0.05, 0.25, 0.02
        call = dc.black_scholes_price(S, K, T, r, sigma, 'call', q=q)
        put = dc.black_scholes_price(S, K, T, r, sigma, 'put', q=q)
        # C - P = S*exp(-qT) - K*exp(-rT)
        expected = S * math.exp(-q * T) - K * math.exp(-r * T)
        assert abs((call - put) - expected) < 1e-8


# ---------------------------------------------------------------
# Greeks naming convention
# ---------------------------------------------------------------

class TestGreeksNaming:
    def setup_method(self):
        self.g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call')

    def test_has_vega_per_1pct(self):
        assert 'vega_per_1pct' in self.g
        assert 'vega' not in self.g  # old name must NOT appear

    def test_has_rho_per_1pct(self):
        assert 'rho_per_1pct' in self.g
        assert 'rho' not in self.g  # old name must NOT appear

    def test_vega_per_1pct_is_small(self):
        """vega_per_1pct should equal raw_vega / 100, which is much smaller."""
        assert self.g['vega_per_1pct'] > 0
        assert self.g['vega_per_1pct'] < 1  # for $100 stock with 6 mo

    def test_rho_per_1pct_sign_call(self):
        """Call rho should be positive."""
        assert self.g['rho_per_1pct'] > 0

    def test_rho_per_1pct_sign_put(self):
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'put')
        assert g['rho_per_1pct'] < 0


# ---------------------------------------------------------------
# Dividend yield effect
# ---------------------------------------------------------------

class TestDividendYield:
    def test_call_price_decreases_with_dividend(self):
        no_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'call', q=0)
        with_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'call', q=0.03)
        assert with_div < no_div

    def test_put_price_increases_with_dividend(self):
        no_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'put', q=0)
        with_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.20, 'put', q=0.03)
        assert with_div > no_div

    def test_greeks_accept_q(self):
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call', q=0.02)
        assert 'price' in g
        assert 'delta' in g

    def test_delta_lower_with_dividend(self):
        g0 = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call', q=0.0)
        g1 = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call', q=0.04)
        assert g1['delta'] < g0['delta']


# ---------------------------------------------------------------
# IV solver uses raw vega (not per-1%)
# ---------------------------------------------------------------

class TestIVSolver:
    def test_round_trip(self):
        """Price → IV → re-price should be consistent."""
        S, K, T, r, sigma = 100, 105, 0.5, 0.05, 0.30
        price = dc.black_scholes_price(S, K, T, r, sigma, 'call')
        iv = dc.calculate_implied_volatility(price, S, K, T, r, 'call')
        assert abs(iv - sigma) < 0.001

    def test_round_trip_with_dividend(self):
        S, K, T, r, sigma, q = 100, 105, 0.5, 0.05, 0.30, 0.02
        price = dc.black_scholes_price(S, K, T, r, sigma, 'call', q=q)
        iv = dc.calculate_implied_volatility(price, S, K, T, r, 'call', q=q)
        assert abs(iv - sigma) < 0.001


# ---------------------------------------------------------------
# calculate_option_metrics still works
# ---------------------------------------------------------------

class TestOptionMetrics:
    def test_basic_metrics(self):
        m = dc.calculate_option_metrics(100, 100, 0.5, 0.25, 0.05, 'call')
        assert 'probability_itm' in m
        assert 'breakeven_price' in m
        assert 'vega_per_1pct' in m

    def test_metrics_with_dividend(self):
        m = dc.calculate_option_metrics(100, 100, 0.5, 0.25, 0.05, 'call', q=0.02)
        assert m['price'] > 0

    def test_expired_greeks(self):
        g = dc.calculate_greeks(100, 90, 0, 0.25, 0.05, 'call')
        assert g['vega_per_1pct'] == 0.0
        assert g['rho_per_1pct'] == 0.0
