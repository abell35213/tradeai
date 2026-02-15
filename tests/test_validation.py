"""Tests for input validation models and API validation behavior."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ['DEMO_MODE'] = 'true'

import pytest
from pydantic import ValidationError
from validation import (
    GreeksRequest, TradeTicketRequest, PositionSizeRequest,
    CircuitBreakerRequest, ExecuteRequest,
)
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ------------------------------------------------------------------
# Pydantic model unit tests
# ------------------------------------------------------------------

class TestGreeksRequestValidation:
    def test_valid_request(self):
        req = GreeksRequest(
            spot_price=100, strike=105, time_to_expiry=0.5,
            volatility=0.25, risk_free_rate=0.05, option_type='call',
        )
        assert req.spot_price == 100

    def test_negative_spot_price_rejected(self):
        with pytest.raises(ValidationError):
            GreeksRequest(
                spot_price=-10, strike=105, time_to_expiry=0.5,
                volatility=0.25,
            )

    def test_zero_volatility_rejected(self):
        with pytest.raises(ValidationError):
            GreeksRequest(
                spot_price=100, strike=105, time_to_expiry=0.5,
                volatility=0.0,
            )

    def test_invalid_option_type_rejected(self):
        with pytest.raises(ValidationError):
            GreeksRequest(
                spot_price=100, strike=105, time_to_expiry=0.5,
                volatility=0.25, option_type='straddle',
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            GreeksRequest(spot_price=100)

    def test_defaults_applied(self):
        req = GreeksRequest(
            spot_price=100, strike=100, time_to_expiry=1.0,
            volatility=0.2,
        )
        assert req.risk_free_rate == 0.05
        assert req.option_type == 'call'
        assert req.dividend_yield == 0.0


class TestTradeTicketRequestValidation:
    def test_valid_request(self):
        req = TradeTicketRequest(
            symbol='SPY', strategy='iron condor',
            legs=[{'type': 'call'}], credit=1.5, max_loss=350,
            width=5.0,
        )
        assert req.symbol == 'SPY'
        assert req.width == 5.0

    def test_empty_symbol_rejected(self):
        with pytest.raises(ValidationError):
            TradeTicketRequest(
                symbol='', strategy='straddle',
                legs=[], credit=1.0, max_loss=100,
            )


class TestPositionSizeRequestValidation:
    def test_defaults(self):
        req = PositionSizeRequest()
        assert req.confidence_score == 3
        assert req.historical_edge == 0.5
        assert req.liquidity_score == 0.5

    def test_out_of_range_confidence(self):
        with pytest.raises(ValidationError):
            PositionSizeRequest(confidence_score=10)


class TestExecuteRequestValidation:
    def test_valid_approve(self):
        req = ExecuteRequest(ticket_id='abc-123', action='approve')
        assert req.action == 'approve'

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            ExecuteRequest(ticket_id='abc', action='cancel')


# ------------------------------------------------------------------
# API endpoint validation tests
# ------------------------------------------------------------------

class TestGreeksEndpointValidation:
    def test_missing_body_returns_422(self, client):
        resp = client.post('/api/greeks/SPY', json={})
        assert resp.status_code == 422

    def test_negative_strike_returns_422(self, client):
        resp = client.post('/api/greeks/SPY', json={
            'spot_price': 100, 'strike': -5,
            'time_to_expiry': 0.5, 'volatility': 0.25,
        })
        assert resp.status_code == 422

    def test_valid_greeks_request(self, client):
        resp = client.post('/api/greeks/SPY', json={
            'spot_price': 100, 'strike': 100,
            'time_to_expiry': 0.5, 'volatility': 0.25,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'greeks' in data
