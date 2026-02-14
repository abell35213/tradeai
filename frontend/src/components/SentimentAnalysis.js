import React, { useState } from 'react';
import axios from 'axios';

function SentimentAnalysis({ apiUrl }) {
  const [symbol, setSymbol] = useState('AAPL');
  const [sentiment, setSentiment] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeSentiment = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [sentimentRes, marketRes] = await Promise.all([
        axios.get(`${apiUrl}/api/sentiment/${symbol}`),
        axios.get(`${apiUrl}/api/market-data/${symbol}`)
      ]);
      
      setSentiment(sentimentRes.data.sentiment);
      setMarketData(marketRes.data.data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSentimentClass = (score) => {
    if (score > 0.2) return 'positive';
    if (score < -0.2) return 'negative';
    return 'neutral';
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    return num.toFixed(2);
  };

  return (
    <>
      <div className="card">
        <h2>Sentiment Analysis</h2>
        
        <div className="input-group">
          <label>Ticker Symbol</label>
          <input 
            type="text" 
            value={symbol} 
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Enter symbol (e.g., AAPL, SPY)"
            onKeyPress={(e) => e.key === 'Enter' && analyzeSentiment()}
          />
        </div>
        
        <button className="btn" onClick={analyzeSentiment} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze Sentiment'}
        </button>
        
        {error && <div className="error">Error: {error}</div>}
      </div>

      {sentiment && (
        <div className="card">
          <h2>Sentiment Results for {symbol}</h2>
          
          <div className={`sentiment-score ${getSentimentClass(sentiment.overall_score)}`}>
            {sentiment.overall_score > 0 ? '+' : ''}{(sentiment.overall_score * 100).toFixed(1)}%
          </div>
          
          <div className="recommendation">
            <strong>Recommendation:</strong> {sentiment.recommendation}
          </div>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Confidence</div>
              <div className="metric-value">{(sentiment.confidence * 100).toFixed(0)}%</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Technical Trend</div>
              <div className="metric-value">{sentiment.technical?.trend || 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Volume Signal</div>
              <div className="metric-value">{sentiment.volume?.signal || 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Volatility Regime</div>
              <div className="metric-value">{sentiment.volatility?.regime || 'N/A'}</div>
            </div>
          </div>
        </div>
      )}

      {marketData && (
        <div className="card full-width">
          <h2>Market Data for {symbol}</h2>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Current Price</div>
              <div className="metric-value">${marketData.current_price?.toFixed(2) || 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Annual Volatility</div>
              <div className="metric-value">{marketData.volatility ? (marketData.volatility * 100).toFixed(1) + '%' : 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Market Cap</div>
              <div className="metric-value">{formatNumber(marketData.market_cap)}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Volume</div>
              <div className="metric-value">{marketData.volume?.toLocaleString() || 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">Beta</div>
              <div className="metric-value">{marketData.beta?.toFixed(2) || 'N/A'}</div>
            </div>
            
            <div className="metric-item">
              <div className="metric-label">P/E Ratio</div>
              <div className="metric-value">{marketData.pe_ratio?.toFixed(2) || 'N/A'}</div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default SentimentAnalysis;
