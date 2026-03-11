"""
Market Breadth Engine for AlphaDesk.

Data source cascade:
  1. financialdatasets.ai (FDS, paid API, reliable price snapshots)
  2. yahoo_direct (batch v8 API for S&P 500 sample)
  3. yfinance batch download (original implementation)
  4. synthetic_estimator (VIX + credit spread regime model)

Calculates advance/decline ratio, McClellan Oscillator approximation,
and breadth thrust from S&P 500 components.
"""

import logging
import time
from typing import Dict, Any
import yfinance as yf
import numpy as np

from backend.services import fds_client as fds
from backend.services import yahoo_direct
from backend.services import synthetic_estimator

logger = logging.getLogger(__name__)

# Cache
_breadth_cache: Dict[str, Any] = {}
_CACHE_TTL_MARKET_HOURS = 900   # 15 minutes during market hours
_CACHE_TTL_OFF_HOURS = 3600     # 60 minutes off hours

# Representative sample of S&P 500 components (top ~100 by weight + sector representatives)
SP500_SAMPLE = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "CRM",
    "AMD", "ADBE", "CSCO", "INTC", "QCOM", "AMAT", "TXN", "INTU", "MU", "NOW",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "ISRG", "MDT", "SYK",
    # Financials
    "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW",
    "AXP", "C", "USB", "PNC", "TFC",
    # Consumer Discretionary
    "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "CMG", "ORLY", "ROST",
    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "MDLZ", "KHC",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
    # Industrials
    "GE", "CAT", "HON", "UPS", "RTX", "BA", "DE", "LMT", "MMM", "UNP",
    # Utilities
    "NEE", "SO", "DUK", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ED",
    # Real Estate
    "PLD", "AMT", "CCI", "EQIX", "SPG", "PSA", "O", "DLR", "WELL", "AVB",
    # Communication Services
    "GOOG", "DIS", "CMCSA", "NFLX", "T", "VZ", "TMUS", "CHTR", "EA", "ATVI",
]


