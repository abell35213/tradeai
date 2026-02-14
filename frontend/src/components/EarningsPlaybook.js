import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

function EarningsPlaybook({ apiUrl }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;

  const fetchCalendar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${apiUrl}/api/earnings/calendar`, {
        params: { year, month }
      });
      setCalendarData(res.data.calendar || {});
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [apiUrl, year, month]);

  useEffect(() => {
    fetchCalendar();
  }, [fetchCalendar]);

  const fetchSnapshot = async (symbol) => {
    setSelectedSymbol(symbol);
    setSnapshotLoading(true);
    setSnapshotError(null);
    setSnapshot(null);
    try {
      const res = await axios.get(`${apiUrl}/api/earnings/snapshot/${symbol}`);
      setSnapshot(res.data.snapshot);
    } catch (err) {
      setSnapshotError(err.response?.data?.error || err.message);
    } finally {
      setSnapshotLoading(false);
    }
  };

  const changeMonth = (delta) => {
    setCurrentDate(prev => {
      const d = new Date(prev);
      d.setMonth(d.getMonth() + delta);
      return d;
    });
    setSelectedSymbol(null);
    setSnapshot(null);
  };

  const monthName = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });

  const getDaysInMonth = (y, m) => new Date(y, m, 0).getDate();
  const getFirstDayOfMonth = (y, m) => new Date(y, m - 1, 1).getDay();

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  const calendarCells = [];
  for (let i = 0; i < firstDay; i++) {
    calendarCells.push(null);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    calendarCells.push(d);
  }

  const renderSignalBadge = (signal) => {
    if (!signal) return null;
    let cls = 'earnings-signal-neutral';
    const lower = signal.toLowerCase();
    if (lower.includes('fear') || lower.includes('crowded') || lower.includes('fragile') || lower.includes('bearish')) {
      cls = 'earnings-signal-warning';
    } else if (lower.includes('complacency') || lower.includes('early positioning') || lower.includes('aligned')) {
      cls = 'earnings-signal-positive';
    }
    return <div className={`earnings-signal ${cls}`}>📡 {signal}</div>;
  };

  return (
    <div className="full-width">
      <div className="card full-width">
        <h2>📅 Earnings Playbook</h2>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          Pre-Earnings analysis — click a ticker for the full Sentiment Snapshot.
        </p>

        <div className="earnings-calendar-nav">
          <button className="btn earnings-nav-btn" onClick={() => changeMonth(-1)}>◀ Prev</button>
          <h3 className="earnings-month-title">{monthName}</h3>
          <button className="btn earnings-nav-btn" onClick={() => changeMonth(1)}>Next ▶</button>
        </div>

        {error && <div className="error">Error: {error}</div>}
        {loading && <div className="loading">Loading earnings calendar...</div>}

        {!loading && (
          <div className="earnings-calendar-grid">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
              <div key={d} className="earnings-calendar-header">{d}</div>
            ))}
            {calendarCells.map((day, idx) => {
              if (day === null) {
                return <div key={`empty-${idx}`} className="earnings-calendar-cell empty"></div>;
              }
              const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const earnings = calendarData[dateStr] || [];
              const isToday =
                new Date().getFullYear() === year &&
                new Date().getMonth() + 1 === month &&
                new Date().getDate() === day;

              return (
                <div
                  key={dateStr}
                  className={`earnings-calendar-cell ${earnings.length > 0 ? 'has-earnings' : ''} ${isToday ? 'today' : ''}`}
                >
                  <div className="earnings-day-number">{day}</div>
                  <div className="earnings-day-companies">
                    {earnings.map(e => (
                      <button
                        key={e.symbol}
                        className={`earnings-ticker-btn ${selectedSymbol === e.symbol ? 'selected' : ''}`}
                        onClick={() => fetchSnapshot(e.symbol)}
                        title={`${e.name} (${e.time})`}
                      >
                        {e.symbol}
                        <span className="earnings-time-badge">{e.time}</span>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {selectedSymbol && (
        <div className="card full-width">
          <h2>🔍 Pre-Earnings Sentiment Snapshot: {selectedSymbol}</h2>

          {snapshotLoading && <div className="loading">Loading snapshot...</div>}
          {snapshotError && <div className="error">Error: {snapshotError}</div>}

          {snapshot && (
            <div className="earnings-snapshot">
              <div className="earnings-snapshot-header">
                <div>
                  <strong>{snapshot.name}</strong> ({snapshot.symbol})
                </div>
                {snapshot.earnings_date && (
                  <div className="earnings-date-badge">
                    Earnings: {snapshot.earnings_date}
                  </div>
                )}
              </div>

              {snapshot.earnings_setup && (
                <div className={`earnings-setup-card setup-${snapshot.earnings_setup.setup}`}>
                  <div className="earnings-setup-header">
                    <span className="earnings-setup-badge">
                      Setup {snapshot.earnings_setup.setup}
                    </span>
                    <span className="earnings-setup-label">
                      {snapshot.earnings_setup.label}
                    </span>
                  </div>
                  <p className="earnings-setup-interpretation">
                    {snapshot.earnings_setup.interpretation}
                  </p>
                  {snapshot.earnings_setup.matched_traits && snapshot.earnings_setup.matched_traits.length > 0 && (
                    <div className="earnings-setup-traits">
                      <strong>Matched Traits:</strong>
                      <ul>
                        {snapshot.earnings_setup.matched_traits.map((t, i) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {snapshot.earnings_setup.preferred_structures && snapshot.earnings_setup.preferred_structures.length > 0 && (
                    <div className="earnings-setup-structures">
                      <strong>Preferred Structures:</strong>
                      <ul>
                        {snapshot.earnings_setup.preferred_structures.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {snapshot.earnings_setup.best_in && snapshot.earnings_setup.best_in.length > 0 && (
                    <div className="earnings-setup-bestin">
                      <strong>Best in:</strong> {snapshot.earnings_setup.best_in.join(', ')}
                    </div>
                  )}
                </div>
              )}

              <div className="earnings-dimensions-grid">
                {/* Dimension 1: Expectation Density */}
                <div className="earnings-dimension-card">
                  <h3>① Expectation Density</h3>
                  <p className="earnings-dimension-desc">
                    Are estimates tightly clustered or wide? Has guidance drifted quietly?
                  </p>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <div className="metric-label">Analyst Count</div>
                      <div className="metric-value">{snapshot.expectation_density.analyst_count ?? 'N/A'}</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Target Mean</div>
                      <div className="metric-value">
                        {snapshot.expectation_density.target_mean != null
                          ? `$${snapshot.expectation_density.target_mean.toFixed(2)}`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Target Range</div>
                      <div className="metric-value">
                        {snapshot.expectation_density.target_low != null && snapshot.expectation_density.target_high != null
                          ? `$${snapshot.expectation_density.target_low.toFixed(2)} – $${snapshot.expectation_density.target_high.toFixed(2)}`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Spread %</div>
                      <div className="metric-value">
                        {snapshot.expectation_density.spread_pct != null
                          ? `${(snapshot.expectation_density.spread_pct * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Consensus</div>
                      <div className="metric-value">
                        {snapshot.expectation_density.consensus_tight ? 'Tight' : 'Wide'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Guidance Drift</div>
                      <div className="metric-value">
                        {snapshot.expectation_density.guidance_drift != null
                          ? `${(snapshot.expectation_density.guidance_drift * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                  </div>
                  {renderSignalBadge(snapshot.expectation_density.signal)}
                </div>

                {/* Dimension 2: Options Market Expectations */}
                <div className="earnings-dimension-card">
                  <h3>② Options Market Expectations</h3>
                  <p className="earnings-dimension-desc">
                    ATM implied move vs historical realized move. Front-week IV vs back-month IV.
                  </p>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <div className="metric-label">ATM IV</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.atm_iv != null
                          ? `${(snapshot.options_expectations.atm_iv * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Historical Vol</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.historical_volatility != null
                          ? `${(snapshot.options_expectations.historical_volatility * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">IV / Historical</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.iv_vs_historical != null
                          ? `${snapshot.options_expectations.iv_vs_historical.toFixed(2)}x`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Front IV</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.front_iv != null
                          ? `${(snapshot.options_expectations.front_iv * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Back IV</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.back_iv != null
                          ? `${(snapshot.options_expectations.back_iv * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">IV Term Spread</div>
                      <div className="metric-value">
                        {snapshot.options_expectations.iv_term_spread != null
                          ? `${(snapshot.options_expectations.iv_term_spread * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                  </div>
                  {renderSignalBadge(snapshot.options_expectations.signal)}
                </div>

                {/* Dimension 3: Positioning & Flow */}
                <div className="earnings-dimension-card">
                  <h3>③ Positioning &amp; Flow</h3>
                  <p className="earnings-dimension-desc">
                    Call vs put OI buildup, directional flow, and stock drift into earnings.
                  </p>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <div className="metric-label">Call OI</div>
                      <div className="metric-value">
                        {snapshot.positioning_flow.call_oi != null
                          ? snapshot.positioning_flow.call_oi.toLocaleString()
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Put OI</div>
                      <div className="metric-value">
                        {snapshot.positioning_flow.put_oi != null
                          ? snapshot.positioning_flow.put_oi.toLocaleString()
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Put/Call OI Ratio</div>
                      <div className="metric-value">
                        {snapshot.positioning_flow.put_call_oi_ratio != null
                          ? snapshot.positioning_flow.put_call_oi_ratio.toFixed(2)
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Price Drift (10d)</div>
                      <div className="metric-value">
                        {snapshot.positioning_flow.price_drift_pct != null
                          ? `${(snapshot.positioning_flow.price_drift_pct * 100).toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Drift Direction</div>
                      <div className="metric-value" style={{ textTransform: 'capitalize' }}>
                        {snapshot.positioning_flow.drift_direction || 'N/A'}
                      </div>
                    </div>
                  </div>
                  {renderSignalBadge(snapshot.positioning_flow.signal)}
                </div>

                {/* Dimension 4: Narrative Alignment */}
                <div className="earnings-dimension-card">
                  <h3>④ Narrative Alignment</h3>
                  <p className="earnings-dimension-desc">
                    Is the company aligned with a dominant macro theme? AI, energy transition, rate sensitivity, geopolitics.
                  </p>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <div className="metric-label">Sector</div>
                      <div className="metric-value">{snapshot.narrative_alignment.sector || 'N/A'}</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Industry</div>
                      <div className="metric-value">{snapshot.narrative_alignment.industry || 'N/A'}</div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Macro Themes</div>
                      <div className="metric-value">
                        {snapshot.narrative_alignment.themes && snapshot.narrative_alignment.themes.length > 0
                          ? snapshot.narrative_alignment.themes.join(', ')
                          : 'None'}
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-label">Price vs Narrative</div>
                      <div className="metric-value">
                        {snapshot.narrative_alignment.price_ahead_of_narrative
                          ? 'Price Ahead'
                          : snapshot.narrative_alignment.narrative_ahead_of_price
                            ? 'Narrative Ahead'
                            : 'Balanced'}
                      </div>
                    </div>
                  </div>
                  {renderSignalBadge(snapshot.narrative_alignment.signal)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default EarningsPlaybook;
