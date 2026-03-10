"""
Three-tier data provider facade for AlphaDesk.

Central data access layer that tries data sources in priority order:
- Tier 1: financialdatasets.ai (fds_client) — stock prices, earnings, fundamentals
- Tier 2: FRED (fred_client) — macro/economic data
- Tier 3: yfinance (yfinance_service) — fallback

All functions check cache first, then try tiers in order.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from backend.services.cache import cache
from backend.services import fds_client as fds
from backend.services import fred_client as fred
from backend.services import yfinance_service as yf_svc
from backend.config import (
    CACHE_TTL_QUOTE,
    CACHE_TTL_HISTORY,
    CACHE_TTL_MACRO,
    CACHE_TTL_FUNDAMENTALS,
    CACHE_TTL_SECTOR,
)

logger = logging.getLogger(__name__)


def _period_to_dates(period: str) -> tuple[str, str]:
    """
    Convert period string to ISO date range strings.

    Args:
        period: Period string like "1y", "6mo", "3mo", "1mo", "5d"

    Returns:
        Tuple of (start_date, end_date) as ISO strings (YYYY-MM-DD)
    """
    end_date = datetime.now().date()

    if period == "1y":
        start_date = end_date - timedelta(days=365)
    elif period == "6mo":
        start_date = end_date - timedelta(days=180)
    elif period == "3mo":
        start_date = end_date - timedelta(days=90)
    elif period == "1mo":
        start_date = end_date - timedelta(days=30)
    elif period == "5d":
        start_date = end_date - timedelta(days=5)
    else:
        # Default to 1 year
        start_date = end_date - timedelta(days=365)

    return (start_date.isoformat(), end_date.isoformat())


def get_quote(ticker: str) -> Dict:
    """
    Get current stock quote for a ticker.

    Tries Tier 1 (FDS) → Tier 3 (yfinance). No macro/FRED tier for individual stocks.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with price, change, pct_change, volume, name, etc.
        Returns empty dict if unavailable.
    """
    cache_key = f"quote:{ticker}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Quote for {ticker} served from cache")
        return cached_result

    # Tier 1: FDS
    if fds.is_available():
        try:
            result = fds.get_price_snapshot(ticker)
            if result:
                logger.info(f"Quote for {ticker} served from FDS (Tier 1)")
                cache.set(cache_key, result, CACHE_TTL_QUOTE)
                return result
        except Exception as e:
            logger.warning(f"FDS quote fetch failed for {ticker}: {e}")

    # Tier 3: yfinance (fallback)
    try:
        result = yf_svc.get_quote(ticker)
        if result:
            logger.info(f"Quote for {ticker} served from yfinance (Tier 3)")
            cache.set(cache_key, result, CACHE_TTL_QUOTE)
            return result
    except Exception as e:
        logger.warning(f"yfinance quote fetch failed for {ticker}: {e}")

    logger.warning(f"Could not fetch quote for {ticker} from any tier")
    return {}


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> List[Dict]:
    """
    Get historical price data for a ticker.

    For daily data: tries Tier 1 (FDS) → Tier 3 (yfinance)
    For intraday (5m, 15m, etc.): goes straight to yfinance (FDS doesn't support intraday)

    Args:
        ticker: Stock ticker symbol
        period: Period string like "1y", "6mo", "3mo", "1mo", "5d"
        interval: Interval like "1d", "5m", "15m", "1h"

    Returns:
        List of dicts with date, open, high, low, close, volume
        Returns empty list if unavailable.
    """
    cache_key = f"history:{ticker}:{period}:{interval}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"History for {ticker} (period={period}, interval={interval}) served from cache")
        return cached_result

    # For intraday data, go straight to yfinance (FDS doesn't support intraday)
    if interval != "1d":
        try:
            result = yf_svc.get_history(ticker, period=period, interval=interval)
            if result:
                logger.info(f"History for {ticker} (intraday) served from yfinance (Tier 3)")
                cache.set(cache_key, result, CACHE_TTL_HISTORY)
                return result
        except Exception as e:
            logger.warning(f"yfinance history fetch failed for {ticker}: {e}")
        return []

    # For daily data, try Tier 1 first
    start_date, end_date = _period_to_dates(period)

    if fds.is_available():
        try:
            result = fds.get_historical_prices(ticker, start=start_date, end=end_date, interval="day")
            if result:
                logger.info(f"History for {ticker} served from FDS (Tier 1)")
                cache.set(cache_key, result, CACHE_TTL_HISTORY)
                return result
        except Exception as e:
            logger.warning(f"FDS history fetch failed for {ticker}: {e}")

    # Tier 3: yfinance (fallback)
    try:
        result = yf_svc.get_history(ticker, period=period, interval=interval)
        if result:
            logger.info(f"History for {ticker} served from yfinance (Tier 3)")
            cache.set(cache_key, result, CACHE_TTL_HISTORY)
            return result
    except Exception as e:
        logger.warning(f"yfinance history fetch failed for {ticker}: {e}")

    logger.warning(f"Could not fetch history for {ticker} from any tier")
    return []


def get_macro_data() -> Dict:
    """
    Get macro economic data from FRED and yfinance.

    Tier 2 (FRED) provides Treasury yields, VIX, Dollar, Oil, etc.
    Tier 3 (yfinance) provides fallback for tickers FRED doesn't cover.

    Returns:
        Dict with ticker keys (e.g., "^TNX", "^VIX") mapping to
        {"price": ..., "change": ..., "pct_change": ...}
        Returns empty dict if unavailable.
    """
    cache_key = "macro:all"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug("Macro data served from cache")
        return cached_result

    result = {}

    # Tier 2: FRED for macro series
    fred_series_mapping = {
        "DGS10": "^TNX",      # 10-Year Treasury
        "DTB3": "^IRX",       # 3-Month Treasury
        "VIXCLS": "^VIX",     # VIX
        "DTWEXBGS": "DX-Y.NYB",  # Dollar Index
        "DCOILWTICO": "CL=F",    # Crude Oil WTI
    }

    fred_snapshot = fred.get_macro_snapshot()

    for fred_series, ticker_key in fred_series_mapping.items():
        if fred_series in fred_snapshot:
            try:
                fred_value = fred_snapshot[fred_series].get("value")
                if fred_value is not None:
                    # Build result in the format expected
                    result[ticker_key] = {
                        "price": float(fred_value),
                        "change": 0.0,  # FRED doesn't provide daily change
                        "pct_change": 0.0,  # Calculate if we have previous value
                    }
                    logger.debug(f"Macro {ticker_key} served from FRED (Tier 2)")
            except Exception as e:
                logger.warning(f"Error processing FRED data for {fred_series}: {e}")

    # Tier 3: yfinance for tickers FRED doesn't cover
    fallback_tickers = ["GC=F", "BTC-USD", "SPY", "QQQ", "IWM"]

    for ticker in fallback_tickers:
        if ticker not in result:
            try:
                quote = yf_svc.get_quote(ticker)
                if quote and "price" in quote:
                    result[ticker] = {
                        "price": quote.get("price", 0),
                        "change": quote.get("change", 0),
                        "pct_change": quote.get("pct_change", 0),
                    }
                    logger.debug(f"Macro {ticker} served from yfinance (Tier 3)")
            except Exception as e:
                logger.warning(f"yfinance macro fetch failed for {ticker}: {e}")

    if result:
        logger.info(f"Macro data served from FRED/yfinance (mixed tiers)")
        cache.set(cache_key, result, CACHE_TTL_MACRO)
        return result

    logger.warning("Could not fetch macro data from any tier")
    return {}


def get_sector_data(period: str = "1D") -> List[Dict]:
    """
    Get sector ETF data.

    No FDS/FRED equivalent for sector bundles, so uses yfinance directly (Tier 3).

    Args:
        period: Period for chart data ("1D", "1W", "1M", "1Y")

    Returns:
        List of dicts with ticker, sector, price, change, chart_data, etc.
        Returns empty list if unavailable.
    """
    cache_key = f"sector:{period}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Sector data (period={period}) served from cache")
        return cached_result

    # Tier 3: yfinance only (no FRED/FDS tier)
    try:
        result = yf_svc.get_sector_data(period=period)
        if result:
            logger.info(f"Sector data served from yfinance (Tier 3)")
            cache.set(cache_key, result, CACHE_TTL_SECTOR)
            return result
    except Exception as e:
        logger.warning(f"yfinance sector fetch failed: {e}")

    logger.warning("Could not fetch sector data from any tier")
    return []


def get_fundamentals(ticker: str) -> Dict:
    """
    Get fundamental data for a stock.

    Tries Tier 1 (FDS) → Tier 3 (yfinance).

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with PE, PB, market cap, fundamentals, etc.
        Returns dict with at least ticker key if unavailable.
    """
    cache_key = f"fundamentals:{ticker}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Fundamentals for {ticker} served from cache")
        return cached_result

    # Tier 1: FDS
    if fds.is_available():
        try:
            result = fds.get_financial_metrics(ticker)
            if result:
                logger.info(f"Fundamentals for {ticker} served from FDS (Tier 1)")
                cache.set(cache_key, result, CACHE_TTL_FUNDAMENTALS)
                return result
        except Exception as e:
            logger.warning(f"FDS fundamentals fetch failed for {ticker}: {e}")

    # Tier 3: yfinance (fallback)
    try:
        result = yf_svc.get_stock_fundamentals(ticker)
        if result:
            logger.info(f"Fundamentals for {ticker} served from yfinance (Tier 3)")
            cache.set(cache_key, result, CACHE_TTL_FUNDAMENTALS)
            return result
    except Exception as e:
        logger.warning(f"yfinance fundamentals fetch failed for {ticker}: {e}")

    logger.warning(f"Could not fetch fundamentals for {ticker} from any tier")
    return {"ticker": ticker}


def get_earnings(ticker: str) -> List[Dict]:
    """
    Get earnings history for a stock.

    Tries Tier 1 (FDS), no fallback to other tiers if unavailable.

    Args:
        ticker: Stock ticker symbol

    Returns:
        List of earnings records
        Returns empty list if unavailable.
    """
    cache_key = f"earnings:{ticker}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Earnings for {ticker} served from cache")
        return cached_result

    # Tier 1: FDS
    if fds.is_available():
        try:
            result = fds.get_earnings(ticker)
            if result:
                logger.info(f"Earnings for {ticker} served from FDS (Tier 1)")
                cache.set(cache_key, result, CACHE_TTL_FUNDAMENTALS)
                return result
        except Exception as e:
            logger.warning(f"FDS earnings fetch failed for {ticker}: {e}")

    logger.warning(f"Could not fetch earnings for {ticker} from any tier")
    return []


def search_ticker(query: str) -> List[Dict]:
    """
    Search for tickers matching a query.

    No caching — passes through to yfinance directly (Tier 3).

    Args:
        query: Search query string

    Returns:
        List of matching tickers with name and sector
        Returns empty list if no matches.
    """
    try:
        result = yf_svc.search_ticker(query)
        if result:
            logger.info(f"Ticker search for '{query}' served from yfinance (Tier 3)")
            return result
    except Exception as e:
        logger.warning(f"yfinance ticker search failed for '{query}': {e}")

    logger.warning(f"Could not search for ticker '{query}' from any tier")
    return []
