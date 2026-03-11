"""
Sector Transitions Service for AlphaDesk.
Detects quadrant transitions, factor decomposition, and business cycle overlay.

Data source cascade for price history:
  1. financialdatasets.ai (FDS) — reliable, paid API
  2. yfinance — fallback, rate-limited
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from backend.services import fds_client as fds
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.regime_detector import detect_regime
from backend.services.yfinance_service import get_history, get_macro_data

logger = logging.getLogger(__name__)

_transitions_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes


def get_previous_rrg_data() -> Dict[str, Any]:
    """
    Get RRG data from one week ago to detect quadrant transitions.
    Since we don't have historical RRG data stored, we'll calculate current
    and use heuristics based on recent trail movement.
    """
    try:
        current_rrg = calculate_rrg(list(SECTOR_ETFS.keys()), benchmark="SPY", weeks=10)
        if not current_rrg or "error" in current_rrg:
            return {}
        return current_rrg
    except Exception as e:
        logger.error(f"Error getting previous RRG: {e}")
        return {}


def detect_quadrant_transitions() -> List[Dict[str, Any]]:
    """
    Detect recent quadrant transitions for each sector.
    Compares current quadrant vs. quadrant from ~5 days ago based on trail.
    """
    try:
        rrg_data = calculate_rrg(list(SECTOR_ETFS.keys()), benchmark="SPY", weeks=10)
        if not rrg_data or "error" in rrg_data:
            return []

        transitions = []
        sectors = rrg_data.get("sectors", [])

        for sector in sectors:
            ticker = sector.get("ticker")
            trail = sector.get("trail", [])
            current_quadrant = sector.get("quadrant", "Unknown")

            if len(trail) < 6:  # Need at least 6 points to detect transition
                continue

            # Check quadrant from 5 days ago (assuming weekly data)
            previous_quadrant = None
            for pt in reversed(trail[:-1]):  # Skip the current point
                from backend.services.rrg_calculator import determine_quadrant
                prev_q = determine_quadrant(pt["rs_ratio"], pt["rs_momentum"])
                if prev_q != current_quadrant:
                    previous_quadrant = prev_q
                    break

            if previous_quadrant and previous_quadrant != current_quadrant:
                # Calculate significance based on tail length and momentum magnitude
                rs_momentum = sector.get("rs_momentum", 0)
                tail_length = sector.get("tail_length", 0)
                significance = min(100, abs(rs_momentum) * 2 + tail_length)

                transitions.append({
                    "ticker": ticker,
                    "name": SECTOR_ETFS.get(ticker, ticker),
                    "from_quadrant": previous_quadrant,
                    "to_quadrant": current_quadrant,
                    "transition_date": trail[-1].get("date", "Unknown"),
                    "significance": round(significance, 1),
                })

        return transitions
    except Exception as e:
        logger.error(f"Error detecting quadrant transitions: {e}")
        return []


def _get_history_cascade(ticker: str, days: int = 365) -> List[Dict]:
    """Fetch price history using FDS → yfinance cascade."""
    if fds.is_available():
        try:
            end_date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            start_date = (datetime.utcnow().date() - timedelta(days=days)).isoformat()
            records = fds.get_historical_prices(ticker, start_date, end_date)
            if records and len(records) >= 20:
                return records
        except Exception as e:
            logger.debug(f"FDS history {ticker}: {e}")
    hist = get_history(ticker, period="1y")
    return hist if hist else []


def _factor_label(name: str, value: float) -> str:
    """Generate human-readable label for factor value."""
    if name == "beta":
        if value < -5:
            return "Very Defensive"
        if value < -1:
            return "Defensive"
        if value < 1:
            return "Neutral"
        if value < 5:
            return "Moderate"
        return "High Beta"
    elif name == "momentum":
        if value > 3:
            return "Strong Uptrend"
        if value > 0:
            return "Positive"
        if value > -3:
            return "Negative"
        return "Strong Downtrend"
    elif name == "value":
        return "Value Tilt" if value > 0 else "Growth Tilt"
    elif name == "size":
        return "Small Cap Tilt" if value > 0 else "Large Cap Tilt"
    return "Neutral"


def _empty_factors() -> Dict[str, Any]:
    """Return zero-valued factor decomposition with labels."""
    return {
        "beta_contribution": 0.0,
        "beta_label": _factor_label("beta", 0.0),
        "size_contribution": 0.0,
        "size_label": _factor_label("size", 0.0),
        "value_contribution": 0.0,
        "value_label": _factor_label("value", 0.0),
        "momentum_contribution": 0.0,
        "momentum_label": _factor_label("momentum", 0.0),
    }


def _make_series(hist: List[Dict]) -> pd.Series:
    """Convert price history list to pandas Series."""
    dates = [pd.to_datetime(h["date"]) for h in hist]
    prices = [h["close"] for h in hist]
    return pd.Series(prices, index=dates).sort_index()


def decompose_factors_batch(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Decompose sector ETF returns into factor contributions for ALL sectors at once.
    Fetches shared factor data (SPY, IWM, IWD, IWF) only once, then each sector once.
    Uses concurrent fetching for speed.
    """
    # Cache check at the start
    cache_key = "factor_decomposition_batch"
    now = time.time()
    if cache_key in _transitions_cache:
        cached = _transitions_cache[cache_key]
        if now - cached["ts"] < _CACHE_TTL:
            # Return cached results, filtering to requested tickers
            cached_results = cached["data"]
            cached_lookup = {r["ticker"]: r for r in cached_results}
            filtered = [cached_lookup.get(t, {"ticker": t, "name": SECTOR_ETFS.get(t, t), **_empty_factors()}) for t in tickers]
            return filtered

    # All tickers we need to fetch (shared factors + sectors)
    shared_tickers = ["SPY", "IWM", "IWD", "IWF"]
    all_tickers = list(set(shared_tickers + tickers))

    # Fetch all histories concurrently
    histories: Dict[str, List[Dict]] = {}

    def _fetch(t: str) -> tuple:
        return t, _get_history_cascade(t)

    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch, t): t for t in all_tickers}
            for future in as_completed(futures, timeout=45):
                try:
                    t, hist = future.result(timeout=30)
                    if hist and len(hist) >= 20:
                        histories[t] = hist
                except Exception as e:
                    t = futures[future]
                    logger.warning(f"Failed to fetch {t}: {e}")
    except Exception as e:
        logger.error(f"Concurrent history fetch failed: {e}")

    # Check shared data is available
    missing_shared = [t for t in shared_tickers if t not in histories]
    if missing_shared:
        logger.warning(f"Missing shared factor data: {missing_shared}")
        if "SPY" not in histories:
            # SPY is essential — can't compute any factors without it
            logger.warning("SPY missing — returning empty factors")
            return [{"ticker": t, "name": SECTOR_ETFS.get(t, t), **_empty_factors()} for t in tickers]
        # Proceed with partial factors (size/value may be None)

    # Build shared series once
    spy_s = _make_series(histories["SPY"])
    spy_ret = spy_s.pct_change().dropna()

    iwm_ret = None
    if "IWM" in histories:
        iwm_s = _make_series(histories["IWM"])
        iwm_ret = iwm_s.pct_change().dropna()

    iwd_ret = None
    iwf_ret = None
    if "IWD" in histories and "IWF" in histories:
        iwd_s = _make_series(histories["IWD"])
        iwf_s = _make_series(histories["IWF"])
        iwd_ret = iwd_s.pct_change().dropna()
        iwf_ret = iwf_s.pct_change().dropna()

    results = []
    for ticker in tickers:
        try:
            if ticker not in histories:
                results.append({"ticker": ticker, "name": SECTOR_ETFS.get(ticker, ticker), **_empty_factors()})
                continue

            ticker_s = _make_series(histories[ticker])
            ticker_ret = ticker_s.pct_change().dropna()

            common_dates = spy_ret.index.intersection(ticker_ret.index)

            # Intersect with available factor ETFs only
            if iwm_ret is not None:
                common_dates = common_dates.intersection(iwm_ret.index)
            if iwd_ret is not None and iwf_ret is not None:
                common_dates = common_dates.intersection(iwd_ret.index).intersection(iwf_ret.index)

            if len(common_dates) < 20:
                results.append({"ticker": ticker, "name": SECTOR_ETFS.get(ticker, ticker), **_empty_factors()})
                continue

            recent_dates = common_dates[-252:]
            spy_r = spy_ret[recent_dates]
            ticker_r = ticker_ret[recent_dates]

            cov_beta = np.cov(ticker_r, spy_r)[0, 1]
            var_spy = np.var(spy_r)
            beta = cov_beta / var_spy if var_spy > 0 else 1.0
            beta_contribution = round((beta - 1.0) * spy_ret.mean() * 252 * 100, 2)

            # Size factor (requires IWM)
            if iwm_ret is not None:
                iwm_r = iwm_ret[recent_dates]
                size_factor = (iwm_r - spy_r).mean() * 252
                size_contribution = round(size_factor * 100, 2)
            else:
                size_contribution = 0.0

            # Value factor (requires IWD and IWF)
            if iwd_ret is not None and iwf_ret is not None:
                iwd_r = iwd_ret[recent_dates]
                iwf_r = iwf_ret[recent_dates]
                value_factor = (iwd_r - iwf_r).mean() * 252
                value_contribution = round(value_factor * 100, 2)
            else:
                value_contribution = 0.0

            momentum_return = (ticker_s.iloc[-1] / ticker_s.iloc[0] - 1) * 100
            momentum_contribution = round(momentum_return * 0.2, 2)

            results.append({
                "ticker": ticker,
                "name": SECTOR_ETFS.get(ticker, ticker),
                "beta_contribution": beta_contribution,
                "beta_label": _factor_label("beta", beta_contribution),
                "size_contribution": size_contribution,
                "size_label": _factor_label("size", size_contribution),
                "value_contribution": value_contribution,
                "value_label": _factor_label("value", value_contribution),
                "momentum_contribution": momentum_contribution,
                "momentum_label": _factor_label("momentum", momentum_contribution),
            })
        except Exception as e:
            logger.error(f"Error decomposing factors for {ticker}: {e}")
            results.append({"ticker": ticker, "name": SECTOR_ETFS.get(ticker, ticker), **_empty_factors()})

    # Cache the batch results
    _transitions_cache[cache_key] = {"ts": time.time(), "data": results}
    return results


