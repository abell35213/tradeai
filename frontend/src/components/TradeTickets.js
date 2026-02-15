import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

function TradeTickets({ apiUrl }) {
  const [symbol, setSymbol] = useState('SPY');
  const [pendingTickets, setPendingTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchPending = useCallback(async () => {
    try {
      const resp = await axios.get(`${apiUrl}/api/trade-ticket/pending`);
      setPendingTickets(resp.data.tickets || []);
    } catch (err) {
      console.error('Failed to fetch pending tickets:', err.message);
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

  const getGateColor = (passed) => (passed ? '#0a0' : '#c00');
  const getEdgeColor = (score) => {
    if (score >= 0.6) return '#0a0';
    if (score >= 0.4) return '#fa0';
    return '#c00';
  };

  return (
    <>
      {/* Generate ticket */}
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

        {error && <div className="error">Error: {error}</div>}
        {successMsg && <div className="success">{successMsg}</div>}
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
