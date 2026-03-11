"""
Options Flow & Gamma Exposure service for Morning Brief.

Data source cascade:
  1. CBOE CDN (SPX options with real Greeks — free, delayed 15min)
  2. yfinance (SPY options chain — when not rate-limited)
  3. synthetic_estimator (VIX-regime-based statistical model)

Implements:
  1. Implied Volatility Skew (IVSKEW): IV of OTM puts vs OTM calls
  2. Put-Call Volume Ratio (CPIV): Total put volume / total call volume
  3. Options Volume Imbalance: Net call vs put volume ratio
  4. GEX Approximation: Gamma exposure signal based on OI and Greeks
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

import yfinance as yf
import pandas as pd
import numpy as np

from backend.services.cache import cache
from backend.services import yfinance_service
from backend.services import fred_service
from backend.services import cboe_service
from backend.services import synthetic_estimator
from backend.services.yfinance_service import _yf_session

logger = logging.getLogger(__name__)

# Cache TTL: 15 minutes for options data
CACHE_TTL_OPTIONS = 15 * 60


def _approximate_gamma(S: float, K: float, T: float, sigma: float, r: float = 0.045) -> float:
    """
    Approximate gamma using Black-Scholes formula.
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    try:
        from scipy.stats import norm

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return float(gamma)
    except Exception as e:
        logger.debug(f"Error calculating gamma: {e}")
        return 0.01 / S


def _get_option_chain_yfinance(ticker: str = "SPY") -> Optional[Dict[str, pd.DataFrame]]:
    """Fetch options chain from yfinance."""
    try:
        if time.time() < yfinance_service._rate_limited_until:
            return None

        ticker_obj = yf.Ticker(ticker, session=_yf_session)
        expirations = ticker_obj.options
        if not expirations:
            return None

        nearest_expiry = expirations[0]
        option_chain = ticker_obj.option_chain(nearest_expiry)

        return {
            "calls": option_chain.calls,
            "puts": option_chain.puts,
            "expiry": nearest_expiry,
        }
    except Exception as e:
        logger.error(f"yfinance options chain {ticker}: {e}")
        return None


def _calculate_from_yfinance(ticker: str, spot_price: float) -> Optional[Dict[str, Any]]:
    """Calculate metrics from yfinance options chain."""
    option_chain = _get_option_chain_yfinance(ticker)
    if option_chain is None:
        return None

    calls = option_chain.get("calls", pd.DataFrame())
    puts = option_chain.get("puts", pd.DataFrame())

    if calls.empty or puts.empty:
        return None

    # IV Skew
    iv_skew = 0.0
    if "impliedVolatility" in calls.columns:
        otm_calls = calls[calls["strike"] > spot_price * 1.02].copy()
        otm_puts = puts[puts["strike"] < spot_price * 0.98].copy()
        otm_calls = otm_calls[otm_calls["impliedVolatility"] > 0]
        otm_puts = otm_puts[otm_puts["impliedVolatility"] > 0]

        if not otm_calls.empty and not otm_puts.empty:
            avg_call_iv = otm_calls["impliedVolatility"].iloc[:3].mean()
            avg_put_iv = otm_puts["impliedVolatility"].iloc[-3:].mean()
            if avg_call_iv > 0:
                iv_skew = float(np.clip((avg_put_iv - avg_call_iv) / avg_call_iv, -1, 1))

    # Put-call ratio
    total_call_volume = int(calls["volume"].sum()) if "volume" in calls.columns else 0
    total_put_volume = int(puts["volume"].sum()) if "volume" in puts.columns else 0
    put_call_ratio = total_put_volume / max(total_call_volume, 1)
    volume_imbalance = total_call_volume / max(total_put_volume, 1)

    total_call_oi = int(calls["openInterest"].sum()) if "openInterest" in calls.columns else 0
    total_put_oi = int(puts["openInterest"].sum()) if "openInterest" in puts.columns else 0

    # GEX
    gex_signal, gex_value = _calculate_gex_from_chain(calls, puts, spot_price)

    # Overall signal
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
        details.append(f"GEX positive ({gex_value:.0f})")
    elif gex_signal == "negative":
        score -= 1
        details.append(f"GEX negative ({gex_value:.0f})")

    if volume_imbalance > 1.2:
        score += 0.5
        details.append(f"Call dominance ({volume_imbalance:.2f}x)")

    signal = "bullish" if score > 1 else ("bearish" if score < -1 else "neutral")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "ticker": ticker,
        "spot_price": float(spot_price),
        "iv_skew": float(iv_skew),
        "put_call_ratio": float(put_call_ratio),
        "volume_imbalance": float(volume_imbalance),
        "gex_signal": gex_signal,
        "gex_value": float(gex_value),
        "total_call_volume": total_call_volume,
        "total_put_volume": total_put_volume,
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "signal": signal,
        "details": details,
        "expiry": option_chain.get("expiry", "unknown"),
        "data_source": "yfinance",
    }


