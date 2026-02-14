"""
Vol Surface Analyzer Module

Analyzes volatility surface characteristics:
- Term structure distortions
- Skew dislocations
- Forward vol vs spot vol
- Cross-sectional vol dislocations
- Earnings IV vs sector IV comparison
- Skew percentile ranking (1-year)
- Portfolio overlap detection

Designed as the vol-intelligence layer for a risk-adjusted capital allocation engine.
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import math
from scipy.stats import norm


class VolSurfaceAnalyzer:
    """Analyzes implied-volatility surface characteristics for trading signals."""

    # Default sector ETF mapping for cross-sectional comparisons
    SECTOR_ETF_MAP = {
        'tech': 'XLK',
        'financials': 'XLF',
        'energy': 'XLE',
        'healthcare': 'XLV',
        'consumer_discretionary': 'XLY',
        'consumer_staples': 'XLP',
        'industrials': 'XLI',
        'utilities': 'XLU',
        'materials': 'XLB',
    }

    def __init__(self):
        pass

    def analyze(self, symbol):
        """
        Run full vol-surface analysis for a symbol.

        Parameters:
            symbol (str): Ticker symbol.

        Returns:
            dict with term structure, skew, forward vol, and dislocation analysis.
        """
        term_structure = self._analyze_term_structure(symbol)
        skew = self._analyze_skew(symbol)
        forward_vol = self._calculate_forward_vol(symbol)
        sector_comparison = self._compare_earnings_iv_to_sector(symbol)
        skew_percentile = self._skew_percentile(symbol)
        cross_sectional = self._detect_cross_sectional_dislocations(symbol)

        return {
            'symbol': symbol,
            'term_structure': term_structure,
            'skew': skew,
            'forward_vol': forward_vol,
            'sector_iv_comparison': sector_comparison,
            'skew_percentile': skew_percentile,
            'cross_sectional_dislocations': cross_sectional,
            'timestamp': datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Term structure analysis
    # ------------------------------------------------------------------

    def _analyze_term_structure(self, symbol):
        """
        Analyze IV term structure across available expirations.
        Detects contango, backwardation, and kinks.
        """
        result = {
            'shape': 'unknown',
            'expirations': [],
            'atm_ivs': [],
            'distortion_detected': False,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            expirations = ticker.options

            if not expirations or not current_price:
                return result

            ivs = []
            exp_labels = []

            for exp_date in expirations[:6]:  # Analyze up to 6 expirations
                try:
                    chain = ticker.option_chain(exp_date)
                    calls = chain.calls
                    if len(calls) == 0:
                        continue
                    atm_idx = (calls['strike'] - current_price).abs().idxmin()
                    atm_iv = float(calls.loc[atm_idx, 'impliedVolatility'])
                    ivs.append(round(atm_iv, 4))
                    exp_labels.append(exp_date)
                except Exception:
                    continue

            if len(ivs) < 2:
                return result

            result['expirations'] = exp_labels
            result['atm_ivs'] = ivs

            # Determine shape
            if ivs[0] > ivs[-1]:
                result['shape'] = 'backwardation'
            elif ivs[0] < ivs[-1]:
                result['shape'] = 'contango'
            else:
                result['shape'] = 'flat'

            # Detect kinks / distortions (non-monotonic)
            diffs = [ivs[i + 1] - ivs[i] for i in range(len(ivs) - 1)]
            sign_changes = sum(
                1 for i in range(len(diffs) - 1)
                if diffs[i] * diffs[i + 1] < 0
            )
            if sign_changes > 0:
                result['distortion_detected'] = True

            if result['distortion_detected']:
                result['signal'] = 'Term structure distortion detected — potential event mispricing'
            elif result['shape'] == 'backwardation':
                result['signal'] = 'Backwardation — near-term fear elevated'
            elif result['shape'] == 'contango':
                result['signal'] = 'Contango — normal term structure'
            else:
                result['signal'] = 'Flat term structure'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Skew analysis
    # ------------------------------------------------------------------

    def _analyze_skew(self, symbol):
        """
        Analyze put-call skew for the front-month expiration.
        Compares 25-delta put IV vs 25-delta call IV approximation.
        """
        result = {
            'put_skew_iv': None,
            'call_skew_iv': None,
            'skew_spread': None,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            expirations = ticker.options

            if not expirations or not current_price:
                return result

            chain = ticker.option_chain(expirations[0])
            calls = chain.calls
            puts = chain.puts

            if len(calls) == 0 or len(puts) == 0:
                return result

            # Approximate 25-delta strikes using ±5% OTM as a simplified proxy.
            # A true 25-delta calculation would require Black-Scholes delta
            # inversion for each strike, which depends on time-to-expiry and IV.
            # This approximation is reasonable for liquid names with moderate IV.
            otm_call_strike = current_price * 1.05
            otm_put_strike = current_price * 0.95

            call_idx = (calls['strike'] - otm_call_strike).abs().idxmin()
            put_idx = (puts['strike'] - otm_put_strike).abs().idxmin()

            call_iv = float(calls.loc[call_idx, 'impliedVolatility'])
            put_iv = float(puts.loc[put_idx, 'impliedVolatility'])

            result['call_skew_iv'] = round(call_iv, 4)
            result['put_skew_iv'] = round(put_iv, 4)
            result['skew_spread'] = round(put_iv - call_iv, 4)

            if result['skew_spread'] > 0.10:
                result['signal'] = 'Heavy put skew — downside protection demand elevated'
            elif result['skew_spread'] < -0.05:
                result['signal'] = 'Inverted skew — unusual call demand'
            else:
                result['signal'] = 'Normal skew'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Forward vol calculation
    # ------------------------------------------------------------------

    def _calculate_forward_vol(self, symbol):
        """
        Calculate forward implied volatility between two expirations.
        Forward vol = sqrt((IV2^2 * T2 - IV1^2 * T1) / (T2 - T1))
        """
        result = {
            'spot_vol': None,
            'forward_vol': None,
            'ratio': None,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            expirations = ticker.options

            if not expirations or len(expirations) < 2 or not current_price:
                return result

            now = datetime.now()

            # Front expiration
            chain1 = ticker.option_chain(expirations[0])
            calls1 = chain1.calls
            if len(calls1) == 0:
                return result
            atm_idx1 = (calls1['strike'] - current_price).abs().idxmin()
            iv1 = float(calls1.loc[atm_idx1, 'impliedVolatility'])
            t1 = max((datetime.strptime(expirations[0], '%Y-%m-%d') - now).days / 365.0, 0.01)

            # Second expiration
            chain2 = ticker.option_chain(expirations[1])
            calls2 = chain2.calls
            if len(calls2) == 0:
                return result
            atm_idx2 = (calls2['strike'] - current_price).abs().idxmin()
            iv2 = float(calls2.loc[atm_idx2, 'impliedVolatility'])
            t2 = max((datetime.strptime(expirations[1], '%Y-%m-%d') - now).days / 365.0, 0.02)

            result['spot_vol'] = round(iv1, 4)

            # Forward vol formula
            var_diff = iv2 ** 2 * t2 - iv1 ** 2 * t1
            dt = t2 - t1
            if var_diff > 0 and dt > 0:
                fwd_vol = math.sqrt(var_diff / dt)
                result['forward_vol'] = round(fwd_vol, 4)
                result['ratio'] = round(fwd_vol / iv1, 4) if iv1 > 0 else None

                if result['ratio'] and result['ratio'] > 1.2:
                    result['signal'] = 'Forward vol elevated vs spot — market pricing future event'
                elif result['ratio'] and result['ratio'] < 0.8:
                    result['signal'] = 'Forward vol depressed — potential mean-reversion opportunity'
                else:
                    result['signal'] = 'Forward vol in line with spot'
            else:
                result['signal'] = 'Unable to compute forward vol (negative variance or zero dt)'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Earnings IV vs sector IV comparison
    # ------------------------------------------------------------------

    def _compare_earnings_iv_to_sector(self, symbol):
        """
        Compare a symbol's front-month ATM IV to its sector ETF's IV.
        """
        result = {
            'symbol_iv': None,
            'sector_etf': None,
            'sector_iv': None,
            'iv_premium': None,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            sector = (info.get('sector') or '').lower().replace(' ', '_')
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')

            expirations = ticker.options
            if not expirations or not current_price:
                return result

            chain = ticker.option_chain(expirations[0])
            calls = chain.calls
            if len(calls) == 0:
                return result
            atm_idx = (calls['strike'] - current_price).abs().idxmin()
            symbol_iv = float(calls.loc[atm_idx, 'impliedVolatility'])
            result['symbol_iv'] = round(symbol_iv, 4)

            # Find matching sector ETF
            sector_etf = None
            for key, etf in self.SECTOR_ETF_MAP.items():
                if key in sector:
                    sector_etf = etf
                    break
            if sector_etf is None:
                sector_etf = 'SPY'  # Fallback to broad market

            result['sector_etf'] = sector_etf

            etf_ticker = yf.Ticker(sector_etf)
            etf_info = etf_ticker.info
            etf_price = etf_info.get('currentPrice') or etf_info.get('regularMarketPrice')
            etf_exps = etf_ticker.options

            if etf_exps and etf_price:
                etf_chain = etf_ticker.option_chain(etf_exps[0])
                etf_calls = etf_chain.calls
                if len(etf_calls) > 0:
                    etf_atm = (etf_calls['strike'] - etf_price).abs().idxmin()
                    s_iv = float(etf_calls.loc[etf_atm, 'impliedVolatility'])
                    result['sector_iv'] = round(s_iv, 4)
                    if s_iv > 0:
                        premium = symbol_iv / s_iv
                        result['iv_premium'] = round(premium, 4)
                        if premium > 1.5:
                            result['signal'] = 'Symbol IV significantly above sector — earnings premium likely'
                        elif premium < 0.8:
                            result['signal'] = 'Symbol IV below sector — potential under-pricing'
                        else:
                            result['signal'] = 'Symbol IV in line with sector'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Skew percentile (1-year)
    # ------------------------------------------------------------------

    def _skew_percentile(self, symbol):
        """
        Rank current put-call skew against historical realized skew
        using 1-year daily return distribution skewness as a proxy.
        """
        result = {
            'current_skew': None,
            'percentile': None,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1y')
            if len(hist) < 60:
                return result

            returns = hist['Close'].pct_change().dropna()

            # Rolling 20-day skewness
            rolling_skew = returns.rolling(window=20).skew().dropna()
            if len(rolling_skew) < 20:
                return result

            current_skew = float(rolling_skew.iloc[-1])
            percentile = float((rolling_skew < current_skew).mean() * 100)

            result['current_skew'] = round(current_skew, 4)
            result['percentile'] = round(percentile, 1)

            if percentile >= 80:
                result['signal'] = 'Skew at high percentile — put demand historically elevated'
            elif percentile <= 20:
                result['signal'] = 'Skew at low percentile — complacency or call dominance'
            else:
                result['signal'] = 'Skew within normal range'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Cross-sectional dislocation detection
    # ------------------------------------------------------------------

    def _detect_cross_sectional_dislocations(self, symbol):
        """
        Compare the symbol's IV rank to peers in the same sector
        to detect cross-sectional dislocations.
        """
        result = {
            'symbol_iv': None,
            'peer_ivs': {},
            'iv_rank_in_sector': None,
            'dislocation_detected': False,
            'signal': 'Insufficient data',
        }

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')

            expirations = ticker.options
            if not expirations or not current_price:
                return result

            chain = ticker.option_chain(expirations[0])
            calls = chain.calls
            if len(calls) == 0:
                return result

            atm_idx = (calls['strike'] - current_price).abs().idxmin()
            symbol_iv = float(calls.loc[atm_idx, 'impliedVolatility'])
            result['symbol_iv'] = round(symbol_iv, 4)

            # Get peers from same sector (use yfinance recommendations or hardcoded peers)
            sector = info.get('sector', '')
            peers = self._get_sector_peers(symbol, sector)
            if not peers:
                return result

            peer_ivs = {}
            for peer in peers[:5]:
                try:
                    p_ticker = yf.Ticker(peer)
                    p_info = p_ticker.info
                    p_price = p_info.get('currentPrice') or p_info.get('regularMarketPrice')
                    p_exps = p_ticker.options
                    if p_exps and p_price:
                        p_chain = p_ticker.option_chain(p_exps[0])
                        p_calls = p_chain.calls
                        if len(p_calls) > 0:
                            p_atm = (p_calls['strike'] - p_price).abs().idxmin()
                            peer_ivs[peer] = round(float(p_calls.loc[p_atm, 'impliedVolatility']), 4)
                except Exception:
                    continue

            result['peer_ivs'] = peer_ivs

            if peer_ivs:
                all_ivs = list(peer_ivs.values()) + [symbol_iv]
                all_ivs.sort()
                rank = all_ivs.index(symbol_iv) + 1
                result['iv_rank_in_sector'] = f'{rank}/{len(all_ivs)}'

                avg_peer = np.mean(list(peer_ivs.values()))
                if avg_peer > 0 and abs(symbol_iv - avg_peer) / avg_peer > 0.3:
                    result['dislocation_detected'] = True
                    if symbol_iv > avg_peer:
                        result['signal'] = 'IV elevated vs sector peers — potential overpricing'
                    else:
                        result['signal'] = 'IV depressed vs sector peers — potential underpricing'
                else:
                    result['signal'] = 'IV in line with sector peers'
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Helper: sector peers
    # ------------------------------------------------------------------

    def _get_sector_peers(self, symbol, sector):
        """
        Return a small list of peer symbols for the given sector.
        """
        sector_peers = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMZN', 'CRM', 'ADBE'],
            'Financial Services': ['JPM', 'V', 'MA', 'BAC', 'GS', 'MS'],
            'Healthcare': ['JNJ', 'UNH', 'PFE', 'MRK', 'ABT', 'TMO'],
            'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'NKE', 'SBUX', 'TGT'],
            'Consumer Defensive': ['WMT', 'PG', 'COST', 'PEP', 'KO', 'CL'],
            'Communication Services': ['GOOGL', 'META', 'DIS', 'NFLX', 'CMCSA', 'T'],
            'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
            'Industrials': ['CAT', 'HON', 'UPS', 'BA', 'GE', 'RTX'],
        }

        peers = sector_peers.get(sector, [])
        # Exclude the symbol itself
        return [p for p in peers if p != symbol]
