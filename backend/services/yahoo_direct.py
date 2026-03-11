"""
Yahoo Finance v8 Direct API Service.

Bypasses the yfinance library entirely to avoid its aggressive rate-limiting.
Uses the public Yahoo Finance v8 chart API with proper headers.

Key advantages over yfinance:
  • No 120s cooldown from library-level rate detection
  • Single HTTP request per ticker (no .info overhead)
  • Custom session with proper User-Agent
  • Independent rate-limit tracking from yfinance_service

Provides:
  • Real-time/delayed quotes for stocks, ETFs, futures, indices
  • Historical OHLCV data (1d, 5d, 1mo, 3mo, 6mo, 1y)
  • Batch fetching with per-ticker error isolation
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import httpx

from backend.services.cache import TTLCache
from backend.services.circuit_breaker import get_breaker

logger = logging.getLogger(__name__)

_cache = TTLCache()
_CACHE_TTL_QUOTE = 300       # 5 min for quotes
_CACHE_TTL_HISTORY = 1800    # 30 min for history

_BASE_URLS = [
    "https://query2.finance.yahoo.com/v8/finance/chart",
    "https://query1.finance.yahoo.com/v8/finance/chart",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# Shared httpx client for connection pooling
_shared_client: Optional[httpx.Client] = None

def _get_client() -> httpx.Client:
    """Get or create shared httpx client."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.Client(
            timeout=10, follow_redirects=True, headers=_HEADERS,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _shared_client

# Crumb authentication state
_crumb: Optional[str] = None
_cookies: Optional[Dict[str, str]] = None
_crumb_fetch_time: float = 0
_CRUMB_TTL = 3600  # Refresh crumb every hour

# Independent rate-limit tracking
_rate_limited_until = 0
_consecutive_failures = 0
_state_lock = threading.Lock()


def _is_rate_limited() -> bool:
    with _state_lock:
        return time.time() < _rate_limited_until


def _mark_rate_limited(seconds: int = 60):
    global _rate_limited_until
    with _state_lock:
        _rate_limited_until = time.time() + seconds
        logger.warning("yahoo_direct: rate limited for %ds", seconds)


def _reset_failures():
    global _consecutive_failures
    with _state_lock:
        _consecutive_failures = 0


def _record_failure():
    global _consecutive_failures
    with _state_lock:
        _consecutive_failures += 1
        if _consecutive_failures >= 12:
            _mark_rate_limited(60)


