"""
Regime Classifier Module

Classifies market regimes across multiple dimensions:
- Volatility regime (compressed, expanding, stressed)
- Correlation regime (low, medium, high)
- Risk appetite (risk_on, neutral, risk_off)

Uses VIX percentile, correlation analysis, index gamma exposure,
and macro event proximity to produce regime classifications.
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from market_cache import get_ticker_history, download_tickers, get_ticker_options, get_option_chain

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """Classifies current market regime across volatility, correlation, and risk appetite."""

    # Default VIX percentile lookback in trading days (~1 year)
    VIX_LOOKBACK_DAYS = 252

    # Thresholds for VIX percentile-based vol regime classification
    VOL_COMPRESSED_PCTL = 25
    VOL_STRESSED_PCTL = 75

    # Thresholds for cross-asset correlation regime
    CORR_LOW_THRESHOLD = 0.3
    CORR_HIGH_THRESHOLD = 0.6

    # Sector ETFs used for correlation analysis
    SECTOR_ETFS = ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLU', 'XLB']

    # Macro-sensitive tickers for event proximity detection
    MACRO_TICKERS = ['TLT', 'GLD', 'UUP']

    # --- SPY-specific gating (v1) ---
    # Block if VIX day-over-day change exceeds this percentage
    VIX_SPIKE_PCT = 10.0
    # Block if VIX absolute level exceeds this ceiling
    VIX_HARD_CEILING = 35.0
    # Block if SPY 5-day ATR / 20-day ATR exceeds this ratio
    ATR_RATIO_THRESHOLD = 1.5
    # Manual macro-event calendar: list of (ISO-date-string, label) tuples.
    # Add upcoming FOMC, CPI, NFP, etc. dates here.
    MACRO_EVENT_CALENDAR = []

    def __init__(self):
        pass

    def classify(self):
        """
        Run full regime classification.

        Returns:
            dict with vol_regime, correlation_regime, risk_appetite, and supporting details.
        """
        vol = self._classify_vol_regime()
        corr = self._classify_correlation_regime()
        gamma = self._estimate_gamma_exposure()
        macro = self._assess_macro_event_proximity()
        risk_appetite = self._determine_risk_appetite(vol, corr, gamma, macro)

        return {
            'vol_regime': vol['regime'],
            'correlation_regime': corr['regime'],
            'risk_appetite': risk_appetite,
            'details': {
                'volatility': vol,
                'correlation': corr,
                'gamma_exposure': gamma,
                'macro_proximity': macro,
            },
            'timestamp': datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Volatility regime
    # ------------------------------------------------------------------

    def _classify_vol_regime(self):
        """
        Classify volatility regime using VIX percentile rank.

        Returns dict with regime label and supporting metrics.
        """
        result = {
            'regime': 'expanding',
            'vix_current': None,
            'vix_percentile': None,
            'vix_sma_20': None,
            'vix_prev_close': None,
            'vix_change_pct': None,
        }

        try:
            hist = get_ticker_history('^VIX', period='1y')
            if len(hist) < 20:
                return result

            closes = hist['Close']
            current = float(closes.iloc[-1])
            percentile = float((closes < current).mean() * 100)
            sma_20 = float(closes.rolling(window=20).mean().iloc[-1])

            result['vix_current'] = round(current, 2)
            result['vix_percentile'] = round(percentile, 1)
            result['vix_sma_20'] = round(sma_20, 2)

            if len(closes) >= 2:
                prev = float(closes.iloc[-2])
                result['vix_prev_close'] = round(prev, 2)
                if prev > 0:
                    result['vix_change_pct'] = round(
                        (current - prev) / prev * 100, 2
                    )

            if percentile <= self.VOL_COMPRESSED_PCTL:
                result['regime'] = 'compressed'
            elif percentile >= self.VOL_STRESSED_PCTL:
                result['regime'] = 'stressed'
            else:
                result['regime'] = 'expanding'
        except Exception:
            logger.exception("Failed to classify vol regime")

        return result

    # ------------------------------------------------------------------
    # Correlation regime
    # ------------------------------------------------------------------

    def _classify_correlation_regime(self):
        """
        Classify correlation regime by computing average pairwise
        correlation among sector ETFs over a rolling 20-day window.
        """
        result = {
            'regime': 'medium',
            'avg_correlation': None,
            'sector_count': 0,
        }

        try:
            data = download_tickers(self.SECTOR_ETFS, period='3mo')
            if data.empty:
                return result

            closes = data['Close'].dropna(axis=1, how='all')
            if closes.shape[1] < 2:
                return result

            returns = closes.pct_change().dropna()
            if len(returns) < 20:
                return result

            recent = returns.iloc[-20:]
            corr_matrix = recent.corr()
            # Average of upper triangle (excluding diagonal)
            mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
            avg_corr = float(corr_matrix.values[mask].mean())

            result['avg_correlation'] = round(avg_corr, 4)
            result['sector_count'] = int(closes.shape[1])

            if avg_corr < self.CORR_LOW_THRESHOLD:
                result['regime'] = 'low'
            elif avg_corr > self.CORR_HIGH_THRESHOLD:
                result['regime'] = 'high'
            else:
                result['regime'] = 'medium'
        except Exception:
            logger.exception("Failed to classify correlation regime")

        return result

    # ------------------------------------------------------------------
    # Gamma exposure estimate
    # ------------------------------------------------------------------

    def _estimate_gamma_exposure(self):
        """
        Estimate index gamma exposure direction using SPY options
        put/call open-interest ratio and volume skew.
        """
        result = {
            'gamma_direction': 'neutral',
            'put_call_oi_ratio': None,
            'total_oi': None,
        }

        try:
            expirations = get_ticker_options('SPY')
            if not expirations:
                return result

            chain = get_option_chain('SPY', expirations[0])
            call_oi = int(chain.calls['openInterest'].sum())
            put_oi = int(chain.puts['openInterest'].sum())
            total_oi = call_oi + put_oi

            result['total_oi'] = total_oi
            if call_oi > 0:
                ratio = put_oi / call_oi
                result['put_call_oi_ratio'] = round(ratio, 4)
                # Put/call OI > 1.2 implies heavy put hedging; dealers are
                # short puts, creating negative gamma (amplifying moves).
                # Below 0.8 implies call-heavy positioning with positive gamma
                # (dampening moves as dealers hedge by selling into rallies).
                if ratio > 1.2:
                    result['gamma_direction'] = 'negative'
                elif ratio < 0.8:
                    result['gamma_direction'] = 'positive'
        except Exception:
            logger.exception("Failed to estimate gamma exposure")

        return result

    # ------------------------------------------------------------------
    # Macro event proximity
    # ------------------------------------------------------------------

    def _assess_macro_event_proximity(self):
        """
        Detect macro-event proximity by looking for recent spikes in
        macro-sensitive assets (TLT, GLD, UUP) volatility.
        """
        result = {
            'elevated': False,
            'signals': [],
        }

        try:
            for sym in self.MACRO_TICKERS:
                hist = get_ticker_history(sym, period='1mo')
                if len(hist) < 10:
                    continue
                returns = hist['Close'].pct_change().dropna()
                recent_vol = float(returns.iloc[-5:].std())
                full_vol = float(returns.std())
                if full_vol > 0 and recent_vol / full_vol > 1.5:
                    result['elevated'] = True
                    result['signals'].append(f'{sym} volatility spike')
        except Exception:
            logger.exception("Failed to assess macro event proximity")

        return result

    # ------------------------------------------------------------------
    # Risk appetite determination
    # ------------------------------------------------------------------

    def _determine_risk_appetite(self, vol, corr, gamma, macro):
        """
        Combine sub-signals into a single risk-appetite label.
        """
        risk_off_signals = 0
        risk_on_signals = 0

        # Volatility contribution
        if vol['regime'] == 'stressed':
            risk_off_signals += 2
        elif vol['regime'] == 'compressed':
            risk_on_signals += 2

        # Correlation contribution
        if corr['regime'] == 'high':
            risk_off_signals += 1
        elif corr['regime'] == 'low':
            risk_on_signals += 1

        # Gamma contribution
        if gamma['gamma_direction'] == 'negative':
            risk_off_signals += 1
        elif gamma['gamma_direction'] == 'positive':
            risk_on_signals += 1

        # Macro proximity contribution
        if macro['elevated']:
            risk_off_signals += 1

        if risk_off_signals >= 3:
            return 'risk_off'
        elif risk_on_signals >= 3:
            return 'risk_on'
        return 'neutral'

    # ------------------------------------------------------------------
    # Trade gate
    # ------------------------------------------------------------------

    def should_trade(self, classification=None):
        """
        Hard gate: return False if regime is *stressed*, macro
        proximity is elevated, VIX is spiking or above the hard ceiling,
        a known macro event is within 48 h, or realized vol is rising
        sharply.

        Parameters
        ----------
        classification : dict or None
            Pre-computed output of ``classify()``.  If *None* the method
            will call ``classify()`` internally.

        Returns
        -------
        dict with keys:
            - pass_trade (bool)
            - reasons (list[str])
        """
        if classification is None:
            classification = self.classify()

        reasons = []

        vol_regime = classification.get('vol_regime', '')
        if vol_regime == 'stressed':
            reasons.append('Volatility regime is stressed')

        macro = classification.get('details', {}).get('macro_proximity', {})
        if macro.get('elevated', False):
            reasons.append('Macro-event proximity is elevated')

        # --- SPY-specific gating (v1) ---

        vol_details = classification.get('details', {}).get('volatility', {})

        # 1. VIX spike (day-over-day change)
        vix_change = vol_details.get('vix_change_pct')
        if vix_change is not None and vix_change > self.VIX_SPIKE_PCT:
            reasons.append(
                f'VIX spike: {vix_change:.1f}% day-over-day '
                f'(threshold: {self.VIX_SPIKE_PCT}%)'
            )

        # 2. VIX hard ceiling
        vix_current = vol_details.get('vix_current')
        if vix_current is not None and vix_current > self.VIX_HARD_CEILING:
            reasons.append(
                f'VIX above hard ceiling: {vix_current:.1f} '
                f'(ceiling: {self.VIX_HARD_CEILING})'
            )

        # 3. Macro event within 48 h (manual calendar)
        macro_event = self._check_macro_event_within_48h()
        if macro_event:
            reasons.append(f'Macro event within 48h: {macro_event}')

        # 4. Realized vol rising sharply (SPY ATR ratio)
        atr_reason = self._check_realized_vol_rising()
        if atr_reason:
            reasons.append(atr_reason)

        return {
            'pass_trade': len(reasons) == 0,
            'reasons': reasons,
        }

    # ------------------------------------------------------------------
    # SPY-specific gating helpers
    # ------------------------------------------------------------------

    def _check_macro_event_within_48h(self):
        """Return event label if a known macro event is within 48 hours,
        else *None*."""
        now = datetime.now()
        cutoff = now + timedelta(hours=48)
        for event_date_str, label in self.MACRO_EVENT_CALENDAR:
            try:
                event_date = datetime.fromisoformat(event_date_str)
                if now <= event_date <= cutoff:
                    return label
            except (ValueError, TypeError):
                continue
        return None

    def _check_realized_vol_rising(self):
        """Return a reason string if SPY 5-day ATR / 20-day ATR exceeds
        the threshold, else *None*."""
        try:
            hist = get_ticker_history('SPY', period='3mo')
            if len(hist) < 21:
                return None

            high = hist['High']
            low = hist['Low']
            close = hist['Close']

            prev_close = close.shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)

            atr_5 = float(tr.iloc[-5:].mean())
            atr_20 = float(tr.iloc[-20:].mean())

            if atr_20 > 0:
                ratio = atr_5 / atr_20
                if ratio > self.ATR_RATIO_THRESHOLD:
                    return (
                        f'Realized vol rising sharply: SPY 5d/20d ATR ratio '
                        f'{ratio:.2f} (threshold: {self.ATR_RATIO_THRESHOLD})'
                    )
        except Exception:
            logger.exception("Failed to check realized vol")

        return None
