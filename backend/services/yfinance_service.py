import yfinance as yf
import pandas as pd
from functools import lru_cache
from typing import Dict, List, Any
import logging
import time
import threading
import requests
from backend.services import mock_data
from backend.services.circuit_breaker import get_breaker

logger = logging.getLogger(__name__)

# Flag to track if network is available
USE_MOCK = False

# Set a global timeout for yfinance requests
class _TimeoutHTTPAdapter(requests.adapters.HTTPAdapter):
    def send(self, *args, **kwargs):
        kwargs.setdefault("timeout", 8)
        return super().send(*args, **kwargs)

_yf_session = requests.Session()
_yf_session.headers.update({"User-Agent": "Mozilla/5.0 (AlphaDesk)"})
_yf_session.mount("https://", _TimeoutHTTPAdapter())
_yf_session.mount("http://", _TimeoutHTTPAdapter())


_rate_limited_until = 0  # Timestamp when rate limiting expires
_state_lock = threading.Lock()

def _retry_with_backoff(func, max_retries=1, initial_delay=0.5, backoff_factor=2.0):
    """Execute function with single attempt (no retries when rate-limited)."""
    global _rate_limited_until
    # If we recently got rate-limited, skip live calls entirely
    with _state_lock:
        if time.time() < _rate_limited_until:
            logger.debug("Skipping live call — still rate-limited, using mock")
            return None
    for attempt in range(max_retries):
        try:
            result = func()
            return result
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "too many requests" in error_str or "rate" in error_str:
                with _state_lock:
                    _rate_limited_until = time.time() + 60  # Back off for 1 minute (was 2 min)
                logger.warning(f"Rate limited by yfinance, backing off 60s: {e}")
                return None
            if attempt == max_retries - 1:
                logger.warning(f"Failed after {max_retries} attempts: {e}")
                return None
            time.sleep(initial_delay)


_consecutive_empty = 0  # Track consecutive empty results from yfinance

def get_quote(ticker: str) -> Dict[str, Any]:
    """Get stock quote including price, change, volume, and market cap."""
    global _rate_limited_until, _consecutive_empty
    with _state_lock:
        rate_limited = time.time() < _rate_limited_until
        consecutive_count = _consecutive_empty

    if rate_limited or consecutive_count >= 8:
        with _state_lock:
            if consecutive_count >= 8 and time.time() >= _rate_limited_until:
                _rate_limited_until = time.time() + 45
        if ticker in mock_data.MOCK_QUOTE_DATA:
            return mock_data.MOCK_QUOTE_DATA[ticker]
        return {}

    def _fetch():
        global _consecutive_empty, _rate_limited_until
        try:
            data = yf.Ticker(ticker, session=_yf_session)
            hist = data.history(period="1d")

            if hist.empty:
                with _state_lock:
                    _consecutive_empty += 1
                    empty_count = _consecutive_empty
                logger.warning(f"Empty hist for {ticker} (consecutive: {empty_count})")
                if empty_count >= 5:
                    with _state_lock:
                        _rate_limited_until = time.time() + 60
                    logger.warning("Multiple empty results — likely rate-limited, backing off 60s")
                get_breaker("yfinance").record_failure()
                if ticker in mock_data.MOCK_QUOTE_DATA:
                    return mock_data.MOCK_QUOTE_DATA[ticker]
                return {}

            with _state_lock:
                _consecutive_empty = 0  # Reset on success

            # Only call .info if history succeeded (avoids extra slow HTTP call on rate limit)
            try:
                info = data.info
            except Exception:
                info = {}

            current_price = info.get("currentPrice", hist["Close"].iloc[-1])
            prev_close = info.get("previousClose", current_price)
            change = current_price - prev_close
            pct_change = (change / prev_close * 100) if prev_close else 0

            get_breaker("yfinance").record_success()
            return {
                "ticker": ticker,
                "price": float(current_price),
                "change": float(change),
                "pct_change": float(pct_change),
                "volume": int(info.get("volume", 0)),
                "52w_high": float(info.get("fiftyTwoWeekHigh", 0)),
                "52w_low": float(info.get("fiftyTwoWeekLow", 0)),
                "market_cap": info.get("marketCap", 0),
                "name": info.get("longName", ticker),
                "sector": info.get("sector", ""),
            }
        except Exception as e:
            with _state_lock:
                _consecutive_empty += 1
                empty_count = _consecutive_empty
            if empty_count >= 5:
                with _state_lock:
                    _rate_limited_until = time.time() + 45
            get_breaker("yfinance").record_failure()
            logger.error(f"Error fetching quote for {ticker}: {e}")
            if ticker in mock_data.MOCK_QUOTE_DATA:
                logger.info(f"Using mock data for quote: {ticker}")
                return mock_data.MOCK_QUOTE_DATA[ticker]
            return {}

    return _retry_with_backoff(_fetch) or {}


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> List[Dict[str, Any]]:
    """Get historical price data."""
    def _fetch():
        try:
            data = yf.Ticker(ticker, session=_yf_session)
            hist = data.history(period=period, interval=interval)

            if hist.empty:
                get_breaker("yfinance").record_failure()
                return []

            result = []
            for date, row in hist.iterrows():
                result.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })
            get_breaker("yfinance").record_success()
            return result
        except Exception as e:
            get_breaker("yfinance").record_failure()
            logger.error(f"Error fetching history for {ticker}: {e}")
            # Return empty list for mock (history is complex to mock)
            logger.info(f"Using mock data (empty) for history: {ticker}")
            return []

    return _retry_with_backoff(_fetch) or []


