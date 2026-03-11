"""
CBOE CDN Options Data Service.

Fetches delayed options data from CBOE's public CDN endpoint.
Provides SPX options with full Greeks (delta, gamma, vega, theta, rho, IV).

No API key required. Data is delayed ~15 minutes during market hours.

Key features:
  • Full options chain for SPX (S&P 500 Index)
  • Complete Greeks: delta, gamma, vega, theta, rho
  • Implied volatility per strike
  • Bid/ask, volume, open interest
  • Derived metrics: IV skew, put-call ratio, GEX approximation
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import requests

from backend.services.cache import TTLCache

logger = logging.getLogger(__name__)

_cache = TTLCache()
_CACHE_TTL = 900  # 15 minutes (data is already delayed)

_CDN_BASE = "https://cdn.cboe.com/api/global/delayed_quotes/options"

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.cboe.com/",
})

# Track availability
_available = True
_last_failure = 0


def _fetch_options(symbol: str = "_SPX") -> Optional[Dict[str, Any]]:
    """
    Fetch full options chain from CBOE CDN.

    Args:
        symbol: CBOE symbol (e.g., "_SPX" for S&P 500, "_DJX" for Dow)

    Returns:
        Parsed JSON with 'data' array of options, or None on failure.
    """
    global _available, _last_failure

    cache_key = f"cboe_options:{symbol}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    # If recently failed, don't retry for 5 minutes
    if not _available and time.time() - _last_failure < 300:
        return None

    try:
        url = f"{_CDN_BASE}/{symbol}.json"
        resp = _session.get(url, timeout=15)

        if resp.status_code == 403:
            logger.warning("CBOE CDN returned 403 for %s — endpoint may be blocked", symbol)
            _available = False
            _last_failure = time.time()
            return None

        if resp.status_code != 200:
            logger.warning("CBOE CDN %s: HTTP %d", symbol, resp.status_code)
            _last_failure = time.time()
            return None

        data = resp.json()
        _available = True
        _cache.set(cache_key, data, _CACHE_TTL)
        logger.info("CBOE CDN: fetched %d options for %s", len(data.get("data", [])), symbol)
        return data

    except Exception as e:
        logger.warning("CBOE CDN fetch %s: %s", symbol, e)
        _last_failure = time.time()
        return None


# ---------------------------------------------------------------------------
# Parsed options data
# ---------------------------------------------------------------------------
def _parse_occ_symbol(symbol: str) -> Dict[str, Any]:
    """
    Parse OCC option symbol to extract expiry, type, and strike.

    Format: SPX260320C00200000
            ^^^       ^ ^^^^^^^^
            root  date C/P strike*1000

    SPX260320C00200000 → expiry=2026-03-20, type=Call, strike=200.0
    """
    try:
        # Find the C or P that separates date from strike
        # The symbol format is: ROOT + YYMMDD + C/P + strike*1000 (8 digits)
        # Work backwards: last 8 chars = strike, then C/P, then 6 chars = date
        if len(symbol) < 16:
            return {"expiration": "", "option_type": "", "strike": 0.0}

        strike_str = symbol[-8:]
        cp = symbol[-9]  # C or P
        date_str = symbol[-15:-9]  # YYMMDD

        strike = float(strike_str) / 1000.0
        option_type = "Call" if cp == "C" else "Put"

        # Parse date
        yy = int(date_str[:2])
        mm = int(date_str[2:4])
        dd = int(date_str[4:6])
        expiration = f"20{yy:02d}-{mm:02d}-{dd:02d}"

        return {"expiration": expiration, "option_type": option_type, "strike": strike}
    except Exception:
        return {"expiration": "", "option_type": "", "strike": 0.0}


def _parse_option(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a single CBOE option record into our format."""
    symbol = raw.get("option", "")
    parsed = _parse_occ_symbol(symbol)

    return {
        "symbol": symbol,
        "bid": _safe_float(raw.get("bid")),
        "ask": _safe_float(raw.get("ask")),
        "last": _safe_float(raw.get("last_trade_price")),
        "volume": _safe_int(raw.get("volume")),
        "open_interest": _safe_int(raw.get("open_interest")),
        "iv": _safe_float(raw.get("iv")),
        "delta": _safe_float(raw.get("delta")),
        "gamma": _safe_float(raw.get("gamma")),
        "vega": _safe_float(raw.get("vega")),
        "theta": _safe_float(raw.get("theta")),
        "rho": _safe_float(raw.get("rho")),
        "strike": parsed["strike"],
        "expiration": parsed["expiration"],
        "option_type": parsed["option_type"],
    }


def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(v) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def get_spx_options() -> Optional[List[Dict[str, Any]]]:
    """
    Get parsed SPX options chain.

    Returns list of option dicts with Greeks, or None if unavailable.
    """
    raw = _fetch_options("_SPX")
    if raw is None:
        return None

    # CBOE structure: data is a dict with 'options' key containing list of options
    data_obj = raw.get("data", {})
    if isinstance(data_obj, dict):
        options = data_obj.get("options", [])
    elif isinstance(data_obj, list):
        options = data_obj
    else:
        return None

    if not options:
        return None

    return [_parse_option(o) for o in options if isinstance(o, dict)]


def get_spx_spot_price() -> Optional[float]:
    """Get SPX current price from CBOE data."""
    raw = _fetch_options("_SPX")
    if raw is None:
        return None

    try:
        data_obj = raw.get("data", {})
        if isinstance(data_obj, dict):
            current_price = data_obj.get("current_price")
            if current_price:
                return float(current_price)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------
