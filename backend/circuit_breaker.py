"""
Circuit Breaker Module

Hard kill-switches for the Automated Earnings Volatility Income Engine.

Kill-switch categories
----------------------
1. **Weekly P&L drawdown** – stop trading for the week if realized P&L
   drawdown exceeds a configurable threshold.
2. **VIX regime** – stop trading if VIX percentile breaches a threshold
   or VIX spikes day-over-day beyond a limit.
3. **Macro calendar** – stop trading within a configurable window of
   known macro events (CPI / FOMC / NFP) sourced from a
   ``MarketDataProvider.get_calendar_events()`` feed.
"""

from datetime import datetime, timedelta


class CircuitBreaker:
    """Evaluate kill-switch conditions and decide whether trading is allowed."""

    # ---- configurable thresholds ----
    DEFAULT_WEEKLY_DRAWDOWN_PCT = 5.0       # stop if weekly P&L drops > X %
    DEFAULT_VIX_PERCENTILE_LIMIT = 80.0     # stop if VIX pctl ≥ this
    DEFAULT_VIX_SPIKE_PCT = 20.0            # stop if VIX jumps > X % day-over-day
    DEFAULT_MACRO_BLACKOUT_DAYS = 1         # days before/after macro event

    def __init__(
        self,
        weekly_drawdown_pct=None,
        vix_percentile_limit=None,
        vix_spike_pct=None,
        macro_blackout_days=None,
    ):
        self.weekly_drawdown_pct = (
            weekly_drawdown_pct
            if weekly_drawdown_pct is not None
            else self.DEFAULT_WEEKLY_DRAWDOWN_PCT
        )
        self.vix_percentile_limit = (
            vix_percentile_limit
            if vix_percentile_limit is not None
            else self.DEFAULT_VIX_PERCENTILE_LIMIT
        )
        self.vix_spike_pct = (
            vix_spike_pct
            if vix_spike_pct is not None
            else self.DEFAULT_VIX_SPIKE_PCT
        )
        self.macro_blackout_days = (
            macro_blackout_days
            if macro_blackout_days is not None
            else self.DEFAULT_MACRO_BLACKOUT_DAYS
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_all(self, weekly_pnl_pct, vix_percentile, vix_day_change_pct,
                  calendar_events, regime_label=None, macro_proximity_elevated=None):
        """
        Run every kill-switch and return a combined verdict.

        Parameters
        ----------
        weekly_pnl_pct : float
            Realized P&L change this week as a percentage (negative = loss).
        vix_percentile : float
            Current VIX percentile rank (0-100).
        vix_day_change_pct : float
            Day-over-day VIX change as a percentage.
        calendar_events : list[dict]
            Output of ``MarketDataProvider.get_calendar_events()``.
        regime_label : str or None
            Current vol-regime label from ``RegimeClassifier``
            (e.g. 'compressed', 'expanding', 'stressed').
        macro_proximity_elevated : bool or None
            Whether the regime classifier flagged macro proximity as elevated.

        Returns
        -------
        dict with keys:
            - trading_allowed (bool)
            - reasons (list[str])  – human-readable reasons when blocked
        """
        reasons = []

        # 1. Weekly drawdown
        if self.check_weekly_drawdown(weekly_pnl_pct):
            reasons.append(
                f'Weekly P&L drawdown ({weekly_pnl_pct:.2f}%) exceeds '
                f'limit ({self.weekly_drawdown_pct:.2f}%)'
            )

        # 2. VIX percentile
        if self.check_vix_percentile(vix_percentile):
            reasons.append(
                f'VIX percentile ({vix_percentile:.1f}) breaches '
                f'threshold ({self.vix_percentile_limit:.1f})'
            )

        # 3. VIX day-over-day spike
        if self.check_vix_spike(vix_day_change_pct):
            reasons.append(
                f'VIX day-over-day spike ({vix_day_change_pct:.2f}%) exceeds '
                f'limit ({self.vix_spike_pct:.2f}%)'
            )

        # 4. Macro calendar proximity
        if self.check_macro_proximity(calendar_events):
            reasons.append(
                f'Inside macro-event blackout window '
                f'(±{self.macro_blackout_days} day(s))'
            )

        # 5. Regime: stressed
        if regime_label is not None and regime_label == 'stressed':
            reasons.append('Regime is stressed — no trading')

        # 6. Macro proximity elevated (from RegimeClassifier)
        if macro_proximity_elevated is True:
            reasons.append('Macro proximity elevated — no trading')

        return {
            'trading_allowed': len(reasons) == 0,
            'reasons': reasons,
        }

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_weekly_drawdown(self, weekly_pnl_pct: float) -> bool:
        """Return True (= blocked) if weekly loss exceeds threshold."""
        return weekly_pnl_pct < -self.weekly_drawdown_pct

    def check_vix_percentile(self, vix_percentile: float) -> bool:
        """Return True (= blocked) if VIX percentile too high."""
        return vix_percentile >= self.vix_percentile_limit

    def check_vix_spike(self, vix_day_change_pct: float) -> bool:
        """Return True (= blocked) if VIX spiked too much in a day."""
        return vix_day_change_pct > self.vix_spike_pct

    def check_macro_proximity(self, calendar_events: list) -> bool:
        """Return True (= blocked) if today falls within the blackout window of any event."""
        today = datetime.now().date()
        for event in calendar_events:
            event_date_str = event.get('date', '')
            try:
                event_date = datetime.fromisoformat(event_date_str).date()
            except (ValueError, TypeError):
                continue
            if abs((today - event_date).days) <= self.macro_blackout_days:
                return True
        return False
