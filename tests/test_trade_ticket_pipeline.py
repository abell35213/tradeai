"""Tests for the trade ticket pipeline API endpoints."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ['DEMO_MODE'] = 'true'

import pytest
from app import app, _pending_tickets, _execution_log


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_state():
    """Clear pending tickets and execution log between tests."""
    _pending_tickets.clear()
    _execution_log.clear()
    yield
    _pending_tickets.clear()
    _execution_log.clear()


# ------------------------------------------------------------------
# /api/index-vol/<symbol>
# ------------------------------------------------------------------

class TestIndexVolEndpoint:
    def test_returns_success(self, client):
        resp = client.get('/api/index-vol/SPY')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_analysis_has_edge_score(self, client):
        resp = client.get('/api/index-vol/SPY')
        analysis = resp.get_json()['analysis']
        assert 'edge_score' in analysis
        assert 0.0 <= analysis['edge_score'] <= 1.0

    def test_analysis_has_components(self, client):
        resp = client.get('/api/index-vol/SPY')
        analysis = resp.get_json()['analysis']
        assert 'components' in analysis
        for key in ('iv_rv_spread', 'term_structure', 'skew_dislocation',
                    'dealer_gamma', 'event_proximity'):
            assert key in analysis['components']

    def test_analysis_has_regime_snapshot(self, client):
        resp = client.get('/api/index-vol/SPY')
        analysis = resp.get_json()['analysis']
        assert 'regime_snapshot' in analysis

    def test_analysis_has_trade_gate(self, client):
        resp = client.get('/api/index-vol/SPY')
        analysis = resp.get_json()['analysis']
        assert 'trade_gate' in analysis
        assert 'passed' in analysis['trade_gate']


# ------------------------------------------------------------------
# /api/trade-ticket/index-vol
# ------------------------------------------------------------------

class TestTradeTicketIndexVol:
    def test_returns_ticket(self, client):
        resp = client.post('/api/trade-ticket/index-vol',
                           json={'symbol': 'SPY'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'ticket' in data

    def test_ticket_has_required_fields(self, client):
        resp = client.post('/api/trade-ticket/index-vol',
                           json={'symbol': 'SPY'})
        ticket = resp.get_json()['ticket']
        required = [
            'ticket_id', 'symbol', 'strategy', 'expiry', 'strikes',
            'wing_width', 'credit', 'max_loss', 'pop_estimate',
            'regime_snapshot', 'trade_gate', 'edge_score', 'components',
            'risk_before', 'risk_after', 'status', 'created_at',
        ]
        for field in required:
            assert field in ticket, f'Missing field: {field}'

    def test_ticket_status_is_pending(self, client):
        resp = client.post('/api/trade-ticket/index-vol',
                           json={'symbol': 'SPY'})
        ticket = resp.get_json()['ticket']
        assert ticket['status'] == 'pending'

    def test_ticket_stored_in_pending(self, client):
        resp = client.post('/api/trade-ticket/index-vol',
                           json={'symbol': 'SPY'})
        ticket = resp.get_json()['ticket']
        assert ticket['ticket_id'] in _pending_tickets


# ------------------------------------------------------------------
# /api/trade-ticket/pending
# ------------------------------------------------------------------

class TestPendingTickets:
    def test_empty_initially(self, client):
        resp = client.get('/api/trade-ticket/pending')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['tickets'] == []

    def test_lists_pending_after_creation(self, client):
        client.post('/api/trade-ticket/index-vol', json={'symbol': 'SPY'})
        resp = client.get('/api/trade-ticket/pending')
        data = resp.get_json()
        assert len(data['tickets']) == 1

    def test_does_not_list_approved(self, client):
        # Create a ticket then approve it
        create_resp = client.post('/api/trade-ticket/index-vol',
                                  json={'symbol': 'SPY'})
        tid = create_resp.get_json()['ticket']['ticket_id']
        client.post('/api/execute',
                     json={'ticket_id': tid, 'action': 'approve'})

        resp = client.get('/api/trade-ticket/pending')
        assert len(resp.get_json()['tickets']) == 0


# ------------------------------------------------------------------
# /api/execute
# ------------------------------------------------------------------

class TestExecuteEndpoint:
    def test_approve_ticket(self, client):
        create_resp = client.post('/api/trade-ticket/index-vol',
                                  json={'symbol': 'SPY'})
        tid = create_resp.get_json()['ticket']['ticket_id']

        resp = client.post('/api/execute',
                           json={'ticket_id': tid, 'action': 'approve'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['ticket']['status'] == 'approved'

    def test_reject_ticket(self, client):
        create_resp = client.post('/api/trade-ticket/index-vol',
                                  json={'symbol': 'SPY'})
        tid = create_resp.get_json()['ticket']['ticket_id']

        resp = client.post('/api/execute',
                           json={'ticket_id': tid, 'action': 'reject'})
        assert resp.status_code == 200
        assert resp.get_json()['ticket']['status'] == 'rejected'

    def test_missing_ticket_id(self, client):
        resp = client.post('/api/execute', json={'action': 'approve'})
        assert resp.status_code == 400

    def test_invalid_action(self, client):
        resp = client.post('/api/execute',
                           json={'ticket_id': 'xxx', 'action': 'cancel'})
        assert resp.status_code == 400

    def test_ticket_not_found(self, client):
        resp = client.post('/api/execute',
                           json={'ticket_id': 'nonexistent', 'action': 'approve'})
        assert resp.status_code == 404

    def test_double_approve_conflict(self, client):
        create_resp = client.post('/api/trade-ticket/index-vol',
                                  json={'symbol': 'SPY'})
        tid = create_resp.get_json()['ticket']['ticket_id']

        client.post('/api/execute',
                     json={'ticket_id': tid, 'action': 'approve'})
        resp = client.post('/api/execute',
                           json={'ticket_id': tid, 'action': 'approve'})
        assert resp.status_code == 409