def _is_market_hours() -> bool:
    """Check if US market is likely open (rough estimate)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour = now.hour
    return weekday < 5 and 14 <= hour < 21


def _calculate_breadth_fds() -> Dict[str, Any] | None:
    """
    Calculate breadth using financialdatasets.ai price snapshots.
    Uses a focused sample (30 tickers) for speed.
    """
    if not fds.is_available():
        return None

    sample = SP500_SAMPLE[:30]
    advances = 0
    declines = 0
    unchanged = 0
    total = 0

    for ticker in sample:
        try:
            snapshot = fds.get_price_snapshot(ticker)
            if snapshot and snapshot.get("pct_change") is not None:
                total += 1
                pct = snapshot["pct_change"]
                if pct > 0.05:
                    advances += 1
                elif pct < -0.05:
                    declines += 1
                else:
                    unchanged += 1
        except Exception:
            continue

    if total < 15:
        return None

    return _build_breadth_result(advances, declines, unchanged, total, "financialdatasets.ai")


def _calculate_breadth_yahoo_direct() -> Dict[str, Any] | None:
    """
    Calculate breadth using yahoo_direct v8 API for a representative sample.
    Uses a smaller sample (30 tickers) for speed.
    """
    if not yahoo_direct.is_available():
        return None

    # Use a focused sample for speed
    sample = SP500_SAMPLE[:30]

    advances = 0
    declines = 0
    unchanged = 0
    total = 0
    fetched = 0

    for ticker in sample:
        if not yahoo_direct.is_available():
            break
        quote = yahoo_direct.get_quote(ticker)
        if quote and quote.get("pct_change") is not None:
            fetched += 1
            total += 1
            pct = quote["pct_change"]
            if pct > 0.05:
                advances += 1
            elif pct < -0.05:
                declines += 1
            else:
                unchanged += 1

    if total < 15:  # Need at least half the sample
        return None

    return _build_breadth_result(advances, declines, unchanged, total, "yahoo_direct")


def _calculate_breadth_yfinance() -> Dict[str, Any] | None:
    """Calculate breadth using yfinance batch download (original implementation)."""
    try:
        tickers_str = " ".join(SP500_SAMPLE)
        data = yf.download(tickers_str, period="5d", group_by="ticker", progress=False, threads=True)

        advances = 0
        declines = 0
        unchanged = 0
        total = 0

        for ticker in SP500_SAMPLE:
            try:
                if ticker in data.columns.get_level_values(0):
                    close_data = data[ticker]["Close"].dropna()
                    if len(close_data) >= 2:
                        daily_return = (close_data.iloc[-1] / close_data.iloc[-2] - 1) * 100
                        total += 1
                        if daily_return > 0.05:
                            advances += 1
                        elif daily_return < -0.05:
                            declines += 1
                        else:
                            unchanged += 1
            except Exception:
                continue

        if total == 0:
            return None

        return _build_breadth_result(advances, declines, unchanged, total, "yfinance")

    except Exception as e:
        logger.error(f"yfinance breadth: {e}")
        return None


def _build_breadth_result(advances, declines, unchanged, total, source) -> Dict[str, Any]:
    """Build breadth result dict from A/D counts."""
    ad_ratio = round(advances / max(declines, 1), 2)
    pct_advancing = round(advances / total * 100, 1)
    breadth_thrust = pct_advancing > 61.5
    net_advances = advances - declines
    mcclellan_approx = round(net_advances * 0.6, 1)

    if ad_ratio > 2.0:
        signal = "strongly_bullish"
    elif ad_ratio > 1.5:
        signal = "bullish"
    elif ad_ratio > 0.67:
        signal = "neutral"
    elif ad_ratio > 0.5:
        signal = "bearish"
    else:
        signal = "strongly_bearish"

    return {
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "total": total,
        "ad_ratio": ad_ratio,
        "pct_advancing": pct_advancing,
        "pct_declining": round(declines / total * 100, 1),
        "breadth_thrust": breadth_thrust,
        "mcclellan": mcclellan_approx,
        "net_advances": net_advances,
        "signal": signal,
        "sample_size": total,
        "data_source": source,
    }


def calculate_breadth() -> Dict[str, Any]:
    """
    Calculate market breadth metrics.
    Cascade: yahoo_direct → yfinance batch → synthetic estimation.
    """
    now = time.time()
    cache_key = "breadth"

    if cache_key in _breadth_cache:
        cached = _breadth_cache[cache_key]
        ttl = _CACHE_TTL_MARKET_HOURS if _is_market_hours() else _CACHE_TTL_OFF_HOURS
        if now - cached["ts"] < ttl:
            return cached["data"]

    # --- Tier 1: FDS (financialdatasets.ai) ---
    result = _calculate_breadth_fds()
    if result:
        _breadth_cache[cache_key] = {"ts": now, "data": result}
        return result

    # --- Tier 2: yahoo_direct ---
    result = _calculate_breadth_yahoo_direct()
    if result:
        _breadth_cache[cache_key] = {"ts": now, "data": result}
        return result

    # --- Tier 3: yfinance batch ---
    result = _calculate_breadth_yfinance()
    if result:
        _breadth_cache[cache_key] = {"ts": now, "data": result}
        return result

    # --- Tier 4: Synthetic estimation ---
    logger.info("Using VIX+credit-based synthetic estimation for market breadth")
    estimated = synthetic_estimator.estimate_breadth()
    _breadth_cache[cache_key] = {"ts": now, "data": estimated}
    return estimated


def _empty_breadth(error: str = "") -> Dict[str, Any]:
    return {
        "advances": 0,
        "declines": 0,
        "unchanged": 0,
        "total": 0,
        "ad_ratio": 1.0,
        "pct_advancing": 50.0,
        "pct_declining": 50.0,
        "breadth_thrust": False,
        "mcclellan": 0,
        "net_advances": 0,
        "signal": "neutral",
        "sample_size": 0,
        "error": error,
    }