def get_options_metrics(expiry_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Calculate options flow metrics from CBOE SPX data.

    Args:
        expiry_filter: Optional expiry date (YYYY-MM-DD) to filter. If None, uses nearest.

    Returns dict with:
        iv_skew, put_call_ratio, total_call_volume, total_put_volume,
        total_call_oi, total_put_oi, gex_signal, gex_value,
        avg_call_iv, avg_put_iv, signal, details
    """
    options = get_spx_options()
    if options is None:
        return None

    # Filter to options with valid data
    valid = [o for o in options if o["iv"] > 0 and o["strike"] > 0]
    if not valid:
        return None

    # Find nearest expiry if not specified
    if expiry_filter is None:
        expirations = sorted(set(o["expiration"] for o in valid if o["expiration"]))
        if not expirations:
            return None
        expiry_filter = expirations[0]

    # Filter to target expiry
    chain = [o for o in valid if o["expiration"] == expiry_filter]
    if not chain:
        return None

    calls = [o for o in chain if o["option_type"].lower() == "call"]
    puts = [o for o in chain if o["option_type"].lower() == "put"]

    if not calls or not puts:
        return None

    # Get approximate spot price from mid-strike with highest OI
    all_strikes = sorted(set(o["strike"] for o in chain))
    if all_strikes:
        # Estimate spot from where call and put IV cross
        mid_idx = len(all_strikes) // 2
        spot_approx = all_strikes[mid_idx]
    else:
        spot_approx = 5000.0  # Default

    # Also try to get from CBOE data
    spot = get_spx_spot_price() or spot_approx

    # ---- IV Skew ----
    otm_calls = [o for o in calls if o["strike"] > spot * 1.02]
    otm_puts = [o for o in puts if o["strike"] < spot * 0.98]

    avg_call_iv = 0.0
    avg_put_iv = 0.0

    if otm_calls:
        # Use nearest 5 OTM calls
        nearest_otm_calls = sorted(otm_calls, key=lambda x: x["strike"])[:5]
        avg_call_iv = sum(o["iv"] for o in nearest_otm_calls) / len(nearest_otm_calls)

    if otm_puts:
        # Use nearest 5 OTM puts
        nearest_otm_puts = sorted(otm_puts, key=lambda x: -x["strike"])[:5]
        avg_put_iv = sum(o["iv"] for o in nearest_otm_puts) / len(nearest_otm_puts)

    iv_skew = 0.0
    if avg_call_iv > 0:
        iv_skew = max(-1.0, min(1.0, (avg_put_iv - avg_call_iv) / avg_call_iv))

    # ---- Volume metrics ----
    total_call_volume = sum(o["volume"] for o in calls)
    total_put_volume = sum(o["volume"] for o in puts)
    total_call_oi = sum(o["open_interest"] for o in calls)
    total_put_oi = sum(o["open_interest"] for o in puts)

    put_call_ratio = total_put_volume / max(total_call_volume, 1)
    volume_imbalance = total_call_volume / max(total_put_volume, 1)

    # ---- GEX from actual Greeks ----
    call_gex = sum(o["gamma"] * o["open_interest"] for o in calls)
    put_gex = sum(o["gamma"] * o["open_interest"] for o in puts)
    net_gex = (call_gex - put_gex) * spot * 100

    if net_gex > 100:
        gex_signal = "positive"
    elif net_gex < -100:
        gex_signal = "negative"
    else:
        gex_signal = "neutral"

    # ---- Overall signal ----
    details = []
    score = 0

    if put_call_ratio > 1.2:
        score -= 1
        details.append(f"Elevated put volume ({put_call_ratio:.2f}x ratio)")
    elif put_call_ratio < 0.8:
        score += 1
        details.append(f"Call-heavy volume ({1/put_call_ratio:.2f}x ratio)")

    if iv_skew > 0.2:
        score -= 1
        details.append(f"Put skew elevated (IV skew: {iv_skew:.2f})")
    elif iv_skew < -0.2:
        score += 1
        details.append(f"Call skew elevated (IV skew: {iv_skew:.2f})")

    if gex_signal == "positive":
        score += 1
        details.append(f"GEX positive ({net_gex:.0f}) — dealer hedging supports")
    elif gex_signal == "negative":
        score -= 1
        details.append(f"GEX negative ({net_gex:.0f}) — dealer hedging amplifies moves")

    if volume_imbalance > 1.2:
        score += 0.5
        details.append(f"Call dominance ({volume_imbalance:.2f}x)")

    if score > 1:
        signal = "bullish"
    elif score < -1:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticker": "SPX",
        "spot_price": spot,
        "iv_skew": round(iv_skew, 4),
        "avg_call_iv": round(avg_call_iv, 4),
        "avg_put_iv": round(avg_put_iv, 4),
        "put_call_ratio": round(put_call_ratio, 3),
        "volume_imbalance": round(volume_imbalance, 3),
        "gex_signal": gex_signal,
        "gex_value": round(net_gex, 1),
        "total_call_volume": total_call_volume,
        "total_put_volume": total_put_volume,
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "signal": signal,
        "details": details,
        "expiry": expiry_filter,
        "chain_size": len(chain),
        "data_source": "CBOE",
    }


def is_available() -> bool:
    """Check if CBOE CDN is currently accessible."""
    return _available or (time.time() - _last_failure >= 300)
