"""Tests for RiskEngine.evaluate_ticket_risk and risk limit enforcement."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from risk_engine import RiskEngine
from trade_ticket import (
    build_trade_ticket, evaluate_ticket, PortfolioAfter,
)


class TestEvaluateTicketRisk:
    """Unit tests for RiskEngine.evaluate_ticket_risk."""

    def setup_method(self):
        self.engine = RiskEngine()
        self.ticket_position = {
            'symbol': 'SPY',
            'delta': -0.30,
            'vega': -0.10,
            'gamma': -0.01,
            'notional': 500,
            'earnings_date': None,
            'expiry_bucket': '7-30d',
        }

    def test_returns_required_keys(self):
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=[],
        )
        expected_keys = [
            'portfolio_delta_before', 'portfolio_vega_before', 'portfolio_gamma_before',
            'portfolio_delta_after', 'portfolio_vega_after', 'portfolio_gamma_after',
            'max_loss_trade', 'max_loss_week', 'sector_concentration',
            'risk_limits_pass', 'reasons',
        ]
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'

    def test_after_greeks_reflect_new_position(self):
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=[],
        )
        assert result['portfolio_delta_before'] == 0.0
        assert result['portfolio_vega_before'] == 0.0
        assert result['portfolio_gamma_before'] == 0.0
        assert result['portfolio_delta_after'] == -0.30
        assert result['portfolio_vega_after'] == -0.10
        assert result['portfolio_gamma_after'] == -0.01

    def test_before_greeks_include_existing(self):
        existing = [
            {'symbol': 'AAPL', 'delta': 0.5, 'vega': 0.2, 'gamma': 0.02,
             'notional': 10000, 'earnings_date': None, 'expiry_bucket': '0-7d'},
        ]
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=existing,
        )
        assert result['portfolio_delta_before'] == 0.5
        assert result['portfolio_vega_before'] == 0.2
        assert result['portfolio_gamma_before'] == 0.02

    def test_small_trade_passes(self):
        """375 max loss on 100k equity = 0.375% < 1.5% → pass."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=[],
            equity=100_000.0,
        )
        assert result['risk_limits_pass'] is True
        assert result['reasons'] == []

    def test_max_loss_trade_stored(self):
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=[],
        )
        assert result['max_loss_trade'] == 375.0

    def test_max_loss_week_accumulates(self):
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.ticket_position,
            existing_positions=[],
            existing_weekly_max_losses=1000.0,
        )
        assert result['max_loss_week'] == 1375.0


