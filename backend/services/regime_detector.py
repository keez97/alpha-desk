"""
Market Regime Detector for AlphaDesk.

Determines bull/bear/neutral regime from:
  - VIX level + percentile (FRED primary, yfinance fallback)
  - Yield curve slope (FRED 10Y-3M spread)
  - S&P 500 price action (yfinance)
  - Credit spreads (FRED HY OAS)
  - CNN Fear & Greed Index (consumer sentiment dimension)
  - Cross-asset correlations
  - Estrella probit recession probability
  - Macro surprise index
"""
import logging
import time
from typing import Dict, Any, List
import numpy as np
from scipy import stats as scipy_stats

from backend.services import fred_service
from backend.services import cnn_fear_greed

logger = logging.getLogger(__name__)

_regime_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes


def _calculate_normal_ranges() -> Dict[str, tuple]:
    """Define normal correlation ranges (historically stable)."""
    return {
        "spy_tlt": (0.0, 0.5),
        "spy_gld": (-0.3, 0.2),
        "vix_spy": (-0.75, -0.5),
    }


def _probit_recession_prob(yield_spread: float) -> float:
    """
    Estrella probit model: P(recession) = Φ(-0.6 - 0.82 * yield_spread)
    where Φ is the standard normal CDF.
    yield_spread = 10Y - 3M in percentage points
    """
    try:
        z = -0.6 - 0.82 * yield_spread
        prob = scipy_stats.norm.cdf(z)
        return min(100, max(0, prob * 100))
    except Exception as e:
        logger.warning(f"Error calculating recession probability: {e}")
        return 50.0


def _calculate_macro_surprise(current_val: float, history: List[float], window: int = 20) -> float:
    """
    Calculate macro surprise score.
    Returns z-score of current value vs 20-day moving average.
    """
    if not history or len(history) < window:
        return 0.0
    try:
        recent = history[-window:]
        ma = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0.0
        zscore = (current_val - ma) / std
        return min(3, max(-3, zscore))
    except Exception as e:
        logger.warning(f"Error calculating macro surprise: {e}")
        return 0.0


def _get_fred_enrichment() -> Dict[str, Any]:
    """
    Pull reliable macro data from FRED (no API key needed).

    Returns dict with vix, yield_spread_10y3m, credit_spread, vix_history.
    """
    enrichment: Dict[str, Any] = {}

    try:
        # VIX
        vix = fred_service.get_vix()
        if vix is not None:
            enrichment["vix"] = vix
            enrichment["vix_history"] = fred_service.get_vix_history(lookback_days=90)

        # Yield curve (10Y-3M spread) — the recession indicator
        spread = fred_service.get_yield_curve_spread()
        if spread is not None:
            enrichment["yield_spread_10y3m"] = spread

        # Credit spread (HY OAS)
        hy_oas = fred_service.get_credit_spread()
        if hy_oas is not None:
            enrichment["hy_credit_spread"] = hy_oas

        # Individual yields for display
        dgs10 = fred_service.get_latest("DGS10")
        dgs2 = fred_service.get_latest("DGS2")
        if dgs10 is not None:
            enrichment["treasury_10y"] = dgs10
        if dgs2 is not None:
            enrichment["treasury_2y"] = dgs2

    except Exception as e:
        logger.warning("FRED enrichment partially failed: %s", e)

    return enrichment


