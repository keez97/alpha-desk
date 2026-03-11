import logging
import time
import requests
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
CACHE_DURATION = 300  # 5 minutes in seconds

_cache = {
    "data": None,
    "timestamp": None
}


def _fetch_vix_central_data() -> Optional[Dict[str, Any]]:
    """
    Fetch VIX futures term structure data from VIX Central.
    Tries both the AJAX endpoint and scraping the main page.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Try AJAX endpoint first
    try:
        response = requests.get(
            "https://vixcentral.com/ajax_update",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        # Parse the response
        data = response.json()
        if data and isinstance(data, dict):
            logger.debug("Successfully fetched from VIX Central AJAX endpoint")
            return data
    except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
        logger.debug(f"AJAX endpoint failed: {e}. Trying main page scrape.")

    # Fall back to scraping the main page
    try:
        response = requests.get(
            "https://vixcentral.com/",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        html_content = response.text

        # Look for JSON data embedded in the page (common pattern)
        json_match = re.search(r'<script[^>]*>\s*var\s+data\s*=\s*(\{.*?\});\s*</script>',
                              html_content, re.DOTALL)
        if not json_match:
            # Try alternative pattern
            json_match = re.search(r'<script[^>]*>\s*var\s+chart_data\s*=\s*(\[.*?\]);\s*</script>',
                                  html_content, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(1))
                logger.debug("Successfully scraped JSON from VIX Central main page")
                return data
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse embedded JSON: {e}")

        # Try to extract data from table rows or script tags
        data = _parse_vix_central_html(html_content)
        if data:
            logger.debug("Successfully parsed VIX Central HTML structure")
            return data

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch from VIX Central main page: {e}")

    return None


def _parse_vix_central_html(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Parse the VIX Central HTML page to extract futures curve data.
    Looks for table rows or structured data in the HTML.
    """
    try:
        # Look for table rows with contract data
        # VIX Central typically shows contracts like VX1, VX2, etc.
        contract_pattern = r'<tr[^>]*>.*?<td[^>]*>([^<]*VX\d+[^<]*)</td>.*?<td[^>]*>(\d+\.?\d*)</td>'
        matches = re.findall(contract_pattern, html_content, re.DOTALL)

        if matches:
            futures_data = {}
            for month_str, price_str in matches:
                month = month_str.strip()
                try:
                    price = float(price_str.strip())
                    futures_data[month] = {"price": price}
                except ValueError:
                    continue

            if futures_data:
                return {"futures": futures_data}

        # Look for VIX spot price (often labeled as "VIX" or "Index")
        spot_pattern = r'(?:VIX|Index)[:\s]*(?:<[^>]*>)*\s*(\d+\.?\d*)'
        spot_match = re.search(spot_pattern, html_content, re.IGNORECASE)

        if spot_match:
            try:
                spot_price = float(spot_match.group(1))
                return {"spot": spot_price}
            except (ValueError, AttributeError):
                pass

    except Exception as e:
        logger.debug(f"Error parsing VIX Central HTML: {e}")

    return None


