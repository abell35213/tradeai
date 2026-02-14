# TradeAI Development Guide

## Project Structure

### Backend (`/backend`)

The backend is a Flask-based REST API that provides endpoints for market analysis and derivatives calculations.

#### Modules:

1. **app.py** - Main Flask application
   - API endpoint definitions
   - Request handling and response formatting
   - CORS configuration

2. **sentiment_analyzer.py** - Market sentiment analysis
   - Technical analysis (moving averages, momentum)
   - Volume pattern analysis
   - Volatility regime detection
   - Multi-factor sentiment scoring

3. **derivatives_calculator.py** - Options pricing and Greeks
   - Black-Scholes option pricing model
   - Greeks calculation (Delta, Gamma, Vega, Theta, Rho)
   - Implied volatility calculation
   - Probability analysis

4. **opportunity_finder.py** - Trading opportunity identification
   - Multi-symbol scanning
   - Opportunity scoring algorithm
   - Strategy recommendation engine
   - Options chain analysis

### Frontend (`/frontend`)

React-based single-page application for user interaction.

#### Components:

1. **SentimentAnalysis.js** - Sentiment analysis interface
   - Symbol input and analysis trigger
   - Sentiment visualization
   - Market data display

2. **OpportunityFinder.js** - Opportunity scanning interface
   - Multi-symbol input
   - Confidence threshold adjustment
   - Ranked opportunity display
   - Strategy recommendations

3. **GreeksCalculator.js** - Options calculator
   - Parameter input form
   - Greeks calculation display
   - Interpretation guide

4. **RiskMetrics.js** - Risk analysis interface
   - Risk metric display
   - Risk level assessment
   - Position sizing recommendations

## Development Workflow

### Running in Development Mode

1. **Backend Development**:
   ```bash
   # Start backend with auto-reload
   python backend/app.py
   ```
   - API available at `http://localhost:5000`
   - Debug mode enabled for development
   - Auto-reloads on code changes

2. **Frontend Development**:
   ```bash
   cd frontend
   npm start
   ```
   - App available at `http://localhost:3000`
   - Hot-reload enabled
   - Opens automatically in browser

### Testing API Endpoints

Use curl or Postman to test endpoints:

```bash
# Health check
curl http://localhost:5000/api/health

# Get sentiment
curl http://localhost:5000/api/sentiment/AAPL

# Get market data
curl http://localhost:5000/api/market-data/SPY

# Calculate Greeks
curl -X POST http://localhost:5000/api/greeks/AAPL \
  -H "Content-Type: application/json" \
  -d '{
    "spot_price": 170,
    "strike": 175,
    "time_to_expiry": 0.082,
    "volatility": 0.3,
    "risk_free_rate": 0.05,
    "option_type": "call"
  }'

# Find opportunities
curl -X POST http://localhost:5000/api/opportunities \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ", "AAPL"],
    "min_confidence": 0.6
  }'
```

## Adding New Features

### Adding a New API Endpoint

1. Define the endpoint in `backend/app.py`:
```python
@app.route('/api/my-endpoint/<symbol>', methods=['GET'])
def my_endpoint(symbol):
    try:
        # Your logic here
        result = process_data(symbol)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

2. Create a corresponding frontend component/function

3. Update documentation

### Adding a New Frontend Component

1. Create component file in `frontend/src/components/`
2. Import and use in `App.js`
3. Add styling in `App.css`
4. Test component functionality

## Data Sources

### Market Data (yfinance)
- Real-time and historical price data
- Options chains
- Company fundamentals
- Market indices

### Limitations
- 15-minute delay for real-time data
- Rate limiting on API calls
- Historical data availability varies by symbol

## Algorithms & Models

### Sentiment Scoring
Combines three components:
1. **Technical (50%)**: Price momentum and trend
2. **Volume (25%)**: Volume patterns and correlation
3. **Volatility (25%)**: Volatility regime

Score range: -1 (bearish) to +1 (bullish)

### Greeks Calculation
Uses Black-Scholes model:
- Assumes log-normal distribution
- European-style options
- No dividends (can be extended)
- Constant volatility and interest rate

### Opportunity Scoring
Scale 0-100 based on:
- Sentiment strength and confidence (40 pts)
- Volatility suitability (20 pts)
- Options availability (20 pts)
- Consistency bonus (20 pts)

## Error Handling

### Backend
- All endpoints use try-catch with error responses
- HTTP status codes: 200 (success), 404 (not found), 500 (error)
- Validation of input parameters

### Frontend
- Error state management in components
- User-friendly error messages
- Graceful degradation

## Performance Considerations

### Backend
- Caching can be added for frequently requested symbols
- Rate limiting to prevent API abuse
- Async processing for multiple symbol analysis

### Frontend
- Component-level state management
- Lazy loading for large data sets
- Debouncing for user inputs

## Security Notes

### API Security
- CORS enabled for localhost development
- Should add authentication for production
- Input validation on all endpoints
- Rate limiting recommended

### Data Privacy
- No user data stored
- Market data is public information
- No PII collected

## Deployment

### Production Considerations

1. **Backend**:
   - Use production WSGI server (gunicorn, uWSGI)
   - Set `debug=False`
   - Configure proper CORS origins
   - Add authentication if needed
   - Set up logging and monitoring

2. **Frontend**:
   - Build production bundle: `npm run build`
   - Serve static files via nginx/Apache
   - Update API URL in environment variables
   - Enable compression and caching

3. **Infrastructure**:
   - Consider containerization (Docker)
   - Set up CI/CD pipeline
   - Monitor API usage and performance
   - Implement backup strategies

## Troubleshooting

### Common Issues

1. **CORS errors**: 
   - Check backend CORS configuration
   - Verify API URL in frontend

2. **No data returned**:
   - Symbol may not exist
   - Market may be closed
   - Rate limiting from data source

3. **Calculation errors**:
   - Verify input parameters
   - Check for division by zero
   - Ensure positive time to expiry

## Contributing

When contributing:
1. Follow existing code style
2. Add comments for complex logic
3. Test all changes
4. Update documentation
5. Submit PR with clear description

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [yfinance Documentation](https://pypi.org/project/yfinance/)
- [Black-Scholes Model](https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model)
- [Options Greeks Explained](https://www.investopedia.com/trading/using-the-greeks-to-understand-options/)
