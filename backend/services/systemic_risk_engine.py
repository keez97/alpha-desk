"""
Institutional-Grade Systemic Risk Engine for AlphaDesk.

Extracts and enhances systemic risk calculations with improved institutional
methodologies:

  • Absorption Ratio: 11 sector ETFs, 52-week rolling window, Ledoit-Wolf shrinkage
  • Turbulence Index: 10 cross-asset ETFs, 60-day rolling window, chi-squared p-value
  • Windham 2x2: Smooth sigmoid transitions with state persistence and hysteresis

Based on:
  [1] Kritzman, Li, Page & Rigobon (2011). Journal of Portfolio Management, 37(4)
  [2] Kritzman & Li (2010). Financial Analysts Journal, 66(5), 30-41
  [3] Chow, Jacquier, Kritzman & Lowry (1999). Financial Analysts Journal
  [4] Harvey, Mulliner et al. (2025). Man Group/Duke
"""

import logging
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from scipy import stats as scipy_stats
from sklearn.covariance import LedoitWolf

from backend.services import yahoo_direct

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Asset Universe Definitions
# ═══════════════════════════════════════════════════════════════════════════════

SECTOR_ETF_UNIVERSE = {
    "XLK": "Information Technology",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLRE": "Real Estate",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLC": "Communication Services",
    "XLB": "Materials",
}

CROSS_ASSET_UNIVERSE = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "EFA": "Int'l Developed",
    "EEM": "Emerging Markets",
    "TLT": "20Y+ Treasury",
    "IEF": "7-10Y Treasury",
    "LQD": "IG Corporate",
    "HYG": "High Yield Corp",
    "GLD": "Gold",
}

# Windham fragility thresholds (percentile-based)
TURBULENCE_THRESHOLD_PCTILE = 75   # above 75th percentile = turbulent
ABSORPTION_THRESHOLD_PCTILE = 80   # above 80th percentile = fragile

# Hysteresis bands for state persistence
TURBULENCE_EXIT_PCTILE = 65        # must drop below 65th to exit turbulent
ABSORPTION_EXIT_PCTILE = 70        # must drop below 70th to exit fragile

# Module-level state tracking for Windham hysteresis
_windham_state_history: List[str] = []
_MAX_HISTORY = 3  # Track last 3 states for persistence


# ═══════════════════════════════════════════════════════════════════════════════
# Sector Returns (11 sector ETFs, weekly, 52-week window)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_sector_returns(lookback_weeks: int = 52) -> Optional[np.ndarray]:
    """
    Fetch weekly returns for 11 sector ETFs.

    Returns:
        (n_weeks x n_assets) ndarray of log returns, or None if insufficient data.
    """
    all_closes = {}
    min_len = None

    for ticker in SECTOR_ETF_UNIVERSE.keys():
        try:
            history = yahoo_direct.get_history(ticker, range_str="1y", interval="1wk")
            if history and len(history) >= 30:
                closes = [bar["close"] for bar in history]
                all_closes[ticker] = closes
                if min_len is None or len(closes) < min_len:
                    min_len = len(closes)
        except Exception as e:
            logger.debug(f"Failed to fetch {ticker} sector returns: {e}")

    if len(all_closes) < 9 or min_len is None or min_len < 30:
        logger.warning(
            f"Insufficient sector data: {len(all_closes)} assets, {min_len} weeks"
        )
        return None

    # Align to minimum length and compute log returns
    price_matrix = np.array(
        [all_closes[t][-min_len:] for t in SECTOR_ETF_UNIVERSE.keys() if t in all_closes]
    ).T  # shape: (n_weeks, n_assets)

    if price_matrix.shape[1] < 9:
        return None

    # Log returns: r_t = ln(P_t / P_{t-1})
    log_returns = np.diff(np.log(price_matrix), axis=0)

    # Remove any rows with NaN/inf
    mask = np.all(np.isfinite(log_returns), axis=1)
    log_returns = log_returns[mask]

    if len(log_returns) < 20:
        return None

    return log_returns


