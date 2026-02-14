"""
Derivatives Trading Sentiment Tracker - Main Flask Application

This application provides endpoints for:
- Market sentiment analysis
- Derivatives pricing and Greeks calculation
- Trading opportunity identification
- Risk metrics and validation
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import yfinance as yf
from sentiment_analyzer import SentimentAnalyzer
from derivatives_calculator import DerivativesCalculator
from opportunity_finder import OpportunityFinder

app = Flask(__name__)
CORS(app)

# Initialize components
sentiment_analyzer = SentimentAnalyzer()
derivatives_calc = DerivativesCalculator()
opportunity_finder = OpportunityFinder()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sentiment/<symbol>', methods=['GET'])
def get_sentiment(symbol):
    """Get sentiment analysis for a given symbol"""
    try:
        sentiment_data = sentiment_analyzer.analyze_symbol(symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'sentiment': sentiment_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/market-data/<symbol>', methods=['GET'])
def get_market_data(symbol):
    """Get market data for a given symbol"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period="1mo")
        
        # Calculate key metrics
        current_price = history['Close'].iloc[-1] if len(history) > 0 else None
        volatility = history['Close'].pct_change().std() * (252 ** 0.5) if len(history) > 1 else None
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': {
                'current_price': float(current_price) if current_price else None,
                'volatility': float(volatility) if volatility else None,
                'market_cap': info.get('marketCap'),
                'volume': int(history['Volume'].iloc[-1]) if len(history) > 0 else None,
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/options/<symbol>', methods=['GET'])
def get_options(symbol):
    """Get options chain and Greeks for a given symbol"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get available expiration dates
        expirations = ticker.options
        if not expirations:
            return jsonify({
                'success': False,
                'error': 'No options data available for this symbol'
            }), 404
        
        # Get first expiration date options
        exp_date = expirations[0]
        opt = ticker.option_chain(exp_date)
        
        # Calculate Greeks for top options
        calls = opt.calls.head(10).to_dict('records')
        puts = opt.puts.head(10).to_dict('records')
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'expiration': exp_date,
            'expirations': expirations,
            'calls': calls,
            'puts': puts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/greeks/<symbol>', methods=['POST'])
def calculate_greeks(symbol):
    """Calculate Greeks for a specific option"""
    try:
        data = request.json
        spot_price = data.get('spot_price')
        strike = data.get('strike')
        time_to_expiry = data.get('time_to_expiry')  # in years
        volatility = data.get('volatility')
        risk_free_rate = data.get('risk_free_rate', 0.05)
        option_type = data.get('option_type', 'call')
        
        greeks = derivatives_calc.calculate_greeks(
            spot_price, strike, time_to_expiry, 
            volatility, risk_free_rate, option_type
        )
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'greeks': greeks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/opportunities', methods=['POST'])
def find_opportunities():
    """Find trading opportunities based on criteria"""
    try:
        data = request.json
        symbols = data.get('symbols', ['SPY', 'QQQ', 'IWM'])
        min_confidence = data.get('min_confidence', 0.6)
        
        opportunities = opportunity_finder.find_opportunities(symbols, min_confidence)
        
        return jsonify({
            'success': True,
            'opportunities': opportunities,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/risk-metrics/<symbol>', methods=['GET'])
def get_risk_metrics(symbol):
    """Get risk metrics for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="3mo")
        
        if len(history) < 2:
            return jsonify({
                'success': False,
                'error': 'Insufficient data'
            }), 404
        
        returns = history['Close'].pct_change().dropna()
        
        metrics = {
            'volatility_daily': float(returns.std()),
            'volatility_annual': float(returns.std() * (252 ** 0.5)),
            'sharpe_ratio': float(returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0,
            'max_drawdown': float((history['Close'] / history['Close'].cummax() - 1).min()),
            'var_95': float(returns.quantile(0.05)),
            'skewness': float(returns.skew()),
            'kurtosis': float(returns.kurtosis())
        }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'risk_metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Derivatives Trading Sentiment Tracker API...")
    print("Available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