def get_business_cycle_overlay() -> Dict[str, Any]:
    """
    Map current economic regime to historically favorable sectors.
    Uses regime_detector to get current phase.
    """
    try:
        macro = get_macro_data()
        regime = detect_regime(macro)
        current_regime = regime.get("regime", "neutral")

        # Hardcoded historical relationships (can be enhanced with ML)
        regime_sector_map = {
            "bull": {
                "favorable": ["XLK", "XLY", "XLF"],  # Tech, Discretionary, Financials
                "unfavorable": ["XLU", "XLP", "XLE"],  # Utilities, Staples, Energy
            },
            "bear": {
                "favorable": ["XLU", "XLP", "XLV"],  # Utilities, Staples, Healthcare
                "unfavorable": ["XLY", "XLK", "XLF"],  # Discretionary, Tech, Financials
            },
            "neutral": {
                "favorable": ["XLI", "XLRE"],  # Industrials, Real Estate
                "unfavorable": [],
            },
        }

        mapping = regime_sector_map.get(current_regime, regime_sector_map["neutral"])
        favorable = [SECTOR_ETFS.get(t, t) for t in mapping.get("favorable", [])]
        unfavorable = [SECTOR_ETFS.get(t, t) for t in mapping.get("unfavorable", [])]

        return {
            "current_phase": current_regime,
            "favorable_sectors": favorable,
            "unfavorable_sectors": unfavorable,
            "recession_probability": regime.get("recession_probability", 50.0),
        }
    except Exception as e:
        logger.error(f"Error getting business cycle overlay: {e}")
        return {
            "current_phase": "unknown",
            "favorable_sectors": [],
            "unfavorable_sectors": [],
            "recession_probability": 50.0,
        }


