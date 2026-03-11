"""
CNN Fear & Greed Index Service for AlphaDesk.

Fetches the CNN Fear & Greed Index from their public dataviz API.
No authentication required. Provides overall score (0-100),
classification, historical comparisons, and 7 sub-indicators.

Endpoints:
  - /graphdata: Full response with sub-indicators as time series
  - /current: Compact response with just the main score
"""
import logging
import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 1800  # 30 minutes
}


def _get_classification(score: int) -> str:
    """Classify fear & greed score into human-readable label."""
    if score < 25:
        return "Extreme Fear"
    elif score < 45:
        return "Fear"
    elif score < 55:
        return "Neutral"
    elif score < 75:
        return "Greed"
    else:
        return "Extreme Greed"


def _extract_score_from_series(series_data) -> Optional[int]:
    """Extract the latest score from a CNN time-series sub-indicator.

    CNN sub-indicators are returned as objects with:
    {timestamp, score, rating, data: [{x, y, rating}, ...]}
    """
    try:
        if isinstance(series_data, dict):
            # Direct score field
            if "score" in series_data:
                return int(float(series_data["score"]))
            # Fallback: last data point in the time series
            if "data" in series_data and isinstance(series_data["data"], list):
                points = series_data["data"]
                if points:
                    last_point = points[-1]
                    if isinstance(last_point, dict) and "y" in last_point:
                        return int(float(last_point["y"]))
        elif isinstance(series_data, (int, float)):
            return int(float(series_data))
    except (ValueError, TypeError, IndexError):
        pass
    return None


def _parse_cnn_response(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse CNN Fear & Greed API response.

    The /graphdata endpoint returns:
      - fear_and_greed: {score, rating, timestamp, previous_close, previous_1_week, ...}
      - market_momentum_sp500, stock_price_strength, etc. (sub-indicators as time series)

    The /current endpoint returns the fear_and_greed fields directly at root level.
    """
    try:
        # Find the main fear_and_greed object
        if "fear_and_greed" in data:
            root = data["fear_and_greed"]
            full_response = data  # Keep reference for sub-indicators at top level
        else:
            root = data
            full_response = data

        # Extract current score
        current_score = None
        if "score" in root:
            current_score = int(float(root["score"]))
        elif "value" in root:
            current_score = int(float(root["value"]))

        if current_score is None:
            logger.warning("Could not extract current score from CNN API response")
            return None

        # Extract timestamp
        timestamp_str = root.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Extract historical data — CNN uses previous_1_week, previous_1_month, etc.
        previous_close = current_score
        one_week_ago = current_score
        one_month_ago = current_score
        one_year_ago = current_score

        if "previous_close" in root:
            previous_close = int(float(root["previous_close"]))
        if "previous_1_week" in root:
            one_week_ago = int(float(root["previous_1_week"]))
        if "previous_1_month" in root:
            one_month_ago = int(float(root["previous_1_month"]))
        if "previous_1_year" in root:
            one_year_ago = int(float(root["previous_1_year"]))

        # Extract sub-indicators from top-level keys in the /graphdata response
        # CNN provides these as time-series objects at the root of the response
        sub_indicators = {}

        indicator_map = {
            "market_momentum_sp500": "market_momentum",
            "market_momentum_sp125": "market_momentum_breadth",
            "stock_price_strength": "stock_price_strength",
            "stock_price_breadth": "stock_price_breadth",
            "put_call_options": "put_call_options",
            "market_volatility_vix": "market_volatility",
            "market_volatility_vix_50": "market_volatility_50d",
            "junk_bond_demand": "junk_bond_demand",
            "safe_haven_demand": "safe_haven_demand",
        }

        for cnn_key, clean_name in indicator_map.items():
            if cnn_key in full_response:
                score_val = _extract_score_from_series(full_response[cnn_key])
                if score_val is not None:
                    sub_indicators[clean_name] = {
                        "score": score_val,
                        "classification": _get_classification(score_val),
                    }

        # Determine trading signal
        if current_score > 55:
            signal = "bullish"
        elif current_score < 45:
            signal = "bearish"
        else:
            signal = "neutral"

        # Determine contrarian signal at extremes
        contrarian_signal = None
        if current_score > 80:
            contrarian_signal = "extreme_greed_warning"
        elif current_score < 20:
            contrarian_signal = "extreme_fear_opportunity"

        return {
            "score": current_score,
            "classification": _get_classification(current_score),
            "previous_close": previous_close,
            "one_week_ago": one_week_ago,
            "one_month_ago": one_month_ago,
            "one_year_ago": one_year_ago,
            "sub_indicators": sub_indicators,
            "signal": signal,
            "contrarian_signal": contrarian_signal,
            "data_source": "cnn_fear_greed",
            "timestamp": str(timestamp_str),
        }

    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing CNN Fear & Greed response: {e}")
        return None


def _fetch_from_cnn_api() -> Optional[Dict[str, Any]]:
    """Fetch Fear & Greed data from CNN API endpoints (graphdata first, then current)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
    }

    endpoints = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://production.dataviz.cnn.io/index/fearandgreed/current",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            parsed = _parse_cnn_response(data)
            if parsed:
                logger.info("Fear & Greed from %s: score=%d (%s)",
                            endpoint.split("/")[-1], parsed["score"], parsed["classification"])
                return parsed
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching from {endpoint}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error fetching from {endpoint}")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error from {endpoint}: {e}")
        except ValueError as e:
            logger.warning(f"JSON parse error from {endpoint}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching from {endpoint}: {e}")

    logger.error("Failed to fetch Fear & Greed data from all endpoints")
    return None


def get_fear_greed() -> Optional[Dict[str, Any]]:
    """
    Fetch the current CNN Fear & Greed Index with 30-minute caching.

    Returns dict with score, classification, historical, sub-indicators, signal.
    """
    if _cache["data"] is not None and _cache["timestamp"] is not None:
        elapsed = time.time() - _cache["timestamp"]
        if elapsed < _cache["ttl_seconds"]:
            return _cache["data"]

    data = _fetch_from_cnn_api()
    if data:
        _cache["data"] = data
        _cache["timestamp"] = time.time()

    return data


def get_score() -> Optional[int]:
    """Get the current Fear & Greed Index score (0-100)."""
    data = get_fear_greed()
    return data["score"] if data else None


def get_signal() -> str:
    """Get trading signal: 'bullish' (>55), 'bearish' (<45), or 'neutral'."""
    data = get_fear_greed()
    return data["signal"] if data else "neutral"


def is_available() -> bool:
    """Check if Fear & Greed data is available."""
    data = get_fear_greed()
    return data is not None


def clear_cache() -> None:
    """Clear the cached data (useful for testing or forcing a refresh)."""
    _cache["data"] = None
    _cache["timestamp"] = None
