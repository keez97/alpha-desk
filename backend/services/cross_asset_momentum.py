"""
Cross-Asset Momentum Spillover service for Morning Brief.

Data source cascade:
  1. yahoo_direct (v8 API — independent rate limiting)
  2. yfinance (library)
  3. stooq (EOD CSV)
  4. synthetic_estimator (FRED macro-based momentum model)

Analyzes 6 asset classes: SPY, TLT, GLD, USO, UUP, BTC-USD
Calculates 1-month and 3-month momentum with cross-asset signal generation.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

import yfinance as yf
import pandas as pd
import numpy as np

from backend.services.cache import cache
from backend.services import yfinance_service
from backend.services import yahoo_direct
from backend.services import stooq_service
from backend.services import synthetic_estimator
from backend.services.yfinance_service import _yf_session

logger = logging.getLogger(__name__)

# Cache TTL: 30 minutes for momentum data
CACHE_TTL_MOMENTUM = 30 * 60

# Asset class definitions
ASSETS = {
    "SPY": {"name": "S&P 500", "asset_class": "Equities"},
    "TLT": {"name": "US Bonds (7-10yr)", "asset_class": "Fixed Income"},
    "GLD": {"name": "Gold", "asset_class": "Commodities"},
    "USO": {"name": "Oil", "asset_class": "Commodities"},
    "UUP": {"name": "US Dollar", "asset_class": "Currencies"},
    "BTC-USD": {"name": "Bitcoin", "asset_class": "Crypto"},
}


def _calculate_momentum_from_prices(prices: List[float]) -> Dict[str, float]:
    """Calculate 1m and 3m momentum from a list of closing prices (oldest first)."""
    if len(prices) < 22:
        return {"momentum_1m": 0.0, "momentum_3m": 0.0}

    current = prices[-1]

    # 1-month (21 trading days)
    m1_start = prices[-22]
    momentum_1m = (current - m1_start) / m1_start if m1_start else 0

    # 3-month (63 trading days)
    if len(prices) >= 64:
        m3_start = prices[-64]
        momentum_3m = (current - m3_start) / m3_start if m3_start else 0
    else:
        momentum_3m = momentum_1m * 2  # Approximate

    return {"momentum_1m": float(momentum_1m), "momentum_3m": float(momentum_3m)}


def _determine_momentum_state(momentum_1m: float, momentum_3m: float) -> str:
    if momentum_1m > 0.02 or momentum_3m > 0.02:
        return "positive"
    elif momentum_1m < -0.02 or momentum_3m < -0.02:
        return "negative"
    return "neutral"


def _get_momentum_cascade(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get momentum data for a single ticker through the data source cascade.
    """
    info = ASSETS.get(ticker, {"name": ticker, "asset_class": "Unknown"})

    # --- Tier 1: yahoo_direct ---
    yd_hist = yahoo_direct.get_history(ticker, range_str="4mo")
    if len(yd_hist) >= 22:
        prices = [d["close"] for d in yd_hist]
        mom = _calculate_momentum_from_prices(prices)
        state = _determine_momentum_state(mom["momentum_1m"], mom["momentum_3m"])
        return {
            "ticker": ticker,
            "name": info["name"],
            "asset_class": info["asset_class"],
            "momentum_1m": round(mom["momentum_1m"], 5),
            "momentum_3m": round(mom["momentum_3m"], 5),
            "state": state,
            "data_source": "yahoo_direct",
        }

    # --- Tier 2: yfinance ---
    if time.time() >= yfinance_service._rate_limited_until:
        try:
            ticker_obj = yf.Ticker(ticker, session=_yf_session)
            hist = ticker_obj.history(period="4mo")
            if not hist.empty and len(hist) >= 22:
                prices = hist["Close"].tolist()
                mom = _calculate_momentum_from_prices(prices)
                state = _determine_momentum_state(mom["momentum_1m"], mom["momentum_3m"])
                return {
                    "ticker": ticker,
                    "name": info["name"],
                    "asset_class": info["asset_class"],
                    "momentum_1m": round(mom["momentum_1m"], 5),
                    "momentum_3m": round(mom["momentum_3m"], 5),
                    "state": state,
                    "data_source": "yfinance",
                }
        except Exception as e:
            logger.debug(f"yfinance momentum {ticker}: {e}")

    # --- Tier 3: stooq ---
    stooq_result = stooq_service.get_momentum(ticker)
    if stooq_result:
        state = _determine_momentum_state(stooq_result["momentum_1m"], stooq_result["momentum_3m"])
        return {
            "ticker": ticker,
            "name": info["name"],
            "asset_class": info["asset_class"],
            "momentum_1m": round(stooq_result["momentum_1m"], 5),
            "momentum_3m": round(stooq_result["momentum_3m"], 5),
            "state": state,
            "data_source": "stooq",
        }

    return None


