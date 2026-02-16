"""
Index Vol Engine Module

Edge-based signal generation for index volatility selling.
Replaces sentiment-weighted opportunity scoring with direct consumption
of vol surface, regime, and position sizing outputs.

Signal components:
- Implied vs realized spread
- Term structure shape
- Skew dislocations
- Dealer gamma state
- Event proximity

Produces a composite edge score and trade recommendation for defined-risk
credit spread strategies.
"""

import logging
import math
import uuid
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)

from vol_surface_analyzer import VolSurfaceAnalyzer
from regime_classifier import RegimeClassifier
from position_sizer import PositionSizer
from risk_engine import RiskEngine
from trade_ticket import (
    TradeTicket, TicketLeg, EdgeMetrics, RegimeGate,
    RiskGate, PortfolioAfter, Exits,
)


class IndexVolEngine:
    """Produces edge-based vol-selling signals by consuming vol surface,
    regime, and position sizer outputs directly."""

    # Edge component weights (must sum to 1.0)
    WEIGHT_IV_RV_SPREAD = 0.30
    WEIGHT_TERM_STRUCTURE = 0.20
    WEIGHT_SKEW = 0.20
    WEIGHT_GAMMA = 0.15
    WEIGHT_EVENT_PROXIMITY = 0.15

    # Thresholds
    IV_RV_RICH_THRESHOLD = 1.15      # IV/RV ratio above which vol is "rich"
    IV_RV_CHEAP_THRESHOLD = 0.90     # IV/RV ratio below which vol is "cheap"
    SKEW_ELEVATED_THRESHOLD = 0.08   # put-call skew spread considered elevated
    EDGE_PASS_THRESHOLD = 0.40       # minimum composite edge to pass

    def __init__(self, vol_surface_analyzer=None, regime_classifier=None,
                 position_sizer=None, risk_engine=None):
        self.vol_surface = vol_surface_analyzer or VolSurfaceAnalyzer()
        self.regime = regime_classifier or RegimeClassifier()
        self.sizer = position_sizer or PositionSizer()
        self.risk_engine = risk_engine or RiskEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, symbol):
        """
        Run the full edge-based analysis for *symbol*.

        Returns a dict with:
        - edge_score (0-1 composite)
        - component scores
        - regime snapshot
        - pass / fail gate with reasons
        - sizing recommendation
        """
        vol_data = self.vol_surface.analyze(symbol)
        regime_data = self.regime.classify()
        trade_gate = self.regime.should_trade(regime_data)

        components = self._score_components(vol_data, regime_data)
        edge_score = self._composite_edge(components)

        # Determine pass/fail
        pass_fail = self._evaluate_gate(edge_score, trade_gate, components)

        # Position sizing recommendation (only if passed)
        sizing = None
        if pass_fail['passed']:
            sizing = self.sizer.calculate_size(
                confidence_score=self._edge_to_confidence(edge_score),
                liquidity_score=0.7,   # default; caller can override
                historical_edge=edge_score,
            )

        return {
            'symbol': symbol,
            'edge_score': round(edge_score, 4),
            'components': components,
            'regime_snapshot': regime_data,
            'trade_gate': pass_fail,
            'sizing': sizing,
            'timestamp': datetime.now().isoformat(),
        }

    def generate_trade_ticket(self, symbol, existing_positions=None):
        """
        Generate a full trade ticket for an index vol credit spread.

        Returns a ``TradeTicket`` instance suitable for the
        ``/api/trade-ticket/index-vol`` endpoint, including strikes,
        credit, max loss, POP estimate, regime snapshot, risk before/after,
        and an idempotency token.
        """
        analysis = self.analyze(symbol)
        existing_positions = existing_positions or []

        # Risk before
        risk_before = self.risk_engine.calculate_portfolio_risk(existing_positions)

        # Build spread parameters from vol surface data
        spread = self._build_spread_params(symbol, analysis)

        # Compute risk after by adding the proposed trade
        proposed_position = {
            'symbol': symbol,
            'delta': spread['estimated_delta'],
            'vega': spread['estimated_vega'],
            'gamma': spread['estimated_gamma'],
            'notional': abs(spread['max_loss']),
            'earnings_date': None,
            'expiry_bucket': '7-30d',
        }
        risk_after = self.risk_engine.calculate_portfolio_risk(
            list(existing_positions) + [proposed_position]
        )

        # Build structured legs
        strikes = spread['strikes']
        legs = []
        if strikes.get('short'):
            legs.append(TicketLeg(
                type='put', side='sell',
                strike=strikes['short'], qty=1,
            ))
        if strikes.get('long'):
            legs.append(TicketLeg(
                type='put', side='buy',
                strike=strikes['long'], qty=1,
            ))

        # Map analysis components to edge_metrics
        components = analysis.get('components', {})
        edge_metrics = EdgeMetrics(
            iv_pct=components.get('iv_rv_spread'),
            skew_metric=components.get('skew_dislocation'),
            term_structure=components.get('term_structure'),
        )

        # Regime gate from analysis trade_gate
        trade_gate = analysis.get('trade_gate', {})
        regime_gate = RegimeGate(
            passed=trade_gate.get('passed', True),
            reasons=trade_gate.get('reasons', []),
        )

        # Risk gate from computed risk_after
        risk_gate = RiskGate(
            passed=True,
            reasons=[],
            portfolio_after=PortfolioAfter(
                delta=risk_after.get('portfolio_delta', 0.0),
                vega=risk_after.get('portfolio_vega', 0.0),
                gamma=risk_after.get('portfolio_gamma', 0.0),
                max_loss_week=spread['max_loss'],
            ),
        )

        confidence_score = analysis.get('edge_score', 0.0)

        ticket = TradeTicket(
            ticket_id=str(uuid.uuid4()),
            underlying=symbol,
            strategy=spread['strategy'],
            expiry=spread['expiry'],
            legs=legs,
            width=spread['wing_width'],
            mid_credit=spread['credit'],
            limit_credit=spread['credit'],
            max_loss=spread['max_loss'],
            pop_estimate=spread['pop_estimate'],
            edge_metrics=edge_metrics,
            regime_gate=regime_gate,
            risk_gate=risk_gate,
            confidence_score=confidence_score,
            exits=Exits(),
            status='pending',
        )
        return ticket

    # ------------------------------------------------------------------
    # Component scoring
    # ------------------------------------------------------------------

    def _score_components(self, vol_data, regime_data):
        """Score each edge component on a 0-1 scale."""
        iv_rv = self._score_iv_rv_spread(vol_data)
        term = self._score_term_structure(vol_data)
        skew = self._score_skew(vol_data)
        gamma = self._score_gamma(regime_data)
        event = self._score_event_proximity(regime_data)

        return {
            'iv_rv_spread': iv_rv,
            'term_structure': term,
            'skew_dislocation': skew,
            'dealer_gamma': gamma,
            'event_proximity': event,
        }

    def _composite_edge(self, components):
        """Weighted sum of component scores."""
        return (
            components['iv_rv_spread'] * self.WEIGHT_IV_RV_SPREAD
            + components['term_structure'] * self.WEIGHT_TERM_STRUCTURE
            + components['skew_dislocation'] * self.WEIGHT_SKEW
            + components['dealer_gamma'] * self.WEIGHT_GAMMA
            + components['event_proximity'] * self.WEIGHT_EVENT_PROXIMITY
        )

    # ------------------------------------------------------------------
    # Individual scorers
    # ------------------------------------------------------------------

    def _score_iv_rv_spread(self, vol_data):
        """
        Score implied-vs-realized spread.
        Higher score when IV > RV (vol is rich → good for selling).
        """
        fwd = vol_data.get('forward_vol', {})
        spot_vol = fwd.get('spot_vol')
        fwd_vol = fwd.get('forward_vol')
        ratio = fwd.get('ratio')

        # Also use sector comparison as IV/RV proxy
        sector = vol_data.get('sector_iv_comparison', {})
        iv_premium = sector.get('iv_premium')

        score = 0.5  # neutral default

        if ratio is not None:
            if ratio > self.IV_RV_RICH_THRESHOLD:
                # Forward vol elevated → market pricing future event, IV rich
                score = min(1.0, 0.5 + (ratio - 1.0) * 1.5)
            elif ratio < self.IV_RV_CHEAP_THRESHOLD:
                score = max(0.0, 0.5 - (1.0 - ratio) * 1.5)

        if iv_premium is not None:
            # Blend in sector premium signal
            if iv_premium > 1.2:
                score = min(1.0, score + 0.15)
            elif iv_premium < 0.85:
                score = max(0.0, score - 0.15)

        return round(score, 4)

    def _score_term_structure(self, vol_data):
        """
        Score term structure shape for vol selling edge.
        Contango = normal, good for selling (higher score).
        Backwardation = fear, less favorable.
        Distortion = potential mispricing opportunity.
        """
        ts = vol_data.get('term_structure', {})
        shape = ts.get('shape', 'unknown')
        distortion = ts.get('distortion_detected', False)

        if shape == 'contango':
            score = 0.75
        elif shape == 'backwardation':
            score = 0.25
        elif shape == 'flat':
            score = 0.50
        else:
            score = 0.50

        # Distortion bonus: potential mispricing we can exploit
        if distortion:
            score = min(1.0, score + 0.20)

        return round(score, 4)

    def _score_skew(self, vol_data):
        """
        Score skew dislocation.
        Heavy put skew → elevated fear → vol selling opportunity.
        Inverted skew → unusual call demand → less edge for selling.
        """
        skew = vol_data.get('skew', {})
        spread = skew.get('skew_spread')

        skew_pctl = vol_data.get('skew_percentile', {})
        percentile = skew_pctl.get('percentile')

        score = 0.5

        if spread is not None:
            if spread > self.SKEW_ELEVATED_THRESHOLD:
                # Heavy put skew → people are overpaying for puts → sell vol
                score = min(1.0, 0.5 + spread * 3.0)
            elif spread < -0.03:
                # Inverted → unusual
                score = max(0.0, 0.5 + spread * 3.0)

        if percentile is not None:
            # High percentile means put demand historically elevated
            if percentile >= 75:
                score = min(1.0, score + 0.10)
            elif percentile <= 25:
                score = max(0.0, score - 0.10)

        return round(score, 4)

    def _score_gamma(self, regime_data):
        """
        Score dealer gamma state.
        Positive gamma → dealers dampen moves → favorable for selling.
        Negative gamma → dealers amplify moves → risky for selling.
        """
        gamma_info = regime_data.get('details', {}).get('gamma_exposure', {})
        direction = gamma_info.get('gamma_direction', 'neutral')

        if direction == 'positive':
            return 0.80
        elif direction == 'negative':
            return 0.20
        return 0.50

    def _score_event_proximity(self, regime_data):
        """
        Score event proximity.
        No elevated events → favorable for selling.
        Elevated events → risky.
        """
        macro = regime_data.get('details', {}).get('macro_proximity', {})
        elevated = macro.get('elevated', False)

        if elevated:
            return 0.15
        return 0.75

    # ------------------------------------------------------------------
    # Gate evaluation
    # ------------------------------------------------------------------

    def _evaluate_gate(self, edge_score, trade_gate, components):
        """Determine pass/fail with reasons."""
        reasons = list(trade_gate.get('reasons', []))
        passed = trade_gate.get('pass_trade', True)

        if edge_score < self.EDGE_PASS_THRESHOLD:
            passed = False
            reasons.append(
                f'Edge score {edge_score:.2f} below threshold {self.EDGE_PASS_THRESHOLD}'
            )

        # Component-level hard blocks
        if components['event_proximity'] < 0.20:
            if 'Macro-event proximity is elevated' not in reasons:
                reasons.append('Event proximity too close')
            passed = False

        if components['dealer_gamma'] < 0.25:
            reasons.append('Dealer gamma is negative — amplified move risk')
            passed = False

        return {
            'passed': passed,
            'reasons': reasons,
            'edge_score': round(edge_score, 4),
        }

    # ------------------------------------------------------------------
    # Spread construction helpers
    # ------------------------------------------------------------------

    def _build_spread_params(self, symbol, analysis):
        """
        Construct defined-risk credit spread parameters from the analysis.

        Uses vol surface data to pick strikes and estimate credit/max-loss.
        When live data is unavailable, uses reasonable approximations.
        """
        # Default spread parameters (will be overridden by live data)
        strategy = 'defined-risk credit spread'
        expiry = None
        short_strike = None
        long_strike = None
        wing_width = 5.0
        credit = 0.0
        max_loss = 0.0

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            expirations = ticker.options

            if current_price and expirations and len(expirations) >= 2:
                # Pick 2nd expiration (typically ~30 DTE)
                expiry = expirations[min(1, len(expirations) - 1)]
                chain = ticker.option_chain(expiry)
                puts = chain.puts

                if len(puts) > 0:
                    # Put credit spread: sell put at ~0.30 delta proxy (5% OTM)
                    short_strike_target = current_price * 0.95
                    long_strike_target = short_strike_target - wing_width

                    short_idx = (puts['strike'] - short_strike_target).abs().idxmin()
                    short_strike = float(puts.loc[short_idx, 'strike'])

                    # Find long strike
                    long_candidates = puts[puts['strike'] < short_strike]
                    if len(long_candidates) > 0:
                        long_idx = (long_candidates['strike'] - long_strike_target).abs().idxmin()
                        long_strike = float(long_candidates.loc[long_idx, 'strike'])
                    else:
                        long_strike = short_strike - wing_width

                    wing_width = round(short_strike - long_strike, 2)

                    # Estimate credit from bid prices
                    short_bid = float(puts.loc[short_idx, 'bid']) if puts.loc[short_idx, 'bid'] > 0 else 0
                    long_ask = 0.0
                    if len(long_candidates) > 0:
                        long_ask = float(long_candidates.loc[long_idx, 'ask']) if long_candidates.loc[long_idx, 'ask'] > 0 else 0

                    credit = round(max(short_bid - long_ask, 0.0), 2)
                    max_loss = round((wing_width - credit) * 100, 2)
        except Exception:
            logger.exception("Failed to build spread params for %s", symbol)

        # Fallback if no live data
        if short_strike is None:
            short_strike = 0.0
            long_strike = 0.0
            wing_width = 5.0
            credit = 0.0
            max_loss = 500.0

        # POP estimate: approximate using credit / wing_width
        if wing_width > 0 and credit > 0:
            pop_estimate = round((1.0 - credit / wing_width) * 100, 1)
            pop_estimate = max(0.0, min(100.0, pop_estimate))
        else:
            pop_estimate = None

        return {
            'strategy': strategy,
            'expiry': expiry,
            'strikes': {
                'short': short_strike,
                'long': long_strike,
            },
            'wing_width': wing_width,
            'credit': credit,
            'max_loss': max_loss,
            'pop_estimate': pop_estimate,
            'estimated_delta': -0.30,
            'estimated_vega': -0.10,
            'estimated_gamma': -0.01,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _edge_to_confidence(edge_score):
        """Map a 0-1 edge score to the 1-5 confidence scale used by PositionSizer."""
        return max(1.0, min(5.0, 1.0 + edge_score * 4.0))
