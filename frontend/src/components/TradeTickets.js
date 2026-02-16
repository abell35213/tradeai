import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

function TradeTickets({ apiUrl }) {
  const [symbol, setSymbol] = useState('SPY');
  const [pendingTickets, setPendingTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [rejectReasons, setRejectReasons] = useState({});
  const [auditLog, setAuditLog] = useState([]);
  const [showAuditLog, setShowAuditLog] = useState(false);
  // Proposed tickets from the manual confirmation workflow
  const [proposedTickets, setProposedTickets] = useState([]);
  const [proposing, setProposing] = useState(false);

  const fetchPending = useCallback(async () => {
    try {
      const resp = await axios.get(`${apiUrl}/api/trade-ticket/pending`);
      setPendingTickets(resp.data.tickets || []);
    } catch (err) {
      console.error('Failed to fetch pending tickets:', err.message);
    }
  }, [apiUrl]);

  const fetchAuditLog = useCallback(async () => {
    try {
      const resp = await axios.get(`${apiUrl}/api/trade-audit-log`);
      setAuditLog(resp.data.log || []);
    } catch (err) {
      console.error('Failed to fetch audit log:', err.message);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  const generateTicket = async () => {
    setGenerating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await axios.post(`${apiUrl}/api/trade-ticket/index-vol`, {
        symbol,
      });
      if (resp.data.success) {
        setSuccessMsg(`Ticket generated for ${symbol}`);
        fetchPending();
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setGenerating(false);
    }
  };

  const executeAction = async (ticketId, action) => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await axios.post(`${apiUrl}/api/execute`, {
        ticket_id: ticketId,
        action,
      });
      if (resp.data.success) {
        setSuccessMsg(`Ticket ${action}d successfully`);
        fetchPending();
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /* Manual Confirmation workflow                                        */
  /* ------------------------------------------------------------------ */

  const proposeSPYTickets = async () => {
    setProposing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await axios.post(`${apiUrl}/api/trade-tickets/spy`, {});
      if (resp.data.success) {
        setProposedTickets(resp.data.tickets || []);
        setSuccessMsg('SPY tickets proposed — review and approve or reject below.');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setProposing(false);
    }
  };

  const approveTicket = async (ticketId) => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await axios.post(`${apiUrl}/api/trade-approve`, {
        ticket_id: ticketId,
      });
      if (resp.data.success) {
        setSuccessMsg(`Ticket approved (hash: ${resp.data.approval.ticket_hash?.slice(0, 8)}…)`);
        setProposedTickets((prev) => prev.filter((t) => t.ticket_id !== ticketId));
        fetchPending();
        if (showAuditLog) fetchAuditLog();
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const rejectTicket = async (ticketId) => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await axios.post(`${apiUrl}/api/trade-reject`, {
        ticket_id: ticketId,
        reason: rejectReasons[ticketId] || null,
      });
      if (resp.data.success) {
        setSuccessMsg(`Ticket rejected (hash: ${resp.data.rejection.ticket_hash?.slice(0, 8)}…)`);
        setProposedTickets((prev) => prev.filter((t) => t.ticket_id !== ticketId));
        setRejectReasons((prev) => {
          const copy = { ...prev };
          delete copy[ticketId];
          return copy;
        });
        if (showAuditLog) fetchAuditLog();
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleAuditLog = () => {
    if (!showAuditLog) fetchAuditLog();
    setShowAuditLog(!showAuditLog);
  };

  const getGateColor = (passed) => (passed ? '#0a0' : '#c00');
  const getEdgeColor = (score) => {
    if (score >= 0.6) return '#0a0';
    if (score >= 0.4) return '#fa0';
    return '#c00';
  };

  return (
    <>
      {/* -------- Manual Confirmation Workflow -------- */}
      <div className="card full-width">
        <h2>🔒 Manual Confirmation (Semi-Automated)</h2>
        <p style={{ color: '#666', marginBottom: '15px' }}>
          Propose SPY trade tickets, then approve or reject each one. Every
          decision is logged with a timestamp and ticket hash for idempotency.
        </p>

        <button className="btn" onClick={proposeSPYTickets} disabled={proposing}>
          {proposing ? 'Proposing…' : 'Propose SPY Tickets'}
        </button>

        {error && <div className="error">Error: {error}</div>}
        {successMsg && <div className="success">{successMsg}</div>}

        {proposedTickets.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ color: '#1e3c72' }}>Proposed Tickets ({proposedTickets.length})</h3>
            {proposedTickets.map((ticket) => (
              <div key={ticket.ticket_id} className="ticket-item">
                <div className="ticket-header">
                  <span className="ticket-symbol">{ticket.underlying}</span>
                  <span style={{ fontSize: '0.85em', color: '#888' }}>
                    {ticket.ticket_id?.slice(0, 8)}…
                  </span>
                  <span
                    className="ticket-edge"
                    style={{ color: getEdgeColor(ticket.confidence_score) }}
                  >
                    Confidence: {(ticket.confidence_score * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="metrics-grid">
                  <div className="metric-item">
                    <div className="metric-label">Strategy</div>
                    <div className="metric-value" style={{ fontSize: '1em' }}>
                      {ticket.strategy}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Expiry</div>
                    <div className="metric-value">{ticket.expiry || '—'}</div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Credit</div>
                    <div className="metric-value">
                      ${ticket.mid_credit?.toFixed(2) || '—'}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Max Loss</div>
                    <div className="metric-value">
                      ${ticket.max_loss?.toFixed(2) || '—'}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">POP</div>
                    <div className="metric-value">
                      {ticket.pop_estimate != null
                        ? `${ticket.pop_estimate.toFixed(1)}%`
                        : '—'}
                    </div>
                  </div>
                  <div className="metric-item">
                    <div className="metric-label">Hash</div>
                    <div className="metric-value" style={{ fontSize: '0.8em' }}>
                      {ticket.ticket_hash?.slice(0, 12)}…
                    </div>
                  </div>
                </div>

                {/* Reject reason input */}
                <div style={{ margin: '10px 0' }}>
                  <input
                    type="text"
                    placeholder="Optional rejection reason…"
                    value={rejectReasons[ticket.ticket_id] || ''}
                    onChange={(e) =>
                      setRejectReasons((prev) => ({
                        ...prev,
                        [ticket.ticket_id]: e.target.value,
                      }))
                    }
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid #ddd',
                      fontSize: '0.9em',
                    }}
                  />
                </div>

                {/* Approve / Reject buttons */}
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    className="btn"
                    style={{ background: '#0a0', flex: 1 }}
                    disabled={loading}
                    onClick={() => approveTicket(ticket.ticket_id)}
                  >
                    ✅ Approve
                  </button>
                  <button
                    className="btn"
                    style={{ background: '#c00', flex: 1 }}
                    disabled={loading}
                    onClick={() => rejectTicket(ticket.ticket_id)}
                  >
                    ❌ Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Audit log toggle */}
        <div style={{ marginTop: '20px' }}>
          <button
            className="btn"
            style={{ background: '#555' }}
            onClick={toggleAuditLog}
          >
            {showAuditLog ? 'Hide Audit Log' : '📜 Show Audit Log'}
          </button>

          {showAuditLog && (
            <div style={{ marginTop: '15px' }}>
              <h3 style={{ color: '#1e3c72' }}>Audit Log ({auditLog.length} entries)</h3>
              {auditLog.length === 0 && (
                <p style={{ color: '#666' }}>No approvals or rejections yet.</p>
              )}
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {auditLog.map((entry, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      gap: '15px',
                      padding: '8px 12px',
                      borderLeft: `4px solid ${entry.action === 'approved' ? '#0a0' : '#c00'}`,
                      background: entry.action === 'approved' ? '#efffef' : '#fff0f0',
                      borderRadius: '4px',
                      marginBottom: '6px',
                      fontSize: '0.9em',
                      alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 'bold', minWidth: '80px' }}>
                      {entry.action === 'approved' ? '✅ Approved' : '❌ Rejected'}
                    </span>
                    <span style={{ color: '#555', flex: 1 }}>
                      {entry.ticket_id?.slice(0, 8)}…
                      {entry.reason && ` — "${entry.reason}"`}
                    </span>
                    <span style={{ color: '#888', fontSize: '0.85em', whiteSpace: 'nowrap' }}>
                      {entry.timestamp}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* -------- Existing: Generate ticket -------- */}
      <div className="card full-width">
        <h2>🎯 Index Vol Trade Ticket</h2>
        <p style={{ color: '#666', marginBottom: '15px' }}>
          Generate edge-based credit spread tickets using implied vs realized
          spread, term structure, skew, dealer gamma, and event proximity.
        </p>

        <div className="input-group">
          <label>Symbol</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="SPY"
          />
        </div>

        <button className="btn" onClick={generateTicket} disabled={generating}>
          {generating ? 'Generating...' : 'Generate Trade Ticket'}
        </button>
      </div>

      {/* Pending tickets */}
      <div className="card full-width">
        <h2>📋 Pending Tickets ({pendingTickets.length})</h2>

        {pendingTickets.length === 0 && (
          <p style={{ textAlign: 'center', color: '#666' }}>
            No pending tickets. Generate one above.
          </p>
        )}

        {pendingTickets.map((ticket) => (
          <div key={ticket.ticket_id} className="ticket-item">
            {/* Header row */}
            <div className="ticket-header">
              <span className="ticket-symbol">{ticket.symbol}</span>
              <span
                className="ticket-gate"
                style={{
                  backgroundColor: getGateColor(ticket.trade_gate?.passed),
                }}
              >
                {ticket.trade_gate?.passed ? '✅ PASS' : '❌ FAIL'}
              </span>
              <span
                className="ticket-edge"
                style={{ color: getEdgeColor(ticket.edge_score) }}
              >
                Edge: {(ticket.edge_score * 100).toFixed(1)}%
              </span>
            </div>

            {/* Strategy & structure */}
            <div className="metrics-grid">
              <div className="metric-item">
                <div className="metric-label">Strategy</div>
                <div className="metric-value" style={{ fontSize: '1em' }}>
                  {ticket.strategy}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Expiry</div>
                <div className="metric-value">{ticket.expiry || '—'}</div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Short Strike</div>
                <div className="metric-value">
                  {ticket.strikes?.short?.toFixed(1) || '—'}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Long Strike</div>
                <div className="metric-value">
                  {ticket.strikes?.long?.toFixed(1) || '—'}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Wing Width</div>
                <div className="metric-value">
                  ${ticket.wing_width?.toFixed(2) || '—'}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Credit</div>
                <div className="metric-value">
                  ${ticket.credit?.toFixed(2) || '—'}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">Max Loss</div>
                <div className="metric-value">
                  ${ticket.max_loss?.toFixed(2) || '—'}
                </div>
              </div>
              <div className="metric-item">
                <div className="metric-label">POP Estimate</div>
                <div className="metric-value">
                  {ticket.pop_estimate != null
                    ? `${ticket.pop_estimate.toFixed(1)}%`
                    : '—'}
                </div>
              </div>
            </div>

            {/* Edge components */}
            {ticket.components && (
              <div style={{ margin: '15px 0' }}>
                <strong style={{ color: '#1e3c72' }}>Edge Components</strong>
                <div className="metrics-grid" style={{ marginTop: '8px' }}>
                  {Object.entries(ticket.components).map(([key, val]) => (
                    <div key={key} className="metric-item">
                      <div className="metric-label">
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className="metric-value">
                        {(val * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Regime snapshot */}
            {ticket.regime_snapshot && (
              <div className="recommendation">
                <strong>Regime:</strong>{' '}
                Vol={ticket.regime_snapshot.vol_regime} |
                Correlation={ticket.regime_snapshot.correlation_regime} |
                Risk Appetite={ticket.regime_snapshot.risk_appetite}
              </div>
            )}

            {/* Pass/fail reasons */}
            {ticket.trade_gate?.reasons?.length > 0 && (
              <div
                style={{
                  background: '#fee',
                  padding: '10px 15px',
                  borderRadius: '6px',
                  margin: '10px 0',
                  borderLeft: '4px solid #c00',
                }}
              >
                <strong style={{ color: '#c00' }}>Fail Reasons:</strong>
                <ul style={{ margin: '5px 0 0', paddingLeft: '20px' }}>
                  {ticket.trade_gate.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Risk before / after */}
            {(ticket.risk_before || ticket.risk_after) && (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '10px',
                  margin: '10px 0',
                }}
              >
                <div
                  style={{
                    background: '#f5f5f5',
                    padding: '10px',
                    borderRadius: '6px',
                  }}
                >
                  <strong>Risk Before</strong>
                  <div>Delta: {ticket.risk_before?.portfolio_delta ?? '—'}</div>
                  <div>Vega: {ticket.risk_before?.portfolio_vega ?? '—'}</div>
                  <div>Gamma: {ticket.risk_before?.portfolio_gamma ?? '—'}</div>
                </div>
                <div
                  style={{
                    background: '#f5f5f5',
                    padding: '10px',
                    borderRadius: '6px',
                  }}
                >
                  <strong>Risk After</strong>
                  <div>Delta: {ticket.risk_after?.portfolio_delta ?? '—'}</div>
                  <div>Vega: {ticket.risk_after?.portfolio_vega ?? '—'}</div>
                  <div>Gamma: {ticket.risk_after?.portfolio_gamma ?? '—'}</div>
                </div>
              </div>
            )}

            {/* Approve / Reject buttons */}
            <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
              <button
                className="btn"
                style={{ background: '#0a0', flex: 1 }}
                disabled={loading}
                onClick={() => executeAction(ticket.ticket_id, 'approve')}
              >
                ✅ Approve
              </button>
              <button
                className="btn"
                style={{ background: '#c00', flex: 1 }}
                disabled={loading}
                onClick={() => executeAction(ticket.ticket_id, 'reject')}
              >
                ❌ Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default TradeTickets;