# ═══════════════════════════════════════════════════════════════════════════════
# Cross-Asset Returns (10 cross-asset ETFs, daily, 252-day window)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_cross_asset_returns(lookback_days: int = 252) -> Optional[np.ndarray]:
    """
    Fetch daily returns for 10 cross-asset ETFs (equities, bonds, commodities).

    Returns:
        (n_days x n_assets) ndarray of log returns, or None if insufficient data.
    """
    all_closes = {}
    min_len = None

    for ticker in CROSS_ASSET_UNIVERSE.keys():
        try:
            history = yahoo_direct.get_history(ticker, range_str="1y", interval="1d")
            if history and len(history) >= 100:
                closes = [bar["close"] for bar in history]
                all_closes[ticker] = closes
                if min_len is None or len(closes) < min_len:
                    min_len = len(closes)
        except Exception as e:
            logger.debug(f"Failed to fetch {ticker} cross-asset returns: {e}")

    if len(all_closes) < 8 or min_len is None or min_len < 100:
        logger.warning(
            f"Insufficient cross-asset data: {len(all_closes)} assets, {min_len} days"
        )
        return None

    # Align to minimum length and compute log returns
    price_matrix = np.array(
        [all_closes[t][-min_len:] for t in CROSS_ASSET_UNIVERSE.keys() if t in all_closes]
    ).T  # shape: (n_days, n_assets)

    if price_matrix.shape[1] < 8:
        return None

    # Log returns: r_t = ln(P_t / P_{t-1})
    log_returns = np.diff(np.log(price_matrix), axis=0)

    # Remove any rows with NaN/inf
    mask = np.all(np.isfinite(log_returns), axis=1)
    log_returns = log_returns[mask]

    if len(log_returns) < 50:
        return None

    return log_returns


