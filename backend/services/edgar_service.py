import logging
import time
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

TICKER_TO_CIK = {
    "AAPL": "0000320193", "MSFT": "0000789019", "GOOGL": "0001652044",
    "AMZN": "0001018724", "NVDA": "0001045810", "META": "0001326801",
    "TSLA": "0001318605", "JPM": "0000019617", "BAC": "0000070858",
    "GS": "0000886982", "UNH": "0000731766", "JNJ": "0000200406",
    "PG": "0000080424", "XOM": "0000034088", "HD": "0000354950",
}

SEC_HEADERS = {
    "User-Agent": "AlphaDesk Research contact@alphadesk.dev",
    "Accept-Encoding": "gzip, deflate"
}

CACHE_DURATION_SECONDS = 4 * 60 * 60
REQUEST_DELAY_SECONDS = 0.15
REQUEST_TIMEOUT_SECONDS = 10
SEC_SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

_earnings_cache: Dict[str, Any] = {}
_cache_timestamp: Optional[datetime] = None


def _is_cache_valid() -> bool:
    """Check if the cached earnings data is still valid."""
    if _cache_timestamp is None:
        return False

    elapsed = (datetime.now(timezone.utc) - _cache_timestamp).total_seconds()
    return elapsed < CACHE_DURATION_SECONDS


def _clear_cache():
    """Clear the earnings cache."""
    global _earnings_cache, _cache_timestamp
    _earnings_cache = {}
    _cache_timestamp = None


