import React, { useState } from 'react';
import axios from 'axios';

function GreeksCalculator({ apiUrl }) {
  const [symbol, setSymbol] = useState('AAPL');
  const [spotPrice, setSpotPrice] = useState('170');
  const [strike, setStrike] = useState('175');
  const [daysToExpiry, setDaysToExpiry] = useState('30');
  const [volatility, setVolatility] = useState('0.3');
  const [riskFreeRate, setRiskFreeRate] = useState('0.05');
  const [optionType, setOptionType] = useState('call');
  const [greeks, setGreeks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const calculateGreeks = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const timeToExpiry = parseFloat(daysToExpiry) / 365;
      
      const response = await axios.post(`${apiUrl}/api/greeks/${symbol}`, {
        spot_price: parseFloat(spotPrice),
        strike: parseFloat(strike),
        time_to_expiry: timeToExpiry,
        volatility: parseFloat(volatility),
        risk_free_rate: parseFloat(riskFreeRate),
        option_type: optionType
      });
      
      setGreeks(response.data.greeks);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2>Greeks Calculator</h2>
        
        <div className="input-group">
          <label>Symbol</label>
          <input 
            type="text" 
            value={symbol} 
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          />
        </div>
        
        <div className="input-group">
          <label>Option Type</label>
          <select 
            value={optionType} 
            onChange={(e) => setOptionType(e.target.value)}
            style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '2px solid #ddd' }}
          >
            <option value="call">Call</option>
            <option value="put">Put</option>
          </select>
        </div>
        
        <div className="input-group">
          <label>Spot Price ($)</label>
          <input 
            type="number" 
            value={spotPrice} 
            onChange={(e) => setSpotPrice(e.target.value)}
            step="0.01"
          />
        </div>
        
        <div className="input-group">
          <label>Strike Price ($)</label>
          <input 
            type="number" 
            value={strike} 
            onChange={(e) => setStrike(e.target.value)}
            step="0.01"
          />
        </div>
        
        <div className="input-group">
          <label>Days to Expiry</label>
          <input 
            type="number" 
            value={daysToExpiry} 
            onChange={(e) => setDaysToExpiry(e.target.value)}
            min="1"
          />
        </div>
        
        <div className="input-group">
          <label>Volatility (annual, e.g., 0.3 for 30%)</label>
          <input 
            type="number" 
            value={volatility} 
            onChange={(e) => setVolatility(e.target.value)}
            step="0.01"
          />
        </div>
        
        <div className="input-group">
          <label>Risk-Free Rate (e.g., 0.05 for 5%)</label>
          <input 
            type="number" 
            value={riskFreeRate} 
            onChange={(e) => setRiskFreeRate(e.target.value)}
            step="0.001"
          />
        </div>
        
        <button className="btn" onClick={calculateGreeks} disabled={loading}>
          {loading ? 'Calculating...' : 'Calculate Greeks'}
        </button>
        
        {error && <div className="error">Error: {error}</div>}
      </div>

      {greeks && (
        <div className="card">
          <h2>Greeks Results</h2>
          
          <div className="metric-item" style={{ marginBottom: '20px' }}>
            <div className="metric-label">Option Price</div>
            <div className="metric-value" style={{ fontSize: '2em', color: '#0a0' }}>
              ${greeks.price?.toFixed(2)}
            </div>
          </div>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Delta (Δ)</div>
              <div className="metric-value">{greeks.delta?.toFixed(4)}</div>
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>
                Price change per $1 move
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Gamma (Γ)</div>
              <div className="metric-value">{greeks.gamma?.toFixed(4)}</div>
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>
                Delta change per $1 move
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Vega (ν) per 1%</div>
              <div className="metric-value">{greeks.vega_per_1pct?.toFixed(4)}</div>
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>
                Price change per 1% vol
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Theta (Θ)</div>
              <div className="metric-value">{greeks.theta?.toFixed(4)}</div>
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>
                Price change per day
              </div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Rho (ρ) per 1%</div>
              <div className="metric-value">{greeks.rho_per_1pct?.toFixed(4)}</div>
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>
                Price change per 1% rate
              </div>
            </div>
          </div>
          
          <div style={{ marginTop: '20px', padding: '15px', background: '#f0f0f0', borderRadius: '6px' }}>
            <h3 style={{ marginTop: 0, fontSize: '1.1em' }}>Greeks Interpretation:</h3>
            <ul style={{ marginBottom: 0, paddingLeft: '20px' }}>
              <li><strong>Delta:</strong> Shows directional exposure. {Math.abs(greeks.delta) > 0.5 ? 'High' : 'Low'} sensitivity to price movements.</li>
              <li><strong>Gamma:</strong> Measures delta acceleration. {greeks.gamma > 0.01 ? 'High' : 'Low'} convexity risk.</li>
              <li><strong>Vega:</strong> {greeks.vega_per_1pct > 0.1 ? 'Significant' : 'Moderate'} exposure to volatility changes.</li>
              <li><strong>Theta:</strong> Time decay of ${Math.abs(greeks.theta).toFixed(2)} per day.</li>
              <li><strong>Rho:</strong> {Math.abs(greeks.rho_per_1pct) > 0.1 ? 'Notable' : 'Limited'} interest rate sensitivity.</li>
            </ul>
          </div>
        </div>
      )}
    </>
  );
}

export default GreeksCalculator;
