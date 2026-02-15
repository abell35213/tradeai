"""
Earnings Backtest Module

Backtests earnings-event strategies over historical data:
- Simulates straddle/strangle returns around earnings events
- Computes implied vs realized move for each event
- Tracks post-earnings drift behavior
- Aggregates statistics by market-cap bucket

Designed to answer: "Show me the Sharpe by setup over 10 years"
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EarningsBacktester:
    """Backtest earnings-event strategies using historical price data."""

    # Market-cap buckets (in billions)
    MCAP_BUCKETS = {
        'mega': 200e9,
        'large': 10e9,
        'mid': 2e9,
        'small': 0,
    }

    def __init__(self):
        pass

    def backtest_earnings(self, symbol, years=10, strategy='straddle'):
        """
        Backtest an earnings strategy for a symbol over N years.

        Parameters:
            symbol (str): Ticker symbol.
            years (int): Number of years of history to analyze.
            strategy (str): 'straddle' or 'strangle'.

        Returns:
            dict with aggregate backtest metrics and per-event results.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            market_cap = info.get('marketCap')
            mcap_bucket = self._classify_market_cap(market_cap)

            # Get historical data
            period = f'{years}y'
            hist = ticker.history(period=period)
            if len(hist) < 60:
                return {'error': 'Insufficient historical data', 'symbol': symbol}

            # Identify historical earnings dates from quarterly financials
            earnings_dates = self._get_historical_earnings_dates(ticker)
            if not earnings_dates:
                return {'error': 'No earnings dates found', 'symbol': symbol}

            events = []
            for edate in earnings_dates:
                event = self._analyze_single_event(hist, edate, strategy)
                if event:
                    events.append(event)

            if not events:
                return {'error': 'No analyzable events', 'symbol': symbol}

            # Aggregate statistics
            returns = [e['return_pct'] for e in events]
            wins = [r for r in returns if r > 0]
            losses = [r for r in returns if r <= 0]

            avg_return = float(np.mean(returns))
            std_return = float(np.std(returns)) if len(returns) > 1 else 0
            sharpe = avg_return / std_return if std_return > 0 else 0

            implied_moves = [e['implied_move'] for e in events if e.get('implied_move') is not None]
            realized_moves = [e['realized_move'] for e in events if e.get('realized_move') is not None]

            return {
                'symbol': symbol,
                'strategy': strategy,
                'years_analyzed': years,
                'market_cap_bucket': mcap_bucket,
                'total_events': len(events),
                'avg_return_pct': round(avg_return, 4),
                'std_return_pct': round(std_return, 4),
                'sharpe_ratio': round(sharpe, 4),
                'win_rate': round(len(wins) / len(returns), 4) if returns else 0,
                'avg_win': round(float(np.mean(wins)), 4) if wins else 0,
                'avg_loss': round(float(np.mean(losses)), 4) if losses else 0,
                'avg_implied_move': round(float(np.mean(implied_moves)), 4) if implied_moves else None,
                'avg_realized_move': round(float(np.mean(realized_moves)), 4) if realized_moves else None,
                'implied_vs_realized_diff': (
                    round(float(np.mean(implied_moves)) - float(np.mean(realized_moves)), 4)
                    if implied_moves and realized_moves else None
                ),
                'events': events[-20:],  # Last 20 events for detail
                'timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            return {'error': str(e), 'symbol': symbol}

    def _get_historical_earnings_dates(self, ticker):
        """
        Extract historical earnings dates from yfinance earnings data.
        """
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

        # Fallback: use quarterly financials dates
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

    def _analyze_single_event(self, hist, earnings_date, strategy):
        """
        Analyze a single earnings event.

        Returns dict with pre/post price data and return calculations.
        """
        try:
            # Convert to datetime for comparison
            if hasattr(earnings_date, 'strftime'):
                ed = pd.Timestamp(earnings_date)
            else:
                ed = pd.Timestamp(earnings_date)

            # Find the closest trading days before and after
            dates = hist.index
            pre_dates = dates[dates < ed]
            post_dates = dates[dates >= ed]

            if len(pre_dates) < 5 or len(post_dates) < 2:
                return None

            pre_close = float(hist.loc[pre_dates[-1], 'Close'])
            post_close = float(hist.loc[post_dates[0], 'Close'])

            # Realized move
            realized_move = abs(post_close - pre_close) / pre_close

            # Implied move estimate: 1-day implied move from recent realized vol
            recent_returns = hist.loc[pre_dates[-20:], 'Close'].pct_change().dropna()
            daily_vol = float(recent_returns.std()) if len(recent_returns) > 5 else 0.02
            implied_move = daily_vol  # 1-day horizon

            # Strategy return calculation:
            if strategy == 'straddle':
                # Straddle profits when |realized move| exceeds implied move
                return_pct = realized_move - implied_move
            else:
                # Strangle breakeven is wider (~1.3x implied for OTM strikes)
                # and max loss is limited to ~50% of premium collected
                return_pct = max(realized_move - implied_move * 1.3, -implied_move * 0.5)

            # Post-earnings drift (5-day)
            drift = None
            if len(post_dates) >= 6:
                drift_close = float(hist.loc[post_dates[5], 'Close'])
                drift = (drift_close - post_close) / post_close

            return {
                'date': ed.strftime('%Y-%m-%d'),
                'pre_close': round(pre_close, 2),
                'post_close': round(post_close, 2),
                'realized_move': round(realized_move, 4),
                'implied_move': round(implied_move, 4),
                'return_pct': round(return_pct, 4),
                'post_earnings_drift_5d': round(drift, 4) if drift is not None else None,
            }

        except Exception:
            logger.exception("Failed to simulate single earnings event")
            return None

    def _classify_market_cap(self, market_cap):
        """Classify market cap into bucket."""
        if market_cap is None:
            return 'unknown'
        for bucket, threshold in self.MCAP_BUCKETS.items():
            if market_cap >= threshold:
                return bucket
        return 'small'
