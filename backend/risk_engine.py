"""
Risk Engine Module

Calculates portfolio-level risk metrics:
- Portfolio delta and vega exposure
- Correlation concentration
- Vega bucket risk
- Gamma convexity concentration
- Event clustering risk
- Sector concentration

Designed for risk-adjusted capital allocation in earnings volatility strategies.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from collections import defaultdict


class RiskEngine:
    """Portfolio-level risk calculator for options/earnings strategies."""

    # Sector mapping for common large-cap tickers
    SECTOR_MAP = {
        'AAPL': 'tech', 'MSFT': 'tech', 'GOOGL': 'tech', 'AMZN': 'tech',
        'NVDA': 'tech', 'META': 'tech', 'TSLA': 'tech', 'ADBE': 'tech',
        'CRM': 'tech', 'INTC': 'tech', 'AMD': 'tech', 'AVGO': 'tech',
        'CSCO': 'tech', 'NFLX': 'tech', 'PYPL': 'tech',
        'JPM': 'financials', 'V': 'financials', 'MA': 'financials',
        'JNJ': 'healthcare', 'MRK': 'healthcare', 'ABT': 'healthcare', 'TMO': 'healthcare',
        'WMT': 'consumer', 'COST': 'consumer', 'HD': 'consumer', 'NKE': 'consumer',
        'PG': 'consumer', 'PEP': 'consumer',
        'DIS': 'communications', 'CMCSA': 'communications',
        'XOM': 'energy', 'CVX': 'energy',
    }

    # Event clustering threshold (days between earnings)
    CLUSTER_WINDOW_DAYS = 3

    def __init__(self):
        pass

    def calculate_portfolio_risk(self, positions):
        """
        Calculate comprehensive portfolio risk metrics.

        Parameters:
            positions: list of dicts, each with:
                - symbol (str)
                - delta (float): position delta
                - vega (float): position vega
                - gamma (float): position gamma
                - notional (float): position notional value
                - earnings_date (str|None): ISO date if known
                - expiry_bucket (str|None): e.g. '0-7d', '7-30d', '30-60d', '60d+'

        Returns:
            dict with portfolio risk summary
        """
        if not positions:
            return self._empty_risk()

        portfolio_delta = 0.0
        portfolio_vega = 0.0
        portfolio_gamma = 0.0
        total_notional = 0.0

        sector_notional = defaultdict(float)
        vega_buckets = defaultdict(float)
        gamma_buckets = defaultdict(float)
        earnings_dates = []

        for pos in positions:
            symbol = pos.get('symbol', '')
            delta = float(pos.get('delta', 0))
            vega = float(pos.get('vega', 0))
            gamma = float(pos.get('gamma', 0))
            notional = float(pos.get('notional', 0))
            earnings_date = pos.get('earnings_date')
            expiry_bucket = pos.get('expiry_bucket', 'unknown')

            portfolio_delta += delta
            portfolio_vega += vega
            portfolio_gamma += gamma
            total_notional += abs(notional)

            # Sector concentration
            sector = self._get_sector(symbol)
            sector_notional[sector] += abs(notional)

            # Vega & gamma by expiry bucket
            vega_buckets[expiry_bucket] += vega
            gamma_buckets[expiry_bucket] += gamma

            # Track earnings dates
            if earnings_date:
                earnings_dates.append(earnings_date)

        # Sector concentration percentages
        sector_concentration = {}
        if total_notional > 0:
            for sector, val in sector_notional.items():
                sector_concentration[sector] = round(val / total_notional * 100, 1)

        # Correlation concentration
        symbols = list({pos.get('symbol', '') for pos in positions if pos.get('symbol')})
        corr_concentration = self._calculate_correlation_concentration(symbols)

        # Event clustering risk
        earnings_cluster = self._assess_earnings_cluster_risk(earnings_dates)

        # Gamma convexity concentration
        gamma_convexity = self._assess_gamma_concentration(gamma_buckets)

        return {
            'portfolio_delta': round(portfolio_delta, 4),
            'portfolio_vega': round(portfolio_vega, 2),
            'portfolio_gamma': round(portfolio_gamma, 4),
            'total_notional': round(total_notional, 2),
            'earnings_cluster_risk': earnings_cluster['level'],
            'sector_concentration': sector_concentration,
            'correlation_concentration': corr_concentration,
            'vega_buckets': dict(vega_buckets),
            'gamma_convexity': gamma_convexity,
            'earnings_cluster_detail': earnings_cluster,
            'timestamp': datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Sector lookup
    # ------------------------------------------------------------------

    def _get_sector(self, symbol):
        """Return sector for a symbol, falling back to yfinance or 'other'."""
        if symbol in self.SECTOR_MAP:
            return self.SECTOR_MAP[symbol]
        try:
            info = yf.Ticker(symbol).info
            return (info.get('sector') or 'other').lower()
        except Exception:
            return 'other'

    # ------------------------------------------------------------------
    # Correlation concentration
    # ------------------------------------------------------------------

    def _calculate_correlation_concentration(self, symbols):
        """
        Calculate average pairwise correlation among portfolio symbols.
        """
        result = {
            'avg_pairwise_correlation': None,
            'level': 'unknown',
        }

        if len(symbols) < 2:
            result['level'] = 'low'
            return result

        try:
            data = yf.download(symbols, period='3mo', progress=False)
            if data.empty:
                return result

            closes = data['Close'].dropna(axis=1, how='all')
            if closes.shape[1] < 2:
                return result

            returns = closes.pct_change().dropna()
            corr_matrix = returns.corr()
            mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
            avg_corr = float(corr_matrix.values[mask].mean())

            result['avg_pairwise_correlation'] = round(avg_corr, 4)
            if avg_corr > 0.7:
                result['level'] = 'high'
            elif avg_corr > 0.4:
                result['level'] = 'medium'
            else:
                result['level'] = 'low'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Earnings cluster risk
    # ------------------------------------------------------------------

    def _assess_earnings_cluster_risk(self, earnings_dates):
        """
        Determine if earnings events are clustered (multiple within a short window).
        """
        result = {
            'level': 'low',
            'count': len(earnings_dates),
            'clusters': [],
        }

        if len(earnings_dates) < 2:
            return result

        try:
            dates = sorted([
                datetime.fromisoformat(d) if isinstance(d, str) else d
                for d in earnings_dates
            ])

            cluster_count = 0
            for i in range(1, len(dates)):
                gap = (dates[i] - dates[i - 1]).days
                if gap <= self.CLUSTER_WINDOW_DAYS:
                    cluster_count += 1
                    result['clusters'].append({
                        'date_a': dates[i - 1].strftime('%Y-%m-%d'),
                        'date_b': dates[i].strftime('%Y-%m-%d'),
                        'gap_days': gap,
                    })

            if cluster_count >= 3:
                result['level'] = 'high'
            elif cluster_count >= 1:
                result['level'] = 'medium'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Gamma convexity concentration
    # ------------------------------------------------------------------

    def _assess_gamma_concentration(self, gamma_buckets):
        """
        Evaluate whether gamma exposure is concentrated in a single bucket.
        """
        result = {
            'level': 'low',
            'dominant_bucket': None,
            'dominant_pct': None,
        }

        total_abs_gamma = sum(abs(v) for v in gamma_buckets.values())
        if total_abs_gamma == 0:
            return result

        for bucket, val in gamma_buckets.items():
            pct = abs(val) / total_abs_gamma * 100
            if result['dominant_pct'] is None or pct > result['dominant_pct']:
                result['dominant_bucket'] = bucket
                result['dominant_pct'] = round(pct, 1)

        if result['dominant_pct'] and result['dominant_pct'] > 70:
            result['level'] = 'high'
        elif result['dominant_pct'] and result['dominant_pct'] > 50:
            result['level'] = 'medium'

        return result

    # ------------------------------------------------------------------
    # Empty risk
    # ------------------------------------------------------------------

    def _empty_risk(self):
        """Return an empty risk report when no positions provided."""
        return {
            'portfolio_delta': 0.0,
            'portfolio_vega': 0.0,
            'portfolio_gamma': 0.0,
            'total_notional': 0.0,
            'earnings_cluster_risk': 'low',
            'sector_concentration': {},
            'correlation_concentration': {'avg_pairwise_correlation': None, 'level': 'low'},
            'vega_buckets': {},
            'gamma_convexity': {'level': 'low', 'dominant_bucket': None, 'dominant_pct': None},
            'earnings_cluster_detail': {'level': 'low', 'count': 0, 'clusters': []},
            'timestamp': datetime.now().isoformat(),
        }
