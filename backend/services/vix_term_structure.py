"""
VIX Term Structure Intelligence for AlphaDesk.

Data source cascade:
  1. VIX Central (real futures curve, ~1 min refresh, no auth)
  2. FRED (reliable daily VIX close, no auth)
  3. yfinance (real-time when available, rate-limited)

Analyzes VIX spot vs VIX3M to determine contango/backwardation,
roll yield estimates, and VIX percentile ranking.
"""
import logging
import time
from typing import Dict, Any, List
import numpy as np

from backend.services import fred_service
from backend.services import vix_central_service
from backend.services import yfinance_service

logger = logging.getLogger(__name__)

_vix_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes
_HISTORY_WINDOW = 252  # 1 year for percentile calculation


def percentile_rank(data: List[float], score: float) -> float:
    """Calculate percentile rank of score in data."""
    try:
        rank = sum(1 for x in data if x <= score)
        return (rank / len(data)) * 100 if data else 50
    except Exception:
        return 50


def _build_from_vix_central() -> Dict[str, Any] | None:
    """
    Build VIX term structure from VIX Central real futures data.

    VIX Central provides actual VIX futures prices with ~1 min refresh,
    giving us the real futures curve instead of estimated VIX3M.
    """
    try:
        vc_data = vix_central_service.fetch_vix_term_structure()
        if not vc_data or not vc_data.get("vix_spot"):
            return None

        vix_spot = vc_data["vix_spot"]
        front_month = vc_data.get("front_month")
        second_month = vc_data.get("second_month")

        if not front_month or front_month <= 0 or vix_spot <= 0:
            return None

        # Use front month as proxy for VIX3M when we have real futures
        # (front month is typically 15-45 days out)
        vix3m = second_month if second_month else front_month

        ratio = vix_spot / vix3m
        state = "contango" if ratio < 1.0 else "backwardation"
        magnitude = abs(ratio - 1.0) * 100

        # Roll yield from the actual futures spread
        roll_yield = vc_data.get("roll_yield_daily", 0) or 0
        if roll_yield == 0 and second_month and front_month > 0:
            roll_yield = (second_month - front_month) / front_month / 30  # ~30 days between contracts

        # Get VIX percentile from FRED history (more reliable than VIX Central for history)
        vix_history_raw = fred_service.get_history("VIXCLS", lookback_days=365)
        vix_values = [v for _, v in vix_history_raw] if vix_history_raw else []
        pct = percentile_rank(vix_values, vix_spot) if len(vix_values) >= 50 else 50

        # Signal
        if state == "contango" and magnitude > 1.5:
            signal = "bullish"
        elif state == "backwardation" and magnitude > 1.5:
            signal = "bearish"
        else:
            signal = "neutral"

        # Build futures curve for display
        futures_curve = []
        for f in vc_data.get("futures", []):
            futures_curve.append({
                "month": f.get("month", ""),
                "price": f.get("price", 0),
                "days_to_expiry": f.get("days_to_expiry"),
            })

        # Use FRED history for chart data (VIX Central doesn't have history)
        history = []
        if vix_history_raw:
            recent = vix_history_raw[-30:] if len(vix_history_raw) >= 30 else vix_history_raw
            for date_str, vix_val in recent:
                approx_ratio = vix_val / vix3m
                history.append({
                    "date": date_str,
                    "ratio": round(approx_ratio, 3),
                    "vix": round(vix_val, 2),
                })

        return {
            "vix_spot": round(vix_spot, 2),
            "vix3m": round(vix3m, 2),
            "ratio": round(ratio, 4),
            "state": state,
            "magnitude": round(magnitude, 2),
            "percentile": int(pct),
            "roll_yield": round(roll_yield, 6),
            "signal": signal,
            "data_source": "vix_central",
            "futures_curve": futures_curve,
            "spot_to_front_basis": vc_data.get("spot_to_front_basis"),
            "history": history,
        }

    except Exception as e:
        logger.error("Error building VIX term structure from VIX Central: %s", e)
        return None