def get_sector_transitions() -> Dict[str, Any]:
    """Main function to get all sector transition data."""
    now = time.time()
    cache_key = "sector_transitions"

    if cache_key in _transitions_cache:
        cached = _transitions_cache[cache_key]
        if now - cached["ts"] < _CACHE_TTL:
            logger.info(f"Returning cached sector transitions (age: {now - cached['ts']:.1f}s)")
            return cached["data"]

    try:
        # Run quadrant transitions and business cycle concurrently with factor batch
        transitions = detect_quadrant_transitions()

        # Get factor decomposition for ALL sectors in one batch (shared data fetched once)
        factor_decomposition = decompose_factors_batch(list(SECTOR_ETFS.keys()))

        # Get business cycle overlay
        cycle_overlay = get_business_cycle_overlay()

        result = {
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "transitions": transitions,
            "factor_decomposition": factor_decomposition,
            "cycle_overlay": cycle_overlay,
        }

        _transitions_cache[cache_key] = {"ts": now, "data": result}
        return result
    except Exception as e:
        logger.error(f"Error in get_sector_transitions: {e}")
        return {
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "transitions": [],
            "factor_decomposition": [],
            "cycle_overlay": {
                "current_phase": "unknown",
                "favorable_sectors": [],
                "unfavorable_sectors": [],
                "recession_probability": 50.0,
            },
            "error": str(e),
        }
