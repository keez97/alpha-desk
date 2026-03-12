"""
Institutional-Grade Market Regime Detector for AlphaDesk.

Architecture based on the Windham Capital Risk Regime Framework (Kritzman)
and Harvey-Mulliner (2025) composite model, with six weighted signal layers:

  Layer 1 — Trend Regime        (25%)  50/200 SMA crossover + fast/slow momentum
  Layer 2 — Volatility Regime   (20%)  VIX level + 1Y percentile + VVIX meta-vol
  Layer 3 — Yield Curve & Credit(15%)  Estrella probit recession prob + HY OAS
  Layer 4 — Sentiment           (15%)  CNN Fear & Greed composite
  Layer 5 — Macro Confirmation  (10%)  Economic trend signals from FRED series
  Layer 6 — Systemic Risk       (15%)  Turbulence Index (Mahalanobis distance)
                                        + Absorption Ratio (PCA fragility)
                                        → Windham 2x2 fragility classification

Each layer produces a normalized score from -1.0 (max bearish) to +1.0 (max
bullish). The weighted composite determines the final regime state and
confidence level. The Windham fragility overlay provides a separate systemic
risk classification that can override regime calls during crisis conditions.

Data sources: FRED (VIX, yields, credit, USD, WTI), Yahoo Direct (SPY, TLT,
GLD, HYG historical OHLCV), CNN Fear & Greed API.

References:
  [1] Hamilton, J.D. (1989). Econometrica, 57(2), 357-384.
  [2] Estrella & Mishkin (1996). Fed Reserve Bank of NY Current Issues, 2(7).
  [3] Kritzman & Li (2010). Financial Analysts Journal, 66(5), 30-41.
  [4] Kritzman et al. (2011). Journal of Portfolio Management, 37(4), 112-126.
  [5] Mulliner, Harvey, Xia, Fang & Van Hemert (2025). Man Group/Duke.
  [6] Chow, Jacquier, Kritzman & Lowry (1999). Financial Analysts Journal.
"""

import logging
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from scipy import stats as scipy_stats

from backend.services import fred_service
from backend.services import cnn_fear_greed
from backend.services import yahoo_direct

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Cache
# ═══════════════════════════════════════════════════════════════════════════════
_regime_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes
_cache_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration — Layer weights (sum = 1.0)
# ═══════════════════════════════════════════════════════════════════════════════
LAYER_WEIGHTS = {
    "trend":       0.25,
    "volatility":  0.20,
    "yield_credit": 0.15,
    "sentiment":   0.15,
    "macro":       0.10,
    "systemic":    0.15,
}

# Multi-asset universe for turbulence / absorption ratio
MULTI_ASSET_TICKERS = ["SPY", "TLT", "GLD", "HYG"]
MULTI_ASSET_LABELS = {
    "SPY": "S&P 500",
    "TLT": "Long Treasury",
    "GLD": "Gold",
    "HYG": "High Yield Corp",
}

# Windham fragility thresholds (percentile-based)
TURBULENCE_THRESHOLD_PCTILE = 75   # above 75th percentile = turbulent
ABSORPTION_THRESHOLD_PCTILE = 80   # above 80th percentile = fragile

# Hysteresis bands — once a threshold is crossed, the opposite direction
# requires a wider margin to prevent rapid oscillation between states.
# Example: turbulence enters "turbulent" at 75th, but must drop to 65th to exit.
TURBULENCE_EXIT_PCTILE = 65        # must drop below 65th to exit turbulent
ABSORPTION_EXIT_PCTILE = 70        # must drop below 70th to exit fragile

