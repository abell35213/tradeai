"""
Opportunity Finder Module

Identifies high-confidence trading opportunities based on:
- Sentiment analysis
- Technical indicators
- Options Greeks
- Risk/reward ratios
- Volatility analysis
"""

import yfinance as yf
from datetime import datetime, timedelta
from sentiment_analyzer import SentimentAnalyzer
from derivatives_calculator import DerivativesCalculator
import numpy as np

class OpportunityFinder:
    """Find high-probability trading opportunities for derivatives"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.derivatives_calc = DerivativesCalculator()
    
    def find_opportunities(self, symbols, min_confidence=0.6):
        """
        Scan multiple symbols for trading opportunities
        
        Parameters:
        symbols: List of ticker symbols to analyze
        min_confidence: Minimum confidence threshold (0-1)
        
        Returns:
        List of opportunities with rankings and analysis
        """
        opportunities = []
        
        for symbol in symbols:
            try:
                opportunity = self._analyze_symbol(symbol)
                
                if opportunity and opportunity.get('confidence', 0) >= min_confidence:
                    opportunities.append(opportunity)
            except Exception as e:
                print(f"Error analyzing {symbol}: {str(e)}")
                continue
        
        # Sort by confidence and potential return
        opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return opportunities
    
    def _analyze_symbol(self, symbol):
        """Analyze a single symbol for opportunities"""
        try:
            # Get sentiment analysis
            sentiment = self.sentiment_analyzer.analyze_symbol(symbol)
            
            if sentiment.get('confidence', 0) < 0.5:
                return None
            
            # Get market data
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="1mo")
            
            if len(history) < 10:
                return None
            
            current_price = history['Close'].iloc[-1]
            volatility = history['Close'].pct_change().std() * np.sqrt(252)
            
            # Analyze options if available
            options_analysis = self._analyze_options(symbol, ticker, current_price, volatility)
            
            # Calculate overall opportunity score
            score = self._calculate_opportunity_score(
                sentiment, current_price, volatility, options_analysis
            )
            
            # Determine strategy recommendation
            strategy = self._recommend_strategy(sentiment, volatility, options_analysis)
            
            return {
                'symbol': symbol,
                'score': score,
                'confidence': sentiment['confidence'],
                'current_price': float(current_price),
                'sentiment': sentiment,
                'volatility': float(volatility),
                'strategy': strategy,
                'options_analysis': options_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return None
    
    def _analyze_options(self, symbol, ticker, current_price, volatility):
        """Analyze options chain for opportunities"""
        try:
            expirations = ticker.options
            
            if not expirations or len(expirations) == 0:
                return {
                    'available': False,
                    'message': 'No options data available'
                }
            
            # Get nearest expiration
            exp_date = expirations[0]
            opt_chain = ticker.option_chain(exp_date)
            
            # Find ATM options
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            # Find closest to ATM
            calls['distance'] = abs(calls['strike'] - current_price)
            puts['distance'] = abs(puts['strike'] - current_price)
            
            atm_call = calls.loc[calls['distance'].idxmin()] if len(calls) > 0 else None
            atm_put = puts.loc[puts['distance'].idxmin()] if len(puts) > 0 else None
            
            analysis = {
                'available': True,
                'expiration': exp_date,
                'expirations_available': len(expirations)
            }
            
            if atm_call is not None:
                analysis['atm_call'] = {
                    'strike': float(atm_call['strike']),
                    'last_price': float(atm_call['lastPrice']),
                    'bid': float(atm_call['bid']),
                    'ask': float(atm_call['ask']),
                    'volume': int(atm_call['volume']) if atm_call['volume'] > 0 else 0,
                    'open_interest': int(atm_call['openInterest'])
                }
            
            if atm_put is not None:
                analysis['atm_put'] = {
                    'strike': float(atm_put['strike']),
                    'last_price': float(atm_put['lastPrice']),
                    'bid': float(atm_put['bid']),
                    'ask': float(atm_put['ask']),
                    'volume': int(atm_put['volume']) if atm_put['volume'] > 0 else 0,
                    'open_interest': int(atm_put['openInterest'])
                }
            
            # Calculate put/call ratio
            total_call_volume = calls['volume'].sum()
            total_put_volume = puts['volume'].sum()
            
            if total_call_volume > 0:
                put_call_ratio = total_put_volume / total_call_volume
                analysis['put_call_ratio'] = float(put_call_ratio)
            
            return analysis
            
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    def _calculate_opportunity_score(self, sentiment, price, volatility, options_analysis):
        """Calculate overall opportunity score (0-100)"""
        score = 0
        
        # Sentiment contribution (0-40 points)
        sentiment_score = abs(sentiment['overall_score']) * sentiment['confidence'] * 40
        score += sentiment_score
        
        # Volatility contribution (0-20 points)
        # Moderate volatility is good for options
        if 0.15 <= volatility <= 0.4:
            vol_score = 20
        elif 0.1 <= volatility < 0.15 or 0.4 < volatility <= 0.6:
            vol_score = 15
        else:
            vol_score = 5
        score += vol_score
        
        # Options availability (0-20 points)
        if options_analysis.get('available', False):
            score += 20
            
            # Bonus for good liquidity
            atm_call = options_analysis.get('atm_call', {})
            if atm_call.get('volume', 0) > 100:
                score += 5
        
        # Consistency bonus (0-15 points)
        if sentiment['confidence'] > 0.7:
            score += 15
        elif sentiment['confidence'] > 0.6:
            score += 10
        
        return min(score, 100)
    
    def _recommend_strategy(self, sentiment, volatility, options_analysis):
        """Recommend specific derivatives strategy"""
        sentiment_score = sentiment['overall_score']
        confidence = sentiment['confidence']
        
        strategies = []
        
        # Directional strategies
        if sentiment_score > 0.4 and confidence > 0.6:
            strategies.append({
                'name': 'Long Call',
                'direction': 'Bullish',
                'risk': 'Limited to premium',
                'reward': 'Unlimited',
                'confidence': 'High',
                'reasoning': 'Strong bullish sentiment with high confidence'
            })
            
            if volatility < 0.3:
                strategies.append({
                    'name': 'Bull Call Spread',
                    'direction': 'Bullish',
                    'risk': 'Limited',
                    'reward': 'Limited',
                    'confidence': 'Medium-High',
                    'reasoning': 'Bullish sentiment with moderate volatility'
                })
        
        elif sentiment_score < -0.4 and confidence > 0.6:
            strategies.append({
                'name': 'Long Put',
                'direction': 'Bearish',
                'risk': 'Limited to premium',
                'reward': 'High (down to zero)',
                'confidence': 'High',
                'reasoning': 'Strong bearish sentiment with high confidence'
            })
            
            strategies.append({
                'name': 'Bear Put Spread',
                'direction': 'Bearish',
                'risk': 'Limited',
                'reward': 'Limited',
                'confidence': 'Medium-High',
                'reasoning': 'Bearish sentiment, limited risk approach'
            })
        
        # Volatility strategies
        if volatility > 0.5:
            strategies.append({
                'name': 'Iron Condor',
                'direction': 'Neutral',
                'risk': 'Limited',
                'reward': 'Limited',
                'confidence': 'Medium',
                'reasoning': 'High volatility - sell premium strategy'
            })
        
        if volatility < 0.2 and abs(sentiment_score) < 0.3:
            strategies.append({
                'name': 'Long Straddle',
                'direction': 'Neutral (expecting move)',
                'risk': 'Limited to premium',
                'reward': 'Unlimited',
                'confidence': 'Medium',
                'reasoning': 'Low volatility - anticipate breakout'
            })
        
        # Conservative strategy
        if confidence < 0.6:
            strategies.append({
                'name': 'Covered Call (if holding stock)',
                'direction': 'Neutral-Bullish',
                'risk': 'Limited upside',
                'reward': 'Premium collected',
                'confidence': 'Low-Medium',
                'reasoning': 'Mixed signals - conservative income strategy'
            })
        
        return strategies if strategies else [{
            'name': 'Wait for clearer signal',
            'direction': 'Neutral',
            'risk': 'None',
            'reward': 'None',
            'confidence': 'N/A',
            'reasoning': 'Insufficient confidence or unclear market conditions'
        }]
