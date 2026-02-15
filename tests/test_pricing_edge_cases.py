"""Additional unit tests for pricing and Greeks edge cases.

Covers boundary conditions, extreme parameters, and numerical
stability that complement the existing test_derivatives_calculator.py.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import math
import pytest
from derivatives_calculator import DerivativesCalculator

dc = DerivativesCalculator()


# ------------------------------------------------------------------
# Boundary / edge-case pricing
# ------------------------------------------------------------------

class TestPricingEdgeCases:
    def test_deep_itm_call(self):
        """Deep ITM call price ≈ S - K*exp(-rT)."""
        S, K, T, r, sigma = 200, 100, 1.0, 0.05, 0.20
        price = dc.black_scholes_price(S, K, T, r, sigma, 'call')
        intrinsic_approx = S - K * math.exp(-r * T)
        assert price > intrinsic_approx * 0.99

    def test_deep_otm_put_near_zero(self):
        """Deep OTM put has near-zero value."""
        price = dc.black_scholes_price(200, 100, 0.1, 0.05, 0.20, 'put')
        assert price < 0.01

    def test_high_volatility(self):
        """Very high vol should not produce NaN or negative prices."""
        price = dc.black_scholes_price(100, 100, 1.0, 0.05, 5.0, 'call')
        assert price > 0
        assert not math.isnan(price)

    def test_very_short_expiry(self):
        """Near-zero time to expiry with ITM should return intrinsic."""
        price = dc.black_scholes_price(110, 100, 0.001, 0.05, 0.25, 'call')
        assert abs(price - 10) < 1.0  # close to intrinsic

    def test_zero_rate(self):
        """Zero risk-free rate should still produce valid prices."""
        price = dc.black_scholes_price(100, 100, 1.0, 0.0, 0.25, 'call')
        assert price > 0

    def test_high_dividend_yield(self):
        """High dividend reduces call price significantly."""
        no_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.25, 'call', q=0)
        high_div = dc.black_scholes_price(100, 100, 1.0, 0.05, 0.25, 'call', q=0.10)
        assert high_div < no_div * 0.85


# ------------------------------------------------------------------
# Greeks edge cases
# ------------------------------------------------------------------

class TestGreeksEdgeCases:
    def test_delta_call_between_0_and_1(self):
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call')
        assert 0.0 < g['delta'] < 1.0

    def test_delta_put_between_neg1_and_0(self):
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'put')
        assert -1.0 < g['delta'] < 0.0

    def test_gamma_positive_for_both(self):
        for opt_type in ('call', 'put'):
            g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, opt_type)
            assert g['gamma'] > 0

    def test_theta_negative_for_long(self):
        """Theta should be negative (time decay hurts long positions)."""
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call')
        assert g['theta'] < 0

    def test_vega_positive_for_both(self):
        for opt_type in ('call', 'put'):
            g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, opt_type)
            assert g['vega_per_1pct'] > 0

    def test_atm_delta_near_half(self):
        """ATM call delta should be near 0.5."""
        g = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call')
        assert 0.4 < g['delta'] < 0.7

    def test_greeks_consistency_call_put(self):
        """Call delta - put delta should be close to exp(-qT) ≈ 1 for q=0."""
        gc = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'call')
        gp = dc.calculate_greeks(100, 100, 0.5, 0.25, 0.05, 'put')
        assert abs((gc['delta'] - gp['delta']) - 1.0) < 0.01


# ------------------------------------------------------------------
# IV solver edge cases
# ------------------------------------------------------------------

class TestIVSolverEdgeCases:
    def test_round_trip_deep_otm(self):
        """IV solver should handle low-value OTM options."""
        S, K, T, r, sigma = 100, 130, 0.25, 0.05, 0.30
        price = dc.black_scholes_price(S, K, T, r, sigma, 'call')
        iv = dc.calculate_implied_volatility(price, S, K, T, r, 'call')
        assert abs(iv - sigma) < 0.005

    def test_round_trip_put(self):
        """IV solver round-trip for put option."""
        S, K, T, r, sigma = 100, 95, 0.5, 0.05, 0.30
        price = dc.black_scholes_price(S, K, T, r, sigma, 'put')
        iv = dc.calculate_implied_volatility(price, S, K, T, r, 'put')
        assert abs(iv - sigma) < 0.005

    def test_round_trip_high_vol(self):
        """IV solver for high-vol options."""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.80
        price = dc.black_scholes_price(S, K, T, r, sigma, 'call')
        iv = dc.calculate_implied_volatility(price, S, K, T, r, 'call')
        assert abs(iv - sigma) < 0.01
