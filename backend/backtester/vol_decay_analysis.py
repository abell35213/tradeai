"""
Vol Decay Analysis Module

Analyzes implied-vs-realized volatility dynamics around earnings:
- Vol crush magnitude distribution
- Implied vs realized move difference over time
- Term-structure decay patterns pre/post earnings
- Statistical distribution of vol crush by setup type

Provides the data layer for understanding how IV premium dissipates.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


class VolDecayAnalyzer:
    """Analyzes volatility crush and decay patterns around earnings events."""

    def __init__(self):
        pass

    def analyze_vol_decay(self, symbol, years=5):
        """
        Analyze historical vol crush patterns for a symbol.

        Parameters:
            symbol (str): Ticker symbol.
            years (int): Years of history to analyze.

        Returns:
            dict with vol crush statistics and distribution.
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f'{years}y')

            if len(hist) < 60:
                return {'error': 'Insufficient data', 'symbol': symbol}

            earnings_dates = self._get_earnings_dates(ticker)
            if not earnings_dates:
                return {'error': 'No earnings dates found', 'symbol': symbol}

            crush_events = []
            for edate in earnings_dates:
                event = self._measure_vol_crush(hist, edate)
                if event:
                    crush_events.append(event)

            if not crush_events:
                return {'error': 'No analyzable crush events', 'symbol': symbol}

            # Aggregate statistics
            crush_magnitudes = [e['crush_magnitude'] for e in crush_events]
            implied_moves = [e['implied_move'] for e in crush_events if e.get('implied_move') is not None]
            realized_moves = [e['realized_move'] for e in crush_events if e.get('realized_move') is not None]

            distribution = {
                'mean': round(float(np.mean(crush_magnitudes)), 4),
                'median': round(float(np.median(crush_magnitudes)), 4),
                'std': round(float(np.std(crush_magnitudes)), 4),
                'min': round(float(np.min(crush_magnitudes)), 4),
                'max': round(float(np.max(crush_magnitudes)), 4),
                'p25': round(float(np.percentile(crush_magnitudes, 25)), 4),
                'p75': round(float(np.percentile(crush_magnitudes, 75)), 4),
            }

            iv_rv_diff = None
            if implied_moves and realized_moves:
                iv_rv_diff = round(
                    float(np.mean(implied_moves)) - float(np.mean(realized_moves)), 4
                )

            return {
                'symbol': symbol,
                'years_analyzed': years,
                'total_events': len(crush_events),
                'crush_distribution': distribution,
                'avg_implied_move': round(float(np.mean(implied_moves)), 4) if implied_moves else None,
                'avg_realized_move': round(float(np.mean(realized_moves)), 4) if realized_moves else None,
                'iv_vs_realized_diff': iv_rv_diff,
                'events': crush_events[-20:],
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            return {'error': str(e), 'symbol': symbol}

    def _get_earnings_dates(self, ticker):
        """Extract earnings dates from yfinance."""
        dates = []
        try:
            earnings = ticker.earnings_dates
            if earnings is not None and len(earnings) > 0:
                for dt in earnings.index:
                    if hasattr(dt, 'date'):
                        dates.append(dt.date())
                    else:
                        dates.append(dt)
        except Exception:
            logger.exception("Failed to retrieve earnings_dates for ticker")
            pass

        if not dates:
            try:
                quarterly = ticker.quarterly_financials
                if quarterly is not None and len(quarterly.columns) > 0:
                    for col in quarterly.columns:
                        if hasattr(col, 'date'):
                            dates.append(col.date())
                        else:
                            dates.append(col)
            except Exception:
                logger.exception("Failed to retrieve quarterly financials dates for ticker")
                pass

        return sorted(dates)

    def _measure_vol_crush(self, hist, earnings_date):
        """
        Measure vol crush around a single earnings event.

        Calculates the change in realized volatility (as proxy for IV crush)
        from the 10-day window pre-earnings to the 5-day window post-earnings.
        """
        try:
            ed = pd.Timestamp(earnings_date)
            dates = hist.index
            pre_dates = dates[dates < ed]
            post_dates = dates[dates >= ed]

            if len(pre_dates) < 10 or len(post_dates) < 5:
                return None

            # Pre-earnings vol (10-day realized)
            pre_returns = hist.loc[pre_dates[-10:], 'Close'].pct_change().dropna()
            pre_vol = float(pre_returns.std()) * math.sqrt(252) if len(pre_returns) > 2 else None

            # Post-earnings vol (5-day realized)
            post_returns = hist.loc[post_dates[:5], 'Close'].pct_change().dropna()
            post_vol = float(post_returns.std()) * math.sqrt(252) if len(post_returns) > 2 else None

            if pre_vol is None or post_vol is None or pre_vol == 0:
                return None

            crush = (pre_vol - post_vol) / pre_vol

            # Realized move
            pre_close = float(hist.loc[pre_dates[-1], 'Close'])
            post_close = float(hist.loc[post_dates[0], 'Close'])
            realized_move = abs(post_close - pre_close) / pre_close

            # Implied move proxy: 1-day implied move from pre-earnings realized vol
            daily_vol = float(pre_returns.std()) if len(pre_returns) > 2 else 0.02
            implied_move = daily_vol  # 1-day horizon

            return {
                'date': ed.strftime('%Y-%m-%d'),
                'pre_vol': round(pre_vol, 4),
                'post_vol': round(post_vol, 4),
                'crush_magnitude': round(crush, 4),
                'realized_move': round(realized_move, 4),
                'implied_move': round(implied_move, 4),
            }

        except Exception:
            logger.exception("Failed to analyze vol event")
            return None