def _get_crumb_and_cookies() -> tuple:
    """
    Get Yahoo Finance crumb token and session cookies.
    Required for authenticated API access (avoids 429s on some IPs).
    """
    global _crumb, _cookies, _crumb_fetch_time

    # Return cached crumb if still fresh
    if _crumb and _cookies and (time.time() - _crumb_fetch_time < _CRUMB_TTL):
        return _crumb, _cookies

    try:
        # Step 1: Get consent cookies by visiting Yahoo Finance
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            # First visit to get cookies
            resp = client.get(
                "https://fc.yahoo.com/",
                headers=_HEADERS,
            )
            cookies = dict(resp.cookies)

            # Step 2: Get crumb using the cookies
            resp2 = client.get(
                "https://query2.finance.yahoo.com/v1/test/getcrumb",
                headers=_HEADERS,
                cookies=cookies,
            )

            if resp2.status_code == 200 and resp2.text:
                _crumb = resp2.text.strip()
                _cookies = cookies
                _crumb_fetch_time = time.time()
                logger.info(f"Got Yahoo crumb: {_crumb[:8]}...")
                return _crumb, _cookies

    except Exception as e:
        logger.warning(f"Failed to get Yahoo crumb: {e}")

    return None, None


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------
def _fetch_chart(
    ticker: str,
    interval: str = "1d",
    range_str: str = "5d",
    timeout: int = 8,
) -> Optional[Dict[str, Any]]:
    """
    Fetch chart data from Yahoo Finance v8 API.

    Returns parsed JSON result dict or None on failure.
    """
    if _is_rate_limited():
        return None

    if not get_breaker("yahoo_direct").is_available():
        return None

    cache_key = f"yd_chart:{ticker}:{interval}:{range_str}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # Get crumb for authenticated requests
    crumb, cookies = _get_crumb_and_cookies()

    params = {"interval": interval, "range": range_str}
    if crumb:
        params["crumb"] = crumb

    # Try multiple base URLs (query2 first, then query1)
    all_429 = True
    for base_url in _BASE_URLS:
        try:
            url = f"{base_url}/{ticker}"
            client = _get_client()
            resp = client.get(url, params=params, cookies=cookies or {})

            if resp.status_code == 429:
                logger.warning("yahoo_direct %s: 429 from %s, trying next", ticker, base_url)
                continue  # Try next base URL before giving up
            all_429 = False
            if resp.status_code != 200:
                _record_failure()
                get_breaker("yahoo_direct").record_failure()
                logger.warning("yahoo_direct %s: HTTP %d from %s", ticker, resp.status_code, base_url)
                continue

            data = resp.json()
            chart = data.get("chart", {})
            result = chart.get("result")
            if not result:
                _record_failure()
                get_breaker("yahoo_direct").record_failure()
                continue

            _reset_failures()
            get_breaker("yahoo_direct").record_success()
            parsed = result[0]
            _cache.set(cache_key, parsed, _CACHE_TTL_QUOTE if range_str == "1d" else _CACHE_TTL_HISTORY)
            return parsed

        except httpx.TimeoutException:
            _record_failure()
            get_breaker("yahoo_direct").record_failure()
            logger.warning("yahoo_direct %s: timeout from %s", ticker, base_url)
            all_429 = False
            continue
        except Exception as e:
            _record_failure()
            get_breaker("yahoo_direct").record_failure()
            logger.warning("yahoo_direct %s: %s from %s", ticker, e, base_url)
            all_429 = False
            continue

    # All base URLs failed — mark rate limited if we got 429s from all
    if all_429:
        _mark_rate_limited(90)
    return None