def _get_sec_submissions(cik: str) -> Optional[Dict[str, Any]]:
    """
    Fetch company submissions from SEC EDGAR.

    Args:
        cik: Padded CIK identifier

    Returns:
        Parsed JSON response or None on failure
    """
    try:
        url = SEC_SUBMISSIONS_BASE_URL.format(cik=cik)
        response = requests.get(
            url,
            headers=SEC_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch SEC submissions for CIK {cik}: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse SEC response for CIK {cik}: {str(e)}")
        return None


def _extract_earnings_date_from_submissions(submissions: Dict[str, Any]) -> Optional[str]:
    """
    Extract the most recent earnings date from SEC submissions data.

    Looks for 8-K filings with Item 2.02 (Results of Operations) which indicate earnings announcements.
    The SEC EDGAR `items` field contains comma-separated item codes like "2.02,9.01".

    Args:
        submissions: Parsed submissions JSON from SEC

    Returns:
        Most recent earnings date in YYYY-MM-DD format or None if not found
    """
    try:
        filings = submissions.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        items = filings.get("items", [])

        if not forms or not dates:
            return None

        latest_earnings_date = None

        for i, form in enumerate(forms):
            if form == "8-K" and i < len(dates):
                # Check the `items` field for "2.02" (Results of Operations)
                item_str = items[i] if i < len(items) else ""

                if "2.02" in item_str:
                    filing_date = dates[i]

                    if latest_earnings_date is None:
                        latest_earnings_date = filing_date
                    else:
                        if filing_date > latest_earnings_date:
                            latest_earnings_date = filing_date

        return latest_earnings_date
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parsing earnings date from submissions: {str(e)}")
        return None


def _estimate_next_earnings_date(last_earnings_date: str) -> str:
    """
    Estimate the next earnings date based on the last one.

    Assumes quarterly earnings (~90 days apart).

    Args:
        last_earnings_date: Most recent earnings date in YYYY-MM-DD format

    Returns:
        Estimated next earnings date in YYYY-MM-DD format
    """
    try:
        last_date = datetime.strptime(last_earnings_date, "%Y-%m-%d")
        next_date = last_date + timedelta(days=90)
        return next_date.strftime("%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Invalid date format for last earnings date: {str(e)}")
        return (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d")


def _calculate_days_until(target_date: str) -> int:
    """
    Calculate days until a target date.

    Args:
        target_date: Date in YYYY-MM-DD format

    Returns:
        Number of days until the target date (can be negative if in the past)
    """
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d")
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        target_utc = target.replace(tzinfo=timezone.utc)
        delta = (target_utc - today).days
        return delta
    except ValueError as e:
        logger.error(f"Invalid date format: {str(e)}")
        return 0


def get_earnings_dates(tickers: List[str]) -> Dict[str, dict]:
    """
    Fetch earnings dates for a list of tickers.

    Results are cached for 4 hours. Uses SEC EDGAR 8-K filings to identify
    the most recent earnings announcement date, then estimates the next one.

    Args:
        tickers: List of stock tickers (e.g., ["AAPL", "MSFT"])

    Returns:
        Dictionary mapping tickers to earnings date information:
        {
            "AAPL": {
                "ticker": "AAPL",
                "last_earnings_date": "2026-01-28",
                "estimated_next_earnings": "2026-04-28",
                "days_until_next": 48,
                "data_source": "sec_edgar",
                "filing_type": "8-K Item 2.02"
            },
            ...
        }
        Returns empty dict on failure.
    """
    global _earnings_cache, _cache_timestamp

    if not tickers:
        return {}

    if _is_cache_valid() and all(ticker in _earnings_cache for ticker in tickers):
        logger.debug("Returning cached earnings data")
        return {ticker: _earnings_cache[ticker] for ticker in tickers if ticker in _earnings_cache}

    results = {}
    valid_tickers = [t for t in tickers if t in TICKER_TO_CIK]

    if not valid_tickers:
        logger.warning(f"No valid tickers provided. Valid tickers: {list(TICKER_TO_CIK.keys())}")
        return {}

    for ticker in valid_tickers:
        cik = TICKER_TO_CIK[ticker]

        submissions = _get_sec_submissions(cik)

        if submissions is None:
            logger.warning(f"Failed to get submissions for {ticker}")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        last_earnings_date = _extract_earnings_date_from_submissions(submissions)

        if last_earnings_date:
            estimated_next = _estimate_next_earnings_date(last_earnings_date)
            days_until = _calculate_days_until(estimated_next)

            results[ticker] = {
                "ticker": ticker,
                "last_earnings_date": last_earnings_date,
                "estimated_next_earnings": estimated_next,
                "days_until_next": days_until,
                "data_source": "sec_edgar",
                "filing_type": "8-K Item 2.02"
            }
        else:
            logger.warning(f"Could not find earnings date for {ticker}")
            results[ticker] = {
                "ticker": ticker,
                "last_earnings_date": None,
                "estimated_next_earnings": None,
                "days_until_next": None,
                "data_source": "sec_edgar",
                "filing_type": "8-K Item 2.02"
            }

        time.sleep(REQUEST_DELAY_SECONDS)

    _earnings_cache = {**_earnings_cache, **results}
    _cache_timestamp = datetime.now(timezone.utc)

    return results


def get_upcoming_earnings(tickers: List[str], days_ahead: int = 14) -> List[dict]:
    """
    Get earnings dates within a specified window.

    Filters the results from get_earnings_dates to only include earnings
    that are coming up within the specified number of days.

    Args:
        tickers: List of stock tickers
        days_ahead: Number of days to look ahead (default: 14)

    Returns:
        List of earnings records with upcoming earnings dates, sorted by date.
        Returns empty list on failure.
    """
    if days_ahead < 0:
        logger.warning("days_ahead must be non-negative")
        return []

    earnings_data = get_earnings_dates(tickers)

    if not earnings_data:
        return []

    upcoming = []
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = today + timedelta(days=days_ahead)

    for ticker, data in earnings_data.items():
        if data.get("estimated_next_earnings") is None:
            continue

        try:
            next_earnings = datetime.strptime(
                data["estimated_next_earnings"],
                "%Y-%m-%d"
            ).replace(tzinfo=timezone.utc)

            if today <= next_earnings <= cutoff_date:
                upcoming.append(data)
        except ValueError as e:
            logger.error(f"Invalid date for {ticker}: {str(e)}")
            continue

    upcoming.sort(key=lambda x: x["estimated_next_earnings"])

    return upcoming


def is_available() -> bool:
    """
    Check if the SEC EDGAR service is available.

    Performs a simple connectivity test to the SEC EDGAR submissions endpoint.

    Returns:
        True if the service is reachable, False otherwise
    """
    try:
        test_cik = TICKER_TO_CIK["AAPL"]
        url = SEC_SUBMISSIONS_BASE_URL.format(cik=test_cik)

        response = requests.head(
            url,
            headers=SEC_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logger.error(f"SEC EDGAR service availability check failed: {str(e)}")
        return False
