"""
Extended financialdatasets.ai client for AlphaDesk.

Covers prices, earnings, metrics, and snapshots in addition to financial statements.
"""

import logging
import re
import time
import threading
from typing import Dict, List, Optional

import httpx

from backend.config import FDS_API_KEY

logger = logging.getLogger(__name__)

# Base configuration
BASE_URL = "https://api.financialdatasets.ai"
TIMEOUT = 15
MAX_RETRIES = 4
RETRY_BACKOFF = 1.0  # seconds

# Global rate limiter — max 1 request per 0.5 seconds
_rate_lock = threading.Lock()
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 0.5  # seconds between requests

# Track if we've already logged the "API key not available" warning
_API_KEY_WARNING_LOGGED = False


def is_available() -> bool:
    """Check if FDS API key is available."""
    return bool(FDS_API_KEY and FDS_API_KEY.strip())


def _get_headers() -> Dict[str, str]:
    """Get request headers with API key."""
    return {"X-API-KEY": FDS_API_KEY}


def _make_request(method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """
    Make HTTP request with retry logic and backoff.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (without base URL)
        params: Query parameters

    Returns:
        JSON response dict or None on failure
    """
    global _API_KEY_WARNING_LOGGED

    # Check if API key is available
    if not is_available():
        if not _API_KEY_WARNING_LOGGED:
            logger.warning("FDS_API_KEY not set or empty. FDS client will return empty results.")
            _API_KEY_WARNING_LOGGED = True
        return None

    url = f"{BASE_URL}{endpoint}"
    headers = _get_headers()

    for attempt in range(MAX_RETRIES):
        # Global rate limiting to avoid 429s
        global _last_request_time
        with _rate_lock:
            now = time.time()
            elapsed = now - _last_request_time
            if elapsed < _MIN_REQUEST_INTERVAL:
                time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
            _last_request_time = time.time()

        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=headers, params=params)
                else:
                    response = client.request(method, url, headers=headers, params=params)

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text

            # Handle 429 rate limiting — extract wait time from response
            if status == 429:
                wait_match = re.search(r"(\d+)\s*seconds?", body)
                wait_time = int(wait_match.group(1)) + 2 if wait_match else 30
                logger.warning(f"Rate limited on {endpoint}, waiting {wait_time}s")
                time.sleep(wait_time)
                continue

            # Don't retry 400 Bad Request (e.g. invalid date) — it won't change
            if status == 400:
                logger.error(f"Bad request on {method} {endpoint}: {body}")
                return None

            # Don't retry 402 Insufficient credits — won't resolve
            if status == 402:
                logger.error(f"Insufficient credits on {method} {endpoint}")
                return None

            logger.error(
                f"HTTP error on {method} {endpoint}: {status} - {body}"
            )
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF * (2 ** attempt)
                logger.debug(f"Retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                return None

        except httpx.RequestError as e:
            logger.error(f"Request error on {method} {endpoint}: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF * (2 ** attempt)
                logger.debug(f"Retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                return None

        except Exception as e:
            logger.error(f"Unexpected error on {method} {endpoint}: {e}")
            return None

    return None


def get_price_snapshot(ticker: str) -> Dict:
    """
    Get current price snapshot for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with keys: ticker, price, change, pct_change, volume, name
        Returns empty dict on failure
    """
    if not is_available():
        return {}

    try:
        endpoint = "/prices/snapshot"
        params = {"ticker": ticker}
        data = _make_request("GET", endpoint, params)

        if not data:
            return {}

        # API wraps in "snapshot" key
        snapshot = data.get("snapshot", data)

        # Map FDS response to standardized format (matching yfinance get_quote shape)
        result = {
            "ticker": ticker,
            "price": snapshot.get("price") or snapshot.get("last_price"),
            "change": snapshot.get("day_change") or snapshot.get("change"),
            "pct_change": snapshot.get("day_change_percent") or snapshot.get("pct_change"),
            "volume": snapshot.get("volume"),
            "name": snapshot.get("name"),
        }

        return result

    except Exception as e:
        logger.error(f"Error getting price snapshot for {ticker}: {e}")
        return {}


def get_historical_prices(
    ticker: str, start: str, end: str, interval: str = "day"
) -> List[Dict]:
    """
    Get historical price data for a ticker.

    Args:
        ticker: Stock ticker symbol
        start: Start date (YYYY-MM-DD format)
        end: End date (YYYY-MM-DD format)
        interval: Interval type (day, week, month, etc.)

    Returns:
        List of dicts with keys: date, open, high, low, close, volume
        Returns empty list on failure
    """
    if not is_available():
        return []

    try:
        endpoint = "/prices"
        params = {
            "ticker": ticker,
            "interval": interval,
            "start_date": start,
            "end_date": end,
        }
        data = _make_request("GET", endpoint, params)

        if not data:
            return []

        # Extract price records — API uses "prices" key
        records = data.get("prices", data.get("records", []))
        result = []

        for record in records:
            # API uses "time" field, normalize to "date"
            date_val = record.get("time", record.get("date", ""))
            if isinstance(date_val, str) and "T" in date_val:
                date_val = date_val.split("T")[0]

            result.append(
                {
                    "date": date_val,
                    "open": record.get("open"),
                    "high": record.get("high"),
                    "low": record.get("low"),
                    "close": record.get("close"),
                    "volume": record.get("volume"),
                }
            )

        return result

    except Exception as e:
        logger.error(f"Error getting historical prices for {ticker}: {e}")
        return []


def get_earnings(ticker: str, limit: int = 8) -> List[Dict]:
    """
    Get earnings history for a ticker.

    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of records to return

    Returns:
        List of earnings dicts
        Returns empty list on failure
    """
    if not is_available():
        return []

    try:
        endpoint = "/earnings"
        params = {"ticker": ticker, "limit": limit}
        data = _make_request("GET", endpoint, params)

        if not data:
            return []

        # Return earnings records
        records = data.get("records", [])
        return records if isinstance(records, list) else []

    except Exception as e:
        logger.error(f"Error getting earnings for {ticker}: {e}")
        return []


def get_financial_metrics(ticker: str) -> Dict:
    """
    Get financial metrics snapshot for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with fundamental metrics (PE, PB, etc.)
        Returns empty dict on failure
    """
    if not is_available():
        return {}

    try:
        endpoint = "/financial-metrics/snapshot"
        params = {"ticker": ticker}
        data = _make_request("GET", endpoint, params)

        if not data:
            return {}

        return data

    except Exception as e:
        logger.error(f"Error getting financial metrics for {ticker}: {e}")
        return {}


def get_analyst_estimates(ticker: str) -> Dict:
    """
    Get analyst consensus estimates for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with analyst consensus data
        Returns empty dict on failure
    """
    if not is_available():
        return {}

    try:
        endpoint = f"/analyst-estimates/{ticker}"
        data = _make_request("GET", endpoint)

        if not data:
            return {}

        return data

    except Exception as e:
        logger.error(f"Error getting analyst estimates for {ticker}: {e}")
        return {}
