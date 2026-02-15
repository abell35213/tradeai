"""
Setup Performance Module

Tracks and aggregates performance metrics by earnings setup type (A-E):
- Average return by setup type
- Win rate by market-cap bucket
- Sharpe ratio by setup type
- Implied vs realized move difference by setup
- Post-earnings drift behavior by setup

Answers the question: "Show me the Sharpe by setup over 10 years"
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

from backtester.earnings_backtest import EarningsBacktester


class SetupPerformanceTracker:
    """Aggregates and reports performance by earnings setup classification."""

    def __init__(self, earnings_analyzer=None):
        """
        Parameters:
            earnings_analyzer: An EarningsAnalyzer instance for setup classification.
                               If None, a new one will be created when needed.
        """
        self.backtester = EarningsBacktester()
        self._earnings_analyzer = earnings_analyzer

    @property
    def earnings_analyzer(self):
        if self._earnings_analyzer is None:
            from earnings_analyzer import EarningsAnalyzer
            self._earnings_analyzer = EarningsAnalyzer()
        return self._earnings_analyzer

    def get_performance_by_setup(self, symbols, years=10):
        """
        Compute performance metrics grouped by setup type across symbols.

        Parameters:
            symbols (list): List of ticker symbols to analyze.
            years (int): Historical lookback in years.

        Returns:
            dict with per-setup metrics: avg return, Sharpe, win rate, etc.
        """
        setup_returns = defaultdict(list)
        setup_wins = defaultdict(int)
        setup_losses = defaultdict(int)
        setup_implied = defaultdict(list)
        setup_realized = defaultdict(list)
        setup_drift = defaultdict(list)
        mcap_wins = defaultdict(lambda: defaultdict(int))
        mcap_total = defaultdict(lambda: defaultdict(int))

        for symbol in symbols:
            try:
                # Classify current setup
                snapshot = self.earnings_analyzer.get_earnings_snapshot(symbol)
                setup_type = snapshot.get('earnings_setup', {}).get('setup', 'E')

                # Backtest
                bt = self.backtester.backtest_earnings(symbol, years=years)
                if 'error' in bt:
                    continue

                mcap_bucket = bt.get('market_cap_bucket', 'unknown')

                for event in bt.get('events', []):
                    ret = event.get('return_pct', 0)
                    setup_returns[setup_type].append(ret)
                    if ret > 0:
                        setup_wins[setup_type] += 1
                        mcap_wins[setup_type][mcap_bucket] += 1
                    else:
                        setup_losses[setup_type] += 1
                    mcap_total[setup_type][mcap_bucket] += 1

                    if event.get('implied_move') is not None:
                        setup_implied[setup_type].append(event['implied_move'])
                    if event.get('realized_move') is not None:
                        setup_realized[setup_type].append(event['realized_move'])
                    if event.get('post_earnings_drift_5d') is not None:
                        setup_drift[setup_type].append(event['post_earnings_drift_5d'])

            except Exception:
                logger.exception("Failed to process symbol %s", symbol)
                continue

        # Build summary per setup
        results = {}
        for setup in sorted(set(list(setup_returns.keys()))):
            rets = setup_returns[setup]
            if not rets:
                continue

            avg_ret = float(np.mean(rets))
            std_ret = float(np.std(rets)) if len(rets) > 1 else 0
            sharpe = avg_ret / std_ret if std_ret > 0 else 0
            total = setup_wins[setup] + setup_losses[setup]
            win_rate = setup_wins[setup] / total if total > 0 else 0

            win_rate_by_mcap = {}
            for bucket in mcap_total[setup]:
                t = mcap_total[setup][bucket]
                w = mcap_wins[setup][bucket]
                win_rate_by_mcap[bucket] = round(w / t, 4) if t > 0 else 0

            avg_implied = (
                round(float(np.mean(setup_implied[setup])), 4)
                if setup_implied[setup] else None
            )
            avg_realized = (
                round(float(np.mean(setup_realized[setup])), 4)
                if setup_realized[setup] else None
            )
            iv_rv_diff = (
                round(avg_implied - avg_realized, 4)
                if avg_implied is not None and avg_realized is not None else None
            )
            avg_drift = (
                round(float(np.mean(setup_drift[setup])), 4)
                if setup_drift[setup] else None
            )

            results[setup] = {
                'total_events': total,
                'avg_return_pct': round(avg_ret, 4),
                'std_return_pct': round(std_ret, 4),
                'sharpe_ratio': round(sharpe, 4),
                'win_rate': round(win_rate, 4),
                'win_rate_by_market_cap': win_rate_by_mcap,
                'avg_implied_move': avg_implied,
                'avg_realized_move': avg_realized,
                'implied_vs_realized_diff': iv_rv_diff,
                'avg_post_earnings_drift_5d': avg_drift,
            }

        return {
            'years_analyzed': years,
            'symbols_analyzed': len(symbols),
            'performance_by_setup': results,
            'timestamp': datetime.now().isoformat(),
        }

    def get_sharpe_by_setup(self, symbols, years=10):
        """
        Convenience method: return just Sharpe ratios by setup type.

        Parameters:
            symbols (list): List of ticker symbols.
            years (int): Historical lookback.

        Returns:
            dict mapping setup label to Sharpe ratio.
        """
        perf = self.get_performance_by_setup(symbols, years)
        sharpes = {}
        for setup, metrics in perf.get('performance_by_setup', {}).items():
            sharpes[setup] = metrics.get('sharpe_ratio', 0)
        return {
            'years_analyzed': years,
            'sharpe_by_setup': sharpes,
            'timestamp': datetime.now().isoformat(),
        }
