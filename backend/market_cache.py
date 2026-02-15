"""
Market data cache utility.

Provides a TTL-based cache (default 15 minutes) keyed by symbol + caller,
so that repeated yfinance calls within the same time bucket are served
from memory instead of hitting the network.
"""

import logging
from cachetools import TTLCache
import yfinance as yf

logger = logging.getLogger(__name__)

# Default TTL is 15 minutes (900 seconds)
_DEFAULT_TTL = 900

# Cache for ticker history data: key = (symbol, period)
_history_cache = TTLCache(maxsize=256, ttl=_DEFAULT_TTL)

# Cache for ticker info data: key = symbol
_info_cache = TTLCache(maxsize=256, ttl=_DEFAULT_TTL)

# Cache for multi-ticker downloads: key = (tuple(symbols), period)
_download_cache = TTLCache(maxsize=64, ttl=_DEFAULT_TTL)

# Cache for ticker options expirations: key = symbol
_options_cache = TTLCache(maxsize=128, ttl=_DEFAULT_TTL)

# Cache for option chain data: key = (symbol, expiration)
_chain_cache = TTLCache(maxsize=256, ttl=_DEFAULT_TTL)


def get_ticker_history(symbol, period='1y'):
    """Fetch ticker history with caching."""
    key = (symbol, period)
    if key in _history_cache:
        return _history_cache[key]
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    _history_cache[key] = hist
    return hist


def get_ticker_info(symbol):
    """Fetch ticker info with caching."""
    if symbol in _info_cache:
        return _info_cache[symbol]
    ticker = yf.Ticker(symbol)
    info = ticker.info
    _info_cache[symbol] = info
    return info


def download_tickers(symbols, period='3mo'):
    """Download multiple tickers with caching."""
    key = (tuple(sorted(symbols)), period)
    if key in _download_cache:
        return _download_cache[key]
    data = yf.download(symbols, period=period, progress=False)
    _download_cache[key] = data
    return data


def get_ticker_options(symbol):
    """Fetch available option expirations with caching."""
    if symbol in _options_cache:
        return _options_cache[symbol]
    ticker = yf.Ticker(symbol)
    expirations = ticker.options
    _options_cache[symbol] = expirations
    return expirations


def get_option_chain(symbol, expiration):
    """Fetch option chain with caching."""
    key = (symbol, expiration)
    if key in _chain_cache:
        return _chain_cache[key]
    ticker = yf.Ticker(symbol)
    chain = ticker.option_chain(expiration)
    _chain_cache[key] = chain
    return chain
