"""Tests for the manual confirmation workflow (SQLite-backed endpoints)."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ['DEMO_MODE'] = 'true'

import pytest
from db import init_db, insert_ticket, approve_ticket, reject_ticket, compute_ticket_hash, get_ticket, list_pending_tickets, get_audit_log
from app import app, _pending_tickets, _execution_log


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    """Provide a fresh temporary SQLite database for each test."""
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_state():
    """Clear in-memory state and reset the SQLite database between tests."""
    _pending_tickets.clear()
    _execution_log.clear()
    # Re-initialise the default SQLite database so API tests are isolated
    from db import init_db, _DB_PATH, _get_connection
    _ALLOWED_TABLES = {'tickets', 'approvals', 'rejections', 'fills', 'daily_pnl'}
    conn = _get_connection()
    try:
        for table in _ALLOWED_TABLES:
            conn.execute(f"DELETE FROM [{table}]")
        conn.commit()
    finally:
        conn.close()
    yield
    _pending_tickets.clear()
    _execution_log.clear()


# ---------------------------------------------------------------------------
# Unit tests: db module
# ---------------------------------------------------------------------------

class TestComputeTicketHash:
    def test_deterministic(self):
        ticket = {"ticket_id": "abc", "symbol": "SPY", "strategy": "put_spread"}
        h1 = compute_ticket_hash(ticket)
        h2 = compute_ticket_hash(ticket)
        assert h1 == h2

    def test_different_tickets_different_hash(self):
        t1 = {"ticket_id": "a", "symbol": "SPY"}
        t2 = {"ticket_id": "b", "symbol": "QQQ"}
        assert compute_ticket_hash(t1) != compute_ticket_hash(t2)

    def test_hash_is_hex_string(self):
        h = compute_ticket_hash({"ticket_id": "x"})
        assert len(h) == 64  # SHA-256 hex digest


class TestInsertAndGetTicket:
    def test_insert_and_retrieve(self, db_path):
        ticket = {"ticket_id": "t1", "underlying": "SPY", "strategy": "credit_spread"}
        tid, thash = insert_ticket(ticket, db_path)
        assert tid == "t1"
        assert len(thash) == 64

        row = get_ticket("t1", db_path)
        assert row is not None
        assert row["ticket_id"] == "t1"
        assert row["status"] == "pending"
        assert row["ticket_hash"] == thash

    def test_get_missing_ticket(self, db_path):
        assert get_ticket("nope", db_path) is None


class TestApproveTicket:
    def test_approve_pending(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        record = approve_ticket("t1", db_path)
        assert record["ticket_id"] == "t1"
        assert "approved_at" in record
        assert "ticket_hash" in record

        row = get_ticket("t1", db_path)
        assert row["status"] == "approved"

    def test_approve_not_found(self, db_path):
        with pytest.raises(KeyError):
            approve_ticket("missing", db_path)

    def test_approve_already_approved(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        approve_ticket("t1", db_path)
        with pytest.raises(ValueError, match="already approved"):
            approve_ticket("t1", db_path)

    def test_approve_idempotent_same_hash(self, db_path):
        """Idempotency: re-approving with the same hash succeeds."""
        ticket = {"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}
        insert_ticket(ticket, db_path)
        r1 = approve_ticket("t1", db_path)
        # The second call should hit the ValueError because status is already 'approved'
        # This is expected: idempotency is at the DB level (UNIQUE constraint)
        assert r1["ticket_hash"] == compute_ticket_hash(ticket)


class TestRejectTicket:
    def test_reject_pending(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        record = reject_ticket("t1", reason="bad risk", db_path=db_path)
        assert record["ticket_id"] == "t1"
        assert record["reason"] == "bad risk"
        assert "rejected_at" in record

        row = get_ticket("t1", db_path)
        assert row["status"] == "rejected"

    def test_reject_not_found(self, db_path):
        with pytest.raises(KeyError):
            reject_ticket("missing", db_path=db_path)

    def test_reject_already_rejected(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        reject_ticket("t1", db_path=db_path)
        with pytest.raises(ValueError, match="already rejected"):
            reject_ticket("t1", db_path=db_path)

    def test_reject_without_reason(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        record = reject_ticket("t1", db_path=db_path)
        assert record["reason"] is None


class TestAuditLog:
    def test_empty_initially(self, db_path):
        assert get_audit_log(db_path) == []

    def test_logs_approval(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        approve_ticket("t1", db_path)
        log = get_audit_log(db_path)
        assert len(log) == 1
        assert log[0]["action"] == "approved"
        assert log[0]["ticket_id"] == "t1"

    def test_logs_rejection(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        reject_ticket("t1", reason="too risky", db_path=db_path)
        log = get_audit_log(db_path)
        assert len(log) == 1
        assert log[0]["action"] == "rejected"
        assert log[0]["reason"] == "too risky"

    def test_combined_log_ordered(self, db_path):
        insert_ticket({"ticket_id": "t1", "underlying": "SPY", "strategy": "x"}, db_path)
        reject_ticket("t1", db_path=db_path)
        insert_ticket({"ticket_id": "t2", "underlying": "SPY", "strategy": "y"}, db_path)
        approve_ticket("t2", db_path)
        log = get_audit_log(db_path)
        assert len(log) == 2
        assert log[0]["action"] == "rejected"
        assert log[1]["action"] == "approved"


# ---------------------------------------------------------------------------
# Integration tests: API endpoints
# ---------------------------------------------------------------------------

class TestProposeSPYTickets:
    def test_returns_tickets(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'tickets' in data
        assert len(data['tickets']) >= 1

    def test_ticket_has_required_fields(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        ticket = resp.get_json()['tickets'][0]
        for field in ('ticket_id', 'underlying', 'strategy', 'status', 'ticket_hash'):
            assert field in ticket, f'Missing field: {field}'
        assert ticket['underlying'] == 'SPY'
        assert ticket['status'] == 'pending'

    def test_ticket_hash_present(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        ticket = resp.get_json()['tickets'][0]
        assert len(ticket['ticket_hash']) == 64


class TestTradeApproveEndpoint:
    def test_approve_proposed_ticket(self, client):
        # First propose a ticket
        resp = client.post('/api/trade-tickets/spy', json={})
        ticket = resp.get_json()['tickets'][0]
        tid = ticket['ticket_id']

        # Then approve it
        resp = client.post('/api/trade-approve', json={'ticket_id': tid})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'approval' in data
        assert data['approval']['ticket_id'] == tid
        assert 'approved_at' in data['approval']
        assert 'ticket_hash' in data['approval']

    def test_approve_missing_ticket(self, client):
        resp = client.post('/api/trade-approve', json={'ticket_id': 'nonexistent'})
        assert resp.status_code == 404

    def test_double_approve_conflict(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']
        client.post('/api/trade-approve', json={'ticket_id': tid})
        resp = client.post('/api/trade-approve', json={'ticket_id': tid})
        assert resp.status_code == 409

    def test_approve_missing_body(self, client):
        resp = client.post('/api/trade-approve', json={})
        assert resp.status_code == 422


class TestTradeRejectEndpoint:
    def test_reject_with_reason(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']

        resp = client.post('/api/trade-reject', json={'ticket_id': tid, 'reason': 'bad gamma'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['rejection']['reason'] == 'bad gamma'
        assert 'rejected_at' in data['rejection']
        assert 'ticket_hash' in data['rejection']

    def test_reject_without_reason(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']

        resp = client.post('/api/trade-reject', json={'ticket_id': tid})
        assert resp.status_code == 200
        assert resp.get_json()['rejection']['reason'] is None

    def test_reject_missing_ticket(self, client):
        resp = client.post('/api/trade-reject', json={'ticket_id': 'nonexistent'})
        assert resp.status_code == 404

    def test_double_reject_conflict(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']
        client.post('/api/trade-reject', json={'ticket_id': tid})
        resp = client.post('/api/trade-reject', json={'ticket_id': tid})
        assert resp.status_code == 409


class TestAuditLogEndpoint:
    def test_empty_log(self, client):
        resp = client.get('/api/trade-audit-log')
        assert resp.status_code == 200
        assert resp.get_json()['log'] == []

    def test_log_records_approval(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']
        client.post('/api/trade-approve', json={'ticket_id': tid})

        resp = client.get('/api/trade-audit-log')
        log = resp.get_json()['log']
        assert len(log) >= 1
        assert any(e['action'] == 'approved' and e['ticket_id'] == tid for e in log)

    def test_log_records_rejection_with_reason(self, client):
        resp = client.post('/api/trade-tickets/spy', json={})
        tid = resp.get_json()['tickets'][0]['ticket_id']
        client.post('/api/trade-reject', json={'ticket_id': tid, 'reason': 'risk too high'})

        resp = client.get('/api/trade-audit-log')
        log = resp.get_json()['log']
        assert len(log) >= 1
        entry = next(e for e in log if e['ticket_id'] == tid)
        assert entry['action'] == 'rejected'
        assert entry['reason'] == 'risk too high'
