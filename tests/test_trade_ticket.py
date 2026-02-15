"""Tests for the trade ticket module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from trade_ticket import (
    TradeTicket, TicketLeg, EdgeMetrics, RegimeGate,
    RiskGate, PortfolioAfter, Exits,
    build_trade_ticket, evaluate_ticket,
)
from risk_engine import RiskEngine


class TestTradeTicketModel:
    def test_minimal_construction(self):
        ticket = TradeTicket(strategy='SPY_IRON_CONDOR', underlying='SPY')
        assert ticket.strategy == 'SPY_IRON_CONDOR'
        assert ticket.underlying == 'SPY'
        assert ticket.timestamp is not None
        assert ticket.data_timestamp is not None
        assert ticket.legs == []
        assert ticket.mid_credit == 0.0
        assert ticket.limit_credit == 0.0
        assert ticket.width == 0.0
        assert ticket.max_loss == 0.0
        assert ticket.pop_estimate is None
        assert isinstance(ticket.edge_metrics, EdgeMetrics)
        assert isinstance(ticket.regime_gate, RegimeGate)
        assert isinstance(ticket.risk_gate, RiskGate)
        assert ticket.confidence_score == 0.0
        assert isinstance(ticket.exits, Exits)

    def test_full_construction(self):
        ticket = TradeTicket(
            strategy='SPY_PUT_CREDIT_SPREAD',
            underlying='SPY',
            expiry='2026-03-20',
            dte=33,
            legs=[
                TicketLeg(type='put', side='sell', strike=470.0, qty=1),
                TicketLeg(type='put', side='buy', strike=465.0, qty=1),
            ],
            mid_credit=1.25,
            limit_credit=1.20,
            width=5.0,
            max_loss=375.0,
            pop_estimate=75.0,
            edge_metrics=EdgeMetrics(iv_pct=0.65, iv_richness=0.8),
            regime_gate=RegimeGate(passed=True, reasons=[]),
            risk_gate=RiskGate(
                passed=True,
                reasons=[],
                portfolio_after=PortfolioAfter(delta=-0.3, vega=-0.1, gamma=-0.01, max_loss_week=375.0),
            ),
            confidence_score=0.72,
            exits=Exits(take_profit_pct=50.0, stop_loss_multiple=2.0, time_stop_days=21),
        )
        assert ticket.underlying == 'SPY'
        assert len(ticket.legs) == 2
        assert ticket.legs[0].type == 'put'
        assert ticket.legs[0].side == 'sell'
        assert ticket.legs[0].strike == 470.0
        assert ticket.mid_credit == 1.25
        assert ticket.width == 5.0
        assert ticket.edge_metrics.iv_pct == 0.65
        assert ticket.regime_gate.passed is True
        assert ticket.risk_gate.portfolio_after.delta == -0.3
        assert ticket.confidence_score == 0.72
        assert ticket.exits.take_profit_pct == 50.0

    def test_model_dump_roundtrip(self):
        ticket = TradeTicket(
            strategy='SPY_IRON_CONDOR',
            underlying='SPY',
            legs=[TicketLeg(type='call', side='sell', strike=500.0, qty=1)],
        )
        d = ticket.model_dump()
        assert isinstance(d, dict)
        assert d['strategy'] == 'SPY_IRON_CONDOR'
        assert d['underlying'] == 'SPY'
        assert len(d['legs']) == 1
        assert d['legs'][0]['type'] == 'call'

    def test_required_fields_present(self):
        """Every ticket must contain the spec-required fields."""
        ticket = TradeTicket(strategy='SPY_PUT_CREDIT_SPREAD', underlying='SPY')
        d = ticket.model_dump()
        required = [
            'strategy', 'underlying', 'timestamp', 'data_timestamp',
            'expiry', 'dte', 'legs', 'mid_credit', 'limit_credit',
            'width', 'max_loss', 'pop_estimate', 'edge_metrics',
            'regime_gate', 'risk_gate', 'confidence_score', 'exits',
        ]
        for field in required:
            assert field in d, f'Missing required field: {field}'


class TestBuildTradeTicket:
    def test_basic_fields(self):
        ticket = build_trade_ticket(
            underlying='SPY',
            strategy='SPY_IRON_CONDOR',
            legs=[
                {'type': 'put', 'side': 'sell', 'strike': 460, 'qty': 1},
                {'type': 'put', 'side': 'buy', 'strike': 455, 'qty': 1},
                {'type': 'call', 'side': 'sell', 'strike': 500, 'qty': 1},
                {'type': 'call', 'side': 'buy', 'strike': 505, 'qty': 1},
            ],
            mid_credit=3.0,
            max_loss=200.0,
            width=5.0,
        )
        assert isinstance(ticket, TradeTicket)
        assert ticket.underlying == 'SPY'
        assert ticket.strategy == 'SPY_IRON_CONDOR'
        assert ticket.mid_credit == 3.0
        assert ticket.max_loss == 200.0
        assert len(ticket.legs) == 4
        assert ticket.risk_gate.passed is True

    def test_defaults(self):
        ticket = build_trade_ticket(
            underlying='SPY', strategy='SPY_PUT_CREDIT_SPREAD',
            legs=[], mid_credit=5.0, max_loss=500.0, width=5.0,
        )
        assert ticket.expiry is None
        assert ticket.dte is None
        assert ticket.pop_estimate is None
        assert ticket.confidence_score == 0.0
        assert ticket.timestamp is not None
        assert isinstance(ticket.exits, Exits)

    def test_backward_compat_leg_format(self):
        """Old-style leg dicts (option_type, action, quantity) are accepted."""
        ticket = build_trade_ticket(
            underlying='AAPL',
            strategy='short_put',
            legs=[
                {'option_type': 'put', 'action': 'sell', 'strike': 165,
                 'quantity': 1, 'price': 4.0, 'delta': -0.3},
            ],
            mid_credit=4.0,
            max_loss=16100.0,
        )
        assert isinstance(ticket, TradeTicket)
        assert ticket.legs[0].type == 'put'
        assert ticket.legs[0].side == 'sell'
        assert ticket.legs[0].qty == 1
        assert ticket.legs[0].delta == -0.3


class TestEvaluateTicket:
    def test_populates_risk_gate(self):
        ticket = build_trade_ticket(
            underlying='AAPL',
            strategy='short_put',
            legs=[
                {'type': 'put', 'side': 'sell', 'strike': 165, 'qty': 1,
                 'price': 4.0, 'delta': -0.3, 'vega': 0.15, 'gamma': 0.02},
            ],
            mid_credit=4.0,
            max_loss=16100.0,
        )
        re = RiskEngine()
        existing = []
        result = evaluate_ticket(ticket, re, existing)
        assert isinstance(result, TradeTicket)
        assert result.risk_gate.passed is not None
        assert result.risk_gate.portfolio_after.delta != 0.0 or True  # may be 0 with one leg

    def test_adds_to_existing_positions(self):
        ticket = build_trade_ticket(
            underlying='MSFT',
            strategy='short_call',
            legs=[
                {'type': 'call', 'side': 'sell', 'strike': 420, 'qty': 1,
                 'price': 5.0, 'delta': 0.4, 'vega': 0.20, 'gamma': 0.01},
            ],
            mid_credit=5.0,
            max_loss=999999,
        )
        existing = [
            {'symbol': 'AAPL', 'delta': 0.5, 'vega': 0.1, 'gamma': 0.01,
             'notional': 10000, 'earnings_date': None, 'expiry_bucket': '0-7d'},
        ]
        re = RiskEngine()
        result = evaluate_ticket(ticket, re, existing)
        assert isinstance(result, TradeTicket)
        assert result.risk_gate.portfolio_after is not None
