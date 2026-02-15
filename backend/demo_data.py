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

def _generate_mock_earnings_calendar(year, month):
    """Generate a mock earnings calendar for the given month."""
    from datetime import datetime, timedelta
    import random

    companies = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'market_cap': 2650000000000},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'market_cap': 2800000000000},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'market_cap': 1750000000000},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'market_cap': 1580000000000},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corporation', 'market_cap': 1820000000000},
        {'symbol': 'META', 'name': 'Meta Platforms Inc.', 'market_cap': 920000000000},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'market_cap': 780000000000},
        {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.', 'market_cap': 490000000000},
        {'symbol': 'V', 'name': 'Visa Inc.', 'market_cap': 520000000000},
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'market_cap': 410000000000},
        {'symbol': 'WMT', 'name': 'Walmart Inc.', 'market_cap': 430000000000},
        {'symbol': 'PG', 'name': 'Procter & Gamble Co.', 'market_cap': 350000000000},
        {'symbol': 'MA', 'name': 'Mastercard Inc.', 'market_cap': 380000000000},
        {'symbol': 'HD', 'name': 'The Home Depot Inc.', 'market_cap': 340000000000},
        {'symbol': 'DIS', 'name': 'The Walt Disney Company', 'market_cap': 195000000000},
        {'symbol': 'NFLX', 'name': 'Netflix Inc.', 'market_cap': 230000000000},
        {'symbol': 'ADBE', 'name': 'Adobe Inc.', 'market_cap': 240000000000},
        {'symbol': 'CRM', 'name': 'Salesforce Inc.', 'market_cap': 210000000000},
        {'symbol': 'INTC', 'name': 'Intel Corporation', 'market_cap': 180000000000},
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices', 'market_cap': 220000000000},
        {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.', 'market_cap': 68000000000},
        {'symbol': 'COST', 'name': 'Costco Wholesale Corp.', 'market_cap': 290000000000},
        {'symbol': 'PEP', 'name': 'PepsiCo Inc.', 'market_cap': 230000000000},
        {'symbol': 'AVGO', 'name': 'Broadcom Inc.', 'market_cap': 370000000000},
    ]

    random.seed(year * 100 + month)
    calendar = {}

    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    business_days = []
    current = start
    while current < end:
        if current.weekday() < 5:
            business_days.append(current)
        current += timedelta(days=1)

    shuffled = list(companies)
    random.shuffle(shuffled)

    for i, company in enumerate(shuffled):
        day = business_days[i % len(business_days)]
        date_str = day.strftime('%Y-%m-%d')
        if date_str not in calendar:
            calendar[date_str] = []
        calendar[date_str].append({
            'symbol': company['symbol'],
            'name': company['name'],
            'time': 'BMO' if random.random() > 0.5 else 'AMC',
            'market_cap': company['market_cap'],
        })

    return calendar


