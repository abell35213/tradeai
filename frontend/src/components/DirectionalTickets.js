// frontend/src/components/DirectionalTickets.js
import React, { useMemo, useState } from "react";
import { API_BASE_URL } from "../config";

export default function DirectionalTickets({ selected }) {
  const [dteTarget, setDteTarget] = useState(14);
  const [maxPremium, setMaxPremium] = useState(1000);
  const [maxTickets, setMaxTickets] = useState(3);

  const [loading, setLoading] = useState(false);
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState("");

  const symbol = selected?.symbol;
  const bias = selected?.bias;

  const disabled = useMemo(() => !symbol || !bias || loading, [symbol, bias, loading]);

  async function generate() {
    if (!symbol || !bias) return;
    setLoading(true);
    setError("");
    setTickets([]);
    try {
      const res = await fetch(`${API_BASE_URL}/api/trade-tickets/directional`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          bias,
          dte_target: dteTarget,
          max_premium: maxPremium,
          max_tickets: maxTickets,
        }),
      });

      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Failed to generate tickets");
      setTickets(json.tickets || []);
    } catch (e) {
      setError(e.message || "Failed to generate tickets");
    } finally {
      setLoading(false);
    }
  }

  async function approve(ticketId) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Approve failed");
      setTickets((prev) => prev.filter((t) => t.ticket_id !== ticketId));
    } catch (e) {
      alert(e.message || "Approve failed");
    }
  }

  async function reject(ticketId) {
    const reason = prompt("Optional reject reason (press OK to reject):") || "";
    try {
      const res = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Reject failed");
      setTickets((prev) => prev.filter((t) => t.ticket_id !== ticketId));
    } catch (e) {
      alert(e.message || "Reject failed");
    }
  }

  const cardStyle = {
    border: "1px solid #eee",
    borderRadius: 12,
    padding: 14,
    marginTop: 10,
    background: "white",
  };

  return (
    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
      <h2 style={{ margin: 0, fontSize: 18 }}>Directional Debit Spreads</h2>

      {!symbol ? (
        <div style={{ marginTop: 10, color: "#666", fontSize: 13 }}>
          Select an ETF opportunity above to generate debit spreads.
        </div>
      ) : (
        <>
          <div style={{ marginTop: 8, fontSize: 13, color: "#444" }}>
            Selected: <b>{symbol}</b> &nbsp;|&nbsp; Bias: <b style={{ textTransform: "capitalize" }}>{bias}</b>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
            <label style={{ fontSize: 13 }}>
              DTE Target:&nbsp;
              <select
                value={dteTarget}
                onChange={(e) => setDteTarget(parseInt(e.target.value, 10))}
                style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid #ddd" }}
              >
                <option value={7}>7</option>
                <option value={14}>14</option>
                <option value={30}>30</option>
              </select>
            </label>

            <label style={{ fontSize: 13 }}>
              Max Premium ($):&nbsp;
              <input
                type="number"
                value={maxPremium}
                min={1}
                onChange={(e) => setMaxPremium(parseInt(e.target.value || "0", 10))}
                style={{ width: 120, padding: "6px 8px", borderRadius: 8, border: "1px solid #ddd" }}
              />
            </label>

            <label style={{ fontSize: 13 }}>
              Max Tickets:&nbsp;
              <input
                type="number"
                value={maxTickets}
                min={1}
                max={10}
                onChange={(e) => setMaxTickets(parseInt(e.target.value || "3", 10))}
                style={{ width: 80, padding: "6px 8px", borderRadius: 8, border: "1px solid #ddd" }}
              />
            </label>

            <button
              onClick={generate}
              disabled={disabled}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #ddd",
                background: disabled ? "#f4f4f4" : "white",
                cursor: disabled ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Generating..." : "Generate Top 3"}
            </button>
          </div>

          {error && (
            <div style={{ marginTop: 12, color: "#b00", fontSize: 13 }}>
              {error}
            </div>
          )}

          {tickets.length > 0 && (
            <div style={{ marginTop: 12, fontSize: 13, color: "#666" }}>
              Showing {tickets.length} ticket(s). (Debit spreads only; no naked selling.)
            </div>
          )}

          {tickets.map((t) => (
            <div key={t.ticket_id} style={cardStyle}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 800 }}>
                    {t.underlying} — {t.strategy}
                  </div>
                  <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>
                    Expiry: {t.expiry} | DTE: {t.dte} | Max Loss: {t.max_loss}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => approve(t.ticket_id)}
                    style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #ddd", cursor: "pointer" }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => reject(t.ticket_id)}
                    style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #ddd", cursor: "pointer" }}
                  >
                    Reject
                  </button>
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>Legs</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#333" }}>
                  {(t.legs || []).map((leg, idx) => (
                    <li key={idx}>
                      {leg.side.toUpperCase()} {leg.type.toUpperCase()} {leg.strike} ×{leg.qty}
                    </li>
                  ))}
                </ul>
              </div>

              {t.regime_gate && (
                <div style={{ marginTop: 10, fontSize: 12, color: t.regime_gate.passed ? "#096" : "#b00" }}>
                  Regime Gate: {t.regime_gate.passed ? "PASS" : "FAIL"}{" "}
                  {t.regime_gate.reasons?.length ? `— ${t.regime_gate.reasons.join("; ")}` : ""}
                </div>
              )}

              {t.risk_gate && (
                <div style={{ marginTop: 6, fontSize: 12, color: t.risk_gate.passed ? "#096" : "#b00" }}>
                  Risk Gate: {t.risk_gate.passed ? "PASS" : "FAIL"}{" "}
                  {t.risk_gate.reasons?.length ? `— ${t.risk_gate.reasons.join("; ")}` : ""}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