# Extreme absorption threshold — when absorption is THIS high, even
# "fragile-calm" should be treated as near-crisis (bearish override)
ABSORPTION_EXTREME_PCTILE = 90     # 90th+ percentile = extreme coupling


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1: Trend Regime
# ═══════════════════════════════════════════════════════════════════════════════
def _compute_trend_layer(spy_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Trend regime from SPY price history.

    Signals:
      - 50/200 SMA crossover (golden cross / death cross)
      - Price position relative to 200 SMA
      - Fast momentum (1-month return) vs slow momentum (6-month return)

    Returns: {"score": float(-1..+1), "signals": [...], "details": {...}}
    """
    result = {"score": 0.0, "signals": [], "details": {}}

    if not spy_history or len(spy_history) < 50:
        result["details"]["status"] = "insufficient_data"
        return result

    closes = [bar["close"] for bar in spy_history]
    n = len(closes)
    current_price = closes[-1]

    # ── 50 & 200 SMA ──────────────────────────────────────────────
    sma50 = np.mean(closes[-50:]) if n >= 50 else None
    sma200 = np.mean(closes[-200:]) if n >= 200 else None

    sma_score = 0.0
    if sma50 is not None and sma200 is not None:
        # Golden cross (50 > 200) vs death cross (50 < 200)
        sma_ratio = (sma50 - sma200) / sma200
        if sma_ratio > 0.02:      # 50 SMA > 200 SMA by 2%+
            sma_score = 1.0
            cross_state = "Golden Cross"
        elif sma_ratio > 0:
            sma_score = 0.5
            cross_state = "Bullish (narrowing)"
        elif sma_ratio > -0.02:
            sma_score = -0.5
            cross_state = "Bearish (narrowing)"
        else:
            sma_score = -1.0
            cross_state = "Death Cross"

        result["signals"].append({
            "name": "SMA Crossover",
            "value": f"50/200 ratio: {sma_ratio:+.3f}",
            "reading": cross_state,
            "bias": "bull" if sma_score > 0 else ("bear" if sma_score < 0 else "neutral"),
        })
        result["details"]["sma50"] = round(sma50, 2)
        result["details"]["sma200"] = round(sma200, 2)
        result["details"]["sma_ratio"] = round(sma_ratio, 4)

    # ── Price vs 200 SMA ──────────────────────────────────────────
    price_200_score = 0.0
    if sma200 is not None:
        pct_above_200 = (current_price - sma200) / sma200
        if pct_above_200 > 0.05:
            price_200_score = 1.0
            pos_reading = f"{pct_above_200*100:+.1f}% above 200 SMA"
        elif pct_above_200 > 0:
            price_200_score = 0.5
            pos_reading = f"{pct_above_200*100:+.1f}% above 200 SMA"
        elif pct_above_200 > -0.05:
            price_200_score = -0.5
            pos_reading = f"{pct_above_200*100:+.1f}% below 200 SMA"
        else:
            price_200_score = -1.0
            pos_reading = f"{pct_above_200*100:+.1f}% below 200 SMA"

        result["signals"].append({
            "name": "Price vs 200 SMA",
            "value": f"${current_price:,.2f}",
            "reading": pos_reading,
            "bias": "bull" if price_200_score > 0 else ("bear" if price_200_score < 0 else "neutral"),
        })
        result["details"]["pct_above_200sma"] = round(pct_above_200 * 100, 2)

    # ── Fast / Slow Momentum (Goulding, Harvey & Mazzoleni 2023) ──
    momentum_score = 0.0
    fast_mom = None  # 1-month (~21 trading days)
    slow_mom = None  # 6-month (~126 trading days)

    if n >= 22:
        fast_mom = (closes[-1] / closes[-22] - 1) * 100

    if n >= 126:
        slow_mom = (closes[-1] / closes[-126] - 1) * 100

    if fast_mom is not None and slow_mom is not None:
        # Both positive = strong bull; both negative = strong bear
        # Divergence = transition
        if fast_mom > 0 and slow_mom > 0:
            momentum_score = min(1.0, (fast_mom + slow_mom) / 20)
            mom_reading = "Bullish acceleration"
        elif fast_mom < 0 and slow_mom < 0:
            momentum_score = max(-1.0, (fast_mom + slow_mom) / 20)
            mom_reading = "Bearish acceleration"
        elif fast_mom > 0 and slow_mom < 0:
            momentum_score = 0.3  # Recovering
            mom_reading = "Bullish reversal"
        else:  # fast < 0, slow > 0
            momentum_score = -0.3  # Deteriorating
            mom_reading = "Bearish divergence"

        result["signals"].append({
            "name": "Momentum",
            "value": f"Fast: {fast_mom:+.1f}% / Slow: {slow_mom:+.1f}%",
            "reading": mom_reading,
            "bias": "bull" if momentum_score > 0 else ("bear" if momentum_score < 0 else "neutral"),
        })
        result["details"]["fast_momentum_1m"] = round(fast_mom, 2)
        result["details"]["slow_momentum_6m"] = round(slow_mom, 2)
    elif fast_mom is not None:
        momentum_score = min(1.0, max(-1.0, fast_mom / 10))
        result["details"]["fast_momentum_1m"] = round(fast_mom, 2)

    # ── Composite trend score (equal-weight sub-signals) ──────────
    components = [s for s in [sma_score, price_200_score, momentum_score] if s != 0.0]
    if components:
        result["score"] = np.clip(np.mean(components), -1.0, 1.0)
    else:
        result["score"] = 0.0

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2: Volatility Regime
# ═══════════════════════════════════════════════════════════════════════════════
def _compute_volatility_layer() -> Dict[str, Any]:
    """
    Volatility regime from VIX level, 1-year percentile, and VVIX.

    Uses dynamic thresholds via percentile ranking rather than fixed
    VIX levels — VIX at 20 means different things in different regimes.
    """
    result = {"score": 0.0, "signals": [], "details": {}}

    # ── VIX Level ─────────────────────────────────────────────────
    vix = fred_service.get_vix()
    vix_history = fred_service.get_vix_history(lookback_days=365) if vix else []

    if vix is not None:
        result["details"]["vix"] = round(vix, 2)

        # Percentile rank over 1 year
        vix_percentile = 50.0
        if vix_history and len(vix_history) >= 50:
            vix_percentile = scipy_stats.percentileofscore(vix_history, vix)
            result["details"]["vix_percentile_1y"] = round(vix_percentile, 1)

        # VIX level score (academic thresholds from PDF)
        if vix < 15:
            level_score = 1.0
            reading = "Low vol / Complacency"
        elif vix < 20:
            level_score = 0.5
            reading = "Normal volatility"
        elif vix < 25:
            level_score = -0.2
            reading = "Elevated uncertainty"
        elif vix < 30:
            level_score = -0.7
            reading = "High stress"
        else:
            level_score = -1.0
            reading = "Crisis / Panic"

        # Adjust by percentile — a VIX of 22 at the 90th percentile
        # is more bearish than VIX 22 at the 50th percentile
        pctile_adjustment = (50 - vix_percentile) / 100  # high pctile → negative
        adjusted_score = np.clip(level_score + pctile_adjustment * 0.3, -1.0, 1.0)

        result["signals"].append({
            "name": "VIX",
            "value": f"{vix:.1f} ({vix_percentile:.0f}th %ile)",
            "reading": reading,
            "bias": "bull" if adjusted_score > 0.1 else ("bear" if adjusted_score < -0.1 else "neutral"),
        })

        # ── VVIX (volatility of volatility) ────────────────────────
        vvix = fred_service.get_latest("VXVCLS")
        vvix_score = 0.0
        if vvix is not None:
            result["details"]["vvix"] = round(vvix, 2)
            if vvix < 80:
                vvix_score = 0.3
                vvix_reading = "Calm"
            elif vvix < 100:
                vvix_score = 0.0
                vvix_reading = "Normal"
            elif vvix < 120:
                vvix_score = -0.3
                vvix_reading = "Elevated"
            else:
                vvix_score = -0.6
                vvix_reading = "Extreme fear of fear"

            result["signals"].append({
                "name": "VVIX",
                "value": f"{vvix:.1f}",
                "reading": vvix_reading,
                "bias": "bull" if vvix_score > 0 else ("bear" if vvix_score < 0 else "neutral"),
            })

        result["score"] = np.clip(adjusted_score * 0.7 + vvix_score * 0.3, -1.0, 1.0)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3: Yield Curve & Credit
# ═══════════════════════════════════════════════════════════════════════════════
def _probit_recession_prob(yield_spread: float) -> float:
    """
    Estrella-Mishkin probit model: P(recession in 12m) = Φ(-0.6 - 0.82 * spread)
    where spread = 10Y - 3M Treasury in percentage points.

    This model has correctly predicted every U.S. recession since 1960
    with only one false positive (1966).  [Estrella & Mishkin, 1996]
    """
    try:
        z = -0.6 - 0.82 * yield_spread
        prob = scipy_stats.norm.cdf(z)
        return min(100.0, max(0.0, prob * 100.0))
    except Exception:
        return 50.0


def _compute_yield_credit_layer() -> Dict[str, Any]:
    """
    Yield curve + credit spread regime signals.

    - 10Y-3M spread → Estrella recession probability
    - HY OAS → credit stress levels (Galai et al. 2014 thresholds)
    """
    result = {"score": 0.0, "signals": [], "details": {}}
    sub_scores = []

    # ── Yield Curve (10Y-3M) + Estrella Probit ─────────────────────
    yield_spread = fred_service.get_yield_curve_spread()
    recession_prob = 50.0

    if yield_spread is not None:
        recession_prob = _probit_recession_prob(yield_spread)
        result["details"]["yield_spread_10y3m"] = round(yield_spread, 3)
        result["details"]["recession_probability"] = round(recession_prob, 1)

        # Score based on recession probability (more nuanced than raw spread)
        if recession_prob < 10:
            yc_score = 1.0
            reading = f"Healthy (+{yield_spread:.2f}%)"
        elif recession_prob < 25:
            yc_score = 0.4
            reading = f"Normal (+{yield_spread:.2f}%)"
        elif recession_prob < 50:
            yc_score = -0.3
            reading = f"Warning ({yield_spread:+.2f}%)"
        elif recession_prob < 75:
            yc_score = -0.7
            reading = f"Inverted ({yield_spread:+.2f}%)"
        else:
            yc_score = -1.0
            reading = f"Deep inversion ({yield_spread:+.2f}%)"

        result["signals"].append({
            "name": "Yield Curve",
            "value": f"{yield_spread:+.2f}% → {recession_prob:.0f}% recession prob",
            "reading": reading,
            "bias": "bull" if yc_score > 0 else ("bear" if yc_score < 0 else "neutral"),
        })
        sub_scores.append(yc_score)

    # ── Credit Spreads (HY OAS) ───────────────────────────────────
    hy_oas = fred_service.get_credit_spread()
    if hy_oas is not None:
        result["details"]["hy_oas"] = round(hy_oas, 3)

        # Thresholds from PDF taxonomy table
        if hy_oas < 3.0:
            cs_score = 0.8
            cs_reading = "Risk-on / Tight"
        elif hy_oas < 5.0:
            cs_score = 0.2
            cs_reading = "Normal"
        elif hy_oas < 8.0:
            cs_score = -0.6
            cs_reading = "Elevated stress"
        else:
            cs_score = -1.0
            cs_reading = "Crisis / Severe distress"

        # Also check BBB spread for investment-grade confirmation
        bbb_spread = fred_service.get_latest("BAMLC0A4CBBB")
        if bbb_spread is not None:
            result["details"]["bbb_spread"] = round(bbb_spread, 3)

        result["signals"].append({
            "name": "HY Credit Spread",
            "value": f"{hy_oas:.2f}%",
            "reading": cs_reading,
            "bias": "bull" if cs_score > 0 else ("bear" if cs_score < 0 else "neutral"),
        })
        sub_scores.append(cs_score)

    if sub_scores:
        result["score"] = np.clip(np.mean(sub_scores), -1.0, 1.0)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4: Sentiment
# ═══════════════════════════════════════════════════════════════════════════════
def _compute_sentiment_layer() -> Dict[str, Any]:
    """
    Sentiment regime from CNN Fear & Greed Index.

    Score 0-100 → normalized to -1..+1 with contrarian extremes.
    Academic basis: Tan et al. (2025) — F&G Granger-causes S&P 500 returns.
    """
    result = {"score": 0.0, "signals": [], "details": {}}

    fg_data = None
    try:
        fg_data = cnn_fear_greed.get_fear_greed()
    except Exception as e:
        logger.debug("CNN Fear & Greed fetch failed: %s", e)

    if fg_data and fg_data.get("score") is not None:
        score = fg_data["score"]
        classification = fg_data.get("classification", "Unknown")
        result["details"]["fear_greed_score"] = score
        result["details"]["fear_greed_class"] = classification
        result["details"]["fear_greed_data"] = fg_data

        # Map 0-100 to -1..+1 (50 = neutral)
        # But apply contrarian adjustment at extremes
        raw_score = (score - 50) / 50  # -1 to +1

        # Contrarian adjustment: extreme greed (>80) is actually a warning
        # and extreme fear (<20) is often an opportunity
        contrarian_adj = 0.0
        contrarian_note = None
        if score > 80:
            contrarian_adj = -0.2
            contrarian_note = "Extreme greed — contrarian warning"
        elif score < 20:
            contrarian_adj = 0.2
            contrarian_note = "Extreme fear — contrarian opportunity"

        adjusted = np.clip(raw_score + contrarian_adj, -1.0, 1.0)

        # Determine reading
        if score >= 75:
            reading = "Extreme Greed"
        elif score >= 55:
            reading = "Greed"
        elif score <= 25:
            reading = "Extreme Fear"
        elif score <= 45:
            reading = "Fear"
        else:
            reading = "Neutral"

        bias = "bull" if adjusted > 0.1 else ("bear" if adjusted < -0.1 else "neutral")

        result["signals"].append({
            "name": "Fear & Greed",
            "value": f"{score}",
            "reading": f"{reading}" + (f" ({contrarian_note})" if contrarian_note else ""),
            "bias": bias,
        })

        if contrarian_note:
            result["details"]["contrarian_signal"] = contrarian_note

        # Include previous readings for trend context
        prev_week = fg_data.get("one_week_ago")
        if prev_week is not None:
            result["details"]["fg_1w_ago"] = prev_week
            fg_direction = "improving" if score > prev_week else "deteriorating"
            result["details"]["fg_trend"] = fg_direction

        result["score"] = float(adjusted)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5: Macro Confirmation
# ═══════════════════════════════════════════════════════════════════════════════
def _compute_macro_layer() -> Dict[str, Any]:
    """
    Macro confirmation using FRED economic series trends.

    Approximates CESI / ISM PMI by analyzing direction and z-scores
    of available FRED macro data (WTI crude, USD, yield curve momentum).
    """
    result = {"score": 0.0, "signals": [], "details": {}}
    sub_scores = []

    # ── WTI Crude Oil trend (commodity/energy cycle) ───────────────
    wti_history = fred_service.get_values_only("DCOILWTICO", lookback_days=180)
    if wti_history and len(wti_history) >= 60:
        wti_current = wti_history[-1]
        wti_3m_avg = np.mean(wti_history[-60:])
        wti_6m_avg = np.mean(wti_history)
        wti_zscore = (wti_current - wti_6m_avg) / max(np.std(wti_history), 0.01)

        result["details"]["wti_current"] = round(wti_current, 2)
        result["details"]["wti_zscore_6m"] = round(wti_zscore, 2)

        # Rising oil = potential inflation/growth concern at extremes
        if -1 < wti_zscore < 1:
            oil_score = 0.2  # Stable = mildly bullish
        elif wti_zscore > 2:
            oil_score = -0.3  # Spiking = inflation risk
        elif wti_zscore < -2:
            oil_score = -0.5  # Crashing = demand destruction
        else:
            oil_score = 0.0

        sub_scores.append(oil_score)

    # ── USD Index trend ────────────────────────────────────────────
    usd_history = fred_service.get_values_only("DTWEXBGS", lookback_days=180)
    if usd_history and len(usd_history) >= 20:
        usd_current = usd_history[-1]
        usd_3m_avg = np.mean(usd_history[-60:]) if len(usd_history) >= 60 else np.mean(usd_history)
        usd_change = (usd_current - usd_3m_avg) / usd_3m_avg * 100

        result["details"]["usd_index"] = round(usd_current, 2)
        result["details"]["usd_3m_change"] = round(usd_change, 2)

        # Strong USD = risk-off headwind; weak USD = risk-on tailwind
        if usd_change > 3:
            usd_score = -0.4  # Strong dollar headwind
        elif usd_change > 1:
            usd_score = -0.1
        elif usd_change < -3:
            usd_score = 0.3   # Weak dollar tailwind
        elif usd_change < -1:
            usd_score = 0.1
        else:
            usd_score = 0.0

        sub_scores.append(usd_score)

    # ── Yield curve momentum (is spread improving or deteriorating?) ─
    yc_history = fred_service.get_values_only("T10Y3M", lookback_days=90)
    if yc_history and len(yc_history) >= 20:
        yc_current = yc_history[-1]
        yc_1m_ago = yc_history[-20] if len(yc_history) >= 20 else yc_history[0]
        yc_momentum = yc_current - yc_1m_ago

        result["details"]["yc_momentum_1m"] = round(yc_momentum, 3)

        if yc_momentum > 0.2:
            yc_score = 0.5   # Steepening = bullish
            yc_reading = "Steepening"
        elif yc_momentum > 0:
            yc_score = 0.2
            yc_reading = "Mildly steepening"
        elif yc_momentum > -0.2:
            yc_score = -0.2
            yc_reading = "Mildly flattening"
        else:
            yc_score = -0.5  # Flattening = bearish
            yc_reading = "Flattening"

        result["signals"].append({
            "name": "Yield Curve Momentum",
            "value": f"{yc_momentum:+.3f} (1m chg)",
            "reading": yc_reading,
            "bias": "bull" if yc_score > 0 else ("bear" if yc_score < 0 else "neutral"),
        })
        sub_scores.append(yc_score)

    if sub_scores:
        result["score"] = np.clip(np.mean(sub_scores), -1.0, 1.0)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 6: Systemic Risk — Turbulence Index + Absorption Ratio
# ═══════════════════════════════════════════════════════════════════════════════
def _fetch_multi_asset_returns(lookback: str = "1y") -> Optional[np.ndarray]:
    """
    Fetch daily close prices for the multi-asset universe and compute
    daily log returns. Returns (n_days x n_assets) array or None.
    """
    all_closes = {}
    min_len = None

    for ticker in MULTI_ASSET_TICKERS:
        try:
            history = yahoo_direct.get_history(ticker, range_str=lookback, interval="1d")
            if history and len(history) >= 50:
                closes = [bar["close"] for bar in history]
                all_closes[ticker] = closes
                if min_len is None or len(closes) < min_len:
                    min_len = len(closes)
        except Exception as e:
            logger.warning("Failed to fetch %s history for turbulence: %s", ticker, e)

    if len(all_closes) < 3 or min_len is None or min_len < 50:
        return None

    # Align to minimum length and compute log returns
    price_matrix = np.array([all_closes[t][-min_len:] for t in MULTI_ASSET_TICKERS
                             if t in all_closes]).T  # shape: (min_len, n_assets)
    if price_matrix.shape[1] < 3:
        return None

    # Log returns: r_t = ln(P_t / P_{t-1})
    log_returns = np.diff(np.log(price_matrix), axis=0)

    # Remove any rows with NaN/inf
    mask = np.all(np.isfinite(log_returns), axis=1)
    log_returns = log_returns[mask]

    if len(log_returns) < 50:
        return None

    return log_returns


def _compute_turbulence_index(returns: np.ndarray) -> Tuple[float, float, List[float]]:
    """
    Turbulence Index using Mahalanobis distance.

    d_t = (1/n) * (r_t - μ)^T Σ^{-1} (r_t - μ)

    where r_t is today's return vector, μ is the historical mean,
    and Σ is the historical covariance matrix.

    Based on Chow et al. (1999) and Kritzman & Li (2010).

    Returns: (current_turbulence, percentile, full_series)
    """
    n_assets = returns.shape[1]
    mu = np.mean(returns, axis=0)
    cov = np.cov(returns, rowvar=False)

    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        # Fallback: use pseudo-inverse for singular matrices
        cov_inv = np.linalg.pinv(cov)

    # Compute turbulence for each day
    turbulence_series = []
    for i in range(len(returns)):
        diff = returns[i] - mu
        d = float(diff.T @ cov_inv @ diff) / n_assets
        turbulence_series.append(d)

    current = turbulence_series[-1]
    percentile = float(scipy_stats.percentileofscore(turbulence_series, current))

    return current, percentile, turbulence_series


def _compute_absorption_ratio(returns: np.ndarray, n_components: int = 1) -> Tuple[float, float, List[float]]:
    """
    Absorption Ratio: fraction of total variance explained by the first
    n eigenvectors (principal components).

    AR = Σ(σ²_eigenvector_i) / Σ(σ²_asset_j)

    High AR → markets are tightly coupled (fragile)
    Low AR → markets are diversified (resilient)

    Based on Kritzman, Li, Page & Rigobon (2011).

    Uses a rolling 60-day window for time-varying absorption ratio.

    Returns: (current_AR, percentile, full_series)
    """
    window = min(60, len(returns) // 3)
    if window < 30:
        window = 30

    ar_series = []
    for i in range(window, len(returns) + 1):
        window_returns = returns[i - window:i]
        cov = np.cov(window_returns, rowvar=False)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.sort(eigenvalues)[::-1]  # Descending

        total_var = np.sum(eigenvalues)
        if total_var == 0:
            ar_series.append(0.5)
            continue

        explained_var = np.sum(eigenvalues[:n_components])
        ar = explained_var / total_var
        ar_series.append(float(ar))

    if not ar_series:
        return 0.5, 50.0, []

    current = ar_series[-1]
    percentile = float(scipy_stats.percentileofscore(ar_series, current))

    return current, percentile, ar_series


# Module-level cache for Windham state hysteresis.
# Prevents rapid oscillation when turbulence/absorption hover near thresholds.
_previous_windham_state: str | None = None


def _windham_fragility_state(
    turbulence_pctile: float,
    absorption_pctile: float,
) -> Dict[str, Any]:
    """
    Windham Capital 2x2 Fragility Classification with hysteresis.

    Combines turbulence (statistical unusualness) with absorption ratio
    (systemic fragility) into four market states:

      Resilient-Calm:      Low absorption + Low turbulence  → Normal markets
      Resilient-Turbulent: Low absorption + High turbulence → Idiosyncratic shock
      Fragile-Calm:        High absorption + Low turbulence → DANGER: hidden risk
      Fragile-Turbulent:   High absorption + High turbulence→ Crisis mode

    Hysteresis: once in an elevated state, requires a larger improvement
    to de-escalate. This prevents oscillation when metrics hover near
    thresholds.  Entry uses standard thresholds; exit requires the
    wider EXIT thresholds.

    The "fragile-calm" state is the most dangerous — it's where markets
    appear calm but are actually tightly coupled and vulnerable. This
    preceded the 2008 crash and COVID sell-off.
    """
    global _previous_windham_state

    # ── Apply hysteresis: use stricter exit thresholds for de-escalation ──
    # If we were previously in a turbulent state, require a bigger drop
    # in turbulence to exit (TURBULENCE_EXIT_PCTILE instead of TURBULENCE_THRESHOLD_PCTILE)
    prev = _previous_windham_state

    if prev and "turbulent" in prev:
        # Was turbulent → require a wider margin to call it "calm"
        is_turbulent = turbulence_pctile >= TURBULENCE_EXIT_PCTILE
    else:
        is_turbulent = turbulence_pctile >= TURBULENCE_THRESHOLD_PCTILE

    if prev and "fragile" in prev:
        # Was fragile → require a wider margin to call it "resilient"
        is_fragile = absorption_pctile >= ABSORPTION_EXIT_PCTILE
    else:
        is_fragile = absorption_pctile >= ABSORPTION_THRESHOLD_PCTILE

    if is_fragile and is_turbulent:
        state = "fragile-turbulent"
        label = "Crisis Mode"
        risk_level = "extreme"
        description = "Markets tightly coupled AND statistically unusual — active de-risking warranted"
        score_override = -1.0
    elif is_fragile and not is_turbulent:
        state = "fragile-calm"
        label = "Hidden Risk"
        risk_level = "high"
        description = "Markets appear calm but are tightly coupled — vulnerability building beneath the surface"
        score_override = -0.5
    elif not is_fragile and is_turbulent:
        state = "resilient-turbulent"
        label = "Idiosyncratic Shock"
        risk_level = "moderate"
        description = "Unusual market moves but well-diversified structure — likely a localized event"
        score_override = -0.3
    else:
        state = "resilient-calm"
        label = "Normal Markets"
        risk_level = "low"
        description = "Markets diversified and behaving normally — risk-on conditions"
        score_override = 0.5

    # Store current state for next evaluation
    _previous_windham_state = state

    return {
        "state": state,
        "label": label,
        "risk_level": risk_level,
        "description": description,
        "score": score_override,
    }


def _compute_systemic_layer() -> Dict[str, Any]:
    """
    Systemic risk layer using Turbulence Index + Absorption Ratio
    → Windham Capital 2x2 fragility classification.
    """
    result = {"score": 0.0, "signals": [], "details": {}}

    returns = _fetch_multi_asset_returns("1y")
    if returns is None:
        result["details"]["status"] = "insufficient_multi_asset_data"
        return result

    # ── Turbulence Index ───────────────────────────────────────────
    try:
        turb_current, turb_pctile, turb_series = _compute_turbulence_index(returns)
        result["details"]["turbulence_index"] = round(turb_current, 4)
        result["details"]["turbulence_percentile"] = round(turb_pctile, 1)

        turb_reading = "Normal"
        if turb_pctile > 90:
            turb_reading = "Extreme"
        elif turb_pctile > 75:
            turb_reading = "Elevated"
        elif turb_pctile > 50:
            turb_reading = "Above average"

        result["signals"].append({
            "name": "Turbulence Index",
            "value": f"{turb_current:.3f} ({turb_pctile:.0f}th %ile)",
            "reading": turb_reading,
            "bias": "bull" if turb_pctile < 50 else ("bear" if turb_pctile > 75 else "neutral"),
        })
    except Exception as e:
        logger.warning("Turbulence calculation failed: %s", e)
        turb_pctile = 50.0

    # ── Absorption Ratio ───────────────────────────────────────────
    try:
        ar_current, ar_pctile, ar_series = _compute_absorption_ratio(returns)
        result["details"]["absorption_ratio"] = round(ar_current, 4)
        result["details"]["absorption_percentile"] = round(ar_pctile, 1)

        ar_reading = "Diversified"
        if ar_pctile > 90:
            ar_reading = "Extremely coupled"
        elif ar_pctile > 80:
            ar_reading = "Tightly coupled"
        elif ar_pctile > 60:
            ar_reading = "Moderately coupled"

        result["signals"].append({
            "name": "Absorption Ratio",
            "value": f"{ar_current:.3f} ({ar_pctile:.0f}th %ile)",
            "reading": ar_reading,
            "bias": "bull" if ar_pctile < 60 else ("bear" if ar_pctile > 80 else "neutral"),
        })
    except Exception as e:
        logger.warning("Absorption ratio calculation failed: %s", e)
        ar_pctile = 50.0

    # ── Windham Fragility Classification ───────────────────────────
    windham = _windham_fragility_state(turb_pctile, ar_pctile)
    result["details"]["windham_state"] = windham["state"]
    result["details"]["windham_label"] = windham["label"]
    result["details"]["windham_risk_level"] = windham["risk_level"]
    result["details"]["windham_description"] = windham["description"]

    result["signals"].append({
        "name": "Windham Fragility",
        "value": windham["label"],
        "reading": windham["description"],
        "bias": "bull" if windham["score"] > 0 else ("bear" if windham["score"] < 0 else "neutral"),
    })

    result["score"] = windham["score"]

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Alpha Insights Generator
# ═══════════════════════════════════════════════════════════════════════════════
def _generate_alpha_insights(
    regime: str,
    composite_score: float,
    layers: Dict[str, Dict],
    windham_state: str,
) -> List[Dict[str, str]]:
    """
    Generate actionable alpha insights based on the regime state,
    layer signals, and Windham fragility classification.

    Each insight has: category, signal, action, conviction (high/medium/low)
    """
    insights = []

    # ── Windham-based insights ─────────────────────────────────────
    if windham_state == "fragile-calm":
        insights.append({
            "category": "Systemic Risk",
            "signal": "Fragile-Calm: markets appear calm but are tightly coupled",
            "action": "Reduce position sizes and add tail-risk hedges (put spreads, VIX calls). This state preceded the 2008 crash and COVID sell-off.",
            "conviction": "high",
        })
    elif windham_state == "fragile-turbulent":
        insights.append({
            "category": "Systemic Risk",
            "signal": "Fragile-Turbulent: crisis mode — markets coupled and dislocating",
            "action": "Maximum defensive posture. Raise cash, close leveraged positions, consider safe havens (TLT, GLD). Volatility selling is extremely dangerous here.",
            "conviction": "high",
        })
    elif windham_state == "resilient-turbulent":
        insights.append({
            "category": "Systemic Risk",
            "signal": "Resilient-Turbulent: idiosyncratic shock in a diversified market",
            "action": "Look for sector-specific dislocations to buy. Broad market structure is intact — this is often a mean-reversion opportunity.",
            "conviction": "medium",
        })

    # ── Trend-based insights ───────────────────────────────────────
    trend_score = layers.get("trend", {}).get("score", 0)
    trend_details = layers.get("trend", {}).get("details", {})

    if trend_score > 0.5 and regime == "bull":
        fast_mom = trend_details.get("fast_momentum_1m", 0)
        insights.append({
            "category": "Trend",
            "signal": f"Strong uptrend with {fast_mom:+.1f}% monthly momentum above golden cross",
            "action": "Stay long equities. Trend-following strategies favored. Consider adding on pullbacks to 50 SMA.",
            "conviction": "high",
        })
    elif trend_score < -0.5 and regime == "bear":
        insights.append({
            "category": "Trend",
            "signal": "Death cross confirmed with negative momentum",
            "action": "Favor defensive sectors and short-duration assets. Reduce equity beta exposure. Trend reversal signals not yet present.",
            "conviction": "high",
        })
    elif trend_score > 0 and layers.get("volatility", {}).get("score", 0) < -0.3:
        insights.append({
            "category": "Divergence",
            "signal": "Trend still positive but volatility spiking — potential regime transition",
            "action": "Tighten stops and reduce position sizes. The trend may be about to break — monitor 50 SMA for confirmation.",
            "conviction": "medium",
        })

    # ── Sentiment extremes ─────────────────────────────────────────
    sentiment_details = layers.get("sentiment", {}).get("details", {})
    fg_score = sentiment_details.get("fear_greed_score")

    if fg_score is not None:
        if fg_score < 20 and regime != "bear":
            insights.append({
                "category": "Sentiment",
                "signal": f"Extreme fear ({fg_score}) but regime is not bearish — contrarian opportunity",
                "action": "Historical data shows extreme fear readings with intact trends produce above-average forward returns. Consider adding risk selectively.",
                "conviction": "medium",
            })
        elif fg_score > 80 and regime == "bull":
            insights.append({
                "category": "Sentiment",
                "signal": f"Extreme greed ({fg_score}) in a bull regime — complacency risk",
                "action": "Don't sell the trend, but hedge tail risk. Put/call ratios at extremes historically precede 5-10% corrections.",
                "conviction": "medium",
            })

    # ── Yield curve / recession ────────────────────────────────────
    yc_details = layers.get("yield_credit", {}).get("details", {})
    recession_prob = yc_details.get("recession_probability")

    if recession_prob is not None and recession_prob > 70:
        insights.append({
            "category": "Macro",
            "signal": f"Estrella model: {recession_prob:.0f}% recession probability in 12 months",
            "action": "Overweight Treasuries and defensive equities (utilities, healthcare, staples). Reduce cyclical exposure. The yield curve has predicted every recession since 1960.",
            "conviction": "high",
        })
    elif recession_prob is not None and recession_prob < 15 and regime == "bull":
        insights.append({
            "category": "Macro",
            "signal": f"Low recession probability ({recession_prob:.0f}%) confirms bull regime",
            "action": "Economic expansion intact. Favor cyclicals and growth sectors. Credit conditions support risk-taking.",
            "conviction": "medium",
        })

    # ── Credit stress divergence ───────────────────────────────────
    hy_oas = yc_details.get("hy_oas")
    if hy_oas is not None and hy_oas > 5.0 and trend_score > 0:
        insights.append({
            "category": "Divergence",
            "signal": f"Credit stress ({hy_oas:.1f}% HY OAS) diverging from equity trend",
            "action": "Credit markets are a leading indicator. When credit stress rises while equities hold up, credit is usually right. Reduce risk.",
            "conviction": "high",
        })

    # Always add at least one insight
    if not insights:
        if regime == "bull":
            insights.append({
                "category": "Regime",
                "signal": "Bullish regime with no major divergences detected",
                "action": "Maintain standard risk allocation. All layers are aligned — low probability of imminent regime change.",
                "conviction": "medium",
            })
        elif regime == "bear":
            insights.append({
                "category": "Regime",
                "signal": "Bearish regime across multiple layers",
                "action": "Maintain defensive positioning. Wait for trend reversal signals (price reclaiming 50 SMA, VIX declining below 20) before adding risk.",
                "conviction": "medium",
            })
        else:
            insights.append({
                "category": "Regime",
                "signal": "Neutral/transitional regime — mixed signals across layers",
                "action": "Reduce directional bets and favor market-neutral strategies. Wait for signal alignment before taking large positions.",
                "conviction": "low",
            })

    return insights


# ═══════════════════════════════════════════════════════════════════════════════
# Main Regime Detection
# ═══════════════════════════════════════════════════════════════════════════════
def detect_regime(macro: dict, correlation_data: dict = None, history_data: dict = None) -> Dict[str, Any]:
    """
    Institutional-grade market regime detection.

    Uses 6 weighted signal layers + Windham Capital fragility classification
    to produce a single composite regime state with actionable alpha insights.

    The API signature is backward-compatible with the previous implementation.
    The `macro` dict from get_macro_data() is used for SPY price data;
    all other data comes from FRED and Yahoo Direct.

    Args:
        macro: Current macro indicators dict (from get_macro_data)
        correlation_data: Optional (legacy — now computed internally)
        history_data: Optional (legacy — now computed internally)

    Returns:
        {
            "regime": "bull" | "bear" | "neutral",
            "confidence": int (0-100),
            "composite_score": float (-1.0 to +1.0),
            "bull_score": int (legacy compat),
            "bear_score": int (legacy compat),
            "signals": [...],
            "layers": {layer_name: {score, signals, details}},
            "recession_probability": float,
            "correlation_regime": str,
            "macro_surprise_score": float,
            "fear_greed_index": dict | None,
            "windham": {state, label, risk_level, description},
            "systemic_risk": {turbulence_index, absorption_ratio, ...},
            "alpha_insights": [...],
            "data_sources": [...],
        }
    """
    now = time.time()
    cache_variant = "full" if macro.get("SPY", {}).get("price") else "fred_only"
    cache_key = f"regime_v2:{cache_variant}"

    with _cache_lock:
        if cache_key in _regime_cache:
            cached = _regime_cache[cache_key]
            if now - cached["ts"] < _CACHE_TTL:
                return cached["data"]

    data_sources: List[str] = []
    all_signals: List[Dict[str, Any]] = []

    # ── Fetch SPY history for trend layer ──────────────────────────
    spy_history = []
    try:
        spy_history = yahoo_direct.get_history("SPY", range_str="1y", interval="1d")
        if spy_history:
            data_sources.append("Yahoo:SPY_history")
    except Exception as e:
        logger.warning("Failed to fetch SPY history: %s", e)

    # ── Compute all 6 layers ───────────────────────────────────────
    layer_results = {}

    # Layer 1: Trend
    layer_results["trend"] = _compute_trend_layer(spy_history)
    if layer_results["trend"]["signals"]:
        data_sources.append("Yahoo:SPY_trend")

    # Layer 2: Volatility
    layer_results["volatility"] = _compute_volatility_layer()
    if layer_results["volatility"]["details"].get("vix") is not None:
        data_sources.append("FRED:VIX")

    # Layer 3: Yield Curve & Credit
    layer_results["yield_credit"] = _compute_yield_credit_layer()
    if layer_results["yield_credit"]["details"].get("yield_spread_10y3m") is not None:
        data_sources.append("FRED:YieldCurve")
    if layer_results["yield_credit"]["details"].get("hy_oas") is not None:
        data_sources.append("FRED:CreditSpread")

    # Layer 4: Sentiment
    layer_results["sentiment"] = _compute_sentiment_layer()
    if layer_results["sentiment"]["details"].get("fear_greed_score") is not None:
        data_sources.append("CNN:FearGreed")

    # Layer 5: Macro
    layer_results["macro"] = _compute_macro_layer()
    if layer_results["macro"]["signals"]:
        data_sources.append("FRED:Macro")

    # Layer 6: Systemic Risk
    layer_results["systemic"] = _compute_systemic_layer()
    if layer_results["systemic"]["details"].get("turbulence_index") is not None:
        data_sources.append("Yahoo:MultiAsset_Turbulence")

    # ── Weighted composite score ───────────────────────────────────
    composite_score = 0.0
    for layer_name, weight in LAYER_WEIGHTS.items():
        layer_score = layer_results.get(layer_name, {}).get("score", 0.0)
        composite_score += layer_score * weight

    composite_score = float(np.clip(composite_score, -1.0, 1.0))

    # ── Crisis / Fragility overrides ────────────────────────────────
    windham_state = layer_results.get("systemic", {}).get("details", {}).get("windham_state", "resilient-calm")
    windham_label = layer_results.get("systemic", {}).get("details", {}).get("windham_label", "Normal Markets")
    windham_risk = layer_results.get("systemic", {}).get("details", {}).get("windham_risk_level", "low")
    windham_desc = layer_results.get("systemic", {}).get("details", {}).get("windham_description", "")
    absorption_pctile = layer_results.get("systemic", {}).get("details", {}).get("absorption_percentile", 0)

    if windham_state == "fragile-turbulent":
        # Full crisis: force bear
        composite_score = min(composite_score, -0.5)
    elif windham_state == "fragile-calm" and absorption_pctile >= ABSORPTION_EXTREME_PCTILE:
        # Extreme hidden risk: absorption at 90th+ percentile means markets
        # are dangerously coupled even if turbulence is below threshold.
        # Apply a less aggressive but still bearish floor.
        composite_score = min(composite_score, -0.3)

    # ── Determine regime from composite score ──────────────────────
    if composite_score > 0.25:
        regime = "bull"
        confidence = int(min(95, 55 + composite_score * 40))
    elif composite_score < -0.25:
        regime = "bear"
        confidence = int(min(95, 55 + abs(composite_score) * 40))
    else:
        regime = "neutral"
        confidence = int(50 - abs(composite_score) * 20)

    # ── Aggregate signals from all layers ──────────────────────────
    for layer_name in LAYER_WEIGHTS:
        layer = layer_results.get(layer_name, {})
        for sig in layer.get("signals", []):
            sig["layer"] = layer_name
            all_signals.append(sig)

    # ── Legacy compatibility fields ────────────────────────────────
    bull_score = sum(1 for s in all_signals if s.get("bias") == "bull")
    bear_score = sum(1 for s in all_signals if s.get("bias") == "bear")

    # ── Extract key metrics for top-level access ───────────────────
    recession_prob = layer_results.get("yield_credit", {}).get("details", {}).get("recession_probability")
    fg_data = layer_results.get("sentiment", {}).get("details", {}).get("fear_greed_data")
    macro_surprise = layer_results.get("macro", {}).get("score", 0.0)

    # Correlation regime (from Windham state)
    correlation_regime = "normal"
    if windham_state in ("fragile-calm", "fragile-turbulent"):
        correlation_regime = "regime_shift"

    # ── Alpha insights ─────────────────────────────────────────────
    alpha_insights = _generate_alpha_insights(regime, composite_score, layer_results, windham_state)

    # ── Build result ───────────────────────────────────────────────
    result = {
        # Primary output
        "regime": regime,
        "confidence": confidence,
        "composite_score": round(composite_score, 3),

        # Layer breakdown (for detailed display)
        "layers": {
            name: {
                "score": round(layer.get("score", 0.0), 3),
                "weight": LAYER_WEIGHTS.get(name, 0),
                "weighted_contribution": round(layer.get("score", 0.0) * LAYER_WEIGHTS.get(name, 0), 3),
                "signals": layer.get("signals", []),
                "details": layer.get("details", {}),
            }
            for name, layer in layer_results.items()
        },

        # Windham Capital fragility classification
        "windham": {
            "state": windham_state,
            "label": windham_label,
            "risk_level": windham_risk,
            "description": windham_desc,
        },

        # Systemic risk detail
        "systemic_risk": {
            "turbulence_index": layer_results.get("systemic", {}).get("details", {}).get("turbulence_index"),
            "turbulence_percentile": layer_results.get("systemic", {}).get("details", {}).get("turbulence_percentile"),
            "absorption_ratio": layer_results.get("systemic", {}).get("details", {}).get("absorption_ratio"),
            "absorption_percentile": layer_results.get("systemic", {}).get("details", {}).get("absorption_percentile"),
        },

        # Alpha-generating insights
        "alpha_insights": alpha_insights,

        # All signals (flat list for backward compat)
        "signals": all_signals,

        # Legacy compatibility
        "bull_score": bull_score,
        "bear_score": bear_score,
        "recession_probability": round(recession_prob, 1) if recession_prob is not None else None,
        "correlation_regime": correlation_regime,
        "macro_surprise_score": round(macro_surprise, 2),
        "fear_greed_index": fg_data,
        "data_sources": list(set(data_sources)),
    }

    with _cache_lock:
        _regime_cache[cache_key] = {"ts": now, "data": result}

    return result