MOCK_EARNINGS_SNAPSHOTS = {
    'AAPL': {
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'earnings_date': '2026-02-26',
        'expectation_density': {
            'analyst_count': 38,
            'target_mean': 195.0,
            'target_low': 160.0,
            'target_high': 220.0,
            'spread': 60.0,
            'spread_pct': 0.3529,
            'consensus_tight': False,
            'guidance_drift': 0.1453,
            'signal': 'Wide dispersion = harder to shock',
        },
        'options_expectations': {
            'atm_iv': 0.32,
            'historical_volatility': 0.28,
            'iv_vs_historical': 1.1429,
            'front_iv': 0.32,
            'back_iv': 0.26,
            'iv_term_spread': 0.06,
            'signal': 'IV roughly in line with historical',
        },
        'positioning_flow': {
            'call_oi': 185000,
            'put_oi': 142000,
            'put_call_oi_ratio': 0.7676,
            'price_drift_pct': 0.035,
            'drift_direction': 'upward',
            'signal': 'Mixed positioning signals',
        },
        'narrative_alignment': {
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'themes': ['AI'],
            'price_ahead_of_narrative': False,
            'narrative_ahead_of_price': False,
            'signal': 'Aligned with theme(s): AI',
        },
        'earnings_setup': {
            'setup': 'D',
            'label': 'Confused / Two-Sided',
            'interpretation': 'Market expects movement but not direction.',
            'preferred_structures': [
                'Long straddles',
                'Long strangles',
                'Backspreads',
            ],
            'best_in': ['Mid-caps', 'Volatile cyclicals', 'Energy E&Ps'],
            'matched_traits': [
                'Elevated IV',
                'Both call & put buying',
                'Wide estimate dispersion',
            ],
            'scores': {'A': 0, 'B': 2, 'C': 2, 'D': 5, 'E': 0},
        },
        'timestamp': '2026-02-14T16:45:00',
    },
    'NVDA': {
        'symbol': 'NVDA',
        'name': 'NVIDIA Corporation',
        'earnings_date': '2026-02-26',
        'expectation_density': {
            'analyst_count': 45,
            'target_mean': 850.0,
            'target_low': 600.0,
            'target_high': 1100.0,
            'spread': 500.0,
            'spread_pct': 0.6868,
            'consensus_tight': False,
            'guidance_drift': 0.1668,
            'signal': 'Wide dispersion = harder to shock',
        },
        'options_expectations': {
            'atm_iv': 0.55,
            'historical_volatility': 0.42,
            'iv_vs_historical': 1.3095,
            'front_iv': 0.55,
            'back_iv': 0.40,
            'iv_term_spread': 0.15,
            'signal': 'IV > historical realized → fear priced in',
        },
        'positioning_flow': {
            'call_oi': 320000,
            'put_oi': 180000,
            'put_call_oi_ratio': 0.5625,
            'price_drift_pct': 0.052,
            'drift_direction': 'upward',
            'signal': 'Drift + call buying = crowded',
        },
        'narrative_alignment': {
            'sector': 'Technology',
            'industry': 'Semiconductors',
            'themes': ['AI'],
            'price_ahead_of_narrative': True,
            'narrative_ahead_of_price': False,
            'signal': 'Price ahead of narrative = early positioning',
        },
        'earnings_setup': {
            'setup': 'C',
            'label': 'Crowded Bull',
            'interpretation': 'Even a "beat" may disappoint.',
            'preferred_structures': [
                'Call spreads (cap upside)',
                'Call flies',
                'Long puts financed with call sales',
            ],
            'best_in': [],
            'matched_traits': [
                'Heavy call OI',
                'Stock up materially pre-earnings',
            ],
            'scores': {'A': 3, 'B': 2, 'C': 5, 'D': 1, 'E': 0},
        },
        'timestamp': '2026-02-14T16:45:00',
    },
    'JPM': {
        'symbol': 'JPM',
        'name': 'JPMorgan Chase & Co.',
        'earnings_date': '2026-02-20',
        'expectation_density': {
            'analyst_count': 28,
            'target_mean': 210.0,
            'target_low': 185.0,
            'target_high': 230.0,
            'spread': 45.0,
            'spread_pct': 0.2250,
            'consensus_tight': False,
            'guidance_drift': 0.05,
            'signal': 'Wide dispersion = harder to shock',
        },
        'options_expectations': {
            'atm_iv': 0.24,
            'historical_volatility': 0.22,
            'iv_vs_historical': 1.0909,
            'front_iv': 0.24,
            'back_iv': 0.20,
            'iv_term_spread': 0.04,
            'signal': 'IV roughly in line with historical',
        },
        'positioning_flow': {
            'call_oi': 95000,
            'put_oi': 110000,
            'put_call_oi_ratio': 1.1579,
            'price_drift_pct': 0.005,
            'drift_direction': 'flat',
            'signal': 'Flat price + rising IV = hedging',
        },
        'narrative_alignment': {
            'sector': 'Financial Services',
            'industry': 'Banks - Diversified',
            'themes': ['Rate Sensitivity'],
            'price_ahead_of_narrative': False,
            'narrative_ahead_of_price': False,
            'signal': 'Aligned with theme(s): Rate Sensitivity',
        },
        'earnings_setup': {
            'setup': 'D',
            'label': 'Confused / Two-Sided',
            'interpretation': 'Market expects movement but not direction.',
            'preferred_structures': [
                'Long straddles',
                'Long strangles',
                'Backspreads',
            ],
            'best_in': ['Mid-caps', 'Volatile cyclicals', 'Energy E&Ps'],
            'matched_traits': [
                'Elevated IV',
                'Both call & put buying',
                'No clear drift',
            ],
            'scores': {'A': 3, 'B': 0, 'C': 0, 'D': 5, 'E': 0},
        },
        'timestamp': '2026-02-14T16:45:00',
    },
    'TSLA': {
        'symbol': 'TSLA',
        'name': 'Tesla Inc.',
        'earnings_date': '2026-02-24',
        'expectation_density': {
            'analyst_count': 42,
            'target_mean': 275.0,
            'target_low': 120.0,
            'target_high': 400.0,
            'spread': 280.0,
            'spread_pct': 1.1200,
            'consensus_tight': False,
            'guidance_drift': 0.10,
            'signal': 'Wide dispersion = harder to shock',
        },
        'options_expectations': {
            'atm_iv': 0.62,
            'historical_volatility': 0.55,
            'iv_vs_historical': 1.1273,
            'front_iv': 0.62,
            'back_iv': 0.48,
            'iv_term_spread': 0.14,
            'signal': 'IV roughly in line with historical',
        },
        'positioning_flow': {
            'call_oi': 410000,
            'put_oi': 380000,
            'put_call_oi_ratio': 0.9268,
            'price_drift_pct': -0.028,
            'drift_direction': 'downward',
            'signal': 'Mixed positioning signals',
        },
        'narrative_alignment': {
            'sector': 'Consumer Cyclical',
            'industry': 'Auto Manufacturers',
            'themes': ['AI', 'Energy Transition'],
            'price_ahead_of_narrative': False,
            'narrative_ahead_of_price': True,
            'signal': 'Narrative ahead of price = late sentiment',
        },
        'earnings_setup': {
            'setup': 'D',
            'label': 'Confused / Two-Sided',
            'interpretation': 'Market expects movement but not direction.',
            'preferred_structures': [
                'Long straddles',
                'Long strangles',
                'Backspreads',
            ],
            'best_in': ['Mid-caps', 'Volatile cyclicals', 'Energy E&Ps'],
            'matched_traits': [
                'Elevated IV',
                'Both call & put buying',
                'Wide estimate dispersion',
            ],
            'scores': {'A': 1, 'B': 0, 'C': 0, 'D': 5, 'E': 0},
        },
        'timestamp': '2026-02-14T16:45:00',
    },
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

def get_mock_earnings_calendar(year, month):
    """Get mock earnings calendar for a given month"""
    return _generate_mock_earnings_calendar(year, month)

def get_mock_earnings_snapshot(symbol):
    """Get mock earnings snapshot for a symbol"""
    return MOCK_EARNINGS_SNAPSHOTS.get(symbol, MOCK_EARNINGS_SNAPSHOTS['AAPL'])


# ------------------------------------------------------------------
# Mock index vol engine data
# ------------------------------------------------------------------

MOCK_VOL_SURFACE = {
    'SPY': {
        'symbol': 'SPY',
        'term_structure': {
            'shape': 'contango',
            'expirations': ['2026-03-20', '2026-04-17', '2026-05-15'],
            'atm_ivs': [0.16, 0.17, 0.18],
            'distortion_detected': False,
            'signal': 'Contango — normal term structure',
        },
        'skew': {
            'put_skew_iv': 0.19,
            'call_skew_iv': 0.14,
            'skew_spread': 0.05,
            'signal': 'Normal skew',
        },
        'forward_vol': {
            'spot_vol': 0.16,
            'forward_vol': 0.19,
            'ratio': 1.19,
            'signal': 'Forward vol in line with spot',
        },
        'sector_iv_comparison': {
            'symbol_iv': 0.16,
            'sector_etf': 'SPY',
            'sector_iv': 0.16,
            'iv_premium': 1.0,
            'signal': 'Symbol IV in line with sector',
        },
        'skew_percentile': {
            'current_skew': -0.12,
            'percentile': 45.0,
            'signal': 'Skew within normal range',
        },
        'cross_sectional_dislocations': {
            'symbol_iv': 0.16,
            'peer_ivs': {},
            'iv_rank_in_sector': None,
            'dislocation_detected': False,
            'signal': 'Insufficient data',
        },
        'timestamp': '2026-02-14T16:45:00',
    },
}

MOCK_REGIME = {
    'vol_regime': 'compressed',
    'correlation_regime': 'medium',
    'risk_appetite': 'risk_on',
    'details': {
        'volatility': {
            'regime': 'compressed',
            'vix_current': 14.5,
            'vix_percentile': 22.0,
            'vix_sma_20': 15.2,
        },
        'correlation': {
            'regime': 'medium',
            'avg_correlation': 0.42,
            'sector_count': 9,
        },
        'gamma_exposure': {
            'gamma_direction': 'positive',
            'put_call_oi_ratio': 0.72,
            'total_oi': 12500000,
        },
        'macro_proximity': {
            'elevated': False,
            'signals': [],
        },
    },
    'timestamp': '2026-02-14T16:45:00',
}


def get_mock_vol_surface(symbol):
    """Get mock vol surface data for a symbol."""
    return MOCK_VOL_SURFACE.get(symbol, MOCK_VOL_SURFACE['SPY'])


def get_mock_regime():
    """Get mock regime data."""
    return MOCK_REGIME
