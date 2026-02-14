import React, { useState } from 'react';
import axios from 'axios';

function OpportunityFinder({ apiUrl }) {
  const [symbols, setSymbols] = useState('SPY,QQQ,IWM,AAPL,MSFT,NVDA');
  const [minConfidence, setMinConfidence] = useState(0.6);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const findOpportunities = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const symbolsList = symbols.split(',').map(s => s.trim()).filter(s => s);
      
      const response = await axios.post(`${apiUrl}/api/opportunities`, {
        symbols: symbolsList,
        min_confidence: minConfidence
      });
      
      setOpportunities(response.data.opportunities || []);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 70) return '#0a0';
    if (score >= 50) return '#fa0';
    return '#c00';
  };

  return (
    <>
      <div className="card full-width">
        <h2>Find Trading Opportunities</h2>
        
        <div className="input-group">
          <label>Symbols (comma-separated)</label>
          <input 
            type="text" 
            value={symbols} 
            onChange={(e) => setSymbols(e.target.value.toUpperCase())}
            placeholder="SPY,QQQ,IWM,AAPL,MSFT"
          />
        </div>
        
        <div className="input-group">
          <label>Minimum Confidence: {(minConfidence * 100).toFixed(0)}%</label>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05"
            value={minConfidence} 
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
          />
        </div>
        
        <button className="btn" onClick={findOpportunities} disabled={loading}>
          {loading ? 'Scanning...' : 'Find Opportunities'}
        </button>
        
        {error && <div className="error">Error: {error}</div>}
      </div>

      {opportunities.length > 0 && (
        <div className="card full-width">
          <h2>Opportunities Found ({opportunities.length})</h2>
          
          <div className="opportunities-list">
            {opportunities.map((opp, index) => (
              <div key={index} className="opportunity-item">
                <div className="opportunity-header">
                  <span className="opportunity-symbol">{opp.symbol}</span>
                  <span className="opportunity-score" style={{ backgroundColor: getScoreColor(opp.score) }}>
                    Score: {opp.score.toFixed(0)}/100
                  </span>
                </div>
                
                <div className="metrics-grid">
                  <div className="metric-item">
                    <div className="metric-label">Current Price</div>
                    <div className="metric-value">${opp.current_price?.toFixed(2)}</div>
                  </div>
                  
                  <div className="metric-item">
                    <div className="metric-label">Confidence</div>
                    <div className="metric-value">{(opp.confidence * 100).toFixed(0)}%</div>
                  </div>
                  
                  <div className="metric-item">
                    <div className="metric-label">Sentiment</div>
                    <div className="metric-value">
                      {opp.sentiment?.overall_score > 0 ? 'Bullish' : 'Bearish'}
                    </div>
                  </div>
                  
                  <div className="metric-item">
                    <div className="metric-label">Volatility</div>
                    <div className="metric-value">{(opp.volatility * 100).toFixed(1)}%</div>
                  </div>
                </div>
                
                <div className="recommendation">
                  <strong>Recommendation:</strong> {opp.sentiment?.recommendation}
                </div>
                
                {opp.strategy && opp.strategy.length > 0 && (
                  <div className="strategy-list">
                    <h3 style={{ marginBottom: '10px', fontSize: '1.1em' }}>Suggested Strategies:</h3>
                    {opp.strategy.map((strategy, idx) => (
                      <div key={idx} className="strategy-item">
                        <div className="strategy-name">
                          {strategy.name} ({strategy.direction})
                        </div>
                        <div className="strategy-details">
                          <strong>Risk:</strong> {strategy.risk} | 
                          <strong> Reward:</strong> {strategy.reward} | 
                          <strong> Confidence:</strong> {strategy.confidence}
                        </div>
                        <div className="strategy-details" style={{ marginTop: '5px' }}>
                          {strategy.reasoning}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                
                {opp.options_analysis?.available && (
                  <div style={{ marginTop: '15px', padding: '10px', background: '#f0f0f0', borderRadius: '6px' }}>
                    <strong>Options Available:</strong> {opp.options_analysis.expirations_available} expirations
                    {opp.options_analysis.put_call_ratio && (
                      <span> | Put/Call Ratio: {opp.options_analysis.put_call_ratio.toFixed(2)}</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && opportunities.length === 0 && symbols && (
        <div className="card full-width">
          <p style={{ textAlign: 'center', color: '#666' }}>
            No opportunities found matching your criteria. Try lowering the minimum confidence or adding more symbols.
          </p>
        </div>
      )}
    </>
  );
}

export default OpportunityFinder;