def _calculate_gex_from_chain(calls, puts, spot_price, days_to_expiry=1):
    """Calculate GEX from yfinance chain using Black-Scholes gamma approx."""
    try:
        T = days_to_expiry / 365.0
        r = 0.045

        call_gex = 0.0
        put_gex = 0.0

        for _, row in calls[calls["openInterest"] > 0].iterrows():
            if pd.isna(row.get("impliedVolatility", 0)):
                continue
            gamma = _approximate_gamma(spot_price, row["strike"], T, row["impliedVolatility"], r)
            call_gex += gamma * row["openInterest"]

        for _, row in puts[puts["openInterest"] > 0].iterrows():
            if pd.isna(row.get("impliedVolatility", 0)):
                continue
            gamma = _approximate_gamma(spot_price, row["strike"], T, row["impliedVolatility"], r)
            put_gex += gamma * row["openInterest"]

        net_gex = (call_gex - put_gex) * spot_price * 100

        if net_gex > 100:
            return ("positive", float(net_gex))
        elif net_gex < -100:
            return ("negative", float(net_gex))
        return ("neutral", float(net_gex))
    except Exception:
        return ("neutral", 0.0)


def get_options_flow(ticker: str = "SPY") -> Dict[str, Any]:
    """
    Get options flow analysis.

    Cascade: CBOE CDN (SPX) → yfinance (SPY) → synthetic estimation
    """
    cache_key = f"options_flow:{ticker}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    logger.info(f"Fetching options flow data for {ticker}")

    # --- Tier 1: CBOE CDN (SPX options with real Greeks) ---
    if cboe_service.is_available():
        cboe_metrics = cboe_service.get_options_metrics()
        if cboe_metrics is not None:
            # Enrich with FRED VIX
            fred_vix = fred_service.get_vix()
            if fred_vix is not None:
                cboe_metrics["fred_vix"] = fred_vix
            logger.info("Options flow from CBOE CDN: %s", cboe_metrics.get("signal"))
            cache.set(cache_key, cboe_metrics, CACHE_TTL_OPTIONS)
            return cboe_metrics

    # --- Tier 2: yfinance ---
    # Get spot price first
    spot_price = None
    try:
        from backend.services import yahoo_direct
        yd_quote = yahoo_direct.get_quote(ticker)
        if yd_quote:
            spot_price = yd_quote["price"]
    except Exception:
        pass

    if spot_price is None:
        try:
            ticker_obj = yf.Ticker(ticker, session=_yf_session)
            hist = ticker_obj.history(period="1d")
            if not hist.empty:
                spot_price = float(hist["Close"].iloc[-1])
        except Exception:
            pass

    if spot_price is not None:
        yf_result = _calculate_from_yfinance(ticker, spot_price)
        if yf_result is not None:
            fred_vix = fred_service.get_vix()
            if fred_vix is not None:
                yf_result["fred_vix"] = fred_vix
            cache.set(cache_key, yf_result, CACHE_TTL_OPTIONS)
            return yf_result

    # --- Tier 3: Synthetic estimation from VIX regime ---
    logger.info("Using VIX-regime synthetic estimation for options flow")
    estimated = synthetic_estimator.estimate_options_flow()

    # Try to get spot price for enrichment
    if spot_price is not None:
        estimated["spot_price"] = spot_price

    cache.set(cache_key, estimated, 10 * 60)  # Shorter TTL for estimates
    return estimated
