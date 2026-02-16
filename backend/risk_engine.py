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

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from collections import defaultdict
from market_cache import get_ticker_info, download_tickers

logger = logging.getLogger(__name__)


class RiskEngine:
    """Portfolio-level risk calculator for options/earnings strategies."""

    # Default risk limits
    MAX_TRADE_RISK_PCT = 1.5       # Max risk per trade as % of equity
    MAX_WEEKLY_LOSS_PCT = 5.0      # Max weekly sum of worst-case losses as % of equity
    KILL_SWITCH_DRAWDOWN_PCT = 3.0 # Weekly realized drawdown kill switch as % of equity

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
    # Ticket-level risk evaluation (before / after)
    # ------------------------------------------------------------------

    def evaluate_ticket_risk(
        self,
        ticket_max_loss,
        ticket_position,
        existing_positions,
        equity=100_000.0,
        weekly_realized_pnl=0.0,
        existing_weekly_max_losses=0.0,
    ):
        """
        Evaluate risk for a proposed trade ticket against current portfolio.

        Parameters
        ----------
        ticket_max_loss : float
            Maximum possible loss for this trade (positive number).
        ticket_position : dict
            Aggregated position dict for the new ticket with keys:
            ``symbol``, ``delta``, ``vega``, ``gamma``, ``notional``,
            ``earnings_date``, ``expiry_bucket``.
        existing_positions : list[dict]
            Current portfolio positions.
        equity : float
            Total account equity (default 100 000).
        weekly_realized_pnl : float
            Realized P&L this week (negative means loss).
        existing_weekly_max_losses : float
            Sum of max-loss values for trades already opened this week.

        Returns
        -------
        dict with keys:
            portfolio_delta_before, portfolio_vega_before, portfolio_gamma_before,
            portfolio_delta_after, portfolio_vega_after, portfolio_gamma_after,
            max_loss_trade, max_loss_week, sector_concentration,
            risk_limits_pass (bool), reasons (list[str]).
        """
        risk_before = self.calculate_portfolio_risk(existing_positions)

        all_positions = list(existing_positions) + [ticket_position]
        risk_after = self.calculate_portfolio_risk(all_positions)

        max_loss_trade = float(ticket_max_loss)
        max_loss_week = float(existing_weekly_max_losses) + max_loss_trade

        reasons = []
        passed = True

        # 1. Max risk per trade: capped at MAX_TRADE_RISK_PCT of equity
        if equity > 0:
            trade_risk_pct = max_loss_trade / equity * 100
            if trade_risk_pct > self.MAX_TRADE_RISK_PCT:
                passed = False
                reasons.append(
                    f"Trade max loss {trade_risk_pct:.1f}% exceeds "
                    f"{self.MAX_TRADE_RISK_PCT}% of equity"
                )

        # 2. Max weekly sum of worst-case losses: MAX_WEEKLY_LOSS_PCT
        if equity > 0:
            week_risk_pct = max_loss_week / equity * 100
            if week_risk_pct > self.MAX_WEEKLY_LOSS_PCT:
                passed = False
                reasons.append(
                    f"Weekly max loss {week_risk_pct:.1f}% exceeds "
                    f"{self.MAX_WEEKLY_LOSS_PCT}% of equity"
                )

        # 3. Kill switch: weekly realized drawdown > KILL_SWITCH_DRAWDOWN_PCT
        if equity > 0 and weekly_realized_pnl < 0:
            dd_pct = abs(weekly_realized_pnl) / equity * 100
            if dd_pct > self.KILL_SWITCH_DRAWDOWN_PCT:
                passed = False
                reasons.append(
                    f"Weekly realized drawdown {dd_pct:.1f}% exceeds "
                    f"{self.KILL_SWITCH_DRAWDOWN_PCT}% kill switch"
                )

        return {
            'portfolio_delta_before': risk_before.get('portfolio_delta', 0.0),
            'portfolio_vega_before': risk_before.get('portfolio_vega', 0.0),
            'portfolio_gamma_before': risk_before.get('portfolio_gamma', 0.0),
            'portfolio_delta_after': risk_after.get('portfolio_delta', 0.0),
            'portfolio_vega_after': risk_after.get('portfolio_vega', 0.0),
            'portfolio_gamma_after': risk_after.get('portfolio_gamma', 0.0),
            'max_loss_trade': round(max_loss_trade, 2),
            'max_loss_week': round(max_loss_week, 2),
            'sector_concentration': risk_after.get('sector_concentration', {}),
            'risk_limits_pass': passed,
            'reasons': reasons,
        }

    # ------------------------------------------------------------------
    # Sector lookup
    # ------------------------------------------------------------------

    def _get_sector(self, symbol):
        """Return sector for a symbol, falling back to yfinance or 'other'."""
        if symbol in self.SECTOR_MAP:
            return self.SECTOR_MAP[symbol]
        try:
            info = get_ticker_info(symbol)
            return (info.get('sector') or 'other').lower()
        except Exception:
            logger.exception("Failed to get sector for %s", symbol)
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
            data = download_tickers(symbols, period='3mo')
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
            logger.exception("Failed to calculate correlation concentration")

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
            logger.exception("Failed to assess earnings cluster risk")

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
