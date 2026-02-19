import React, { useState } from 'react';
import ETFOpportunities from "./components/ETFOpportunities";
import DirectionalTickets from "./components/DirectionalTickets";
import './App.css';
import SentimentAnalysis from './components/SentimentAnalysis';
import OpportunityFinder from './components/OpportunityFinder';
import GreeksCalculator from './components/GreeksCalculator';
import RiskMetrics from './components/RiskMetrics';
import EarningsPlaybook from './components/EarningsPlaybook';
import TradeTickets from './components/TradeTickets';
import PendingTicketsSPY from "./components/PendingTicketsSpy";



const API_BASE_URL = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5055';

function App() {
  const [activeTab, setActiveTab] = useState('sentiment');
  const [selectedETF, setSelectedETF] = useState(null);


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
        <button 
          className={`tab ${activeTab === 'earnings' ? 'active' : ''}`}
          onClick={() => setActiveTab('earnings')}
        >
          Earnings Playbook
        </button>
        <button 
          className={`tab ${activeTab === 'tickets' ? 'active' : ''}`}
          onClick={() => setActiveTab('tickets')}
        >
          Trade Tickets
        </button>
        <button 
          className={`tab ${activeTab === 'spy' ? 'active' : ''}`}
          onClick={() => setActiveTab('spy')}
        >
          SPY Tickets
        </button>
        <button
          className={`tab ${activeTab === 'etf' ? 'active' : ''}`}
          onClick={() => setActiveTab('etf')}
        >
          ETF Directional
        </button>
       </div>

    <div className="main-content">
      {activeTab === 'sentiment' && <SentimentAnalysis apiUrl={API_BASE_URL} />}
      {activeTab === 'opportunities' && <OpportunityFinder apiUrl={API_BASE_URL} />}
      {activeTab === 'greeks' && <GreeksCalculator apiUrl={API_BASE_URL} />}
      {activeTab === 'risk' && <RiskMetrics apiUrl={API_BASE_URL} />}
      {activeTab === 'earnings' && <EarningsPlaybook apiUrl={API_BASE_URL} />}
      {activeTab === 'tickets' && <TradeTickets apiUrl={API_BASE_URL} />}
      {activeTab === 'spy' && <PendingTicketsSPY />}
      {activeTab === 'etf' && (
        <div>
          <ETFOpportunities onSelect={setSelectedETF} />
          <div style={{ height: 12 }} />
          <DirectionalTickets selected={selectedETF} />
        </div>
      )}
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
