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
import logging

# Suppress yfinance + underlying noisy logs
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

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
from etf_universe import get_etf_universe
from etf_ranker import ETFRanker
from circuit_breaker import CircuitBreaker
from trade_ticket import (
    TradeTicket, TicketLeg, EdgeMetrics, RegimeGate,
    RiskGate, PortfolioAfter, Exits,
    build_trade_ticket, evaluate_ticket,
)
from index_vol_engine import IndexVolEngine
from backtester.earnings_backtest import EarningsBacktester
from backtester.vol_decay_analysis import VolDecayAnalyzer
from backtester.setup_performance import SetupPerformanceTracker
from demo_data import (
    get_mock_sentiment, get_mock_market_data, get_mock_risk_metrics,
    get_mock_earnings_calendar, get_mock_earnings_snapshot,
    get_mock_vol_surface, get_mock_regime,
)
from validation import (
    GreeksRequest, TradeTicketRequest, PositionSizeRequest,
    CircuitBreakerRequest, OpportunitiesRequest, PortfolioRiskRequest,
    IndexVolTicketRequest, ExecuteRequest, TradeApproveRequest,
    TradeRejectRequest,
)
from db import (
    init_db, insert_ticket, approve_ticket as db_approve,
    reject_ticket as db_reject, list_pending_tickets as db_list_pending,
    get_ticket as db_get_ticket, get_audit_log,
)
from pydantic import ValidationError
import os
import json
import uuid

app = Flask(__name__)
CORS(app)

logger = logging.getLogger(__name__)

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
etf_ranker = ETFRanker()
circuit_breaker = CircuitBreaker()
earnings_backtester = EarningsBacktester()
vol_decay_analyzer = VolDecayAnalyzer()
setup_tracker = SetupPerformanceTracker(earnings_analyzer=earnings_analyzer)
index_vol_engine = IndexVolEngine(
    vol_surface_analyzer=vol_surface_analyzer,
    regime_classifier=regime_classifier,
    position_sizer=position_sizer,
    risk_engine=risk_engine,
)

# In-memory store for pending trade tickets (keyed by ticket_id)
_pending_tickets = {}
# In-memory log of approved / rejected tickets
_execution_log = []

# Initialise SQLite database for the manual-confirmation workflow
init_db()

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
        
