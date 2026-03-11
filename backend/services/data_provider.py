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
from backend.services import yahoo_direct as yd
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
    # Use yesterday as end_date to avoid FDS "end_date must be today or older" errors
    # when our VM clock is ahead of FDS market-time clock
    end_date = datetime.now().date() - timedelta(days=1)

    if period == "1y":
        start_date = end_date - timedelta(days=365)
    elif period == "6mo":
        start_date = end_date - timedelta(days=180)
    elif period == "3mo":
        start_date = end_date - timedelta(days=90)
    elif period == "1mo":
        start_date = end_date - timedelta(days=30)
    elif period == "5d":
        start_date = end_date - timedelta(days=7)  # extra buffer for weekends
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

    # Tier 0: yahoo_direct (fastest, no library overhead)
    try:
        result = yd.get_quote(ticker)
        if result and result.get("price"):
            logger.info(f"Quote for {ticker} served from yahoo_direct (Tier 0)")
            cache.set(cache_key, result, CACHE_TTL_QUOTE)
            return result
    except Exception as e:
        logger.warning(f"yahoo_direct quote fetch failed for {ticker}: {e}")

    # Tier 1: FDS
    if fds.is_available():
        try:
            result = fds.get_price_snapshot(ticker)
            if result and result.get("price"):
                logger.info(f"Quote for {ticker} served from FDS (Tier 1)")
                cache.set(cache_key, result, CACHE_TTL_QUOTE)
                return result
        except Exception as e:
            logger.warning(f"FDS quote fetch failed for {ticker}: {e}")

    # Tier 3: yfinance (last resort)
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

    # Map period to Yahoo range string
    yahoo_range_map = {"1y": "1y", "6mo": "6mo", "3mo": "3mo", "1mo": "1mo", "5d": "5d"}
    yahoo_range = yahoo_range_map.get(period, period)

    # Tier 0: yahoo_direct
    try:
        result = yd.get_history(ticker, range_str=yahoo_range, interval=interval)
        if result:
            logger.info(f"History for {ticker} served from yahoo_direct (Tier 0)")
            cache.set(cache_key, result, CACHE_TTL_HISTORY)
            return result
    except Exception as e:
        logger.warning(f"yahoo_direct history fetch failed for {ticker}: {e}")

    # Tier 1: FDS
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

    # Tier 3: yfinance (last resort)
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

    Tier 1.5 (FDS) provides stock-based macro tickers (SPY, QQQ, IWM) with real daily changes.
    Tier 2 (FRED) provides Treasury yields, VIX, Dollar, Oil, etc.
    Tier 3 (yfinance) provides fallback for tickers FRED doesn't cover.

    Returns:
        Dict with ticker keys (e.g., "^TNX", "^VIX") mapping to
        {"price": ..., "change": ..., "pct_change": ...}
        pct_change can be None if change data is unavailable.
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
                fred_entry = fred_snapshot[fred_series]
                fred_value = fred_entry.get("value")
                if fred_value is not None:
                    result[ticker_key] = {
                        "price": float(fred_value),
                        "change": fred_entry.get("change"),
                        "pct_change": fred_entry.get("pct_change"),
                    }
                    logger.debug(f"Macro {ticker_key} served from FRED (Tier 2)")
            except Exception as e:
                logger.warning(f"Error processing FRED data for {fred_series}: {e}")

    # Tier 0: yahoo_direct for equity/commodity/crypto tickers (parallel batch)
    equity_tickers = ["SPY", "QQQ", "IWM", "GC=F", "BTC-USD"]
    missing_equities = [t for t in equity_tickers if t not in result]

    if missing_equities:
        try:
            yd_quotes = yd.batch_quotes(missing_equities)
            for ticker, quote in yd_quotes.items():
                if quote and quote.get("price"):
                    result[ticker] = {
                        "price": quote["price"],
                        "change": quote.get("change", 0),
                        "pct_change": quote.get("pct_change", 0),
                    }
                    logger.debug(f"Macro {ticker} served from yahoo_direct (Tier 0)")
        except Exception as e:
            logger.warning(f"yahoo_direct batch macro fetch failed: {e}")

    if result:
        logger.info(f"Macro data served from FDS/FRED/yfinance (mixed tiers)")
        cache.set(cache_key, result, max(CACHE_TTL_MACRO, 1800))  # At least 30 min cache
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

    # Tier 0: yahoo_direct sector charts
    sector_etfs = {
        "XLK": "Information Technology", "XLV": "Healthcare",
        "XLF": "Financials", "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples", "XLE": "Energy",
        "XLRE": "Real Estate", "XLI": "Industrials",
        "XLU": "Utilities", "XLC": "Communication Services",
    }
    try:
        # Map period format (1D→5d, 5D→10d, etc.)
        range_map = {"1D": "5d", "5D": "10d", "1M": "1mo", "3M": "3mo", "1Y": "1y"}
        range_str = range_map.get(period, "1mo")
        yd_quotes = yd.batch_quotes(list(sector_etfs.keys()))
        if yd_quotes and len(yd_quotes) >= 5:
            result = []
            for ticker, name in sector_etfs.items():
                q = yd_quotes.get(ticker)
                if q:
                    result.append({
                        "ticker": ticker,
                        "sector": name,
                        "price": q.get("price", 0),
                        "daily_change": q.get("change", 0),
                        "daily_pct_change": q.get("pct_change", 0),
                        "chart_data": [],  # Basic sector data doesn't need chart_data
                    })
            if result:
                logger.info(f"Sector data served from yahoo_direct (Tier 0)")
                cache.set(cache_key, result, CACHE_TTL_SECTOR)
                return result
    except Exception as e:
        logger.warning(f"yahoo_direct sector fetch failed: {e}")

    # Tier 3: yfinance fallback
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


