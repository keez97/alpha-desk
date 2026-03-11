"""
FRED (Federal Reserve Economic Data) API client for AlphaDesk.

Provides methods to fetch economic data series from the Federal Reserve Economic Data API.
"""

import logging
import time
from typing import Dict, List, Optional, Any

import httpx

from backend.config import FRED_API_KEY

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds


def _make_request(
    series_id: str,
    observation_start: Optional[str] = None,
    limit: int = 30,
    sort_order: str = "desc",
) -> Optional[Dict[str, Any]]:
    """
    Make a request to the FRED API with retry logic and backoff.

    Args:
        series_id: FRED series ID (e.g., "DGS10")
        observation_start: Optional start date in YYYY-MM-DD format
        limit: Number of observations to retrieve (default 30)
        sort_order: Sort order for observations (default "desc")

    Returns:
        Parsed JSON response as dict, or None if request fails
    """
    params = {
        "api_key": FRED_API_KEY,
        "series_id": series_id,
        "file_type": "json",
        "limit": limit,
        "sort_order": sort_order,
    }

    if observation_start:
        params["observation_start"] = observation_start

    retry_delay = INITIAL_RETRY_DELAY

    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client() as client:
                response = client.get(FRED_BASE_URL, params=params, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching {series_id} (attempt {attempt + 1}/{MAX_RETRIES}): {e.status_code}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
        except httpx.RequestError as e:
            logger.error(
                f"Request error fetching {series_id} (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
        except Exception as e:
            logger.error(f"Unexpected error fetching {series_id}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(retry_delay)
                retry_delay *= 2

    logger.error(f"Failed to fetch {series_id} after {MAX_RETRIES} attempts")
    return None


def _parse_observations(data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse FRED API response observations.

    Args:
        data: Response dict from FRED API

    Returns:
        List of dicts with 'date' and 'value' fields (value is float or None)
    """
    if not data or "observations" not in data:
        return []

    observations = []
    for obs in data.get("observations", []):
        try:
            value_str = obs.get("value", ".")
            # FRED uses "." to represent missing data
            value = None if value_str == "." else float(value_str)
            observations.append(
                {
                    "date": obs.get("date"),
                    "value": value,
                }
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse observation: {obs}, error: {e}")
            continue

    return observations


def get_series(series_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch a generic FRED data series.

    Args:
        series_id: FRED series ID
        limit: Number of observations to retrieve (default 30)

    Returns:
        List of dicts with 'date' and 'value' fields
    """
    data = _make_request(series_id, limit=limit)
    return _parse_observations(data)


def get_treasury_10y() -> List[Dict[str, Any]]:
    """
    Fetch 10-Year Treasury yield data (DGS10).

    Returns:
        List of observations with date and value
    """
    return get_series("DGS10")


def get_treasury_3m() -> List[Dict[str, Any]]:
    """
    Fetch 3-Month Treasury yield data (DTB3).

    Returns:
        List of observations with date and value
    """
    return get_series("DTB3")


def get_vix() -> List[Dict[str, Any]]:
    """
    Fetch VIX (Volatility Index) data (VIXCLS).

    Returns:
        List of observations with date and value
    """
    return get_series("VIXCLS")


def get_dollar_index() -> List[Dict[str, Any]]:
    """
    Fetch Trade Weighted Dollar Index data (DTWEXBGS).

    Returns:
        List of observations with date and value
    """
    return get_series("DTWEXBGS")


def get_crude_oil() -> List[Dict[str, Any]]:
    """
    Fetch WTI Crude Oil price data (DCOILWTICO).

    Returns:
        List of observations with date and value
    """
    return get_series("DCOILWTICO")


def get_yield_curve() -> List[Dict[str, Any]]:
    """
    Fetch 10Y-2Y Treasury spread data (T10Y2Y).

    Returns:
        List of observations with date and value
    """
    return get_series("T10Y2Y")


def get_credit_spread() -> List[Dict[str, Any]]:
    """
    Fetch Baa-10Y Credit spread data (BAA10Y).

    Returns:
        List of observations with date and value
    """
    return get_series("BAA10Y")


def get_fed_funds() -> List[Dict[str, Any]]:
    """
    Fetch Federal Funds Rate data (FEDFUNDS).

    Returns:
        List of observations with date and value
    """
    return get_series("FEDFUNDS")


def get_macro_snapshot() -> Dict[str, Dict[str, Any]]:
    """
    Fetch the latest value for all key economic series.

    Returns:
        Dict with series_id as key and dict of {value, date} as value.
        Example: {"DGS10": {"value": 4.25, "date": "2026-03-10"}, ...}
        Missing or failed series are omitted from the result.
    """
    series_ids = [
        "DGS10",       # 10-Year Treasury
        "DTB3",        # 3-Month Treasury
        "VIXCLS",      # VIX
        "DTWEXBGS",    # Dollar Index
        "DCOILWTICO",  # Crude Oil
        "T10Y2Y",      # Yield Curve (10Y-2Y)
        "BAA10Y",      # Credit Spread (Baa-10Y)
        "FEDFUNDS",    # Federal Funds Rate
    ]

    snapshot = {}

    for series_id in series_ids:
        try:
            observations = get_series(series_id, limit=2)
            if observations and observations[0]["value"] is not None:
                current = observations[0]["value"]
                entry = {
                    "value": current,
                    "date": observations[0]["date"],
                }
                # Calculate change from previous observation if available
                if len(observations) >= 2 and observations[1]["value"] is not None:
                    prev = observations[1]["value"]
                    entry["change"] = round(current - prev, 4)
                    if prev != 0:
                        entry["pct_change"] = round((current - prev) / abs(prev) * 100, 4)
                    else:
                        entry["pct_change"] = 0.0
                snapshot[series_id] = entry
            else:
                logger.warning(f"No valid data returned for {series_id}")
        except Exception as e:
            logger.error(f"Error fetching snapshot for {series_id}: {e}")
            continue

    return snapshot