class TestTradeRiskLimit:
    """Max risk per trade: 1.0–1.5% of equity."""

    def setup_method(self):
        self.engine = RiskEngine()
        self.pos = {
            'symbol': 'SPY', 'delta': -0.30, 'vega': -0.10,
            'gamma': -0.01, 'notional': 500,
            'earnings_date': None, 'expiry_bucket': '7-30d',
        }

    def test_at_limit_passes(self):
        """1500 on 100k = exactly 1.5% → pass."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=1500.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
        )
        assert result['risk_limits_pass'] is True

    def test_above_limit_fails(self):
        """2000 on 100k = 2.0% > 1.5% → fail."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=2000.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
        )
        assert result['risk_limits_pass'] is False
        assert any('Trade max loss' in r for r in result['reasons'])

    def test_small_equity_triggers_limit(self):
        """375 on 10k = 3.75% > 1.5% → fail."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=10_000.0,
        )
        assert result['risk_limits_pass'] is False


class TestWeeklyLossLimit:
    """Max weekly sum of worst-case losses: 5% of equity."""

    def setup_method(self):
        self.engine = RiskEngine()
        self.pos = {
            'symbol': 'SPY', 'delta': -0.30, 'vega': -0.10,
            'gamma': -0.01, 'notional': 500,
            'earnings_date': None, 'expiry_bucket': '7-30d',
        }

    def test_within_weekly_limit_passes(self):
        """1000 existing + 375 new = 1375 on 100k = 1.375% → pass."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            existing_weekly_max_losses=1000.0,
        )
        assert result['risk_limits_pass'] is True

    def test_exceeds_weekly_limit_fails(self):
        """4800 existing + 375 new = 5175 on 100k = 5.175% → fail."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            existing_weekly_max_losses=4800.0,
        )
        assert result['risk_limits_pass'] is False
        assert any('Weekly max loss' in r for r in result['reasons'])


class TestKillSwitch:
    """Kill switch: weekly realized drawdown > 3% → block new tickets."""

    def setup_method(self):
        self.engine = RiskEngine()
        self.pos = {
            'symbol': 'SPY', 'delta': -0.30, 'vega': -0.10,
            'gamma': -0.01, 'notional': 500,
            'earnings_date': None, 'expiry_bucket': '7-30d',
        }

    def test_no_drawdown_passes(self):
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            weekly_realized_pnl=0.0,
        )
        assert result['risk_limits_pass'] is True

    def test_small_loss_passes(self):
        """2000 loss on 100k = 2.0% < 3% → pass."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            weekly_realized_pnl=-2000.0,
        )
        assert result['risk_limits_pass'] is True

    def test_large_drawdown_blocks(self):
        """3500 loss on 100k = 3.5% > 3% → fail."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            weekly_realized_pnl=-3500.0,
        )
        assert result['risk_limits_pass'] is False
        assert any('kill switch' in r for r in result['reasons'])

    def test_positive_pnl_not_blocked(self):
        """Positive PnL should never trigger kill switch."""
        result = self.engine.evaluate_ticket_risk(
            ticket_max_loss=375.0,
            ticket_position=self.pos,
            existing_positions=[],
            equity=100_000.0,
            weekly_realized_pnl=5000.0,
        )
        assert result['risk_limits_pass'] is True


class TestMultipleRiskBreaches:
    """Multiple risk limits can be breached simultaneously."""

    def test_multiple_reasons(self):
        engine = RiskEngine()
        pos = {
            'symbol': 'SPY', 'delta': -0.30, 'vega': -0.10,
            'gamma': -0.01, 'notional': 500,
            'earnings_date': None, 'expiry_bucket': '7-30d',
        }
        result = engine.evaluate_ticket_risk(
            ticket_max_loss=2000.0,       # 2% > 1.5% per trade
            ticket_position=pos,
            existing_positions=[],
            equity=100_000.0,
            weekly_realized_pnl=-4000.0,  # 4% > 3% kill switch
            existing_weekly_max_losses=4000.0,  # 4000+2000 = 6% > 5% weekly
        )
        assert result['risk_limits_pass'] is False
        assert len(result['reasons']) == 3


class TestEvaluateTicketIntegration:
    """Integration tests: evaluate_ticket populates risk_gate from RiskEngine."""

    def test_passing_trade_sets_risk_gate_true(self):
        ticket = build_trade_ticket(
            underlying='SPY',
            strategy='SPY_PUT_CREDIT_SPREAD',
            legs=[
                {'type': 'put', 'side': 'sell', 'strike': 470, 'qty': 1,
                 'price': 1.25, 'delta': -0.15, 'vega': 0.10, 'gamma': 0.01},
                {'type': 'put', 'side': 'buy', 'strike': 465, 'qty': 1,
                 'price': 0.50, 'delta': -0.10, 'vega': 0.05, 'gamma': 0.005},
            ],
            mid_credit=0.75,
            max_loss=375.0,
            width=5.0,
        )
        engine = RiskEngine()
        result = evaluate_ticket(ticket, engine, [], equity=100_000.0)
        assert result.risk_gate.passed is True
        assert result.risk_gate.reasons == []
        assert result.risk_gate.portfolio_after.max_loss_trade == 375.0

    def test_failing_trade_sets_risk_gate_false(self):
        ticket = build_trade_ticket(
            underlying='SPY',
            strategy='SPY_PUT_CREDIT_SPREAD',
            legs=[
                {'type': 'put', 'side': 'sell', 'strike': 470, 'qty': 1,
                 'price': 1.25, 'delta': -0.15, 'vega': 0.10, 'gamma': 0.01},
            ],
            mid_credit=0.75,
            max_loss=2000.0,  # 2% of 100k → exceeds 1.5%
            width=5.0,
        )
        engine = RiskEngine()
        result = evaluate_ticket(ticket, engine, [], equity=100_000.0)
        assert result.risk_gate.passed is False
        assert len(result.risk_gate.reasons) > 0

    def test_kill_switch_blocks_ticket(self):
        ticket = build_trade_ticket(
            underlying='SPY',
            strategy='SPY_PUT_CREDIT_SPREAD',
            legs=[],
            mid_credit=0.75,
            max_loss=375.0,
            width=5.0,
        )
        engine = RiskEngine()
        result = evaluate_ticket(
            ticket, engine, [],
            equity=100_000.0,
            weekly_realized_pnl=-4000.0,
        )
        assert result.risk_gate.passed is False
        assert any('kill switch' in r for r in result.risk_gate.reasons)

    def test_portfolio_after_has_max_loss_trade(self):
        ticket = build_trade_ticket(
            underlying='SPY',
            strategy='SPY_PUT_CREDIT_SPREAD',
            legs=[],
            mid_credit=0.75,
            max_loss=375.0,
            width=5.0,
        )
        engine = RiskEngine()
        result = evaluate_ticket(ticket, engine, [])
        assert isinstance(result.risk_gate.portfolio_after, PortfolioAfter)
        assert result.risk_gate.portfolio_after.max_loss_trade == 375.0
        assert result.risk_gate.portfolio_after.max_loss_week == 375.0