def get_macro_data() -> Dict[str, Any]:
    """Fetch macro indicators: TNX, IRX, VIX, Dollar, Gold, Oil, BTC, SPY, QQQ, IWM."""
    global _rate_limited_until
    with _state_lock:
        if time.time() < _rate_limited_until:
            logger.info("Using mock macro data (rate-limited)")
            return mock_data.MOCK_MACRO_DATA

    def _fetch():
        try:
            tickers = ["^TNX", "^IRX", "^VIX", "DX-Y.NYB", "GC=F", "CL=F", "BTC-USD", "SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV"]
            result = {}
            consecutive_failures = 0

            for ticker in tickers:
                if consecutive_failures >= 5:
                    logger.warning("Too many consecutive failures, stopping live fetches")
                    with _state_lock:
                        _rate_limited_until = time.time() + 45
                    break
                try:
                    data = yf.Ticker(ticker, session=_yf_session)
                    hist = data.history(period="1d")

                    if hist.empty:
                        consecutive_failures += 1
                        continue

                    consecutive_failures = 0
                    current = hist["Close"].iloc[-1]
                    # Skip .info call — use hist data only for speed
                    prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else current
                    change = current - prev_close
                    pct_change = (change / prev_close * 100) if prev_close else 0

                    result[ticker] = {
                        "price": float(current),
                        "change": float(change),
                        "pct_change": float(pct_change),
                    }
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        with _state_lock:
                            _rate_limited_until = time.time() + 45
                        break
                    continue

            return result if result else None
        except Exception as e:
            logger.error(f"Error in get_macro_data: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched
    # Fall back to mock data
    logger.info("Using mock macro data")
    return mock_data.MOCK_MACRO_DATA


def get_sector_data(period: str = "1D") -> List[Dict[str, Any]]:
    """Fetch all 10 sector ETFs with price action and normalized chart data."""
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

    with _state_lock:
        if time.time() < _rate_limited_until:
            logger.info("Using mock sector data (rate-limited)")
            return mock_data.MOCK_SECTOR_DATA

    def _fetch():
        try:
            results = []
            period_map = {"1D": "1mo", "5D": "1mo", "1M": "3mo", "3M": "6mo", "1Y": "1y"}
            hist_period = period_map.get(period, "3mo")
            consecutive_failures = 0

            for ticker, sector_name in sector_etfs.items():
                if consecutive_failures >= 5:
                    logger.warning("Too many sector failures, stopping live fetches")
                    with _state_lock:
                        _rate_limited_until = time.time() + 45
                    break
                try:
                    data = yf.Ticker(ticker, session=_yf_session)
                    hist = data.history(period=hist_period)

                    if hist.empty:
                        consecutive_failures += 1
                        continue

                    consecutive_failures = 0
                    current_price = hist["Close"].iloc[-1]
                    # Use hist data for prev close instead of slow .info call
                    prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else current_price
                    daily_change = current_price - prev_close
                    daily_pct_change = (daily_change / prev_close * 100) if prev_close else 0

                    # Rebase chart to 100
                    first_price = hist["Close"].iloc[0]
                    normalized_prices = [(float(p) / first_price * 100) for p in hist["Close"]]

                    results.append({
                        "ticker": ticker,
                        "sector": sector_name,
                        "price": float(current_price),
                        "daily_change": float(daily_change),
                        "daily_pct_change": float(daily_pct_change),
                        "chart_data": normalized_prices,
                    })
                except Exception as e:
                    logger.error(f"Error fetching sector {ticker}: {e}")
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        with _state_lock:
                            _rate_limited_until = time.time() + 45
                        break
                    continue

            return results if results else None
        except Exception as e:
            logger.error(f"Error in get_sector_data: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched
    # Fall back to mock data
    logger.info("Using mock sector data")
    return mock_data.MOCK_SECTOR_DATA


def search_ticker(query: str) -> List[Dict[str, str]]:
    """Search for tickers matching query."""
    def _fetch():
        try:
            # yfinance doesn't have native search, so we'll return partial matches
            # In production, you'd use a dedicated API or database
            result = yf.Ticker(query, session=_yf_session)
            info = result.info

            if "longName" in info:
                return [{
                    "ticker": query.upper(),
                    "name": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                }]
            return None
        except Exception as e:
            logger.error(f"Error searching ticker {query}: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched

    # Try mock search results
    query_lower = query.lower()
    if query_lower in mock_data.MOCK_SEARCH_RESULTS:
        logger.info(f"Using mock search results for: {query}")
        return mock_data.MOCK_SEARCH_RESULTS[query_lower]

    return []


def get_stock_fundamentals(ticker: str) -> Dict[str, Any]:
    """Get comprehensive fundamental data for stock grading."""
    def _fetch():
        try:
            data = yf.Ticker(ticker, session=_yf_session)
            info = data.info

            # Get financials
            fundamentals = {
                "ticker": ticker,
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", None),
                "peg_ratio": info.get("pegRatio", None),
                "forward_pe": info.get("forwardPE", None),
                "price_to_book": info.get("priceToBook", None),
                "price_to_sales": info.get("priceToSalesTrailing12Months", None),
                "debt_to_equity": info.get("debtToEquity", None),
                "current_ratio": info.get("currentRatio", None),
                "quick_ratio": info.get("quickRatio", None),
                "beta": info.get("beta", None),
                "dividend_yield": info.get("dividendYield", None),
                "payout_ratio": info.get("payoutRatio", None),
                "short_interest": info.get("shortPercentOfFloat", None),
                "institutional_ownership": info.get("heldPercentInstitutions", None),
                "insider_ownership": info.get("heldPercentInsiders", None),
                "eps": info.get("trailingEps", None),
                "eps_growth": info.get("epsTrailingTwelveMonths", None),
                "revenue": info.get("totalRevenue", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "operating_cash_flow": info.get("operatingCashflow", 0),
                "free_cash_flow": info.get("freeCashflow", 0),
                "52w_high": info.get("fiftyTwoWeekHigh", None),
                "52w_low": info.get("fiftyTwoWeekLow", None),
                "50day_ma": info.get("fiftyDayAverage", None),
                "200day_ma": info.get("twoHundredDayAverage", None),
            }
            return fundamentals
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {e}")
            return None

    fetched = _retry_with_backoff(_fetch)
    if fetched:
        return fetched

    # Try mock fundamentals
    if ticker in mock_data.MOCK_FUNDAMENTALS:
        logger.info(f"Using mock fundamentals for: {ticker}")
        return mock_data.MOCK_FUNDAMENTALS[ticker]

    return {"ticker": ticker}
