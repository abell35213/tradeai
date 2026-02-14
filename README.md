# TradeAI - Derivatives Trading Sentiment Tracker

An automated web application for tracking sentiment and identifying high-confidence trading opportunities in financial derivatives.

## 🎯 Overview

TradeAI helps derivatives traders make informed decisions by providing:

- **Real-time Sentiment Analysis**: Comprehensive market sentiment scoring based on technical indicators, volume patterns, and volatility
- **Options Greeks Calculator**: Black-Scholes pricing model with full Greeks (Delta, Gamma, Vega, Theta, Rho)
- **Opportunity Finder**: Automated scanning to identify high-probability trades
- **Risk Metrics**: Advanced risk analysis including VaR, Sharpe ratio, and drawdown analysis

## 📊 What Top Derivatives Traders Track

This application addresses the key metrics and data that professional derivatives traders monitor:

### Data Tracked:
1. **Market Sentiment Indicators**
   - Technical momentum and trend analysis
   - Volume patterns and price-volume correlation
   - Volatility regime classification

2. **Options Analytics**
   - Greeks (Delta, Gamma, Vega, Theta, Rho)
   - Implied vs Historical Volatility
   - Put/Call Ratios
   - Open Interest and Volume

3. **Risk Metrics**
   - Value at Risk (VaR)
   - Sharpe Ratio
   - Maximum Drawdown
   - Distribution characteristics (Skewness, Kurtosis)

### Assumptions Validated:
- **Market Efficiency**: Checks for anomalies in pricing
- **Liquidity Conditions**: Analyzes volume and open interest
- **Volatility Predictions**: Compares implied vs realized volatility
- **Risk/Reward Ratios**: Calculates probability-weighted outcomes

### Investment Strategy Components:
- Entry/exit signals based on multi-factor sentiment
- Position sizing recommendations based on volatility
- Strategy recommendations (long calls, spreads, straddles, etc.)
- Confidence scoring for decision support

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 14+
- npm or yarn

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/abell35213/tradeai.git
cd tradeai
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Frontend dependencies**
```bash
cd frontend
npm install
cd ..
```

### Running the Application

#### Development Mode

1. **Start the Backend API**
```bash
# For development with debug mode enabled
DEBUG=true DEMO_MODE=true python backend/app.py
```
The API will be available at `http://localhost:5000`

2. **Start the Frontend (in a new terminal)**
```bash
cd frontend
npm start
```
The web app will open at `http://localhost:3000`

#### Production Mode

For production deployment, ensure debug mode is disabled:

```bash
# Production mode (debug disabled, requires internet for real data)
python backend/app.py
```

**Security Note:** Never run Flask with `debug=True` in production environments as it can expose sensitive information and allow arbitrary code execution.

## 💡 Features

### 1. Sentiment Analysis
- Analyzes ticker symbols for bullish/bearish sentiment
- Combines technical, volume, and volatility signals
- Provides confidence scores and actionable recommendations

### 2. Opportunity Finder
- Scans multiple symbols simultaneously
- Ranks opportunities by score and confidence
- Suggests specific derivatives strategies for each opportunity
- Displays options chain data when available

### 3. Greeks Calculator
- Calculate theoretical option prices using Black-Scholes model
- Compute all Greeks for risk management
- Understand sensitivity to price, volatility, time, and interest rates
- Get interpretation of each Greek metric

### 4. Risk Metrics
- Volatility analysis (daily and annual)
- Sharpe ratio for risk-adjusted returns
- Value at Risk (VaR) calculations
- Distribution analysis for tail risk
- Position sizing recommendations

## 🏗️ Architecture

```
tradeai/
├── backend/
│   ├── app.py                      # Flask API server
│   ├── sentiment_analyzer.py      # Sentiment analysis module
│   ├── derivatives_calculator.py  # Black-Scholes & Greeks
│   └── opportunity_finder.py      # Opportunity identification
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SentimentAnalysis.js
│   │   │   ├── OpportunityFinder.js
│   │   │   ├── GreeksCalculator.js
│   │   │   └── RiskMetrics.js
│   │   ├── App.js
│   │   └── index.js
│   └── public/
└── requirements.txt
```

## 📡 API Endpoints

### Market Data
- `GET /api/health` - Health check
- `GET /api/sentiment/<symbol>` - Get sentiment analysis
- `GET /api/market-data/<symbol>` - Get market data
- `GET /api/options/<symbol>` - Get options chain
- `GET /api/risk-metrics/<symbol>` - Get risk metrics

### Calculations
- `POST /api/greeks/<symbol>` - Calculate option Greeks
- `POST /api/opportunities` - Find trading opportunities

## 🎓 Usage Examples

### Analyzing a Stock
1. Go to "Sentiment Analysis" tab
2. Enter ticker symbol (e.g., AAPL)
3. Click "Analyze Sentiment"
4. Review sentiment score, confidence, and recommendation

### Finding Opportunities
1. Go to "Find Opportunities" tab
2. Enter comma-separated symbols (e.g., SPY,QQQ,AAPL)
3. Set minimum confidence threshold
4. Click "Find Opportunities"
5. Review ranked opportunities with strategy suggestions

### Calculating Greeks
1. Go to "Greeks Calculator" tab
2. Enter option parameters (spot, strike, expiry, volatility)
3. Select call or put
4. Click "Calculate Greeks"
5. Review option price and all Greeks

## ⚠️ Disclaimer

**This tool is for educational and informational purposes only.**

- NOT financial advice
- Past performance does not guarantee future results
- Trading derivatives involves substantial risk of loss
- Always do your own research
- Consult with a licensed financial advisor before making investment decisions

## 🔧 Technologies Used

### Backend
- **Flask**: Web framework for API
- **yfinance**: Market data retrieval
- **pandas/numpy**: Data processing
- **scipy**: Statistical calculations
- **textblob**: Sentiment analysis capabilities

### Frontend
- **React**: UI framework
- **Axios**: HTTP client
- **Recharts**: Data visualization

## 📈 Future Enhancements

- Real-time news sentiment integration
- Machine learning models for prediction
- Backtesting capabilities
- Portfolio tracking and management
- Advanced options strategies (Iron Condor, Butterfly, etc.)
- Alert system for opportunities
- Historical performance tracking

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

MIT License - see LICENSE file for details

## 📞 Support

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ for derivatives traders**
