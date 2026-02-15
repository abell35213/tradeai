"""
Market Data Provider Interface

Defines a standard interface for all market-data access used by the
Automated Earnings Volatility Income Engine.  Concrete implementations
can wrap yfinance, a broker API, or mock data for testing.

Methods
-------
get_spot(symbol)
    Current spot price for *symbol*.
get_history(symbol, window)
    Historical OHLCV DataFrame for *symbol* over *window* (e.g. '3mo').
get_options_chain(symbol, expiry)
    Options chain (calls, puts) for *symbol* at a given *expiry* date string.
get_vix_history()
    1-year VIX close Series.
get_calendar_events()
    Upcoming macro-calendar events (CPI, FOMC, NFP, …).
"""

from abc import ABC, abstractmethod
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


class MarketDataProvider(ABC):
    """Abstract base class that every data provider must implement."""

    @abstractmethod
    def get_spot(self, symbol: str) -> float:
        """Return the latest spot price for *symbol*."""

    @abstractmethod
    def get_history(self, symbol: str, window: str) -> pd.DataFrame:
        """Return OHLCV history for *symbol* over *window* (e.g. '1mo', '3mo')."""

    @abstractmethod
    def get_options_chain(self, symbol: str, expiry: str) -> dict:
        """
        Return the options chain for *symbol* at *expiry*.

        Returns
        -------
        dict with keys 'calls' and 'puts', each a ``pandas.DataFrame``.
        """

    @abstractmethod
    def get_vix_history(self) -> pd.Series:
        """Return ~1 year of VIX closing prices as a pandas Series."""

    @abstractmethod
    def get_calendar_events(self) -> list:
        """
        Return a list of upcoming macro-calendar events.

        Each event is a dict with at least:
            - 'date'  (str, ISO-8601)
            - 'event' (str, e.g. 'FOMC', 'CPI', 'NFP')
        """


class YFinanceDataProvider(MarketDataProvider):
    """Concrete implementation backed by the *yfinance* library."""

    def get_spot(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price is None:
            hist = ticker.history(period='1d')
            if len(hist) > 0:
                price = float(hist['Close'].iloc[-1])
        return float(price) if price is not None else 0.0

    def get_history(self, symbol: str, window: str) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        return ticker.history(period=window)

    def get_options_chain(self, symbol: str, expiry: str) -> dict:
        ticker = yf.Ticker(symbol)
        chain = ticker.option_chain(expiry)
        return {'calls': chain.calls, 'puts': chain.puts}

    def get_vix_history(self) -> pd.Series:
        vix = yf.Ticker('^VIX')
        hist = vix.history(period='1y')
        return hist['Close']

    def get_calendar_events(self) -> list:
        """
        Return scheduled macro events.

        A production system should integrate a real calendar feed
        (e.g. Econoday, Trading Economics API).  This implementation
        provides a static schedule of recurring US macro events so the
        circuit-breaker layer has something concrete to reason about.
        """
        events = []
        today = datetime.now().date()
        # Look 30 days ahead
        for offset in range(31):
            dt = today + timedelta(days=offset)
            # FOMC: typically 8 meetings/year, approximate as 3rd Wed of
            # Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
            fomc_months = {1, 3, 5, 6, 7, 9, 11, 12}
            if dt.weekday() == 2 and 15 <= dt.day <= 21 and dt.month in fomc_months:
                events.append({'date': dt.isoformat(), 'event': 'FOMC'})
            # CPI: typically ~12th of each month
            if 10 <= dt.day <= 14 and dt.weekday() < 5:
                # Only flag once per month window
                if dt.day == 12 or (dt.day == 13 and datetime(dt.year, dt.month, 12).weekday() >= 5):
                    events.append({'date': dt.isoformat(), 'event': 'CPI'})
            # NFP: first Friday of each month
            if dt.weekday() == 4 and dt.day <= 7:
                events.append({'date': dt.isoformat(), 'event': 'NFP'})
        return events
