"""
SQLite persistence layer for the manual confirmation workflow.

Tables
------
- tickets       – every proposed trade ticket
- approvals     – approved tickets (with timestamp + ticket hash)
- rejections    – rejected tickets (with timestamp + ticket hash + optional reason)
- fills         – placeholder for future broker fills
- daily_pnl     – placeholder for daily P&L tracking
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone


_DB_PATH = os.environ.get("TRADEAI_DB_PATH", os.path.join(
    os.path.dirname(__file__), "..", "tradeai.db"
))


def _get_connection(db_path=None):
    """Return a new connection with WAL mode and row-factory enabled."""
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    """Create tables if they do not already exist."""
    conn = _get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id   TEXT PRIMARY KEY,
                ticket_hash TEXT NOT NULL,
                symbol      TEXT NOT NULL,
                strategy    TEXT,
                payload     TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT NOT NULL,
                ticket_hash TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                UNIQUE(ticket_id, ticket_hash)
            );

            CREATE TABLE IF NOT EXISTS rejections (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT NOT NULL,
                ticket_hash TEXT NOT NULL,
                reason      TEXT,
                rejected_at TEXT NOT NULL,
                UNIQUE(ticket_id, ticket_hash)
            );

            CREATE TABLE IF NOT EXISTS fills (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT NOT NULL,
                fill_price  REAL,
                fill_qty    INTEGER,
                filled_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_pnl (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                realized    REAL DEFAULT 0.0,
                unrealized  REAL DEFAULT 0.0,
                total       REAL DEFAULT 0.0,
                recorded_at TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_ticket_hash(ticket_dict):
    """Produce a deterministic SHA-256 hash of the ticket payload.

    Used as an idempotency key – two calls with the identical ticket
    content will produce the same hash.
    """
    stable = json.dumps(ticket_dict, sort_keys=True, default=str)
    return hashlib.sha256(stable.encode()).hexdigest()


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def insert_ticket(ticket_dict, db_path=None):
    """Insert a proposed ticket and return (ticket_id, ticket_hash)."""
    conn = _get_connection(db_path)
    try:
        ticket_id = ticket_dict["ticket_id"]
        ticket_hash = compute_ticket_hash(ticket_dict)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO tickets (ticket_id, ticket_hash, symbol, strategy, payload, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (
                ticket_id,
                ticket_hash,
                ticket_dict.get("underlying", ticket_dict.get("symbol", "")),
                ticket_dict.get("strategy", ""),
                json.dumps(ticket_dict, default=str),
                now,
            ),
        )
        conn.commit()
        return ticket_id, ticket_hash
    finally:
        conn.close()


def get_ticket(ticket_id, db_path=None):
    """Fetch a ticket row by id, or *None*."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def approve_ticket(ticket_id, db_path=None):
    """Approve a pending ticket.  Returns the approval record or raises."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Ticket {ticket_id} not found")
        if row["status"] != "pending":
            raise ValueError(f"Ticket {ticket_id} is already {row['status']}")

        now = datetime.now(timezone.utc).isoformat()
        ticket_hash = row["ticket_hash"]

        # Idempotency: if already approved with this hash, return existing
        existing = conn.execute(
            "SELECT * FROM approvals WHERE ticket_id = ? AND ticket_hash = ?",
            (ticket_id, ticket_hash),
        ).fetchone()
        if existing:
            return dict(existing)

        conn.execute(
            "UPDATE tickets SET status = 'approved' WHERE ticket_id = ?",
            (ticket_id,),
        )
        conn.execute(
            "INSERT INTO approvals (ticket_id, ticket_hash, approved_at) VALUES (?, ?, ?)",
            (ticket_id, ticket_hash, now),
        )
        conn.commit()
        return {
            "ticket_id": ticket_id,
            "ticket_hash": ticket_hash,
            "approved_at": now,
        }
    finally:
        conn.close()


def reject_ticket(ticket_id, reason=None, db_path=None):
    """Reject a pending ticket.  Returns the rejection record or raises."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Ticket {ticket_id} not found")
        if row["status"] != "pending":
            raise ValueError(f"Ticket {ticket_id} is already {row['status']}")

        now = datetime.now(timezone.utc).isoformat()
        ticket_hash = row["ticket_hash"]

        existing = conn.execute(
            "SELECT * FROM rejections WHERE ticket_id = ? AND ticket_hash = ?",
            (ticket_id, ticket_hash),
        ).fetchone()
        if existing:
            return dict(existing)

        conn.execute(
            "UPDATE tickets SET status = 'rejected' WHERE ticket_id = ?",
            (ticket_id,),
        )
        conn.execute(
            "INSERT INTO rejections (ticket_id, ticket_hash, reason, rejected_at) VALUES (?, ?, ?, ?)",
            (ticket_id, ticket_hash, reason, now),
        )
        conn.commit()
        return {
            "ticket_id": ticket_id,
            "ticket_hash": ticket_hash,
            "reason": reason,
            "rejected_at": now,
        }
    finally:
        conn.close()


def list_pending_tickets(db_path=None):
    """Return all tickets with status ``'pending'``."""
    conn = _get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_audit_log(db_path=None):
    """Return all approval and rejection records in chronological order."""
    conn = _get_connection(db_path)
    try:
        approvals = conn.execute(
            "SELECT ticket_id, ticket_hash, approved_at AS timestamp, "
            "'approved' AS action, NULL AS reason FROM approvals"
        ).fetchall()
        rejections = conn.execute(
            "SELECT ticket_id, ticket_hash, rejected_at AS timestamp, "
            "'rejected' AS action, reason FROM rejections"
        ).fetchall()
        combined = [dict(r) for r in approvals] + [dict(r) for r in rejections]
        combined.sort(key=lambda r: r["timestamp"])
        return combined
    finally:
        conn.close()