# ---------------------------------------------------------------------------
# Public API: Quotes
# ---------------------------------------------------------------------------
def get_quote(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get latest quote for a ticker.

    Returns dict with: ticker, price, change, pct_change, open, high, low, volume, prev_close
    """
    chart = _fetch_chart(ticker, interval="1d", range_str="2d")
    if chart is None:
        return None

    try:
        meta = chart.get("meta", {})
        indicators = chart.get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]

        close_prices = quotes.get("close", [])
        open_prices = quotes.get("open", [])
        high_prices = quotes.get("high", [])
        low_prices = quotes.get("low", [])
        volumes = quotes.get("volume", [])

        # Filter out None values
        valid_closes = [c for c in close_prices if c is not None]
        if len(valid_closes) < 1:
            return None

        current_price = valid_closes[-1]
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if prev_close is None and len(valid_closes) >= 2:
            prev_close = valid_closes[-2]
        if prev_close is None:
            prev_close = current_price

        change = current_price - prev_close
        pct_change = (change / prev_close * 100) if prev_close else 0

        valid_opens = [o for o in open_prices if o is not None]
        valid_highs = [h for h in high_prices if h is not None]
        valid_lows = [l for l in low_prices if l is not None]
        valid_volumes = [v for v in volumes if v is not None]

        return {
            "ticker": ticker,
            "price": round(current_price, 4),
            "change": round(change, 4),
            "pct_change": round(pct_change, 3),
            "open": round(valid_opens[-1], 4) if valid_opens else current_price,
            "high": round(max(valid_highs[-2:]) if len(valid_highs) >= 2 else valid_highs[-1], 4) if valid_highs else current_price,
            "low": round(min(valid_lows[-2:]) if len(valid_lows) >= 2 else valid_lows[-1], 4) if valid_lows else current_price,
            "volume": valid_volumes[-1] if valid_volumes else 0,
            "prev_close": round(prev_close, 4),
            "data_source": "yahoo_direct",
        }
    except Exception as e:
        logger.warning("yahoo_direct quote parse %s: %s", ticker, e)
        return None


def get_history(
    ticker: str,
    range_str: str = "3mo",
    interval: str = "1d",
) -> List[Dict[str, Any]]:
    """
    Get historical OHLCV data.

    Returns list of dicts with: date, open, high, low, close, volume
    """
    chart = _fetch_chart(ticker, interval=interval, range_str=range_str)
    if chart is None:
        return []

    try:
        timestamps = chart.get("timestamp", [])
        indicators = chart.get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]

        closes = quotes.get("close", [])
        opens = quotes.get("open", [])
        highs = quotes.get("high", [])
        lows = quotes.get("low", [])
        volumes = quotes.get("volume", [])

        result = []
        for i, ts in enumerate(timestamps):
            c = closes[i] if i < len(closes) else None
            if c is None:
                continue
            result.append({
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "open": round(opens[i], 4) if i < len(opens) and opens[i] is not None else round(c, 4),
                "high": round(highs[i], 4) if i < len(highs) and highs[i] is not None else round(c, 4),
                "low": round(lows[i], 4) if i < len(lows) and lows[i] is not None else round(c, 4),
                "close": round(c, 4),
                "volume": volumes[i] if i < len(volumes) and volumes[i] is not None else 0,
            })
        return result
    except Exception as e:
        logger.warning("yahoo_direct history parse %s: %s", ticker, e)
        return []


def get_overnight_return(ticker: str) -> Optional[Dict[str, float]]:
    """
    Calculate overnight return: (today_open - yesterday_close) / yesterday_close.

    Returns dict with: overnight_pct, today_open, yesterday_close
    """
    chart = _fetch_chart(ticker, interval="1d", range_str="5d")
    if chart is None:
        return None

    try:
        indicators = chart.get("indicators", {})
        quotes = indicators.get("quote", [{}])[0]

        closes = [c for c in quotes.get("close", []) if c is not None]
        opens = [o for o in quotes.get("open", []) if o is not None]

        if len(closes) < 2 or len(opens) < 1:
            return None

        yesterday_close = closes[-2]
        today_open = opens[-1]

        if yesterday_close == 0:
            return None

        overnight_pct = (today_open - yesterday_close) / yesterday_close * 100

        return {
            "overnight_pct": round(overnight_pct, 4),
            "today_open": round(today_open, 4),
            "yesterday_close": round(yesterday_close, 4),
        }
    except Exception as e:
        logger.warning("yahoo_direct overnight %s: %s", ticker, e)
        return None


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------
def batch_quotes(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch quotes for multiple tickers concurrently. Returns dict keyed by ticker.
    Uses ThreadPoolExecutor for parallel fetching.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if _is_rate_limited():
        return {}

    if not get_breaker("yahoo_direct").is_available():
        return {}

    results = {}

    def _fetch_one(ticker: str):
        return ticker, get_quote(ticker)

    with ThreadPoolExecutor(max_workers=min(len(tickers), 8)) as executor:
        futures = {executor.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures, timeout=30):
            try:
                ticker, quote = future.result(timeout=15)
                if quote:
                    results[ticker] = quote
            except Exception as e:
                ticker = futures[future]
                logger.debug(f"batch_quotes failed for {ticker}: {e}")

    return results


def batch_overnight_returns(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch overnight returns for multiple tickers. Returns dict keyed by ticker.
    """
    results = {}
    for ticker in tickers:
        if _is_rate_limited():
            break
        ret = get_overnight_return(ticker)
        if ret:
            results[ticker] = ret
    return results


def is_available() -> bool:
    """Check if yahoo_direct is currently available (not rate-limited)."""
    return not _is_rate_limited()
