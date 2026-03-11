"""
Sector Transitions Service for AlphaDesk.
Detects quadrant transitions, factor decomposition, and business cycle overlay.

Data source cascade for price history:
  1. financialdatasets.ai (FDS) — reliable, paid API
  2. yfinance — fallback, rate-limited
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
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


def decompose_factors(ticker: str) -> Dict[str, float]:
    """
    Decompose sector ETF returns into factor contributions using regression.
    Factors: market beta (vs SPY), size (IWM-SPY), value (IWD-IWF), momentum.
    """
    try:
        # Fetch 1-year history via FDS → yfinance cascade
        spy_hist = _get_history_cascade("SPY")
        ticker_hist = _get_history_cascade(ticker)
        iwm_hist = _get_history_cascade("IWM")  # Size factor
        iwd_hist = _get_history_cascade("IWD")  # Value ETF
        iwf_hist = _get_history_cascade("IWF")  # Growth ETF

        if not all([spy_hist, ticker_hist, iwm_hist, iwd_hist, iwf_hist]):
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

        # Convert to DataFrames
        def make_series(hist):
            dates = [pd.to_datetime(h["date"]) for h in hist]
            prices = [h["close"] for h in hist]
            return pd.Series(prices, index=dates).sort_index()

        spy_s = make_series(spy_hist)
        ticker_s = make_series(ticker_hist)
        iwm_s = make_series(iwm_hist)
        iwd_s = make_series(iwd_hist)
        iwf_s = make_series(iwf_hist)

        # Calculate daily returns
        spy_ret = spy_s.pct_change().dropna()
        ticker_ret = ticker_s.pct_change().dropna()
        iwm_ret = iwm_s.pct_change().dropna()
        iwd_ret = iwd_s.pct_change().dropna()
        iwf_ret = iwf_s.pct_change().dropna()

        # Align data
        common_dates = spy_ret.index.intersection(
            ticker_ret.index
        ).intersection(iwm_ret.index).intersection(iwd_ret.index).intersection(iwf_ret.index)

        if len(common_dates) < 20:
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

        # Use last 252 trading days (1 year)
        recent_dates = common_dates[-252:]
        spy_r = spy_ret[recent_dates]
        ticker_r = ticker_ret[recent_dates]
        iwm_r = iwm_ret[recent_dates]
        iwd_r = iwd_ret[recent_dates]
        iwf_r = iwf_ret[recent_dates]

        # Calculate market beta (ticker vs SPY)
        cov_beta = np.cov(ticker_r, spy_r)[0, 1]
        var_spy = np.var(spy_r)
        beta = cov_beta / var_spy if var_spy > 0 else 1.0

        # Size factor: IWM - SPY (small cap premium)
        size_factor = (iwm_r - spy_r).mean() * 252

        # Value factor: IWD - IWF (value premium)
        value_factor = (iwd_r - iwf_r).mean() * 252

        # Momentum: 12-month return
        momentum_return = (ticker_s.iloc[-1] / ticker_s.iloc[0] - 1) * 100

        # Contribution calculation (simplified)
        beta_contribution = (beta - 1.0) * spy_ret.mean() * 252 * 100
        size_contribution = size_factor * 100
        value_contribution = value_factor * 100
        momentum_contribution = momentum_return * 0.2  # Weight momentum less

        beta_contrib_rounded = round(beta_contribution, 2)
        size_contrib_rounded = round(size_contribution, 2)
        value_contrib_rounded = round(value_contribution, 2)
        momentum_contrib_rounded = round(momentum_contribution, 2)

        return {
            "beta_contribution": beta_contrib_rounded,
            "beta_label": _factor_label("beta", beta_contrib_rounded),
            "size_contribution": size_contrib_rounded,
            "size_label": _factor_label("size", size_contrib_rounded),
            "value_contribution": value_contrib_rounded,
            "value_label": _factor_label("value", value_contrib_rounded),
            "momentum_contribution": momentum_contrib_rounded,
            "momentum_label": _factor_label("momentum", momentum_contrib_rounded),
        }
    except Exception as e:
        logger.error(f"Error decomposing factors for {ticker}: {e}")
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
        # Get quadrant transitions
        transitions = detect_quadrant_transitions()

        # Get factor decomposition for each sector
        factor_decomposition = []
        for ticker in SECTOR_ETFS.keys():
            factors = decompose_factors(ticker)
            factor_decomposition.append({
                "ticker": ticker,
                "name": SECTOR_ETFS[ticker],
                **factors,
            })

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
