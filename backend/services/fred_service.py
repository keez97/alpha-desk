"""
FRED (Federal Reserve Economic Data) Service.

Provides free, reliable, no-API-key daily data for:
  • VIX (VIXCLS)              – CBOE Volatility Index
  • VVIX (VXVCLS)             – VIX of VIX
  • 10Y Treasury (DGS10)      – 10-Year Treasury Constant Maturity Rate
  • 2Y Treasury (DGS2)        – 2-Year Treasury Constant Maturity Rate
  • 10Y-2Y Spread (T10Y2Y)    – Yield curve slope
  • 10Y-3M Spread (T10Y3M)    – Yield curve slope (recession indicator)
  • HY OAS (BAMLH0A0HYM2)     – ICE BofA US High Yield OAS
  • BBB Spread (BAMLC0A4CBBB)  – ICE BofA BBB Corporate Index OAS
  • USD Index (DTWEXBGS)       – Trade Weighted U.S. Dollar Index
  • WTI Crude (DCOILWTICO)     – Crude Oil Prices: WTI

Data is fetched via FRED's public CSV endpoint (no API key required),
cached for 2 hours, and provides both latest value and full history
for percentile/z-score calculations.
"""

import logging
import csv
from io import StringIO
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import requests

from backend.services.cache import TTLCache

logger = logging.getLogger(__name__)

_fred_cache = TTLCache()
_CACHE_TTL = 7200  # 2 hours (FRED updates daily after market close)

# ---------------------------------------------------------------------------
# Series definitions
# ---------------------------------------------------------------------------
FRED_SERIES: Dict[str, Dict[str, str]] = {
    "VIXCLS":        {"name": "VIX", "category": "volatility"},
    "VXVCLS":        {"name": "VVIX", "category": "volatility"},
    "DGS10":         {"name": "10Y Yield", "category": "rates"},
    "DGS2":          {"name": "2Y Yield", "category": "rates"},
    "T10Y2Y":        {"name": "10Y-2Y Spread", "category": "yield_curve"},
    "T10Y3M":        {"name": "10Y-3M Spread", "category": "yield_curve"},
    "BAMLH0A0HYM2":  {"name": "HY OAS Spread", "category": "credit"},
    "BAMLC0A4CBBB":  {"name": "BBB Spread", "category": "credit"},
    "DTWEXBGS":      {"name": "USD Index", "category": "fx"},
    "DCOILWTICO":    {"name": "WTI Crude", "category": "commodities"},
}

_FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def _fetch_series(series_id: str, lookback_days: int = 365) -> List[Tuple[str, float]]:
    """
    Fetch a single FRED series as [(date_str, value), ...].

    Uses the public CSV endpoint — no API key needed.
    Returns empty list on failure.
    """
    cache_key = f"fred_raw:{series_id}:{lookback_days}"
    cached = _fred_cache.get(cache_key)
    if cached is not None:
        return cached

    start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    try:
        url = f"{_FRED_CSV_BASE}?id={series_id}&cosd={start_date}"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "AlphaDesk/1.0"})
        resp.raise_for_status()

        rows: List[Tuple[str, float]] = []
        reader = csv.reader(StringIO(resp.text))
        next(reader, None)  # skip header

        for row in reader:
            if len(row) >= 2:
                date_str = row[0].strip()
                val_str = row[1].strip()
                if val_str and val_str != ".":
                    try:
                        rows.append((date_str, float(val_str)))
                    except ValueError:
                        continue

        logger.info("FRED %s: %d data points from %s", series_id, len(rows), start_date)
        _fred_cache.set(cache_key, rows, _CACHE_TTL)
        return rows

    except Exception as e:
        logger.warning("Failed to fetch FRED series %s: %s", series_id, e)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_latest(series_id: str) -> Optional[float]:
    """Get the latest value for a FRED series."""
    data = _fetch_series(series_id)
    if data:
        return data[-1][1]
    return None


def get_history(series_id: str, lookback_days: int = 365) -> List[Tuple[str, float]]:
    """Get full history as [(date, value), ...] tuples."""
    return _fetch_series(series_id, lookback_days)


def get_values_only(series_id: str, lookback_days: int = 365) -> List[float]:
    """Get just the values (no dates) for percentile/z-score calculations."""
    return [v for _, v in _fetch_series(series_id, lookback_days)]


def get_vix() -> Optional[float]:
    """Shorthand: get latest VIX close."""
    return get_latest("VIXCLS")


def get_vix_history(lookback_days: int = 365) -> List[float]:
    """Get VIX history as list of floats."""
    return get_values_only("VIXCLS", lookback_days)


def get_yield_curve_spread() -> Optional[float]:
    """Get 10Y-3M yield curve spread (recession indicator)."""
    return get_latest("T10Y3M")


def get_credit_spread() -> Optional[float]:
    """Get HY OAS credit spread."""
    return get_latest("BAMLH0A0HYM2")


def get_all_latest() -> Dict[str, Any]:
    """
    Fetch latest values for all tracked FRED series.

    Returns:
        {
            "VIXCLS": {"name": "VIX", "value": 25.50, "date": "2026-03-09", "category": "volatility"},
            ...
            "timestamp": "...",
            "series_count": 10,
        }
    """
    cache_key = "fred_all_latest"
    cached = _fred_cache.get(cache_key)
    if cached is not None:
        return cached

    result: Dict[str, Any] = {}

    for series_id, meta in FRED_SERIES.items():
        data = _fetch_series(series_id)
        if data:
            date_str, value = data[-1]
            result[series_id] = {
                "name": meta["name"],
                "value": value,
                "date": date_str,
                "category": meta["category"],
            }
        else:
            result[series_id] = {
                "name": meta["name"],
                "value": None,
                "date": None,
                "category": meta["category"],
            }

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["series_count"] = sum(1 for v in result.values() if isinstance(v, dict) and v.get("value") is not None)

    _fred_cache.set(cache_key, result, _CACHE_TTL)
    return result
