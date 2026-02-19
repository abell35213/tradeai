// frontend/src/components/ETFOpportunities.js
import React, { useEffect, useState } from "react";
import { API_BASE_URL } from "../config";

export default function ETFOpportunities({ onSelect }) {
  const [loading, setLoading] = useState(false);
  const [minScore, setMinScore] = useState(65);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const url = `${API_BASE_URL}/api/etf/opportunities?top=5&min_score=${encodeURIComponent(minScore)}`;
      const res = await fetch(url);
      const json = await res.json();
      if (!json.success) throw new Error(json.error || "Failed to load opportunities");
      setItems(json.ranked || []);
    } catch (e) {
      setError(e.message || "Failed to load opportunities");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const badgeStyle = (signalType) => {
    const base = {
      display: "inline-block",
      padding: "2px 8px",
      borderRadius: 999,
      fontSize: 12,
      border: "1px solid #ddd",
      background: "#f7f7f7",
      marginLeft: 8,
      textTransform: "capitalize",
    };
    return base;
  };

  const biasStyle = (bias) => ({
    fontWeight: 700,
    color: bias === "bullish" ? "#0a7" : "#c33",
    textTransform: "capitalize",
  });

  return (
    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 16, marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18 }}>Top ETF Opportunities</h2>
          <div style={{ fontSize: 13, color: "#666" }}>
            Breakout-weighted ranking (Top 5). Click a row to generate debit spreads.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 13, color: "#333" }}>
            Min score:&nbsp;
            <input
              type="number"
              value={minScore}
              min={0}
              max={100}
              onChange={(e) => setMinScore(parseInt(e.target.value || "0", 10))}
              style={{ width: 80, padding: "6px 8px", borderRadius: 8, border: "1px solid #ddd" }}
            />
          </label>
          <button
            onClick={load}
            disabled={loading}
            style={{
              padding: "8px 12px",
              borderRadius: 10,
              border: "1px solid #ddd",
              background: loading ? "#f4f4f4" : "white",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ marginTop: 12, color: "#b00", fontSize: 13 }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        {items.length === 0 && !loading && (
          <div style={{ color: "#666", fontSize: 13 }}>
            No opportunities returned at this threshold. Try lowering Min score (e.g., 55).
          </div>
        )}

        <div style={{ width: "100%", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>
                <th style={{ padding: "10px 8px" }}>Symbol</th>
                <th style={{ padding: "10px 8px" }}>Bias</th>
                <th style={{ padding: "10px 8px" }}>Signal</th>
                <th style={{ padding: "10px 8px" }}>Score</th>
                <th style={{ padding: "10px 8px" }}>Trigger</th>
                <th style={{ padding: "10px 8px" }}>Stop</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr
                  key={row.symbol}
                  onClick={() => onSelect(row)}
                  style={{
                    borderBottom: "1px solid #f1f1f1",
                    cursor: "pointer",
                  }}
                >
                  <td style={{ padding: "10px 8px", fontWeight: 700 }}>{row.symbol}</td>
                  <td style={{ padding: "10px 8px" }}>
                    <span style={biasStyle(row.bias)}>{row.bias}</span>
                  </td>
                  <td style={{ padding: "10px 8px" }}>
                    <span style={badgeStyle(row.signal_type)}>{row.signal_type || "neutral"}</span>
                    {row.strength_label && (
                      <span style={{ ...badgeStyle(row.strength_label), marginLeft: 6 }}>
                        {row.strength_label}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "10px 8px" }}>{row.score}</td>
                  <td style={{ padding: "10px 8px" }}>{row.levels?.trigger ?? "-"}</td>
                  <td style={{ padding: "10px 8px" }}>{row.levels?.stop ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: 10, fontSize: 12, color: "#777" }}>
          Tip: If you’re running in DEMO_MODE, scores/signals may be mocked for UI testing.
        </div>
      </div>
    </div>
  );
}