def detect_regime(macro: dict, correlation_data: dict = None, history_data: dict = None) -> Dict[str, Any]:
    """
    Detect market regime from macro data + FRED enrichment.

    Uses FRED as primary source for VIX, yield curve, and credit spreads
    (free, reliable, never rate-limited). Falls back to yfinance macro
    data when FRED is unavailable.

    Args:
        macro: Current macro indicators dict (from get_macro_data)
        correlation_data: Optional dict with historical correlations
        history_data: Optional dict with historical values

    Returns:
        Regime dict with regime, confidence, signals, recession_probability,
        correlation_regime, macro_surprise_score, data_sources
    """
    now = time.time()
    # Cache key includes whether SPY data is present so FRED-only vs full results don't collide
    cache_variant = "full" if macro.get("SPY", {}).get("price") else "fred_only"
    cache_key = f"regime:{cache_variant}"
    if cache_key in _regime_cache:
        cached = _regime_cache[cache_key]
        if now - cached["ts"] < _CACHE_TTL:
            return cached["data"]

    signals: List[Dict[str, Any]] = []
    bull_score = 0
    bear_score = 0
    data_sources: List[str] = []

    # Pull FRED data (reliable backbone)
    fred_data = _get_fred_enrichment()

    # ─── Signal 1: VIX level ──────────────────────────────────
    # Prefer FRED, fall back to yfinance macro dict
    vix = fred_data.get("vix")
    if vix is not None:
        data_sources.append("FRED:VIX")
    else:
        vix_entry = macro.get("^VIX", {})
        vix = vix_entry.get("price")
        if vix is not None:
            data_sources.append("yfinance:VIX")

    if vix is not None:
        if vix < 15:
            signals.append({"name": "VIX", "value": f"{vix:.1f}", "reading": "Low vol", "bias": "bull"})
            bull_score += 2
        elif vix < 20:
            signals.append({"name": "VIX", "value": f"{vix:.1f}", "reading": "Normal", "bias": "bull"})
            bull_score += 1
        elif vix < 25:
            signals.append({"name": "VIX", "value": f"{vix:.1f}", "reading": "Elevated", "bias": "neutral"})
        elif vix < 30:
            signals.append({"name": "VIX", "value": f"{vix:.1f}", "reading": "High", "bias": "bear"})
            bear_score += 1
        else:
            signals.append({"name": "VIX", "value": f"{vix:.1f}", "reading": "Panic", "bias": "bear"})
            bear_score += 2

    # ─── Signal 2: Yield curve + Recession Probability ────────
    yield_spread = fred_data.get("yield_spread_10y3m")
    recession_probability = 50.0

    if yield_spread is not None:
        data_sources.append("FRED:YieldCurve")
        recession_probability = _probit_recession_prob(yield_spread)

        if yield_spread < -0.5:
            signals.append({"name": "Yield Curve", "value": f"{yield_spread:+.2f}%", "reading": "Deep inversion", "bias": "bear"})
            bear_score += 2
        elif yield_spread < 0:
            signals.append({"name": "Yield Curve", "value": f"{yield_spread:+.2f}%", "reading": "Inverted", "bias": "bear"})
            bear_score += 1
        elif yield_spread < 0.5:
            signals.append({"name": "Yield Curve", "value": f"{yield_spread:+.2f}%", "reading": "Flat", "bias": "neutral"})
        else:
            signals.append({"name": "Yield Curve", "value": f"{yield_spread:+.2f}%", "reading": "Positive", "bias": "bull"})
            bull_score += 1
    else:
        # Fall back to yfinance
        tnx = macro.get("^TNX", {}).get("price")
        irx = macro.get("^IRX", {}).get("price")
        if tnx is not None and irx is not None:
            spread = tnx - irx
            recession_probability = _probit_recession_prob(spread)
            data_sources.append("yfinance:YieldCurve")

            if spread < -0.5:
                signals.append({"name": "Yield Curve", "value": f"{spread:+.2f}%", "reading": "Deep inversion", "bias": "bear"})
                bear_score += 2
            elif spread < 0:
                signals.append({"name": "Yield Curve", "value": f"{spread:+.2f}%", "reading": "Inverted", "bias": "bear"})
                bear_score += 1
            elif spread < 0.5:
                signals.append({"name": "Yield Curve", "value": f"{spread:+.2f}%", "reading": "Flat", "bias": "neutral"})
            else:
                signals.append({"name": "Yield Curve", "value": f"{spread:+.2f}%", "reading": "Positive", "bias": "bull"})
                bull_score += 1

    # ─── Signal 3: S&P 500 price action (yfinance only) ──────
    spy = macro.get("SPY", {})
    spy_chg = spy.get("pct_change", 0) or spy.get("daily_pct_change", 0) or 0
    spy_price = spy.get("price")
    if spy_price:
        if spy_chg > 0.5:
            signals.append({"name": "S&P 500", "value": f"{spy_chg:+.2f}%", "reading": "Rallying", "bias": "bull"})
            bull_score += 1
        elif spy_chg < -0.5:
            signals.append({"name": "S&P 500", "value": f"{spy_chg:+.2f}%", "reading": "Selling", "bias": "bear"})
            bear_score += 1
        else:
            signals.append({"name": "S&P 500", "value": f"{spy_chg:+.2f}%", "reading": "Flat", "bias": "neutral"})

    # ─── Signal 4: Credit spread (FRED HY OAS) ───────────────
    hy_spread = fred_data.get("hy_credit_spread")
    if hy_spread is not None:
        data_sources.append("FRED:CreditSpread")
        if hy_spread > 5.0:
            signals.append({"name": "HY Spread", "value": f"{hy_spread:.2f}%", "reading": "Stress", "bias": "bear"})
            bear_score += 2
        elif hy_spread > 4.0:
            signals.append({"name": "HY Spread", "value": f"{hy_spread:.2f}%", "reading": "Widening", "bias": "bear"})
            bear_score += 1
        elif hy_spread < 3.0:
            signals.append({"name": "HY Spread", "value": f"{hy_spread:.2f}%", "reading": "Tight", "bias": "bull"})
            bull_score += 1
        else:
            signals.append({"name": "HY Spread", "value": f"{hy_spread:.2f}%", "reading": "Normal", "bias": "neutral"})
    else:
        # Fall back to gold as haven proxy
        gold = macro.get("GC=F", {}).get("price")
        if gold and vix:
            if gold > 2500 and vix > 25:
                signals.append({"name": "Haven Demand", "value": f"${gold:,.0f}", "reading": "Strong", "bias": "bear"})
                bear_score += 1
            elif gold > 2400 and vix > 20:
                signals.append({"name": "Haven Demand", "value": f"${gold:,.0f}", "reading": "Moderate", "bias": "neutral"})
            else:
                signals.append({"name": "Haven Demand", "value": f"${gold:,.0f}", "reading": "Low", "bias": "bull"})

    # ─── Signal 5: Cross-asset correlation regime ─────────────
    correlation_regime = "normal"
    if correlation_data:
        try:
            normal_ranges = _calculate_normal_ranges()
            shift_score = 0

            for pair, (lo, hi) in normal_ranges.items():
                val = correlation_data.get(pair, (lo + hi) / 2)
                if val < lo or val > hi:
                    shift_score += 1

            if shift_score >= 2:
                correlation_regime = "regime_shift"
                bear_score += 1
        except Exception as e:
            logger.warning(f"Error analyzing correlation regime: {e}")

    # ─── Signal 6: Macro surprise index ───────────────────────
    macro_surprise_score = 0.0
    vix_history = fred_data.get("vix_history", [])
    if vix and vix_history and len(vix_history) >= 20:
        macro_surprise_score = _calculate_macro_surprise(vix, vix_history)
    elif history_data:
        try:
            vix_hist_yf = history_data.get("^VIX", [])
            if vix and vix_hist_yf:
                macro_surprise_score = _calculate_macro_surprise(vix, vix_hist_yf)
        except Exception as e:
            logger.warning(f"Error calculating macro surprise: {e}")

    # ─── Signal 7: CNN Fear & Greed Index ─────────────────────
    fear_greed_data = None
    try:
        fear_greed_data = cnn_fear_greed.get_fear_greed()
    except Exception as e:
        logger.debug("CNN Fear & Greed fetch failed: %s", e)

    if fear_greed_data and fear_greed_data.get("score") is not None:
        fg_score = fear_greed_data["score"]
        fg_class = fear_greed_data.get("classification", "Unknown")
        data_sources.append("CNN:FearGreed")

        if fg_score >= 75:
            signals.append({"name": "Fear & Greed", "value": f"{fg_score}", "reading": fg_class, "bias": "bull"})
            bull_score += 1
        elif fg_score >= 55:
            signals.append({"name": "Fear & Greed", "value": f"{fg_score}", "reading": fg_class, "bias": "bull"})
            bull_score += 1
        elif fg_score <= 25:
            signals.append({"name": "Fear & Greed", "value": f"{fg_score}", "reading": fg_class, "bias": "bear"})
            bear_score += 2
        elif fg_score <= 45:
            signals.append({"name": "Fear & Greed", "value": f"{fg_score}", "reading": fg_class, "bias": "bear"})
            bear_score += 1
        else:
            signals.append({"name": "Fear & Greed", "value": f"{fg_score}", "reading": fg_class, "bias": "neutral"})

    # ─── Determine regime ─────────────────────────────────────
    net = bull_score - bear_score
    if net >= 3:
        regime = "bull"
        confidence = min(95, 60 + net * 8)
    elif net >= 1:
        regime = "bull"
        confidence = min(80, 50 + net * 10)
    elif net <= -3:
        regime = "bear"
        confidence = min(95, 60 + abs(net) * 8)
    elif net <= -1:
        regime = "bear"
        confidence = min(80, 50 + abs(net) * 10)
    else:
        regime = "neutral"
        confidence = 50

    result = {
        "regime": regime,
        "confidence": confidence,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "signals": signals,
        "recession_probability": round(recession_probability, 1),
        "correlation_regime": correlation_regime,
        "macro_surprise_score": round(macro_surprise_score, 2),
        "fear_greed_index": fear_greed_data if fear_greed_data else None,
        "data_sources": data_sources,
    }

    _regime_cache[cache_key] = {"ts": now, "data": result}
    return result
