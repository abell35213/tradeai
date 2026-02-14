"""
Demo Mode - Mock data for testing without internet connection
"""

MOCK_SENTIMENT_DATA = {
    'AAPL': {
        'overall_score': 0.65,
        'confidence': 0.78,
        'technical': {
            'score': 0.7,
            'momentum': 0.08,
            'trend': 'bullish',
            'sma_20': 168.50,
            'sma_50': 165.20
        },
        'volume': {
            'score': 0.6,
            'volume_ratio': 1.35,
            'correlation': 0.45,
            'signal': 'accumulation'
        },
        'volatility': {
            'score': 0.2,
            'annual_volatility': 0.28,
            'volatility_ratio': 0.95,
            'regime': 'normal'
        },
        'timestamp': '2026-02-14T16:45:00',
        'recommendation': 'BUY - Strong bullish sentiment'
    },
    'SPY': {
        'overall_score': 0.35,
        'confidence': 0.72,
        'technical': {
            'score': 0.4,
            'momentum': 0.03,
            'trend': 'bullish',
            'sma_20': 495.30,
            'sma_50': 492.80
        },
        'volume': {
            'score': 0.3,
            'volume_ratio': 1.15,
            'correlation': 0.25,
            'signal': 'neutral'
        },
        'volatility': {
            'score': 0.0,
            'annual_volatility': 0.18,
            'volatility_ratio': 1.0,
            'regime': 'normal'
        },
        'timestamp': '2026-02-14T16:45:00',
        'recommendation': 'WEAK BUY - Moderately bullish'
    },
    'QQQ': {
        'overall_score': 0.52,
        'confidence': 0.80,
        'technical': {
            'score': 0.6,
            'momentum': 0.06,
            'trend': 'bullish',
            'sma_20': 422.10,
            'sma_50': 418.50
        },
        'volume': {
            'score': 0.5,
            'volume_ratio': 1.28,
            'correlation': 0.38,
            'signal': 'accumulation'
        },
        'volatility': {
            'score': 0.1,
            'annual_volatility': 0.22,
            'volatility_ratio': 0.88,
            'regime': 'low'
        },
        'timestamp': '2026-02-14T16:45:00',
        'recommendation': 'BUY - Strong bullish sentiment'
    },
    'NVDA': {
        'overall_score': 0.48,
        'confidence': 0.75,
        'technical': {
            'score': 0.55,
            'momentum': 0.05,
            'trend': 'bullish',
            'sma_20': 725.80,
            'sma_50': 710.20
        },
        'volume': {
            'score': 0.45,
            'volume_ratio': 1.42,
            'correlation': 0.52,
            'signal': 'accumulation'
        },
        'volatility': {
            'score': -0.2,
            'annual_volatility': 0.42,
            'volatility_ratio': 1.35,
            'regime': 'high'
        },
        'timestamp': '2026-02-14T16:45:00',
        'recommendation': 'WEAK BUY - Moderately bullish'
    }
}

MOCK_MARKET_DATA = {
    'AAPL': {
        'current_price': 170.25,
        'volatility': 0.28,
        'market_cap': 2650000000000,
        'volume': 52345000,
        'beta': 1.24,
        'pe_ratio': 28.5
    },
    'SPY': {
        'current_price': 495.80,
        'volatility': 0.18,
        'market_cap': None,
        'volume': 85234000,
        'beta': 1.0,
        'pe_ratio': None
    },
    'QQQ': {
        'current_price': 422.45,
        'volatility': 0.22,
        'market_cap': None,
        'volume': 42156000,
        'beta': 1.15,
        'pe_ratio': None
    },
    'NVDA': {
        'current_price': 728.50,
        'volatility': 0.42,
        'market_cap': 1820000000000,
        'volume': 38945000,
        'beta': 1.68,
        'pe_ratio': 65.3
    }
}

MOCK_RISK_METRICS = {
    'AAPL': {
        'volatility_daily': 0.0175,
        'volatility_annual': 0.28,
        'sharpe_ratio': 1.42,
        'max_drawdown': -0.23,
        'var_95': -0.028,
        'skewness': -0.15,
        'kurtosis': 3.85
    },
    'SPY': {
        'volatility_daily': 0.0112,
        'volatility_annual': 0.18,
        'sharpe_ratio': 0.95,
        'max_drawdown': -0.18,
        'var_95': -0.019,
        'skewness': -0.35,
        'kurtosis': 4.12
    },
    'QQQ': {
        'volatility_daily': 0.0138,
        'volatility_annual': 0.22,
        'sharpe_ratio': 1.18,
        'max_drawdown': -0.21,
        'var_95': -0.023,
        'skewness': -0.22,
        'kurtosis': 3.65
    },
    'NVDA': {
        'volatility_daily': 0.0265,
        'volatility_annual': 0.42,
        'sharpe_ratio': 1.85,
        'max_drawdown': -0.38,
        'var_95': -0.042,
        'skewness': 0.28,
        'kurtosis': 5.25
    }
}

def get_mock_sentiment(symbol):
    """Get mock sentiment data for a symbol"""
    return MOCK_SENTIMENT_DATA.get(symbol, MOCK_SENTIMENT_DATA['AAPL'])

def get_mock_market_data(symbol):
    """Get mock market data for a symbol"""
    return MOCK_MARKET_DATA.get(symbol, MOCK_MARKET_DATA['AAPL'])

def get_mock_risk_metrics(symbol):
    """Get mock risk metrics for a symbol"""
    return MOCK_RISK_METRICS.get(symbol, MOCK_RISK_METRICS['AAPL'])
