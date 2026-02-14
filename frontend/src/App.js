import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
import SentimentAnalysis from './components/SentimentAnalysis';
import OpportunityFinder from './components/OpportunityFinder';
import GreeksCalculator from './components/GreeksCalculator';
import RiskMetrics from './components/RiskMetrics';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [activeTab, setActiveTab] = useState('sentiment');

  return (
    <div className="App">
      <header className="header">
        <h1>📈 TradeAI - Derivatives Sentiment Tracker</h1>
        <p>Find High-Confidence Trading Opportunities in Financial Derivatives</p>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'sentiment' ? 'active' : ''}`}
          onClick={() => setActiveTab('sentiment')}
        >
          Sentiment Analysis
        </button>
        <button 
          className={`tab ${activeTab === 'opportunities' ? 'active' : ''}`}
          onClick={() => setActiveTab('opportunities')}
        >
          Find Opportunities
        </button>
        <button 
          className={`tab ${activeTab === 'greeks' ? 'active' : ''}`}
          onClick={() => setActiveTab('greeks')}
        >
          Greeks Calculator
        </button>
        <button 
          className={`tab ${activeTab === 'risk' ? 'active' : ''}`}
          onClick={() => setActiveTab('risk')}
        >
          Risk Metrics
        </button>
      </div>

      <div className="main-content">
        {activeTab === 'sentiment' && <SentimentAnalysis apiUrl={API_BASE_URL} />}
        {activeTab === 'opportunities' && <OpportunityFinder apiUrl={API_BASE_URL} />}
        {activeTab === 'greeks' && <GreeksCalculator apiUrl={API_BASE_URL} />}
        {activeTab === 'risk' && <RiskMetrics apiUrl={API_BASE_URL} />}
      </div>

      <footer style={{ textAlign: 'center', color: 'white', marginTop: '40px', padding: '20px' }}>
        <p><strong>Derivatives Trading - Key Metrics Tracked:</strong></p>
        <p>
          Sentiment Score • Volatility Analysis • Greeks (Delta, Gamma, Vega, Theta, Rho) • 
          Risk Metrics • Put/Call Ratios • Volume Analysis • Technical Indicators
        </p>
        <p style={{ marginTop: '20px', fontSize: '0.9em', opacity: 0.8 }}>
          ⚠️ Disclaimer: This tool is for educational and informational purposes only. 
          Not financial advice. Always do your own research and consult with a financial advisor.
        </p>
      </footer>
    </div>
  );
}

export default App;
