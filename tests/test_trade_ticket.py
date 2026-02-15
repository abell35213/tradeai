"""Tests for the trade ticket module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from trade_ticket import build_trade_ticket, evaluate_ticket
from risk_engine import RiskEngine


class TestBuildTradeTicket:
    def test_basic_fields(self):
        ticket = build_trade_ticket(
            symbol='AAPL',
            strategy='iron_condor',
            legs=[
                {'option_type': 'put', 'strike': 160, 'action': 'sell',
                 'quantity': 1, 'price': 3.0},
                {'option_type': 'put', 'strike': 155, 'action': 'buy',
                 'quantity': 1, 'price': 1.5},
                {'option_type': 'call', 'strike': 180, 'action': 'sell',
                 'quantity': 1, 'price': 2.5},
                {'option_type': 'call', 'strike': 185, 'action': 'buy',
                 'quantity': 1, 'price': 1.0},
            ],
            credit=3.0,
            max_loss=200.0,
            breakevens=[157.0, 183.0],
        )
        assert ticket['symbol'] == 'AAPL'
        assert ticket['strategy'] == 'iron_condor'
        assert ticket['credit'] == 3.0
        assert ticket['max_loss'] == 200.0
        assert ticket['breakevens'] == [157.0, 183.0]
        assert len(ticket['legs']) == 4
        assert ticket['portfolio_risk_after_trade'] is None

    def test_defaults(self):
        ticket = build_trade_ticket(
            symbol='SPY', strategy='short_straddle',
            legs=[], credit=5.0, max_loss=500.0, breakevens=[490, 510],
        )
        assert ticket['quantity'] == 1
        assert ticket['expiry'] is None
        assert ticket['notes'] is None
        assert 'created_at' in ticket


class TestEvaluateTicket:
    def test_populates_portfolio_risk(self):
        ticket = build_trade_ticket(
            symbol='AAPL',
            strategy='short_put',
            legs=[
                {'option_type': 'put', 'strike': 165, 'action': 'sell',
                 'quantity': 1, 'price': 4.0, 'delta': -0.3,
                 'vega': 0.15, 'gamma': 0.02},
            ],
            credit=4.0,
            max_loss=16100.0,
            breakevens=[161.0],
        )
        re = RiskEngine()
        existing = []
        result = evaluate_ticket(ticket, re, existing)
        assert result['portfolio_risk_after_trade'] is not None
        assert 'portfolio_delta' in result['portfolio_risk_after_trade']

    def test_adds_to_existing_positions(self):
        ticket = build_trade_ticket(
            symbol='MSFT',
            strategy='short_call',
            legs=[
                {'option_type': 'call', 'strike': 420, 'action': 'sell',
                 'quantity': 1, 'price': 5.0, 'delta': 0.4,
                 'vega': 0.20, 'gamma': 0.01},
            ],
            credit=5.0,
            max_loss=999999,
            breakevens=[425.0],
        )
        existing = [
            {'symbol': 'AAPL', 'delta': 0.5, 'vega': 0.1, 'gamma': 0.01,
             'notional': 10000, 'earnings_date': None, 'expiry_bucket': '0-7d'},
        ]
        re = RiskEngine()
        result = evaluate_ticket(ticket, re, existing)
        risk = result['portfolio_risk_after_trade']
        # Should reflect both the existing position and the new ticket
        assert risk['total_notional'] > 0
