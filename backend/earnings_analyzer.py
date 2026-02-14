"""
Earnings Calendar & Pre-Earnings Sentiment Snapshot Analyzer

Provides:
- Earnings calendar data (companies reporting on each day)
- Pre-earnings sentiment snapshot with four scored dimensions:
  1. Expectation Density
  2. Options Market Expectations
  3. Positioning & Flow
  4. Narrative Alignment
"""

from datetime import datetime, timedelta
import yfinance as yf
import math


class EarningsAnalyzer:
    """Analyzes pre-earnings sentiment across four key dimensions."""

    def get_earnings_calendar(self, year, month):
        """
        Get earnings calendar for a given month.
        Returns a dict mapping date strings to lists of company earnings entries.
        """
        symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
            'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS',
            'NFLX', 'ADBE', 'CRM', 'INTC', 'AMD', 'PYPL', 'COST',
            'PEP', 'AVGO', 'CSCO', 'CMCSA', 'NKE', 'MRK', 'ABT', 'TMO'
        ]

        calendar = {}
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                earnings_ts = info.get('earningsTimestamp')
                if earnings_ts:
                    earnings_date = datetime.fromtimestamp(earnings_ts)
                    if start_date <= earnings_date < end_date:
                        date_str = earnings_date.strftime('%Y-%m-%d')
                        if date_str not in calendar:
                            calendar[date_str] = []
                        calendar[date_str].append({
                            'symbol': sym,
                            'name': info.get('shortName', sym),
                            'time': 'BMO' if earnings_date.hour < 12 else 'AMC',
                            'market_cap': info.get('marketCap'),
                        })
            except Exception:
                continue

        return calendar

    def get_earnings_snapshot(self, symbol):
        """
        Generate the Pre-Earnings Sentiment Snapshot for a symbol.
        Scores four dimensions: Expectation Density, Options Market Expectations,
        Positioning & Flow, and Narrative Alignment.
        Then classifies the earnings setup into one of five buckets (A–E).
        """
        ticker = yf.Ticker(symbol)
        info = ticker.info

        expectation = self._analyze_expectation_density(ticker, info)
        options_mkt = self._analyze_options_expectations(ticker, info)
        positioning = self._analyze_positioning_flow(ticker, info)
        narrative = self._analyze_narrative_alignment(ticker, info)
        setup = self.classify_earnings_setup(
            expectation, options_mkt, positioning, narrative
        )

        return {
            'symbol': symbol,
            'name': info.get('shortName', symbol),
            'earnings_date': self._get_earnings_date_str(info),
            'expectation_density': expectation,
            'options_expectations': options_mkt,
            'positioning_flow': positioning,
            'narrative_alignment': narrative,
            'earnings_setup': setup,
            'timestamp': datetime.now().isoformat(),
        }

    def _get_earnings_date_str(self, info):
        """Extract earnings date string from ticker info."""
        ts = info.get('earningsTimestamp')
        if ts:
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        return None

    def _analyze_expectation_density(self, ticker, info):
        """
        Dimension 1 – Expectation Density.
        Evaluates consensus tightness, guidance drift, and whisper divergence.
        """
        target_mean = info.get('targetMeanPrice')
        target_low = info.get('targetLowPrice')
        target_high = info.get('targetHighPrice')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        num_analysts = info.get('numberOfAnalystOpinions', 0)

        spread = None
        spread_pct = None
        if target_high and target_low and current_price and current_price > 0:
            spread = target_high - target_low
            spread_pct = spread / current_price

        consensus_tight = False
        if spread_pct is not None:
            consensus_tight = spread_pct < 0.20

        guidance_drift = None
        if target_mean and current_price and current_price > 0:
            guidance_drift = (target_mean - current_price) / current_price

        signal = 'Tight consensus = fragile' if consensus_tight else 'Wide dispersion = harder to shock'

        return {
            'analyst_count': num_analysts,
            'target_mean': target_mean,
            'target_low': target_low,
            'target_high': target_high,
            'spread': spread,
            'spread_pct': round(spread_pct, 4) if spread_pct is not None else None,
            'consensus_tight': consensus_tight,
            'guidance_drift': round(guidance_drift, 4) if guidance_drift is not None else None,
            'signal': signal,
        }

    def _analyze_options_expectations(self, ticker, info):
        """
        Dimension 2 – Options Market Expectations.
        Compares ATM implied move vs historical realized moves and skew shape.
        """
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        result = {
            'atm_iv': None,
            'historical_volatility': None,
            'iv_vs_historical': None,
            'front_iv': None,
            'back_iv': None,
            'iv_term_spread': None,
            'signal': 'Insufficient options data',
        }

        try:
            history = ticker.history(period='6mo')
            if len(history) > 20:
                returns = history['Close'].pct_change().dropna()
                hist_vol = float(returns.std() * math.sqrt(252))
                result['historical_volatility'] = round(hist_vol, 4)
        except Exception:
            pass

        try:
            expirations = ticker.options
            if expirations and len(expirations) >= 1:
                front_chain = ticker.option_chain(expirations[0])
                if current_price and len(front_chain.calls) > 0:
                    calls = front_chain.calls
                    atm_idx = (calls['strike'] - current_price).abs().idxmin()
                    atm_iv = float(calls.loc[atm_idx, 'impliedVolatility'])
                    result['atm_iv'] = round(atm_iv, 4)
                    result['front_iv'] = round(atm_iv, 4)

                if len(expirations) >= 2:
                    back_chain = ticker.option_chain(expirations[1])
                    if current_price and len(back_chain.calls) > 0:
                        back_calls = back_chain.calls
                        back_idx = (back_calls['strike'] - current_price).abs().idxmin()
                        back_iv = float(back_calls.loc[back_idx, 'impliedVolatility'])
                        result['back_iv'] = round(back_iv, 4)

                if result['front_iv'] and result['back_iv']:
                    result['iv_term_spread'] = round(result['front_iv'] - result['back_iv'], 4)
        except Exception:
            pass

        if result['atm_iv'] and result['historical_volatility']:
            ratio = result['atm_iv'] / result['historical_volatility'] if result['historical_volatility'] > 0 else None
            result['iv_vs_historical'] = round(ratio, 4) if ratio else None
            if ratio and ratio > 1.2:
                result['signal'] = 'IV > historical realized → fear priced in'
            elif ratio and ratio < 0.8:
                result['signal'] = 'IV < historical → complacency'
            else:
                result['signal'] = 'IV roughly in line with historical'

        return result

    def _analyze_positioning_flow(self, ticker, info):
        """
        Dimension 3 – Positioning & Flow.
        Tracks call vs put OI, directional flow, and stock drift into earnings.
        """
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        result = {
            'call_oi': 0,
            'put_oi': 0,
            'put_call_oi_ratio': None,
            'price_drift_pct': None,
            'drift_direction': None,
            'signal': 'Insufficient data',
        }

        try:
            expirations = ticker.options
            if expirations:
                chain = ticker.option_chain(expirations[0])
                result['call_oi'] = int(chain.calls['openInterest'].sum())
                result['put_oi'] = int(chain.puts['openInterest'].sum())
                if result['call_oi'] > 0:
                    result['put_call_oi_ratio'] = round(result['put_oi'] / result['call_oi'], 4)
        except Exception:
            pass

        try:
            history = ticker.history(period='1mo')
            if len(history) >= 10:
                recent = history['Close'].iloc[-1]
                past = history['Close'].iloc[-10]
                drift = (recent - past) / past
                result['price_drift_pct'] = round(float(drift), 4)
                if drift > 0.02:
                    result['drift_direction'] = 'upward'
                elif drift < -0.02:
                    result['drift_direction'] = 'downward'
                else:
                    result['drift_direction'] = 'flat'
        except Exception:
            pass

        pc = result['put_call_oi_ratio']
        drift_dir = result['drift_direction']

        if drift_dir == 'upward' and pc is not None and pc < 0.7:
            result['signal'] = 'Drift + call buying = crowded'
        elif drift_dir == 'flat' and pc is not None and pc > 1.0:
            result['signal'] = 'Flat price + rising IV = hedging'
        elif drift_dir == 'downward' and pc is not None and pc > 1.2:
            result['signal'] = 'Downward drift + put heavy = bearish positioning'
        elif pc is not None:
            result['signal'] = 'Mixed positioning signals'

        return result

    def _analyze_narrative_alignment(self, ticker, info):
        """
        Dimension 4 – Narrative Alignment.
        Checks if the company is aligned with dominant macro themes.
        """
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        name = info.get('shortName', '')
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        themes = []
        theme_keywords = {
            'AI': ['artificial intelligence', 'semiconductor', 'chip', 'gpu',
                   'data center', 'cloud', 'software'],
            'Energy Transition': ['solar', 'wind', 'battery', 'electric',
                                  'renewable', 'energy', 'utility'],
            'Rate Sensitivity': ['bank', 'financial', 'insurance', 'reit',
                                 'real estate', 'mortgage'],
            'Geopolitics': ['defense', 'aerospace', 'cyber', 'security'],
        }

        combined = f'{sector} {industry} {name}'.lower()
        for theme, keywords in theme_keywords.items():
            if any(kw in combined for kw in keywords):
                themes.append(theme)

        target_mean = info.get('targetMeanPrice')
        price_ahead = False
        narrative_ahead = False

        if target_mean and current_price:
            upside = (target_mean - current_price) / current_price if current_price > 0 else 0
            if upside < 0.05 and len(themes) > 0:
                price_ahead = True
            elif upside > 0.15 and len(themes) > 0:
                narrative_ahead = True

        if price_ahead:
            signal = 'Price ahead of narrative = early positioning'
        elif narrative_ahead:
            signal = 'Narrative ahead of price = late sentiment'
        elif len(themes) > 0:
            signal = f'Aligned with theme(s): {", ".join(themes)}'
        else:
            signal = 'No dominant macro theme alignment detected'

        return {
            'sector': sector,
            'industry': industry,
            'themes': themes,
            'price_ahead_of_narrative': price_ahead,
            'narrative_ahead_of_price': narrative_ahead,
            'signal': signal,
        }

    # ------------------------------------------------------------------
    # Phase 2 – Classify the Earnings Setup (A–E)
    # ------------------------------------------------------------------

    SETUP_DEFINITIONS = {
        'A': {
            'label': 'Overpriced Fear',
            'interpretation': 'Market is overpaying for disaster.',
            'preferred_structures': [
                'Short straddles (selectively)',
                'Iron condors',
                'Put spreads financed by call overwrites',
                'Calendars (front-week short)',
            ],
            'best_in': [
                'S&P 500 names',
                'Defensive sectors',
                'Energy majors',
            ],
        },
        'B': {
            'label': 'Complacent Optimism',
            'interpretation': 'Market assumes "nothing can go wrong."',
            'preferred_structures': [
                'Long puts or put spreads',
                'Long straddles if IV historically cheap',
                'Ratio spreads (defined risk)',
            ],
            'best_in': [
                'Mega-cap growth',
                'Momentum mid-caps',
            ],
        },
        'C': {
            'label': 'Crowded Bull',
            'interpretation': 'Even a "beat" may disappoint.',
            'preferred_structures': [
                'Call spreads (cap upside)',
                'Call flies',
                'Long puts financed with call sales',
            ],
            'best_in': [],
        },
        'D': {
            'label': 'Confused / Two-Sided',
            'interpretation': 'Market expects movement but not direction.',
            'preferred_structures': [
                'Long straddles',
                'Long strangles',
                'Backspreads',
            ],
            'best_in': [
                'Mid-caps',
                'Volatile cyclicals',
                'Energy E&Ps',
            ],
        },
        'E': {
            'label': 'Neglected / Asymmetric',
            'interpretation': 'Optionality underpriced.',
            'preferred_structures': [
                'Long calls or puts',
                'Cheap strangles',
                'Defined-risk directional bets',
            ],
            'best_in': [],
        },
    }

    def classify_earnings_setup(self, expectation, options_mkt, positioning, narrative):
        """
        Score each of the five setups (A–E) against the snapshot dimensions
        and return the best-matching setup with its metadata and matched traits.
        """
        scores = {}
        traits = {}

        iv_ratio = options_mkt.get('iv_vs_historical')
        pc_ratio = positioning.get('put_call_oi_ratio')
        drift_dir = positioning.get('drift_direction')
        drift_pct = positioning.get('price_drift_pct')
        consensus_tight = expectation.get('consensus_tight')
        spread_pct = expectation.get('spread_pct')
        analyst_count = expectation.get('analyst_count') or 0
        call_oi = positioning.get('call_oi') or 0
        put_oi = positioning.get('put_oi') or 0
        total_oi = call_oi + put_oi
        atm_iv = options_mkt.get('atm_iv')
        themes = narrative.get('themes') or []

        # --- Setup A: Overpriced Fear ---
        a_score = 0
        a_traits = []
        if iv_ratio is not None and iv_ratio > 1.2:
            a_score += 3
            a_traits.append('IV very high vs history')
        if pc_ratio is not None and pc_ratio > 1.0:
            a_score += 2
            a_traits.append('Heavy downside skew')
        if drift_dir in ('flat', 'downward'):
            a_score += 1
            a_traits.append('Flat or mildly weak price action')
        scores['A'] = a_score
        traits['A'] = a_traits

        # --- Setup B: Complacent Optimism ---
        b_score = 0
        b_traits = []
        if iv_ratio is not None and iv_ratio < 0.9:
            b_score += 3
            b_traits.append('IV cheap vs history')
        if drift_dir == 'upward':
            b_score += 2
            b_traits.append('Strong drift higher')
        if len(themes) > 0 and narrative.get('narrative_ahead_of_price'):
            b_score += 1
            b_traits.append('Positive narrative saturation')
        scores['B'] = b_score
        traits['B'] = b_traits

        # --- Setup C: Crowded Bull ---
        c_score = 0
        c_traits = []
        if pc_ratio is not None and pc_ratio < 0.7:
            c_score += 3
            c_traits.append('Heavy call OI')
        if drift_dir == 'upward' and drift_pct is not None and drift_pct > 0.03:
            c_score += 2
            c_traits.append('Stock up materially pre-earnings')
        if consensus_tight:
            c_score += 1
            c_traits.append('Analysts unanimously positive')
        scores['C'] = c_score
        traits['C'] = c_traits

        # --- Setup D: Confused / Two-Sided ---
        d_score = 0
        d_traits = []
        if iv_ratio is not None and iv_ratio > 1.0:
            d_score += 1
            d_traits.append('Elevated IV')
        if pc_ratio is not None and 0.7 <= pc_ratio <= 1.3:
            d_score += 2
            d_traits.append('Both call & put buying')
        if not consensus_tight and spread_pct is not None and spread_pct > 0.30:
            d_score += 2
            d_traits.append('Wide estimate dispersion')
        if drift_dir == 'flat':
            d_score += 2
            d_traits.append('No clear drift')
        scores['D'] = d_score
        traits['D'] = d_traits

        # --- Setup E: Neglected / Asymmetric ---
        e_score = 0
        e_traits = []
        if atm_iv is not None and atm_iv < 0.25:
            e_score += 2
            e_traits.append('Low IV')
        if total_oi < 50000:
            e_score += 2
            e_traits.append('Thin options market')
        if analyst_count < 10:
            e_score += 2
            e_traits.append('Little media coverage')
        if len(themes) == 0:
            e_score += 1
            e_traits.append('No dominant macro theme')
        scores['E'] = e_score
        traits['E'] = e_traits

        # Pick highest-scoring setup; ties broken by alphabetical order (A first)
        best = max(scores, key=lambda k: (scores[k], -ord(k)))
        defn = self.SETUP_DEFINITIONS[best]

        return {
            'setup': best,
            'label': defn['label'],
            'interpretation': defn['interpretation'],
            'preferred_structures': defn['preferred_structures'],
            'best_in': defn['best_in'],
            'matched_traits': traits[best],
            'scores': scores,
        }