def _fetch_single_sector(ticker: str, sector_name: str, yf_period: str, trim_days: int = 0, fds_days: int = 30) -> Optional[Dict]:
    """Fetch chart data for a single sector ETF. Uses yahoo_direct → FDS → yfinance cascade."""
    try:
        # Map yf_period to yahoo range string
        range_map = {"5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y"}
        range_str = range_map.get(yf_period, "1mo")

        # Tier 0: yahoo_direct (fastest)
        history = yd.get_history(ticker, range_str=range_str, interval="1d")

        # Tier 1: FDS fallback
        if not history and fds.is_available():
            try:
                from datetime import datetime as dt
                end_date = (dt.utcnow().date() - timedelta(days=1)).isoformat()
                start_date = (dt.utcnow().date() - timedelta(days=fds_days)).isoformat()
                history = fds.get_historical_prices(ticker, start=start_date, end=end_date)
            except Exception as e:
                logger.debug(f"FDS fetch failed for {ticker}: {e}")

        # Tier 3: yfinance last resort
        if not history:
            history = yf_svc.get_history(ticker, period=yf_period, interval="1d")

        if not history or len(history) < 2:
            logger.warning(f"No history data for {ticker}")
            return None

        # Trim to requested number of days if specified (e.g., 1D = last 2 days)
        if trim_days > 0 and len(history) > trim_days:
            history = history[-trim_days:]

        chart_data = [h.get("close", 0) for h in history]
        chart_dates = [h.get("date", h.get("time", "")) for h in history]

        # Get price + daily change from yahoo_direct quote
        quote = yd.get_quote(ticker) or {}

        # Compute daily change from chart data if quote is empty
        daily_pct_change = quote.get("pct_change", 0)
        if not daily_pct_change and len(chart_data) >= 2 and chart_data[-2] > 0:
            daily_pct_change = round((chart_data[-1] / chart_data[-2] - 1) * 100, 2)

        return {
            "ticker": ticker,
            "sector": sector_name,
            "price": quote.get("price", chart_data[-1] if chart_data else 0),
            "daily_change": quote.get("change", 0),
            "daily_pct_change": daily_pct_change,
            "chart_data": chart_data,
            "chart_dates": chart_dates,
        }
    except Exception as e:
        logger.warning(f"Error fetching sector chart data for {ticker}: {e}")
        return None


def get_sector_chart_data(period: str = "1M") -> Dict[str, Any]:
    """
    Get sector ETF chart data with actual prices and real dates.

    Uses FDS cascade for actual close prices with ISO dates instead of normalized values.
    Fetches all sector ETFs concurrently using ThreadPoolExecutor for speed.

    Args:
        period: Period for chart data ("1D", "5D", "1M", "3M")

    Returns:
        Dict with period and sectors list containing:
        - ticker, sector name, latest price, daily change
        - chart_data: actual close prices (not normalized)
        - chart_dates: ISO date strings (YYYY-MM-DD)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cache_key = f"sector_chart:{period}"

    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Sector chart data (period={period}) served from cache")
        return cached_result

    # Map period to yfinance period + optional trim + FDS lookback days
    period_config = {
        "1D": {"yf_period": "5d", "trim_days": 2, "fds_days": 5},       # Last 2 trading days, 5 days FDS lookback
        "5D": {"yf_period": "5d", "trim_days": 0, "fds_days": 10},      # Full 5 days, 10 days FDS lookback
        "1M": {"yf_period": "1mo", "trim_days": 0, "fds_days": 35},     # ~22 trading days, 35 days FDS lookback
        "3M": {"yf_period": "3mo", "trim_days": 0, "fds_days": 100},    # ~66 trading days, 100 days FDS lookback
    }
    config = period_config.get(period, {"yf_period": "1mo", "trim_days": 0, "fds_days": 30})
    yf_period = config["yf_period"]
    trim_days = config["trim_days"]
    fds_days = config.get("fds_days", 30)

    # Sector ETF mapping
    sector_etfs = {
        "XLK": "Information Technology",
        "XLV": "Healthcare",
        "XLF": "Financials",
        "XLY": "Consumer Discretionary",
        "XLP": "Consumer Staples",
        "XLE": "Energy",
        "XLRE": "Real Estate",
        "XLI": "Industrials",
        "XLU": "Utilities",
        "XLC": "Communication Services",
    }

    sectors = []

    # Fetch all sectors concurrently (5 workers to respect FDS rate limits)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_fetch_single_sector, ticker, name, yf_period, trim_days, fds_days): ticker
            for ticker, name in sector_etfs.items()
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                result = future.result(timeout=30)
                if result:
                    sectors.append(result)
                    logger.debug(f"Sector chart data for {ticker} retrieved: {len(result['chart_data'])} points")
            except Exception as e:
                logger.warning(f"Sector chart fetch timed out for {ticker}: {e}")

    # Sort by ticker for consistent ordering
    sectors.sort(key=lambda s: s["ticker"])

    result = {
        "period": period,
        "sectors": sectors,
    }

    if sectors:
        logger.info(f"Sector chart data (period={period}): {len(sectors)} sectors from FDS/yfinance cascade")
        cache.set(cache_key, result, CACHE_TTL_SECTOR)
        return result

    logger.warning(f"Could not fetch sector chart data for period {period}")
    return {"period": period, "sectors": []}


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
