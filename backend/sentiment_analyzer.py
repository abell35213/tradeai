"""
Sentiment Analyzer Module

Analyzes market sentiment from multiple sources including:
- Price action and technical indicators
- Volume analysis
- Volatility patterns
- Market trends
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from textblob import TextBlob

class SentimentAnalyzer:
    """Analyzes sentiment for trading symbols"""
    
    def __init__(self):
        self.lookback_period = "3mo"
    
    def analyze_symbol(self, symbol):
        """
        Analyze sentiment for a given symbol
        
        Returns a comprehensive sentiment analysis including:
        - Technical sentiment (price momentum, trend)
        - Volume sentiment
        - Volatility sentiment
        - Overall sentiment score
        """
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=self.lookback_period)
            
            if len(history) < 10:
                return {
                    'error': 'Insufficient data for analysis',
                    'overall_score': 0,
                    'confidence': 0
                }
            
            # Technical sentiment analysis
            technical_sentiment = self._analyze_technical(history)
            
            # Volume sentiment
            volume_sentiment = self._analyze_volume(history)
            
            # Volatility sentiment
            volatility_sentiment = self._analyze_volatility(history)
            
            # Calculate overall sentiment
            overall_score = (
                technical_sentiment['score'] * 0.5 +
                volume_sentiment['score'] * 0.25 +
                volatility_sentiment['score'] * 0.25
            )
            
            # Determine confidence based on data quality and consistency
            confidence = self._calculate_confidence(
                technical_sentiment, volume_sentiment, volatility_sentiment
            )
            
            return {
                'overall_score': round(overall_score, 3),
                'confidence': round(confidence, 3),
                'technical': technical_sentiment,
                'volume': volume_sentiment,
                'volatility': volatility_sentiment,
                'timestamp': datetime.now().isoformat(),
                'recommendation': self._get_recommendation(overall_score, confidence)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'overall_score': 0,
                'confidence': 0
            }
    
    def _analyze_technical(self, history):
        """Analyze technical indicators for sentiment"""
        closes = history['Close']
        
        # Calculate moving averages
        sma_20 = closes.rolling(window=20).mean()
        sma_50 = closes.rolling(window=50).mean()
        
        # Momentum
        current_price = closes.iloc[-1]
        price_20d_ago = closes.iloc[-20] if len(closes) >= 20 else closes.iloc[0]
        momentum = (current_price - price_20d_ago) / price_20d_ago
        
        # Trend analysis
        trend_score = 0
        if len(sma_20) > 0 and len(sma_50) > 0:
            if current_price > sma_20.iloc[-1]:
                trend_score += 0.5
            if current_price > sma_50.iloc[-1]:
                trend_score += 0.3
            if sma_20.iloc[-1] > sma_50.iloc[-1]:
                trend_score += 0.2
        
        # Normalize momentum to -1 to 1 range
        momentum_normalized = np.tanh(momentum * 5)
        
        # Combined score
        score = (trend_score + momentum_normalized) / 2
        
        return {
            'score': float(score),
            'momentum': float(momentum),
            'trend': 'bullish' if score > 0.2 else 'bearish' if score < -0.2 else 'neutral',
            'sma_20': float(sma_20.iloc[-1]) if len(sma_20) > 0 else None,
            'sma_50': float(sma_50.iloc[-1]) if len(sma_50) > 0 else None
        }
    
    def _analyze_volume(self, history):
        """Analyze volume patterns for sentiment"""
        volumes = history['Volume']
        closes = history['Close']
        
        # Average volume
        avg_volume = volumes.mean()
        recent_volume = volumes.iloc[-5:].mean()
        
        # Volume trend
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Price-volume correlation
        price_changes = closes.pct_change()
        volume_changes = volumes.pct_change()
        correlation = price_changes.corr(volume_changes)
        
        # Score based on volume patterns
        score = 0
        if volume_ratio > 1.2:  # High volume
            if correlation > 0:  # Positive correlation
                score = 0.6
            else:
                score = -0.6
        else:
            score = 0
        
        return {
            'score': float(score),
            'volume_ratio': float(volume_ratio),
            'correlation': float(correlation) if not np.isnan(correlation) else 0,
            'signal': 'accumulation' if score > 0.3 else 'distribution' if score < -0.3 else 'neutral'
        }
    
    def _analyze_volatility(self, history):
        """Analyze volatility for sentiment"""
        closes = history['Close']
        returns = closes.pct_change()
        
        # Historical volatility
        volatility = returns.std() * np.sqrt(252)
        
        # Recent volatility vs historical
        recent_vol = returns.iloc[-20:].std() * np.sqrt(252) if len(returns) >= 20 else volatility
        vol_ratio = recent_vol / volatility if volatility > 0 else 1
        
        # Lower volatility can be bullish (stability), high volatility bearish (uncertainty)
        # But context matters - use moderate approach
        if vol_ratio < 0.8:
            score = 0.3  # Low volatility - stable
        elif vol_ratio > 1.5:
            score = -0.3  # High volatility - risky
        else:
            score = 0
        
        return {
            'score': float(score),
            'annual_volatility': float(volatility),
            'volatility_ratio': float(vol_ratio),
            'regime': 'low' if vol_ratio < 0.8 else 'high' if vol_ratio > 1.5 else 'normal'
        }
    
    def _calculate_confidence(self, technical, volume, volatility):
        """Calculate confidence in sentiment analysis"""
        # Base confidence on consistency of signals
        scores = [technical['score'], volume['score'], volatility['score']]
        
        # If all agree (same sign), high confidence
        positive_count = sum(1 for s in scores if s > 0.2)
        negative_count = sum(1 for s in scores if s < -0.2)
        
        if positive_count >= 2 or negative_count >= 2:
            confidence = 0.8
        elif positive_count == 1 and negative_count == 0:
            confidence = 0.6
        elif negative_count == 1 and positive_count == 0:
            confidence = 0.6
        else:
            confidence = 0.4  # Mixed signals
        
        return confidence
    
    def _get_recommendation(self, score, confidence):
        """Get trading recommendation based on sentiment"""
        if confidence < 0.5:
            return "HOLD - Mixed signals, wait for clearer picture"
        
        if score > 0.4:
            return "BUY - Strong bullish sentiment"
        elif score > 0.2:
            return "WEAK BUY - Moderately bullish"
        elif score < -0.4:
            return "SELL - Strong bearish sentiment"
        elif score < -0.2:
            return "WEAK SELL - Moderately bearish"
        else:
            return "HOLD - Neutral sentiment"
