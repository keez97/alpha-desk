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
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import httpx

from backend.services.cache import TTLCache

logger = logging.getLogger(__name__)

_cache = TTLCache()
_CACHE_TTL_QUOTE = 300       # 5 min for quotes
_CACHE_TTL_HISTORY = 1800    # 30 min for history

_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

# Independent rate-limit tracking
_rate_limited_until = 0
_consecutive_failures = 0


def _is_rate_limited() -> bool:
    return time.time() < _rate_limited_until


def _mark_rate_limited(seconds: int = 60):
    global _rate_limited_until
    _rate_limited_until = time.time() + seconds
    logger.warning("yahoo_direct: rate limited for %ds", seconds)


def _reset_failures():
    global _consecutive_failures
    _consecutive_failures = 0


def _record_failure():
    global _consecutive_failures
    _consecutive_failures += 1
    if _consecutive_failures >= 8:
        _mark_rate_limited(60)


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

    cache_key = f"yd_chart:{ticker}:{interval}:{range_str}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        url = f"{_BASE_URL}/{ticker}"
        params = {"interval": interval, "range": range_str}

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=_HEADERS, params=params)

        if resp.status_code == 429:
            _mark_rate_limited(120)
            return None
        if resp.status_code != 200:
            _record_failure()
            logger.warning("yahoo_direct %s: HTTP %d", ticker, resp.status_code)
            return None

        data = resp.json()
        chart = data.get("chart", {})
        result = chart.get("result")
        if not result:
            _record_failure()
            return None

        _reset_failures()
        parsed = result[0]
        _cache.set(cache_key, parsed, _CACHE_TTL_QUOTE if range_str == "1d" else _CACHE_TTL_HISTORY)
        return parsed

    except httpx.TimeoutException:
        _record_failure()
        logger.warning("yahoo_direct %s: timeout", ticker)
        return None
    except Exception as e:
        _record_failure()
        logger.warning("yahoo_direct %s: %s", ticker, e)
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