def _generate_signals(assets_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate cross-asset predictive signals based on momentum combinations."""
    signals = []

    equity_data = next((a for a in assets_data if a["ticker"] == "SPY"), None)
    bond_data = next((a for a in assets_data if a["ticker"] == "TLT"), None)
    gold_data = next((a for a in assets_data if a["ticker"] == "GLD"), None)
    oil_data = next((a for a in assets_data if a["ticker"] == "USO"), None)
    dollar_data = next((a for a in assets_data if a["ticker"] == "UUP"), None)
    crypto_data = next((a for a in assets_data if a["ticker"] == "BTC-USD"), None)

    if not equity_data or not bond_data:
        return signals

    if bond_data["state"] == "positive":
        signals.append({
            "description": "Bond momentum positive — equity outlook favorable",
            "type": "bullish",
            "confidence": 0.7,
            "based_on": ["TLT"],
        })

    if bond_data["state"] == "positive" and equity_data["state"] == "negative":
        signals.append({
            "description": "Contrarian equity buy signal: Bond momentum positive vs equity weakness",
            "type": "bullish",
            "confidence": 0.8,
            "based_on": ["TLT", "SPY"],
        })

    if gold_data and gold_data["state"] == "positive" and equity_data["state"] == "negative":
        signals.append({
            "description": "Risk-off warning: Gold momentum positive with equity weakness",
            "type": "warning",
            "confidence": 0.75,
            "based_on": ["GLD", "SPY"],
        })

    if equity_data["state"] == "positive" and dollar_data and dollar_data["state"] == "negative":
        signals.append({
            "description": "Risk-on environment: Strong equity momentum with dollar weakness",
            "type": "bullish",
            "confidence": 0.65,
            "based_on": ["SPY", "UUP"],
        })

    if crypto_data and crypto_data["momentum_1m"] > 0.15 and equity_data["momentum_1m"] > 0.05:
        signals.append({
            "description": "Crypto-equity momentum spillover: Both breaking higher",
            "type": "bullish",
            "confidence": 0.6,
            "based_on": ["BTC-USD", "SPY"],
        })

    if oil_data and oil_data["state"] == "positive" and equity_data["state"] == "negative":
        signals.append({
            "description": "Inflation concern: Oil momentum rising while equities weaken",
            "type": "warning",
            "confidence": 0.65,
            "based_on": ["USO", "SPY"],
        })

    positive_count = sum(1 for a in assets_data if a["state"] == "positive")
    negative_count = sum(1 for a in assets_data if a["state"] == "negative")

    if positive_count >= 3 and equity_data["state"] == "positive":
        signals.append({
            "description": "Broad momentum alignment: Multiple asset classes rallying",
            "type": "bullish",
            "confidence": 0.75,
            "based_on": [a["ticker"] for a in assets_data if a["state"] == "positive"],
        })

    if negative_count >= 3 and equity_data["state"] == "negative":
        signals.append({
            "description": "Broad momentum weakness: Multiple asset classes declining",
            "type": "bearish",
            "confidence": 0.75,
            "based_on": [a["ticker"] for a in assets_data if a["state"] == "negative"],
        })

    return signals


def get_momentum_spillover() -> Dict[str, Any]:
    """
    Get cross-asset momentum spillover analysis.
    Uses 4-tier cascade: yahoo_direct → yfinance → stooq → synthetic estimation.
    """
    cache_key = "momentum_spillover:all"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    logger.info("Fetching momentum spillover data")

    assets_data = []
    data_sources = set()

    for ticker in ASSETS:
        result = _get_momentum_cascade(ticker)
        if result:
            assets_data.append(result)
            data_sources.add(result.get("data_source", "unknown"))

    # If we got at least 4 of 6 assets from live data
    if len(assets_data) >= 4:
        signals = _generate_signals(assets_data)
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": assets_data,
            "signals": signals,
            "matrix": {
                "positive_count": sum(1 for a in assets_data if a["state"] == "positive"),
                "negative_count": sum(1 for a in assets_data if a["state"] == "negative"),
                "neutral_count": sum(1 for a in assets_data if a["state"] == "neutral"),
            },
            "data_sources": list(data_sources),
        }
        cache.set(cache_key, result, CACHE_TTL_MOMENTUM)
        return result

    # --- Tier 4: Synthetic estimation from FRED macro ---
    logger.info("Using FRED-based synthetic estimation for momentum")
    estimated = synthetic_estimator.estimate_momentum()
    cache.set(cache_key, estimated, 15 * 60)
    return estimated
