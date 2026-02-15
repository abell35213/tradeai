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
from earnings_analyzer import EarningsAnalyzer
from regime_classifier import RegimeClassifier
from risk_engine import RiskEngine
from position_sizer import PositionSizer
from vol_surface_analyzer import VolSurfaceAnalyzer
from market_data_provider import YFinanceDataProvider
from circuit_breaker import CircuitBreaker
from trade_ticket import build_trade_ticket, evaluate_ticket
from backtester.earnings_backtest import EarningsBacktester
from backtester.vol_decay_analysis import VolDecayAnalyzer
from backtester.setup_performance import SetupPerformanceTracker
from demo_data import get_mock_sentiment, get_mock_market_data, get_mock_risk_metrics, get_mock_earnings_calendar, get_mock_earnings_snapshot
import os

app = Flask(__name__)
CORS(app)

# Demo mode flag (set to True when no internet access)
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'

# Initialize components
sentiment_analyzer = SentimentAnalyzer()
derivatives_calc = DerivativesCalculator()
opportunity_finder = OpportunityFinder()
earnings_analyzer = EarningsAnalyzer()
regime_classifier = RegimeClassifier()
risk_engine = RiskEngine()
position_sizer = PositionSizer()
vol_surface_analyzer = VolSurfaceAnalyzer()
market_data_provider = YFinanceDataProvider()
circuit_breaker = CircuitBreaker()
earnings_backtester = EarningsBacktester()
vol_decay_analyzer = VolDecayAnalyzer()
setup_tracker = SetupPerformanceTracker(earnings_analyzer=earnings_analyzer)

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
        if DEMO_MODE:
            sentiment_data = get_mock_sentiment(symbol)
        else:
            sentiment_data = sentiment_analyzer.analyze_symbol(symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'sentiment': sentiment_data,
            'demo_mode': DEMO_MODE
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
        if DEMO_MODE:
            data = get_mock_market_data(symbol)
        else:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            history = ticker.history(period="1mo")
            
            # Calculate key metrics
            current_price = history['Close'].iloc[-1] if len(history) > 0 else None
            volatility = history['Close'].pct_change().std() * (252 ** 0.5) if len(history) > 1 else None
            
            data = {
                'current_price': float(current_price) if current_price else None,
                'volatility': float(volatility) if volatility else None,
                'market_cap': info.get('marketCap'),
                'volume': int(history['Volume'].iloc[-1]) if len(history) > 0 else None,
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
            }
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': data,
            'demo_mode': DEMO_MODE
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
        dividend_yield = data.get('dividend_yield', 0.0)
        
        greeks = derivatives_calc.calculate_greeks(
            spot_price, strike, time_to_expiry, 
            volatility, risk_free_rate, option_type,
            q=dividend_yield,
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
        if DEMO_MODE:
            metrics = get_mock_risk_metrics(symbol)
        else:
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
            'risk_metrics': metrics,
            'demo_mode': DEMO_MODE
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/earnings/calendar', methods=['GET'])
def get_earnings_calendar():
    """Get earnings calendar for a given month"""
    try:
        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        if DEMO_MODE:
            calendar = get_mock_earnings_calendar(year, month)
        else:
            calendar = earnings_analyzer.get_earnings_calendar(year, month)

        return jsonify({
            'success': True,
            'year': year,
            'month': month,
            'calendar': calendar,
            'demo_mode': DEMO_MODE
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/earnings/snapshot/<symbol>', methods=['GET'])
def get_earnings_snapshot(symbol):
    """Get pre-earnings sentiment snapshot for a symbol"""
    try:
        if DEMO_MODE:
            snapshot = get_mock_earnings_snapshot(symbol)
        else:
            snapshot = earnings_analyzer.get_earnings_snapshot(symbol)

        return jsonify({
            'success': True,
            'symbol': symbol,
            'snapshot': snapshot,
            'demo_mode': DEMO_MODE
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Regime classification
# ------------------------------------------------------------------

@app.route('/api/regime', methods=['GET'])
def get_regime():
    """Get current market regime classification"""
    try:
        regime = regime_classifier.classify()
        return jsonify({
            'success': True,
            'regime': regime,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Risk engine
# ------------------------------------------------------------------

@app.route('/api/risk/portfolio', methods=['POST'])
def get_portfolio_risk():
    """Calculate portfolio-level risk metrics"""
    try:
        data = request.json
        positions = data.get('positions', [])
        risk = risk_engine.calculate_portfolio_risk(positions)
        return jsonify({
            'success': True,
            'risk': risk,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Position sizing
# ------------------------------------------------------------------

@app.route('/api/position-size', methods=['POST'])
def calculate_position_size():
    """Calculate recommended position size"""
    try:
        data = request.json
        symbol = data.get('symbol')
        confidence_score = data.get('confidence_score', 3)
        historical_edge = data.get('historical_edge', 0.5)
        implied_edge = data.get('implied_edge')
        base_risk = data.get('base_risk')

        if symbol:
            result = position_sizer.size_from_symbol(
                symbol=symbol,
                confidence_score=confidence_score,
                historical_edge=historical_edge,
                implied_edge=implied_edge,
                base_risk=base_risk,
            )
        else:
            liquidity_score = data.get('liquidity_score', 0.5)
            result = position_sizer.calculate_size(
                confidence_score=confidence_score,
                liquidity_score=liquidity_score,
                historical_edge=historical_edge,
                implied_edge=implied_edge,
                base_risk=base_risk,
            )

        return jsonify({
            'success': True,
            'sizing': result,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Vol surface analysis
# ------------------------------------------------------------------

@app.route('/api/vol-surface/<symbol>', methods=['GET'])
def get_vol_surface(symbol):
    """Get vol surface analysis for a symbol"""
    try:
        analysis = vol_surface_analyzer.analyze(symbol)
        return jsonify({
            'success': True,
            'symbol': symbol,
            'analysis': analysis,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Backtesting
# ------------------------------------------------------------------

@app.route('/api/backtest/earnings/<symbol>', methods=['GET'])
def backtest_earnings(symbol):
    """Backtest earnings strategy for a symbol"""
    try:
        years = request.args.get('years', 10, type=int)
        strategy = request.args.get('strategy', 'straddle')
        result = earnings_backtester.backtest_earnings(symbol, years=years, strategy=strategy)
        return jsonify({
            'success': True,
            'backtest': result,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/backtest/vol-decay/<symbol>', methods=['GET'])
def backtest_vol_decay(symbol):
    """Analyze vol decay patterns for a symbol"""
    try:
        years = request.args.get('years', 5, type=int)
        result = vol_decay_analyzer.analyze_vol_decay(symbol, years=years)
        return jsonify({
            'success': True,
            'vol_decay': result,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/backtest/setup-performance', methods=['POST'])
def get_setup_performance():
    """Get performance metrics by setup type"""
    try:
        data = request.json
        symbols = data.get('symbols', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'])
        years = data.get('years', 10)
        result = setup_tracker.get_performance_by_setup(symbols, years=years)
        return jsonify({
            'success': True,
            'performance': result,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/backtest/sharpe-by-setup', methods=['POST'])
def get_sharpe_by_setup():
    """Get Sharpe ratio by setup type"""
    try:
        data = request.json
        symbols = data.get('symbols', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'])
        years = data.get('years', 10)
        result = setup_tracker.get_sharpe_by_setup(symbols, years=years)
        return jsonify({
            'success': True,
            'sharpe': result,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ------------------------------------------------------------------
# Circuit breaker
# ------------------------------------------------------------------

@app.route('/api/circuit-breaker', methods=['POST'])
def check_circuit_breaker():
    """Check all kill-switches and return trading permission."""
    try:
        data = request.json or {}
        weekly_pnl_pct = data.get('weekly_pnl_pct', 0.0)
        vix_percentile = data.get('vix_percentile', 50.0)
        vix_day_change_pct = data.get('vix_day_change_pct', 0.0)

        # Attempt to get calendar events from data provider
        try:
            calendar_events = market_data_provider.get_calendar_events()
        except Exception:
            calendar_events = []

        # Regime info (optional)
        regime_label = data.get('regime_label')
        macro_proximity_elevated = data.get('macro_proximity_elevated')

        result = circuit_breaker.check_all(
            weekly_pnl_pct=weekly_pnl_pct,
            vix_percentile=vix_percentile,
            vix_day_change_pct=vix_day_change_pct,
            calendar_events=calendar_events,
            regime_label=regime_label,
            macro_proximity_elevated=macro_proximity_elevated,
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------------------------------------------------------
# Regime trade gate
# ------------------------------------------------------------------

@app.route('/api/regime/should-trade', methods=['GET'])
def regime_should_trade():
    """Check whether regime conditions allow trading."""
    try:
        result = regime_classifier.should_trade()
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------------------------------------------------------
# Trade ticket
# ------------------------------------------------------------------

@app.route('/api/trade-ticket', methods=['POST'])
def submit_trade_ticket():
    """Build a trade ticket and evaluate portfolio risk after trade."""
    try:
        data = request.json
        ticket = build_trade_ticket(
            symbol=data['symbol'],
            strategy=data['strategy'],
            legs=data['legs'],
            credit=data['credit'],
            max_loss=data['max_loss'],
            breakevens=data['breakevens'],
            quantity=data.get('quantity', 1),
            expiry=data.get('expiry'),
            notes=data.get('notes'),
        )
        existing = data.get('existing_positions', [])
        ticket = evaluate_ticket(ticket, risk_engine, existing)
        return jsonify({'success': True, 'ticket': ticket})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Derivatives Trading Sentiment Tracker API...")
    print("Available at: http://localhost:5000")
    if DEMO_MODE:
        print("⚠️  DEMO MODE: Using mock data (no internet connection)")
    
    # Debug mode should be disabled in production
    # Set DEBUG environment variable to 'true' for development
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
