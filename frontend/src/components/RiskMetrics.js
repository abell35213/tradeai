import React, { useState } from 'react';
import axios from 'axios';

function RiskMetrics({ apiUrl }) {
  const [symbol, setSymbol] = useState('SPY');
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getRiskMetrics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${apiUrl}/api/risk-metrics/${symbol}`);
      setMetrics(response.data.risk_metrics);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevel = (sharpe) => {
    if (sharpe > 1.5) return { level: 'Excellent', color: '#0a0' };
    if (sharpe > 1) return { level: 'Good', color: '#6a0' };
    if (sharpe > 0.5) return { level: 'Acceptable', color: '#fa0' };
    return { level: 'Poor', color: '#c00' };
  };

  return (
    <>
      <div className="card">
        <h2>Risk Metrics Analysis</h2>
        
        <div className="input-group">
          <label>Ticker Symbol</label>
          <input 
            type="text" 
            value={symbol} 
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Enter symbol (e.g., SPY, AAPL)"
            onKeyPress={(e) => e.key === 'Enter' && getRiskMetrics()}
          />
        </div>
        
        <button className="btn" onClick={getRiskMetrics} disabled={loading}>
          {loading ? 'Analyzing...' : 'Get Risk Metrics'}
        </button>
        
        {error && <div className="error">Error: {error}</div>}
      </div>

      {metrics && (
        <div className="card">
          <h2>Risk Analysis for {symbol}</h2>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Daily Volatility</div>
              <div className="metric-value">{(metrics.volatility_daily * 100).toFixed(2)}%</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Annual Volatility</div>
              <div className="metric-value">{(metrics.volatility_annual * 100).toFixed(2)}%</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Sharpe Ratio</div>
              <div className="metric-value" style={{ color: getRiskLevel(metrics.sharpe_ratio).color }}>
                {metrics.sharpe_ratio.toFixed(2)}
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Max Drawdown</div>
              <div className="metric-value" style={{ color: '#c00' }}>
                {(metrics.max_drawdown * 100).toFixed(2)}%
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">VaR (95%)</div>
              <div className="metric-value">{(metrics.var_95 * 100).toFixed(2)}%</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Skewness</div>
              <div className="metric-value">{metrics.skewness.toFixed(3)}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Kurtosis</div>
              <div className="metric-value">{metrics.kurtosis.toFixed(3)}</div>
            </div>
          </div>
          
          <div style={{ marginTop: '20px', padding: '15px', background: '#f0f0f0', borderRadius: '6px' }}>
            <h3 style={{ marginTop: 0, fontSize: '1.1em' }}>Risk Assessment:</h3>
            <ul style={{ marginBottom: 0, paddingLeft: '20px' }}>
              <li>
                <strong>Sharpe Ratio:</strong> {getRiskLevel(metrics.sharpe_ratio).level} 
                {' - '}Risk-adjusted returns are {getRiskLevel(metrics.sharpe_ratio).level.toLowerCase()}.
              </li>
              <li>
                <strong>Volatility:</strong> {metrics.volatility_annual > 0.4 ? 'High' : metrics.volatility_annual > 0.2 ? 'Moderate' : 'Low'} 
                {' - '}Annual volatility of {(metrics.volatility_annual * 100).toFixed(1)}%.
              </li>
              <li>
                <strong>Max Drawdown:</strong> Worst historical loss was {(Math.abs(metrics.max_drawdown) * 100).toFixed(1)}%.
              </li>
              <li>
                <strong>VaR (95%):</strong> Expected to lose at most {(Math.abs(metrics.var_95) * 100).toFixed(2)}% in a day (95% confidence).
              </li>
              <li>
                <strong>Distribution:</strong> Skewness of {metrics.skewness.toFixed(2)} 
                {metrics.skewness > 0 ? ' (right-tailed)' : ' (left-tailed)'}, 
                Kurtosis of {metrics.kurtosis.toFixed(2)}
                {Math.abs(metrics.kurtosis) > 3 ? ' (fat tails - outlier risk)' : ' (normal distribution)'}.
              </li>
            </ul>
          </div>
          
          <div className="recommendation" style={{ marginTop: '15px' }}>
            <strong>Position Sizing Recommendation:</strong> Based on the {(metrics.volatility_annual * 100).toFixed(0)}% 
            annual volatility and {(Math.abs(metrics.max_drawdown) * 100).toFixed(0)}% max drawdown, 
            consider limiting position size to {metrics.volatility_annual > 0.4 ? '1-2%' : metrics.volatility_annual > 0.2 ? '3-5%' : '5-10%'} 
            {' '}of portfolio to manage risk appropriately.
          </div>
        </div>
      )}
    </>
  );
}

export default RiskMetrics;