def _build_from_fred() -> Dict[str, Any] | None:
    """
    Build VIX term structure from FRED data.

    FRED provides daily VIX close (VIXCLS) with 1-year history.
    VIX3M isn't on FRED, so we estimate it from VIX history
    (typical contango is ~2% above spot in normal conditions).
    """
    try:
        # Get VIX history (1 year)
        vix_history_raw = fred_service.get_history("VIXCLS", lookback_days=365)
        if not vix_history_raw or len(vix_history_raw) < 20:
            return None

        vix_values = [v for _, v in vix_history_raw]
        vix_spot = vix_values[-1]

        if vix_spot <= 0:
            return None

        # Estimate VIX3M: use 20-day moving average as a proxy
        # (VIX3M tends to track the medium-term average of VIX)
        ma_20 = np.mean(vix_values[-20:])
        # In contango, VIX3M is typically 1-5% above spot
        # Use the relationship: VIX3M ≈ max(VIX * 1.02, MA20)
        vix3m_estimate = max(vix_spot * 1.02, ma_20)

        # Calculate metrics
        ratio = vix_spot / vix3m_estimate
        state = "contango" if ratio < 1.0 else "backwardation"
        magnitude = abs(ratio - 1.0) * 100

        # VIX percentile against 1-year history
        pct = percentile_rank(vix_values, vix_spot) if len(vix_values) >= 50 else 50

        # Roll yield estimate (daily)
        roll_yield = (vix3m_estimate - vix_spot) / vix_spot / 252 if vix_spot > 0 else 0

        # Signal
        if state == "contango" and magnitude > 1.5:
            signal = "bullish"
        elif state == "backwardation" and magnitude > 1.5:
            signal = "bearish"
        else:
            signal = "neutral"

        # Build 30-day history with dates
        history = []
        recent = vix_history_raw[-30:] if len(vix_history_raw) >= 30 else vix_history_raw
        for date_str, vix_val in recent:
            approx_ratio = vix_val / vix3m_estimate
            history.append({
                "date": date_str,
                "ratio": round(approx_ratio, 3),
                "vix": round(vix_val, 2),
            })

        return {
            "vix_spot": round(vix_spot, 2),
            "vix3m": round(vix3m_estimate, 2),
            "ratio": round(ratio, 4),
            "state": state,
            "magnitude": round(magnitude, 2),
            "percentile": int(pct),
            "roll_yield": round(roll_yield, 6),
            "signal": signal,
            "data_source": "FRED",
            "history": history,
        }

    except Exception as e:
        logger.error("Error building VIX term structure from FRED: %s", e)
        return None


def _build_from_yfinance() -> Dict[str, Any] | None:
    """Fallback: try yfinance for real-time VIX data."""
    if time.time() < yfinance_service._rate_limited_until:
        return None

    try:
        import yfinance as yf

        vix_ticker = yf.Ticker("^VIX")
        vix_hist = vix_ticker.history(period="1y", interval="1d")

        if vix_hist.empty:
            return None

        vix_spot = float(vix_hist["Close"].iloc[-1])
        vix_values = vix_hist["Close"].tolist()

        # Try VIX3M
        vix3m_ticker = yf.Ticker("^VIX3M")
        vix3m_hist = vix3m_ticker.history(period="1d")
        vix3m = float(vix3m_hist["Close"].iloc[-1]) if not vix3m_hist.empty else vix_spot * 1.02

        if vix3m <= 0 or vix_spot <= 0:
            return None

        ratio = vix_spot / vix3m
        state = "contango" if ratio < 1.0 else "backwardation"
        magnitude = abs(ratio - 1.0) * 100
        pct = percentile_rank(vix_values, vix_spot) if len(vix_values) >= _HISTORY_WINDOW else 50
        roll_yield = (vix3m - vix_spot) / vix_spot / 252 if vix_spot > 0 else 0

        if state == "contango" and magnitude > 1.5:
            signal = "bullish"
        elif state == "backwardation" and magnitude > 1.5:
            signal = "bearish"
        else:
            signal = "neutral"

        history = []
        dates = vix_hist.index[-30:]
        for i, dt in enumerate(dates):
            vix_val = float(vix_hist["Close"].iloc[-(30 - i)])
            history.append({
                "date": dt.strftime("%Y-%m-%d"),
                "ratio": round(vix_val / vix3m, 3),
                "vix": round(vix_val, 2),
            })

        return {
            "vix_spot": round(vix_spot, 2),
            "vix3m": round(vix3m, 2),
            "ratio": round(ratio, 4),
            "state": state,
            "magnitude": round(magnitude, 2),
            "percentile": int(pct),
            "roll_yield": round(roll_yield, 6),
            "signal": signal,
            "data_source": "yfinance",
            "history": history,
        }
    except Exception as e:
        logger.error("Error fetching VIX from yfinance: %s", e)
        return None


def get_vix_term_structure() -> Dict[str, Any]:
    """
    Get VIX term structure with cascading data sources:
    1. VIX Central (real futures curve, ~1 min refresh)
    2. FRED (reliable, daily VIX close)
    3. yfinance (real-time when available)
    """
    now = time.time()
    if "vix_term" in _vix_cache:
        cached = _vix_cache["vix_term"]
        if now - cached["ts"] < _CACHE_TTL:
            return cached["data"]

    # Tier 1: VIX Central (real futures data)
    result = _build_from_vix_central()
    if result:
        logger.info("VIX term structure from VIX Central: spot=%.2f, state=%s", result["vix_spot"], result["state"])
        _vix_cache["vix_term"] = {"ts": now, "data": result}
        return result

    # Tier 2: FRED (reliable daily)
    result = _build_from_fred()
    if result:
        logger.info("VIX term structure from FRED: spot=%.2f, state=%s", result["vix_spot"], result["state"])
        _vix_cache["vix_term"] = {"ts": now, "data": result}
        return result

    # Tier 3: yfinance
    result = _build_from_yfinance()
    if result:
        logger.info("VIX term structure from yfinance: spot=%.2f, state=%s", result["vix_spot"], result["state"])
        _vix_cache["vix_term"] = {"ts": now, "data": result}
        return result

    # All sources failed — return minimal honest response
    logger.warning("All VIX term structure sources failed")
    return {
        "vix_spot": 0,
        "vix3m": 0,
        "ratio": 1.0,
        "state": "unknown",
        "magnitude": 0,
        "percentile": 50,
        "roll_yield": 0,
        "signal": "neutral",
        "data_source": "none",
        "history": [],
        "note": "All data sources unavailable",
    }