# ═══════════════════════════════════════════════════════════════════════════════
# Absorption Ratio (Institutional Grade with Ledoit-Wolf)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_absorption_ratio(
    weekly_returns: np.ndarray,
    n_components: int = 2,
    rolling_window: int = 52,
) -> Dict[str, Any]:
    """
    Compute Absorption Ratio with Ledoit-Wolf shrinkage and AR delta tracking.

    AR = sum(top n eigenvalues) / sum(all eigenvalues)
    High AR → markets tightly coupled (fragile)
    Low AR → markets diversified (resilient)

    Args:
        weekly_returns: (n_weeks x n_assets) array of log returns
        n_components: Number of top components to track (default: 2)
        rolling_window: Rolling window in weeks (default: 52)

    Returns:
        {
            "current": float,
            "percentile": float,
            "delta": float,  # AR change from previous window
            "delta_zscore": float,  # Normalized AR delta
            "series": list,
            "n_assets": int,
            "n_components": int,
            "window": int,
        }
    """
    if weekly_returns is None or len(weekly_returns) < rolling_window + 1:
        return {
            "current": None,
            "percentile": 50.0,
            "delta": 0.0,
            "delta_zscore": 0.0,
            "series": [],
            "n_assets": 0,
            "n_components": n_components,
            "window": rolling_window,
        }

    n_assets = weekly_returns.shape[1]
    ar_series = []
    ar_deltas = []

    # Compute AR for each rolling window
    for i in range(rolling_window, len(weekly_returns) + 1):
        window_returns = weekly_returns[i - rolling_window : i]

        # Ledoit-Wolf shrinkage for covariance estimation
        lw = LedoitWolf()
        try:
            cov = lw.fit(window_returns).covariance_
        except Exception as e:
            logger.debug(f"LedoitWolf failed: {e}, using numpy cov")
            cov = np.cov(window_returns, rowvar=False)

        # Eigenvalue decomposition
        try:
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)[::-1]  # Descending order
        except Exception:
            ar_series.append(0.5)
            continue

        total_var = np.sum(eigenvalues)
        if total_var <= 0:
            ar_series.append(0.5)
            continue

        explained_var = np.sum(eigenvalues[:n_components])
        ar = explained_var / total_var
        ar_series.append(float(ar))

        # Track deltas for zscore
        if len(ar_series) > 1:
            delta = ar_series[-1] - ar_series[-2]
            ar_deltas.append(delta)

    if not ar_series:
        return {
            "current": None,
            "percentile": 50.0,
            "delta": 0.0,
            "delta_zscore": 0.0,
            "series": [],
            "n_assets": n_assets,
            "n_components": n_components,
            "window": rolling_window,
        }

    current = ar_series[-1]
    percentile = float(scipy_stats.percentileofscore(ar_series, current))

    # Compute AR delta and zscore
    delta = 0.0
    delta_zscore = 0.0
    if len(ar_series) > 1:
        delta = ar_series[-1] - ar_series[-2]
        if ar_deltas:
            delta_mean = np.mean(ar_deltas)
            delta_std = np.std(ar_deltas)
            if delta_std > 0:
                delta_zscore = (delta - delta_mean) / delta_std
            else:
                delta_zscore = 0.0

    return {
        "current": float(current),
        "percentile": float(percentile),
        "delta": float(delta),
        "delta_zscore": float(delta_zscore),
        "series": ar_series,
        "n_assets": n_assets,
        "n_components": n_components,
        "window": rolling_window,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Turbulence Index (Institutional Grade with Ledoit-Wolf + Chi-Squared)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_turbulence_index(
    daily_returns: np.ndarray,
    rolling_window: int = 60,
) -> Dict[str, Any]:
    """
    Compute Turbulence Index using Mahalanobis distance with chi-squared p-value.

    d_t = (r_t - μ)^T Σ^{-1} (r_t - μ) / n_assets

    Computes chi-squared p-value to assess statistical significance of deviation.
    No look-ahead bias: window excludes current day for computing statistics.

    Args:
        daily_returns: (n_days x n_assets) array of log returns
        rolling_window: Lookback window in days (default: 60)

    Returns:
        {
            "current": float,
            "percentile": float,
            "p_value": float,  # Chi-squared p-value for current day
            "series": list,
            "n_assets": int,
            "window": int,
        }
    """
    if daily_returns is None or len(daily_returns) < rolling_window + 1:
        return {
            "current": None,
            "percentile": 50.0,
            "p_value": 1.0,
            "series": [],
            "n_assets": 0,
            "window": rolling_window,
        }

    n_assets = daily_returns.shape[1]
    turbulence_series = []
    p_values = []

    # Compute turbulence for each day (from rolling_window onwards)
    for i in range(rolling_window, len(daily_returns)):
        # Window excluding current day (no look-ahead)
        window_returns = daily_returns[i - rolling_window : i]

        mu = np.mean(window_returns, axis=0)

        # Ledoit-Wolf shrinkage for covariance estimation
        lw = LedoitWolf()
        try:
            cov = lw.fit(window_returns).covariance_
        except Exception as e:
            logger.debug(f"LedoitWolf failed: {e}, using numpy cov")
            cov = np.cov(window_returns, rowvar=False)

        # Compute inverse
        try:
            cov_inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            cov_inv = np.linalg.pinv(cov)

        # Mahalanobis distance for current day
        diff = daily_returns[i] - mu
        d = float((diff @ cov_inv @ diff) / n_assets)
        turbulence_series.append(d)

        # Chi-squared p-value: P(X^2_df > d * n_assets)
        # where X^2_df has df = n_assets
        try:
            p_val = 1.0 - scipy_stats.chi2.cdf(d * n_assets, df=n_assets)
            p_values.append(p_val)
        except Exception:
            p_values.append(1.0)

    if not turbulence_series:
        return {
            "current": None,
            "percentile": 50.0,
            "p_value": 1.0,
            "series": [],
            "n_assets": n_assets,
            "window": rolling_window,
        }

    current = turbulence_series[-1]
    percentile = float(scipy_stats.percentileofscore(turbulence_series, current))
    p_value = p_values[-1] if p_values else 1.0

    return {
        "current": float(current),
        "percentile": float(percentile),
        "p_value": float(p_value),
        "series": turbulence_series,
        "n_assets": n_assets,
        "window": rolling_window,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Windham 2x2 with Smooth Sigmoid Transitions
# ═══════════════════════════════════════════════════════════════════════════════

def _sigmoid(x: float, center: float = 0.0, slope: float = 0.1) -> float:
    """Smooth sigmoid transition: 1 / (1 + exp(-slope * (x - center)))"""
    try:
        return 1.0 / (1.0 + np.exp(-slope * (x - center)))
    except (OverflowError, ValueError):
        return 1.0 if x > center else 0.0


def classify_windham_state(
    turb_pctile: float,
    ar_pctile: float,
    ar_delta_zscore: float = 0.0,
    turb_p_value: float = 1.0,
    prev_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Windham Capital 2x2 Fragility Classification with smooth sigmoid transitions
    and state persistence.

    States:
      Resilient-Calm:      Low absorption + Low turbulence  → Normal markets
      Resilient-Turbulent: Low absorption + High turbulence → Idiosyncratic shock
      Fragile-Calm:        High absorption + Low turbulence → DANGER: hidden risk
      Fragile-Turbulent:   High absorption + High turbulence→ Crisis mode

    Hysteresis: once in elevated state, requires wider margin to de-escalate.
    Smooth sigmoid transitions reduce oscillation near thresholds.

    Args:
        turb_pctile: Turbulence percentile (0-100)
        ar_pctile: Absorption Ratio percentile (0-100)
        ar_delta_zscore: AR delta zscore for rapid fragility changes (optional)
        turb_p_value: Chi-squared p-value for turbulence (optional)
        prev_state: Previous state for hysteresis (optional)

    Returns:
        {
            "state": str,
            "label": str,
            "risk_level": str,
            "description": str,
            "score": float,
            "fragility_score": float,  # Smooth sigmoid fragility (0-1)
            "turbulence_score": float,  # Smooth sigmoid turbulence (0-1)
            "consecutive_periods": int,
            "ar_delta_warning": bool,
        }
    """
    global _windham_state_history

    # ── Determine entry vs. exit thresholds based on hysteresis ──
    turb_entry = TURBULENCE_THRESHOLD_PCTILE
    turb_exit = TURBULENCE_EXIT_PCTILE
    ar_entry = ABSORPTION_THRESHOLD_PCTILE
    ar_exit = ABSORPTION_EXIT_PCTILE

    # Use exit thresholds if we were in elevated state
    if prev_state and ("turbulent" in prev_state):
        turb_threshold = turb_exit
    else:
        turb_threshold = turb_entry

    if prev_state and ("fragile" in prev_state):
        ar_threshold = ar_exit
    else:
        ar_threshold = ar_entry

    # ── Smooth sigmoid transitions ──
    # Sigmoid slope: steeper = faster transition (sharper decision boundary)
    fragility_score = _sigmoid(ar_pctile, center=ar_threshold, slope=0.1)
    turbulence_score = _sigmoid(turb_pctile, center=turb_threshold, slope=0.1)

    # ── Classification using threshold scores ──
    is_fragile = fragility_score > 0.5
    is_turbulent = turbulence_score > 0.5

    # ── AR delta warning: rapid increase in coupling ──
    ar_delta_warning = ar_delta_zscore > 1.0

    # ── State determination ──
    if is_fragile and is_turbulent:
        state = "fragile-turbulent"
        label = "Crisis Mode"
        risk_level = "extreme"
        description = (
            "Markets tightly coupled AND statistically unusual — "
            "active de-risking warranted"
        )
        score = -1.0
    elif is_fragile and not is_turbulent:
        state = "fragile-calm"
        label = "Hidden Risk"
        risk_level = "high"
        description = (
            "Markets appear calm but are tightly coupled — "
            "vulnerability building beneath the surface"
        )
        score = -0.5
    elif not is_fragile and is_turbulent:
        state = "resilient-turbulent"
        label = "Idiosyncratic Shock"
        risk_level = "moderate"
        description = (
            "Unusual market moves but well-diversified structure — "
            "likely a localized event"
        )
        score = -0.3
    else:
        state = "resilient-calm"
        label = "Normal Markets"
        risk_level = "low"
        description = "Markets diversified and behaving normally — risk-on conditions"
        score = 0.5

    # ── Track state persistence ──
    _windham_state_history.append(state)
    if len(_windham_state_history) > _MAX_HISTORY:
        _windham_state_history.pop(0)

    consecutive_periods = 0
    if _windham_state_history:
        current = _windham_state_history[-1]
        for s in reversed(_windham_state_history):
            if s == current:
                consecutive_periods += 1
            else:
                break

    return {
        "state": state,
        "label": label,
        "risk_level": risk_level,
        "description": description,
        "score": float(score),
        "fragility_score": float(fragility_score),
        "turbulence_score": float(turbulence_score),
        "consecutive_periods": consecutive_periods,
        "ar_delta_warning": ar_delta_warning,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Top-Level Computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_systemic_risk() -> Dict[str, Any]:
    """
    Top-level systemic risk computation.

    Fetches data for both sector and cross-asset universes and computes
    all systemic risk metrics in a single call.

    Returns:
        {
            "turbulence": {...},
            "absorption": {...},
            "windham": {...},
            "data_quality": {
                "sector_assets_available": int,
                "cross_assets_available": int,
            },
        }
    """
    result = {
        "turbulence": {},
        "absorption": {},
        "windham": {},
        "data_quality": {
            "sector_assets_available": 0,
            "cross_assets_available": 0,
        },
    }

    # ── Fetch cross-asset returns for turbulence ──
    cross_asset_returns = fetch_cross_asset_returns(lookback_days=252)
    if cross_asset_returns is not None:
        result["data_quality"]["cross_assets_available"] = cross_asset_returns.shape[1]
        turb_result = compute_turbulence_index(cross_asset_returns, rolling_window=60)
        result["turbulence"] = turb_result
    else:
        result["turbulence"]["current"] = None
        result["turbulence"]["percentile"] = 50.0
        result["turbulence"]["p_value"] = 1.0
        result["turbulence"]["series"] = []

    # ── Fetch sector returns for absorption ratio ──
    sector_returns = fetch_sector_returns(lookback_weeks=52)
    if sector_returns is not None:
        result["data_quality"]["sector_assets_available"] = sector_returns.shape[1]
        ar_result = compute_absorption_ratio(sector_returns, n_components=2, rolling_window=52)
        result["absorption"] = ar_result
    else:
        result["absorption"]["current"] = None
        result["absorption"]["percentile"] = 50.0
        result["absorption"]["delta"] = 0.0
        result["absorption"]["delta_zscore"] = 0.0
        result["absorption"]["series"] = []

    # ── Windham classification ──
    turb_pctile = result["turbulence"].get("percentile", 50.0)
    ar_pctile = result["absorption"].get("percentile", 50.0)
    ar_delta_zscore = result["absorption"].get("delta_zscore", 0.0)
    turb_p_value = result["turbulence"].get("p_value", 1.0)

    # Get previous state from history if available
    prev_state = _windham_state_history[-1] if _windham_state_history else None

    windham_result = classify_windham_state(
        turb_pctile=turb_pctile,
        ar_pctile=ar_pctile,
        ar_delta_zscore=ar_delta_zscore,
        turb_p_value=turb_p_value,
        prev_state=prev_state,
    )
    result["windham"] = windham_result

    return result
