# backend/etf_ranker.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

try:
    import yfinance as yf  # type: ignore
except ImportError:
    yf = None  # type: ignore


@dataclass
class RankerConfig:
    lookback_period: str = "6mo"  # enough to compute 200MA if available
    breakout_lookback: int = 20
    vol_lookback: int = 20
    atr_short: int = 5
    atr_long: int = 20
    vol_avg: int = 20
    buffer_up: float = 1.002   # +0.2%
    buffer_down: float = 0.998 # -0.2%

    # thresholds
    eligible_score: int = 65
    caution_score: int = 55

    # weights (sum to 100)
    w_trend: int = 35
    w_breakout: int = 45
    w_meanrev: int = 10
    w_volctx: int = 10


def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1
    ).max(axis=1)
    return tr.rolling(n).mean()


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    upper = ma + k * sd
    lower = ma - k * sd
    return lower, ma, upper


class ETFRanker:
    """
    Breakout-weighted ETF opportunity ranker.

    Output includes:
    - bias: bullish/bearish
    - signal_type: breakout/breakdown/pullback/neutral
    - score: 0-100
    - trigger/stop context
    - component scores for explainability
    """

    def __init__(self, config: Optional[RankerConfig] = None):
        self.cfg = config or RankerConfig()

    def _fetch_history(self, symbol: str) -> pd.DataFrame:
        if yf is None:
            raise RuntimeError("Required dependency 'yfinance' is not installed.")
        t = yf.Ticker(symbol)
        df = t.history(period=self.cfg.lookback_period, auto_adjust=False)
        # standardize columns
        if df is None or df.empty:
            return pd.DataFrame()
        # Some tickers return tz-aware index; normalize
        df = df.copy()
        df.columns = [c.title() for c in df.columns]
        return df

    def _compute_components(self, df: pd.DataFrame) -> Dict:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        vol = df["Volume"]

        ma20 = _sma(close, 20)
        ma50 = _sma(close, 50)
        ma200 = _sma(close, 200)

        # breakout levels
        hh20 = close.rolling(self.cfg.breakout_lookback).max()
        ll20 = close.rolling(self.cfg.breakout_lookback).min()

        # ATR + volume ratios
        atr5 = _atr(high, low, close, self.cfg.atr_short)
        atr20 = _atr(high, low, close, self.cfg.atr_long)
        atr_ratio = (atr5 / atr20).replace([np.inf, -np.inf], np.nan)

        vol_avg20 = vol.rolling(self.cfg.vol_avg).mean()
        vol_ratio = (vol / vol_avg20).replace([np.inf, -np.inf], np.nan)

        # RSI + Bollinger for mean reversion
        rsi14 = _rsi(close, 14)
        bb_lower, bb_mid, bb_upper = _bollinger(close, 20, 2.0)

        # ATR20 percentile proxy for vol context (over last ~252 trading days when available)
        atr20_hist = atr20.dropna()
        if len(atr20_hist) >= 60:
            # percentile rank of latest atr20 within history window
            latest_atr20 = atr20_hist.iloc[-1]
            pct = float((atr20_hist <= latest_atr20).mean())
        else:
            pct = float("nan")

        out = {
            "close": float(close.iloc[-1]),
            "ma20": float(ma20.iloc[-1]) if not np.isnan(ma20.iloc[-1]) else None,
            "ma50": float(ma50.iloc[-1]) if not np.isnan(ma50.iloc[-1]) else None,
            "ma200": float(ma200.iloc[-1]) if not np.isnan(ma200.iloc[-1]) else None,
            "hh20": float(hh20.iloc[-1]) if not np.isnan(hh20.iloc[-1]) else None,
            "ll20": float(ll20.iloc[-1]) if not np.isnan(ll20.iloc[-1]) else None,
            "atr_ratio": float(atr_ratio.iloc[-1]) if not np.isnan(atr_ratio.iloc[-1]) else None,
            "atr20": float(atr20.iloc[-1]) if not np.isnan(atr20.iloc[-1]) else None,
            "vol_ratio": float(vol_ratio.iloc[-1]) if not np.isnan(vol_ratio.iloc[-1]) else None,
            "rsi14": float(rsi14.iloc[-1]) if not np.isnan(rsi14.iloc[-1]) else None,
            "bb_lower": float(bb_lower.iloc[-1]) if not np.isnan(bb_lower.iloc[-1]) else None,
            "bb_upper": float(bb_upper.iloc[-1]) if not np.isnan(bb_upper.iloc[-1]) else None,
            "atr20_percentile": pct if not np.isnan(pct) else None,
            "ma50_slope_10d": None,
        }

        # MA50 slope over last 10 days (simple)
        if len(ma50.dropna()) >= 11:
            out["ma50_slope_10d"] = float(ma50.iloc[-1] - ma50.iloc[-11])

        return out

    def _score_trend(self, c: Dict) -> Tuple[int, int]:
        """
        Returns (bull_trend_score, bear_trend_score) in 0..35 bucket before weighting normalization.
        """
        close = c["close"]
        ma20 = c["ma20"]
        ma50 = c["ma50"]
        ma200 = c["ma200"]
        slope = c["ma50_slope_10d"]

        bull = 0
        bear = 0

        if ma20 is not None and close is not None:
            bull += 10 if close > ma20 else 0
            bear += 10 if close < ma20 else 0

        if ma20 is not None and ma50 is not None:
            bull += 10 if ma20 > ma50 else 0
            bear += 10 if ma20 < ma50 else 0

        if slope is not None:
            bull += 10 if slope > 0 else 0
            bear += 10 if slope < 0 else 0

        if ma200 is not None and close is not None:
            bull += 5 if close > ma200 else 0
            bear += 5 if close < ma200 else 0

        return bull, bear

    def _score_breakout(self, c: Dict, bias: str) -> int:
        """
        Returns 0..45 bucket score.
        """
        close = c["close"]
        hh20 = c["hh20"]
        ll20 = c["ll20"]
        atr_ratio = c["atr_ratio"]
        vol_ratio = c["vol_ratio"]

        score = 0
        if bias == "bullish":
            if hh20 is not None and close >= hh20 * self.cfg.buffer_up:
                score += 25
        else:
            if ll20 is not None and close <= ll20 * self.cfg.buffer_down:
                score += 25

        if atr_ratio is not None and atr_ratio >= 1.15:
            score += 10

        if vol_ratio is not None and vol_ratio >= 1.25:
            score += 10

        return score

    def _score_mean_reversion(self, c: Dict, bias: str) -> int:
        """
        Returns 0..10 bucket score.
        """
        close = c["close"]
        rsi14 = c["rsi14"]
        bb_lower = c["bb_lower"]
        bb_upper = c["bb_upper"]
        ma50 = c["ma50"]

        score = 0
        if bias == "bullish":
            if rsi14 is not None and rsi14 <= 35:
                score += 5
            # pullback in trend
            if bb_lower is not None and ma50 is not None and close <= bb_lower and close > ma50:
                score += 5
        else:
            if rsi14 is not None and rsi14 >= 65:
                score += 5
            if bb_upper is not None and ma50 is not None and close >= bb_upper and close < ma50:
                score += 5
        return score

    def _score_vol_context(self, c: Dict) -> int:
        """
        Returns 0..10 bucket score, preferring low/normal realized vol.
        Uses ATR20 percentile as proxy.
        """
        pct = c.get("atr20_percentile")
        if pct is None:
            return 5  # neutral fallback
        # lower ATR percentile = calmer; better for debit spreads
        if pct <= 0.50:
            return 10
        if pct <= 0.75:
            return 5
        return 0

    def rank(self, symbols: List[str], top: int = 5, min_score: int = 65) -> List[Dict]:
        ranked: List[Dict] = []

        for sym in symbols:
            try:
                df = self._fetch_history(sym)
                if df is None or df.empty or len(df) < 60:
                    continue
                c = self._compute_components(df)

                bull_trend, bear_trend = self._score_trend(c)
                bias = "bullish" if bull_trend >= bear_trend else "bearish"

                breakout_score = self._score_breakout(c, bias)
                meanrev_score = self._score_mean_reversion(c, bias)
                volctx_score = self._score_vol_context(c)

                # Trend bucket already on 0..35; breakout 0..45; meanrev 0..10; volctx 0..10
                if bias == "bullish":
                    trend_score = bull_trend
                else:
                    trend_score = bear_trend

                total = int(round(trend_score + breakout_score + meanrev_score + volctx_score))

                # signal_type
                signal_type = "neutral"
                if breakout_score >= 30:
                    signal_type = "breakout" if bias == "bullish" else "breakdown"
                elif meanrev_score >= 7 and trend_score >= 20:
                    signal_type = "pullback"

                # context levels
                trigger = c["hh20"] if bias == "bullish" else c["ll20"]
                # stop: MA20 or +/- 1.2*ATR20
                atr20 = c.get("atr20")
                ma20 = c.get("ma20")
                close = c["close"]
                if atr20 is not None and close is not None:
                    if bias == "bullish":
                        stop_atr = close - 1.2 * atr20
                    else:
                        stop_atr = close + 1.2 * atr20
                else:
                    stop_atr = None

                stop = None
                if ma20 is not None and stop_atr is not None:
                    # tighter stop
                    stop = max(stop_atr, ma20) if bias == "bullish" else min(stop_atr, ma20)
                else:
                    stop = ma20 or stop_atr

                strength_label = (
                    "eligible" if total >= self.cfg.eligible_score
                    else "caution" if total >= self.cfg.caution_score
                    else "no_trade"
                )

                row = {
                    "symbol": sym,
                    "bias": bias,
                    "signal_type": signal_type,
                    "score": total,
                    "strength_label": strength_label,
                    "price": c["close"],
                    "levels": {
                        "trigger": round(trigger, 4) if trigger is not None else None,
                        "stop": round(stop, 4) if stop is not None else None,
                    },
                    "components": {
                        "trend_score": trend_score,
                        "breakout_score": breakout_score,
                        "mean_reversion_score": meanrev_score,
                        "vol_context_score": volctx_score,
                    },
                    "metrics": {
                        "ma20": c.get("ma20"),
                        "ma50": c.get("ma50"),
                        "ma200": c.get("ma200"),
                        "atr_ratio": c.get("atr_ratio"),
                        "vol_ratio": c.get("vol_ratio"),
                        "rsi14": c.get("rsi14"),
                    },
                }

                if total >= min_score:
                    ranked.append(row)

            except Exception:
                # skip symbols that error (bad history, rate limits, etc.)
                continue

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top]
