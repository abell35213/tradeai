"""
Position Sizer Module

Determines optimal position size driven by:
- Signal confidence (1-5 scale)
- Liquidity score
- Historical setup performance
- Implied edge vs historical edge

Core formula:
    size = base_risk * (confidence_score / 5) * (historical_edge / max_edge)

Designed for risk-adjusted capital allocation in earnings volatility strategies.
"""

import logging
import numpy as np
import yfinance as yf
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculates risk-adjusted position sizes for earnings volatility strategies."""

    # Default configuration
    DEFAULT_BASE_RISK = 10000  # base risk in dollars
    MAX_CONFIDENCE = 5
    MAX_EDGE = 1.0  # maximum historical edge for normalization
    MIN_LIQUIDITY_SCORE = 0.1  # floor to avoid zero sizing

    def __init__(self, base_risk=None, max_edge=None):
        self.base_risk = base_risk or self.DEFAULT_BASE_RISK
        self.max_edge = max_edge or self.MAX_EDGE

    def calculate_size(self, confidence_score, liquidity_score,
                       historical_edge, implied_edge=None,
                       base_risk=None):
        """
        Calculate position size based on multi-factor model.

        Parameters:
            confidence_score (float): Signal confidence, 1-5 scale.
            liquidity_score (float): 0-1 score reflecting market liquidity.
            historical_edge (float): Historical performance edge (e.g., Sharpe).
            implied_edge (float|None): Implied edge from current IV analysis.
            base_risk (float|None): Override default base risk.

        Returns:
            dict with recommended size and component breakdown.
        """
        base = base_risk if base_risk is not None else self.base_risk

        # Clamp inputs
        confidence = max(1.0, min(float(confidence_score), self.MAX_CONFIDENCE))
        liquidity = max(self.MIN_LIQUIDITY_SCORE, min(float(liquidity_score), 1.0))
        hist_edge = max(0.0, min(float(historical_edge), self.max_edge))

        # Core sizing formula
        confidence_factor = confidence / self.MAX_CONFIDENCE
        edge_factor = hist_edge / self.max_edge if self.max_edge > 0 else 0

        raw_size = base * confidence_factor * edge_factor

        # Liquidity adjustment
        liquidity_adjusted_size = raw_size * liquidity

        # Implied-edge overlay (optional): boost if implied edge > historical.
        # The ±30% cap prevents extreme sizing swings from a single IV
        # snapshot while still rewarding high-conviction dislocations.
        edge_adjustment = 1.0
        if implied_edge is not None and hist_edge > 0:
            implied = max(0.0, float(implied_edge))
            edge_ratio = implied / hist_edge if hist_edge > 0 else 1.0
            edge_adjustment = max(0.7, min(1.3, edge_ratio))

        final_size = round(liquidity_adjusted_size * edge_adjustment, 2)

        return {
            'recommended_size': final_size,
            'base_risk': base,
            'confidence_score': confidence,
            'confidence_factor': round(confidence_factor, 4),
            'liquidity_score': round(liquidity, 4),
            'historical_edge': round(hist_edge, 4),
            'edge_factor': round(edge_factor, 4),
            'implied_edge': float(implied_edge) if implied_edge is not None else None,
            'edge_adjustment': round(edge_adjustment, 4),
            'raw_size': round(raw_size, 2),
            'liquidity_adjusted_size': round(liquidity_adjusted_size, 2),
            'timestamp': datetime.now().isoformat(),
        }

    def calculate_liquidity_score(self, symbol):
        """
        Calculate a 0-1 liquidity score for a symbol based on
        average volume, bid-ask spread proxy, and options open interest.

        Parameters:
            symbol (str): Ticker symbol.

        Returns:
            dict with liquidity score and components.
        """
        score_components = []

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='1mo')

            # Volume score (relative to 1M shares/day benchmark)
            if len(hist) > 0:
                avg_vol = float(hist['Volume'].mean())
                vol_score = min(avg_vol / 1_000_000, 1.0)
                score_components.append(vol_score)
        except Exception:
            logger.exception("Failed to compute volume score for %s", symbol)
            score_components.append(0.5)

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if expirations:
                chain = ticker.option_chain(expirations[0])
                total_oi = int(chain.calls['openInterest'].sum() +
                               chain.puts['openInterest'].sum())
                # OI score (relative to 100K benchmark)
                oi_score = min(total_oi / 100_000, 1.0)
                score_components.append(oi_score)
        except Exception:
            logger.exception("Failed to compute OI score for %s", symbol)
            score_components.append(0.5)

        liquidity_score = float(np.mean(score_components)) if score_components else 0.5

        return {
            'symbol': symbol,
            'liquidity_score': round(liquidity_score, 4),
            'components': score_components,
        }

    def size_from_symbol(self, symbol, confidence_score, historical_edge,
                         implied_edge=None, base_risk=None):
        """
        Convenience method: compute liquidity for a symbol and calculate size.

        Parameters:
            symbol (str): Ticker symbol.
            confidence_score (float): 1-5.
            historical_edge (float): Historical edge metric.
            implied_edge (float|None): Optional implied edge.
            base_risk (float|None): Override base risk.

        Returns:
            dict with sizing result and liquidity detail.
        """
        liq = self.calculate_liquidity_score(symbol)
        sizing = self.calculate_size(
            confidence_score=confidence_score,
            liquidity_score=liq['liquidity_score'],
            historical_edge=historical_edge,
            implied_edge=implied_edge,
            base_risk=base_risk,
        )
        sizing['liquidity_detail'] = liq
        return sizing