def _calculate_term_structure(vix_spot: float, futures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate term structure metrics from spot price and futures prices.
    """
    if not futures or len(futures) < 2:
        return {
            "spot_to_front_basis": None,
            "roll_yield_daily": None,
            "term_structure_state": None,
            "contango_magnitude_pct": None
        }

    front_month = futures[0]["price"]
    second_month = futures[1]["price"] if len(futures) > 1 else None

    # Spot to front month basis (percentage)
    spot_to_front_basis = ((front_month - vix_spot) / vix_spot * 100) if vix_spot > 0 else None

    # Roll yield calculation (annualized)
    # Using front-to-second-month spread as proxy for roll yield
    roll_yield_daily = None
    if second_month and front_month > 0:
        # Approximate days between contracts (typically 30 days)
        days_between = 30
        daily_spread = (second_month - front_month) / days_between
        roll_yield_daily = (daily_spread / front_month * 100 * 252)  # Annualize

    # Determine term structure state
    term_structure_state = None
    if front_month > vix_spot:
        term_structure_state = "contango"
    elif front_month < vix_spot:
        term_structure_state = "backwardation"

    # Contango magnitude
    contango_magnitude_pct = spot_to_front_basis if term_structure_state == "contango" else None

    return {
        "spot_to_front_basis": spot_to_front_basis,
        "roll_yield_daily": roll_yield_daily,
        "term_structure_state": term_structure_state,
        "contango_magnitude_pct": contango_magnitude_pct
    }


def _normalize_futures_data(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize raw data from VIX Central into standard format.
    """
    try:
        normalized = {}

        # Extract spot price
        if "spot" in raw_data:
            normalized["vix_spot"] = float(raw_data["spot"])
        elif "index" in raw_data:
            normalized["vix_spot"] = float(raw_data["index"])

        # Extract futures prices
        futures_list = []

        if "futures" in raw_data:
            futures_dict = raw_data["futures"]
            if isinstance(futures_dict, dict):
                for month, data in futures_dict.items():
                    if isinstance(data, dict) and "price" in data:
                        price = float(data["price"])
                    else:
                        price = float(data)

                    futures_list.append({
                        "month": month.upper(),
                        "price": price,
                        "days_to_expiry": None  # Would need additional data
                    })

        if futures_list:
            # Sort by contract month (VX1, VX2, etc.)
            futures_list.sort(key=lambda x: int(re.search(r'\d+', x['month']).group())
                            if re.search(r'\d+', x['month']) else float('inf'))
            normalized["futures"] = futures_list

        return normalized if normalized else None

    except (ValueError, KeyError, AttributeError) as e:
        logger.debug(f"Error normalizing VIX Central data: {e}")
        return None


def _build_response(vix_spot: float, futures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build the final response dictionary with all calculated metrics.
    """
    term_structure = _calculate_term_structure(vix_spot, futures)

    front_month = futures[0]["price"] if futures else None
    second_month = futures[1]["price"] if len(futures) > 1 else None

    response = {
        "vix_spot": vix_spot,
        "futures": futures,
        "front_month": front_month,
        "second_month": second_month,
        "spot_to_front_basis": term_structure["spot_to_front_basis"],
        "roll_yield_daily": term_structure["roll_yield_daily"],
        "term_structure_state": term_structure["term_structure_state"],
        "contango_magnitude_pct": term_structure["contango_magnitude_pct"],
        "data_source": "vix_central",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    return response


def fetch_vix_term_structure() -> Optional[Dict[str, Any]]:
    """
    Fetch and parse VIX futures term structure from VIX Central.
    Uses cache to avoid excessive requests.

    Returns:
        Dictionary with VIX spot price, futures prices, and calculated metrics,
        or None if fetch fails.
    """
    current_time = time.time()

    # Check cache validity
    if (_cache["data"] is not None and
        _cache["timestamp"] is not None and
        current_time - _cache["timestamp"] < CACHE_DURATION):
        logger.debug("Returning cached VIX Central data")
        return _cache["data"]

    # Fetch fresh data
    raw_data = _fetch_vix_central_data()
    if not raw_data:
        logger.warning("Failed to fetch VIX Central data")
        return None

    # Normalize the data
    normalized = _normalize_futures_data(raw_data)
    if not normalized or "vix_spot" not in normalized:
        logger.warning("Could not extract VIX spot price from VIX Central data")
        return None

    # Build response
    try:
        result = _build_response(
            vix_spot=normalized["vix_spot"],
            futures=normalized.get("futures", [])
        )

        # Cache the result
        _cache["data"] = result
        _cache["timestamp"] = current_time

        logger.info("Successfully fetched and cached VIX Central data")
        return result

    except (ValueError, KeyError) as e:
        logger.error(f"Error building response from VIX Central data: {e}")
        return None


def is_available() -> bool:
    """
    Check if we have recently cached VIX Central data.

    Returns:
        True if data was fetched within the cache duration, False otherwise.
    """
    if _cache["data"] is None or _cache["timestamp"] is None:
        return False

    current_time = time.time()
    return (current_time - _cache["timestamp"]) < CACHE_DURATION


def get_vix_spot() -> Optional[float]:
    """
    Get the current VIX spot price from cached data.

    Returns:
        VIX spot price as float, or None if not available.
    """
    if not is_available():
        # Try to fetch fresh data
        data = fetch_vix_term_structure()
        if not data:
            return None

    if _cache["data"] and "vix_spot" in _cache["data"]:
        return _cache["data"]["vix_spot"]

    return None


def get_term_structure() -> Optional[Dict[str, Any]]:
    """
    Get the full VIX futures term structure from cached data.

    Returns:
        Dictionary with term structure data, or None if not available.
    """
    if not is_available():
        # Try to fetch fresh data
        data = fetch_vix_term_structure()
        if not data:
            return None

    return _cache["data"]


def clear_cache() -> None:
    """
    Clear the cached data (useful for testing or forcing a refresh).
    """
    _cache["data"] = None
    _cache["timestamp"] = None
    logger.debug("VIX Central cache cleared")
