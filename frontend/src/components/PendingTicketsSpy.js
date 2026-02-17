import React, { useState } from "react";
import { apiGet, apiPost } from "../api/client";
import "./PendingTicketsSPY.css";

function formatLeg(leg) {
  // leg: { side: "SELL"/"BUY", type: "CALL"/"PUT", strike: number, qty: number }
  return `${leg.side} ${leg.qty} ${leg.type} ${leg.strike}`;
}

function Money({ value }) {
  if (value === null || value === undefined || value === "") return <span>-</span>;
  const n = Number(value);
  if (Number.isNaN(n)) return <span>{String(value)}</span>;
  return <span>${n.toFixed(2)}</span>;
}

export default function PendingTicketsSPY() {
  const [loading, setLoading] = useState(false);
  const [tickets, setTickets] = useState([]);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const [accountEquity, setAccountEquity] = useState(100000);
  const [maxTickets, setMaxTickets] = useState(3);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost("/api/trade-tickets/spy", {
        account_equity: Number(accountEquity),
        max_tickets: Number(maxTickets),
      });
      setStatus(res.status || "OK");
      setTickets(res.tickets || []);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(ticketId) {
    setLoading(true);
    setError(null);
    try {
      await apiPost(`/api/tickets/${ticketId}/approve`, {});
      // Optimistic: remove from list
      setTickets((prev) => prev.filter((t) => t.id !== ticketId));
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleReject(ticketId) {
    setLoading(true);
    setError(null);
    try {
      await apiPost(`/api/tickets/${ticketId}/reject`, {});
      setTickets((prev) => prev.filter((t) => t.id !== ticketId));
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleHealth() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet("/health");
      setStatus(`Backend: ${res.status}`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="spyWrap">
      <div className="spyHeader">
        <div>
          <h2>SPY Vol Income — Pending Tickets</h2>
          <p className="spySub">
            Generates up to {maxTickets} ranked, $5-wide iron condors (semi-automated). Manual approval required.
          </p>
        </div>
        <div className="spyHeaderActions">
          <button className="btnSecondary" onClick={handleHealth} disabled={loading}>
            Check Backend
          </button>
          <button className="btnPrimary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Working..." : "Generate Tickets"}
          </button>
        </div>
      </div>

      <div className="spyControls">
        <div className="ctrl">
          <label>Account Equity</label>
          <input
            type="number"
            value={accountEquity}
            onChange={(e) => setAccountEquity(e.target.value)}
            min="0"
          />
        </div>
        <div className="ctrl">
          <label>Max Tickets</label>
          <input
            type="number"
            value={maxTickets}
            onChange={(e) => setMaxTickets(e.target.value)}
            min="1"
            max="3"
          />
        </div>
        <div className="ctrlStatus">
          <span className="pill">{status || "—"}</span>
        </div>
      </div>

      {error && (
        <div className="spyError">
          <strong>Error:</strong> {error}
        </div>
      )}

      {tickets.length === 0 ? (
        <div className="spyEmpty">
          <p>No tickets yet. Click <strong>Generate Tickets</strong>.</p>
        </div>
      ) : (
        <div className="spyGrid">
          {tickets.map((t, idx) => {
            const regimePass = t.regime_gate?.pass !== false;
            const riskPass = t.risk_gate?.pass !== false;

            return (
              <div className="ticketCard" key={t.id || idx}>
                <div className="ticketTop">
                  <div>
                    <div className="ticketRank">Rank #{idx + 1}</div>
                    <div className="ticketTitle">
                      {t.underlying} — {t.strategy}
                    </div>
                    <div className="ticketMeta">
                      Expiry: <strong>{t.expiry}</strong> · DTE: <strong>{t.dte}</strong> · Width: <strong>${t.width}</strong>
                    </div>
                  </div>

                  <div className="ticketScore">
                    <div className="scoreNumber">{t.score ?? "—"}</div>
                    <div className="scoreLabel">Score</div>
                  </div>
                </div>

                <div className="ticketBadges">
                  <span className={`badge ${regimePass ? "ok" : "bad"}`}>
                    Regime: {regimePass ? "PASS" : "FAIL"}
                  </span>
                  <span className={`badge ${riskPass ? "ok" : "bad"}`}>
                    Risk: {riskPass ? "PASS" : "FAIL"}
                  </span>
                  <span className="badge neutral">
                    Credit: <Money value={t.mid_credit} />
                  </span>
                  <span className="badge neutral">
                    Max Loss: <Money value={t.max_loss} />
                  </span>
                </div>

                <div className="ticketSection">
                  <div className="sectionTitle">Legs</div>
                  <ul className="legs">
                    {(t.legs || []).map((leg, i) => (
                      <li key={i}>{formatLeg(leg)}</li>
                    ))}
                  </ul>
                </div>

                <div className="ticketSection">
                  <div className="sectionTitle">Why it ranked</div>
                  <div className="why">
                    <div>Edge: {t.score_breakdown?.edge ?? "—"}</div>
                    <div>Payoff: {t.score_breakdown?.payoff ?? "—"}</div>
                    <div>Safety: {t.score_breakdown?.safety ?? "—"}</div>
                  </div>
                </div>

                <div className="ticketSection">
                  <div className="sectionTitle">Exits</div>
                  <div className="exits">
                    <div>Take profit: {t.exits?.tp_pct ?? 65}%</div>
                    <div>Stop loss: {t.exits?.sl_multiple ?? 2.0}× credit</div>
                    <div>Time stop: {t.exits?.time_stop_dte ?? 2} DTE</div>
                  </div>
                </div>

                {!regimePass && t.regime_gate?.reasons?.length ? (
                  <div className="ticketWarn">
                    <strong>Regime block:</strong> {t.regime_gate.reasons.join("; ")}
                  </div>
                ) : null}

                {!riskPass && t.risk_gate?.reasons?.length ? (
                  <div className="ticketWarn">
                    <strong>Risk block:</strong> {t.risk_gate.reasons.join("; ")}
                  </div>
                ) : null}

                <div className="ticketActions">
                  <button
                    className="btnSecondary"
                    onClick={() => handleReject(t.id)}
                    disabled={loading}
                  >
                    Reject
                  </button>
                  <button
                    className="btnPrimary"
                    onClick={() => handleApprove(t.id)}
                    disabled={loading || !regimePass || !riskPass}
                    title={!regimePass || !riskPass ? "Blocked by regime/risk gate" : "Approve this ticket"}
                  >
                    Approve
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
