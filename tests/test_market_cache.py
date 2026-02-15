"""Tests for the market data cache module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from unittest.mock import patch, MagicMock
from market_cache import (
    get_ticker_history, get_ticker_info, download_tickers,
    get_ticker_options, get_option_chain,
    _history_cache, _info_cache, _download_cache,
    _options_cache, _chain_cache,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear all caches between tests."""
    _history_cache.clear()
    _info_cache.clear()
    _download_cache.clear()
    _options_cache.clear()
    _chain_cache.clear()
    yield
    _history_cache.clear()
    _info_cache.clear()
    _download_cache.clear()
    _options_cache.clear()
    _chain_cache.clear()


class TestHistoryCache:
    @patch('market_cache.yf.Ticker')
    def test_caches_history(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = 'history_data'
        mock_ticker_cls.return_value = mock_ticker

        result1 = get_ticker_history('SPY', '1y')
        result2 = get_ticker_history('SPY', '1y')

        assert result1 == 'history_data'
        assert result2 == 'history_data'
        # yfinance should only be called once (second call from cache)
        assert mock_ticker.history.call_count == 1

    @patch('market_cache.yf.Ticker')
    def test_different_periods_not_shared(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = 'data'
        mock_ticker_cls.return_value = mock_ticker

        get_ticker_history('SPY', '1y')
        get_ticker_history('SPY', '3mo')

        assert mock_ticker.history.call_count == 2


class TestInfoCache:
    @patch('market_cache.yf.Ticker')
    def test_caches_info(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {'currentPrice': 480}
        mock_ticker_cls.return_value = mock_ticker

        result1 = get_ticker_info('SPY')
        result2 = get_ticker_info('SPY')

        assert result1 == {'currentPrice': 480}
        assert result2 == {'currentPrice': 480}
        assert mock_ticker_cls.call_count == 1


class TestDownloadCache:
    @patch('market_cache.yf.download')
    def test_caches_download(self, mock_download):
        mock_download.return_value = 'download_data'

        result1 = download_tickers(['SPY', 'QQQ'], '3mo')
        result2 = download_tickers(['SPY', 'QQQ'], '3mo')

        assert result1 == 'download_data'
        assert result2 == 'download_data'
        assert mock_download.call_count == 1

    @patch('market_cache.yf.download')
    def test_order_independent(self, mock_download):
        """Same symbols in different order should use same cache entry."""
        mock_download.return_value = 'data'

        download_tickers(['QQQ', 'SPY'], '3mo')
        download_tickers(['SPY', 'QQQ'], '3mo')

        assert mock_download.call_count == 1


class TestOptionsCache:
    @patch('market_cache.yf.Ticker')
    def test_caches_options(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.options = ['2026-03-20', '2026-04-17']
        mock_ticker_cls.return_value = mock_ticker

        result1 = get_ticker_options('SPY')
        result2 = get_ticker_options('SPY')

        assert result1 == ['2026-03-20', '2026-04-17']
        assert result2 == result1
        assert mock_ticker_cls.call_count == 1


class TestChainCache:
    @patch('market_cache.yf.Ticker')
    def test_caches_chain(self, mock_ticker_cls):
        mock_chain = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.option_chain.return_value = mock_chain
        mock_ticker_cls.return_value = mock_ticker

        result1 = get_option_chain('SPY', '2026-03-20')
        result2 = get_option_chain('SPY', '2026-03-20')

        assert result1 is mock_chain
        assert result2 is mock_chain
        assert mock_ticker.option_chain.call_count == 1