@app.route('/api/etf/opportunities', methods=['GET'])
def get_etf_opportunities():
    """
    Return top ranked ETF opportunities (breakout-weighted) for directional sleeve.

    Query params:
      top (int): number of results, default 5
      min_score (int): minimum score threshold, default 65
    """
    try:
        top = request.args.get('top', 5, type=int)
        min_score = request.args.get('min_score', 65, type=int)

        symbols = get_etf_universe()
        
        if DEMO_MODE:
            # simple mock ranking so UI/dev flow works offline
            ranked = []
            demo_rows = [
                ("SPY", "bullish", "breakout", 78),
                ("QQQ", "bullish", "breakout", 74),
                ("XLE", "bullish", "pullback", 68),
                ("XLF", "bearish", "breakdown", 67),
                ("IWM", "bearish", "pullback", 61),
            ]
            for sym, bias, signal_type, score in demo_rows:
                if score < min_score:
                    continue
                ranked.append({
                    "symbol": sym,
                    "bias": bias,
                    "signal_type": signal_type,
                    "score": score,
                    "strength_label": "eligible" if score >= 65 else "caution",
                    "price": None,
                    "levels": {"trigger": None, "stop": None},
                    "components": {},
                    "metrics": {},
                })
            ranked = ranked[:top]
        else:
            ranked = etf_ranker.rank(symbols, top=top, min_score=min_score)

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'universe_size': len(symbols),
            'top': top,
            'min_score': min_score,
            'ranked': ranked,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        data = request.json or {}
        try:
            validated = GreeksRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422
        
        greeks = derivatives_calc.calculate_greeks(
            validated.spot_price, validated.strike, validated.time_to_expiry,
            validated.volatility, validated.risk_free_rate, validated.option_type,
            q=validated.dividend_yield,
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
        data = request.json or {}
        try:
            validated = OpportunitiesRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422
        
        opportunities = opportunity_finder.find_opportunities(
            validated.symbols, validated.min_confidence
        )
        
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
        data = request.json or {}
        try:
            validated = PortfolioRiskRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422
        risk = risk_engine.calculate_portfolio_risk(validated.positions)
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
        data = request.json or {}
        try:
            validated = PositionSizeRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422

        if validated.symbol:
            result = position_sizer.size_from_symbol(
                symbol=validated.symbol,
                confidence_score=validated.confidence_score,
                historical_edge=validated.historical_edge,
                implied_edge=validated.implied_edge,
                base_risk=validated.base_risk,
            )
        else:
            result = position_sizer.calculate_size(
                confidence_score=validated.confidence_score,
                liquidity_score=validated.liquidity_score,
                historical_edge=validated.historical_edge,
                implied_edge=validated.implied_edge,
                base_risk=validated.base_risk,
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
        try:
            validated = CircuitBreakerRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422

        # Attempt to get calendar events from data provider
        try:
            calendar_events = market_data_provider.get_calendar_events()
        except Exception:
            logger.exception("Failed to get calendar events from data provider")
            calendar_events = []

        result = circuit_breaker.check_all(
            weekly_pnl_pct=validated.weekly_pnl_pct,
            vix_percentile=validated.vix_percentile,
            vix_day_change_pct=validated.vix_day_change_pct,
            calendar_events=calendar_events,
            regime_label=validated.regime_label,
            macro_proximity_elevated=validated.macro_proximity_elevated,
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
        data = request.json or {}
        try:
            validated = TradeTicketRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422
        ticket = build_trade_ticket(
            underlying=validated.symbol,
            strategy=validated.strategy,
            legs=validated.legs,
            mid_credit=validated.credit,
            max_loss=validated.max_loss,
            width=validated.width,
            expiry=validated.expiry,
        )
        existing = validated.existing_positions
        ticket = evaluate_ticket(
            ticket, risk_engine, existing,
            equity=validated.equity,
            weekly_realized_pnl=validated.weekly_realized_pnl,
            existing_weekly_max_losses=validated.existing_weekly_max_losses,
        )
        return jsonify({'success': True, 'ticket': ticket.model_dump()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------------------------------------------------------
# Index vol engine  (edge-based signal)
# ------------------------------------------------------------------

@app.route('/api/index-vol/<symbol>', methods=['GET'])
def get_index_vol_analysis(symbol):
    """Get edge-based vol-selling analysis for a symbol."""
    try:
        if DEMO_MODE:
            from index_vol_engine import IndexVolEngine as _IVE
            vol_surface_data = get_mock_vol_surface(symbol)
            regime_data = get_mock_regime()
            trade_gate = regime_classifier.should_trade(regime_data)
            engine = _IVE()
            components = engine._score_components(vol_surface_data, regime_data)
            edge_score = engine._composite_edge(components)
            pass_fail = engine._evaluate_gate(edge_score, trade_gate, components)
            result = {
                'symbol': symbol,
                'edge_score': round(edge_score, 4),
                'components': components,
                'regime_snapshot': regime_data,
                'trade_gate': pass_fail,
                'sizing': None,
                'timestamp': datetime.now().isoformat(),
            }
        else:
            result = index_vol_engine.analyze(symbol)
        return jsonify({'success': True, 'analysis': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------------------------------------------------------
# Trade ticket pipeline  — index vol
# ------------------------------------------------------------------

@app.route('/api/trade-ticket/index-vol', methods=['POST'])
def generate_index_vol_ticket():
    """
    Generate a trade ticket for an index vol credit spread.

    Request body (JSON):
        symbol (str): Underlying ticker.
        existing_positions (list, optional): Current portfolio positions.

    Returns a full ticket with strikes, credit, max loss, POP estimate,
    regime snapshot, risk before/after, and an idempotency key.
    """
    try:
        data = request.json or {}
        try:
            validated = IndexVolTicketRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422
        symbol = validated.symbol
        existing = validated.existing_positions

        if DEMO_MODE:
            from index_vol_engine import IndexVolEngine as _IVE
            vol_surface_data = get_mock_vol_surface(symbol)
            regime_data = get_mock_regime()
            trade_gate = regime_classifier.should_trade(regime_data)
            engine = _IVE(risk_engine=risk_engine)
            components = engine._score_components(vol_surface_data, regime_data)
            edge_score = engine._composite_edge(components)
            pass_fail = engine._evaluate_gate(edge_score, trade_gate, components)

            risk_result = risk_engine.evaluate_ticket_risk(
                ticket_max_loss=375.0,
                ticket_position={
                    'symbol': symbol, 'delta': -0.30, 'vega': -0.10,
                    'gamma': -0.01, 'notional': 500,
                    'earnings_date': None, 'expiry_bucket': '7-30d',
                },
                existing_positions=existing,
                equity=validated.equity,
                weekly_realized_pnl=validated.weekly_realized_pnl,
                existing_weekly_max_losses=validated.existing_weekly_max_losses,
            )
            ticket = TradeTicket(
                ticket_id=str(uuid.uuid4()),
                underlying=symbol,
                strategy='SPY_PUT_CREDIT_SPREAD',
                expiry='2026-03-20',
                dte=33,
                legs=[
                    TicketLeg(type='put', side='sell', strike=470.0, qty=1),
                    TicketLeg(type='put', side='buy', strike=465.0, qty=1),
                ],
                width=5.0,
                mid_credit=1.25,
                limit_credit=1.20,
                max_loss=375.0,
                pop_estimate=75.0,
                edge_metrics=EdgeMetrics(
                    iv_pct=components.get('iv_rv_spread'),
                    skew_metric=components.get('skew_dislocation'),
                    term_structure=components.get('term_structure'),
                ),
                regime_gate=RegimeGate(
                    passed=pass_fail.get('passed', True),
                    reasons=pass_fail.get('reasons', []),
                ),
                risk_gate=RiskGate(
                    passed=risk_result.get('risk_limits_pass', True),
                    reasons=risk_result.get('reasons', []),
                    portfolio_after=PortfolioAfter(
                        delta=risk_result.get('portfolio_delta_after', 0.0),
                        vega=risk_result.get('portfolio_vega_after', 0.0),
                        gamma=risk_result.get('portfolio_gamma_after', 0.0),
                        max_loss_trade=risk_result.get('max_loss_trade', 375.0),
                        max_loss_week=risk_result.get('max_loss_week', 375.0),
                    ),
                ),
                confidence_score=round(edge_score, 4),
                exits=Exits(),
                status='pending',
            )
        else:
            ticket = index_vol_engine.generate_trade_ticket(symbol, existing)

        # Store in pending tickets (as dict for mutability)
        ticket_dict = ticket.model_dump()
        _pending_tickets[ticket_dict['ticket_id']] = ticket_dict
        return jsonify({'success': True, 'ticket': ticket_dict})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trade-ticket/pending', methods=['GET'])
def get_pending_tickets():
    """Return all pending trade tickets."""
    try:
        pending = [
            t for t in _pending_tickets.values()
            if t.get('status') == 'pending'
            and t.get('regime_gate', {}).get('passed', True)
            and t.get('risk_gate', {}).get('passed', True)
        ]
        return jsonify({'success': True, 'tickets': pending})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/execute', methods=['POST'])
def execute_trade():
    """
    Approve or reject a pending trade ticket.

    Request body (JSON):
        ticket_id (str): The idempotency key / ticket ID.
        action (str): 'approve' or 'reject'.

    On approval the ticket is logged for track-record building.
    """
    try:
        data = request.json or {}
        try:
            validated = ExecuteRequest(**data)
        except ValidationError as ve:
            return jsonify({
                'success': False,
                'error': 'ticket_id and action (approve|reject) are required',
            }), 400

        ticket = _pending_tickets.get(validated.ticket_id)
        if ticket is None:
            return jsonify({
                'success': False,
                'error': f'Ticket {validated.ticket_id} not found',
            }), 404

        if ticket.get('status') != 'pending':
            return jsonify({
                'success': False,
                'error': f'Ticket {validated.ticket_id} is already {ticket.get("status")}',
            }), 409

        ticket['status'] = 'approved' if validated.action == 'approve' else 'rejected'
        ticket['executed_at'] = datetime.now().isoformat()

        _execution_log.append({
            'ticket_id': validated.ticket_id,
            'action': validated.action,
            'timestamp': ticket['executed_at'],
            'symbol': ticket.get('symbol'),
            'strategy': ticket.get('strategy'),
        })

        return jsonify({'success': True, 'ticket': ticket})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ------------------------------------------------------------------
# Manual Confirmation workflow
# ------------------------------------------------------------------

@app.route('/api/trade-tickets/spy', methods=['POST'])
def propose_spy_tickets():
    """Generate proposed trade tickets for SPY and persist them in SQLite.

    This is the entry-point for the semi-automated manual-confirmation
    workflow.  It leverages the existing index-vol engine (or demo data)
    to build a ticket, stores it in the ``tickets`` table, and returns
    it for human review.
    """
    try:
        data = request.json or {}
        symbol = 'SPY'

        # Re-use existing index-vol ticket generation logic
        existing = data.get('existing_positions', [])
        equity = data.get('equity', 100_000.0)
        weekly_realized_pnl = data.get('weekly_realized_pnl', 0.0)
        existing_weekly_max_losses = data.get('existing_weekly_max_losses', 0.0)

        if DEMO_MODE:
            from index_vol_engine import IndexVolEngine as _IVE
            vol_surface_data = get_mock_vol_surface(symbol)
            regime_data = get_mock_regime()
            trade_gate = regime_classifier.should_trade(regime_data)
            engine = _IVE(risk_engine=risk_engine)
            components = engine._score_components(vol_surface_data, regime_data)
            edge_score = engine._composite_edge(components)
            pass_fail = engine._evaluate_gate(edge_score, trade_gate, components)

            risk_result = risk_engine.evaluate_ticket_risk(
                ticket_max_loss=375.0,
                ticket_position={
                    'symbol': symbol, 'delta': -0.30, 'vega': -0.10,
                    'gamma': -0.01, 'notional': 500,
                    'earnings_date': None, 'expiry_bucket': '7-30d',
                },
                existing_positions=existing,
                equity=equity,
                weekly_realized_pnl=weekly_realized_pnl,
                existing_weekly_max_losses=existing_weekly_max_losses,
            )
            ticket = TradeTicket(
                ticket_id=str(uuid.uuid4()),
                underlying=symbol,
                strategy='SPY_PUT_CREDIT_SPREAD',
                expiry='2026-03-20',
                dte=33,
                legs=[
                    TicketLeg(type='put', side='sell', strike=470.0, qty=1),
                    TicketLeg(type='put', side='buy', strike=465.0, qty=1),
                ],
                width=5.0,
                mid_credit=1.25,
                limit_credit=1.20,
                max_loss=375.0,
                pop_estimate=75.0,
                edge_metrics=EdgeMetrics(
                    iv_pct=components.get('iv_rv_spread'),
                    skew_metric=components.get('skew_dislocation'),
                    term_structure=components.get('term_structure'),
                ),
                regime_gate=RegimeGate(
                    passed=pass_fail.get('passed', True),
                    reasons=pass_fail.get('reasons', []),
                ),
                risk_gate=RiskGate(
                    passed=risk_result.get('risk_limits_pass', True),
                    reasons=risk_result.get('reasons', []),
                    portfolio_after=PortfolioAfter(
                        delta=risk_result.get('portfolio_delta_after', 0.0),
                        vega=risk_result.get('portfolio_vega_after', 0.0),
                        gamma=risk_result.get('portfolio_gamma_after', 0.0),
                        max_loss_trade=risk_result.get('max_loss_trade', 375.0),
                        max_loss_week=risk_result.get('max_loss_week', 375.0),
                    ),
                ),
                confidence_score=round(edge_score, 4),
                exits=Exits(),
                status='pending',
            )
        else:
            ticket = index_vol_engine.generate_trade_ticket(symbol, existing)

        ticket_dict = ticket.model_dump()
        # Also keep in memory for backward compat with existing /api/execute
        _pending_tickets[ticket_dict['ticket_id']] = ticket_dict
        # Persist to SQLite
        ticket_id, ticket_hash = insert_ticket(ticket_dict)
        ticket_dict['ticket_hash'] = ticket_hash

        return jsonify({'success': True, 'tickets': [ticket_dict]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trade-approve', methods=['POST'])
def trade_approve():
    """Approve a pending trade ticket.

    Stores the approval in SQLite with a timestamp and the ticket hash
    for idempotency.  No broker execution is performed.
    """
    try:
        data = request.json or {}
        try:
            validated = TradeApproveRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422

        try:
            record = db_approve(validated.ticket_id)
        except KeyError:
            return jsonify({
                'success': False,
                'error': f'Ticket {validated.ticket_id} not found',
            }), 404
        except ValueError as ve:
            return jsonify({
                'success': False,
                'error': str(ve),
            }), 409

        # Keep in-memory store in sync
        if validated.ticket_id in _pending_tickets:
            _pending_tickets[validated.ticket_id]['status'] = 'approved'

        return jsonify({'success': True, 'approval': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trade-reject', methods=['POST'])
def trade_reject():
    """Reject a pending trade ticket with an optional reason.

    Stores the rejection in SQLite with a timestamp, ticket hash,
    and the optional reason text.
    """
    try:
        data = request.json or {}
        try:
            validated = TradeRejectRequest(**data)
        except ValidationError as ve:
            return jsonify({'success': False, 'error': ve.errors()}), 422

        try:
            record = db_reject(validated.ticket_id, reason=validated.reason)
        except KeyError:
            return jsonify({
                'success': False,
                'error': f'Ticket {validated.ticket_id} not found',
            }), 404
        except ValueError as ve:
            return jsonify({
                'success': False,
                'error': str(ve),
            }), 409

        # Keep in-memory store in sync
        if validated.ticket_id in _pending_tickets:
            _pending_tickets[validated.ticket_id]['status'] = 'rejected'

        return jsonify({'success': True, 'rejection': record})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trade-audit-log', methods=['GET'])
def trade_audit_log():
    """Return the full approval / rejection audit log."""
    try:
        log = get_audit_log()
        return jsonify({'success': True, 'log': log})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    import os

    port = int(os.environ.get('TRADEAI_PORT', '5055'))  # fixed for desktop mode
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'

    print("Starting TradeAI Local API...")
    print(f"Available at: http://127.0.0.1:{port}")
    if DEMO_MODE:
        print("⚠️  DEMO MODE: Using mock data (no internet connection)")

    # Local-only bind for desktop safety (do NOT use 0.0.0.0)
    app.run(debug=debug_mode, host='127.0.0.1', port=port)
