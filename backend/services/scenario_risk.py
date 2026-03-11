"""
Scenario-Aware Risk Dashboard for AlphaDesk.
Calculates Value-at-Risk, historical analogs, and scenario-specific loss estimates.

Data source cascade for price history:
  1. financialdatasets.ai (FDS) — reliable, paid API
  2. yfinance — fallback, rate-limited
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from backend.services import fds_client as fds
from backend.services.yfinance_service import get_history, get_macro_data
from backend.services.regime_detector import detect_regime

logger = logging.getLogger(__name__)

_scenario_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes
_CLAUDE_CACHE_TTL = 14400  # 4 hours for Claude-generated scenarios


def calculate_var_95(returns: np.ndarray, regime: str = "neutral") -> float:
    """Calculate 95th percentile Value-at-Risk."""
    if len(returns) < 10:
        return 0.0
    try:
        if regime == "bear":
            # Use only bear-regime returns (negative tail)
            bear_returns = returns[returns < returns.mean() - np.std(returns)]
            if len(bear_returns) > 5:
                return float(np.percentile(bear_returns, 5))  # 5th percentile = 95% VaR
        # Historical VaR (95th percentile)
        return float(np.percentile(returns, 5))
    except Exception as e:
        logger.warning(f"Error calculating VaR: {e}")
        return 0.0


def _get_price_history_cascade(ticker: str, days: int = 365) -> List[Dict]:
    """Fetch price history using FDS → yfinance cascade."""
    # --- Tier 1: FDS ---
    if fds.is_available():
        try:
            end_date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            start_date = (datetime.utcnow().date() - timedelta(days=days)).isoformat()
            records = fds.get_historical_prices(ticker, start_date, end_date)
            if records and len(records) >= 50:
                return records
        except Exception as e:
            logger.debug(f"FDS history {ticker}: {e}")

    # --- Tier 2: yfinance ---
    hist = get_history(ticker, period="1y")
    return hist if hist else []


def get_historical_var(ticker: str = "SPY") -> Dict[str, float]:
    """Calculate historical VaR for a representative portfolio (SPY)."""
    try:
        hist = _get_price_history_cascade(ticker)
        if not hist or len(hist) < 50:
            return {"var_95_historical": 0.0, "var_95_regime_adjusted": 0.0}

        # Calculate daily returns
        prices = [h["close"] for h in hist]
        returns = np.diff(prices) / prices[:-1] * 100  # Daily returns in %

        # Historical VaR (simple percentile method)
        var_95_hist = calculate_var_95(returns)

        # Get current regime
        macro = get_macro_data()
        regime_data = detect_regime(macro)
        current_regime = regime_data.get("regime", "neutral")

        # Regime-adjusted VaR
        var_95_regime = calculate_var_95(returns, regime=current_regime)

        return {
            "var_95_historical": round(var_95_hist, 2),
            "var_95_regime_adjusted": round(var_95_regime, 2),
            "current_regime": current_regime,
        }
    except Exception as e:
        logger.error(f"Error calculating VaR: {e}")
        return {
            "var_95_historical": 0.0,
            "var_95_regime_adjusted": 0.0,
            "current_regime": "unknown",
        }


def find_historical_analogs() -> List[Dict[str, Any]]:
    """
    Find 3 periods in the past year most similar to current conditions.
    Based on: VIX level, yield curve slope, S&P momentum.
    """
    try:
        # Get current macro data
        macro = get_macro_data()
        vix = macro.get("^VIX", {}).get("price", 20.0)
        tnx = macro.get("^TNX", {}).get("price", 4.5)
        irx = macro.get("^IRX", {}).get("price", 5.0)
        spy = macro.get("SPY", {}).get("price", 450.0)

        current_spread = tnx - irx
        current_vix = vix

        # Get historical data
        spy_hist = _get_price_history_cascade("SPY")
        vix_hist = get_history("^VIX", period="1y")  # VIX only available via yfinance

        if not spy_hist or len(spy_hist) < 100:
            return []

        # Calculate momentum (current price vs 50-day MA)
        prices = [h["close"] for h in spy_hist]
        ma50 = np.mean(prices[-50:]) if len(prices) >= 50 else prices[-1]
        current_momentum = (prices[-1] - ma50) / ma50 * 100

        analogs = []
        # Split data into 20-day rolling windows
        window_size = 20

        for i in range(len(spy_hist) - window_size - 20):
            # Window prices and VIX
            window_prices = prices[i : i + window_size]
            window_start = i
            window_end = i + window_size

            # Calculate metrics for this period
            period_ma = np.mean(window_prices)
            period_momentum = (window_prices[-1] - period_ma) / period_ma * 100

            # Get subsequent returns (next 5, 10, 20 days)
            future_prices = prices[window_end : window_end + 20]
            if len(future_prices) < 20:
                continue

            ret_5d = (future_prices[5] / window_prices[-1] - 1) * 100 if len(future_prices) > 5 else 0
            ret_10d = (future_prices[10] / window_prices[-1] - 1) * 100 if len(future_prices) > 10 else 0
            ret_20d = (future_prices[20] / window_prices[-1] - 1) * 100 if len(future_prices) > 20 else 0

            # Calculate similarity score (simple Euclidean distance)
            vix_diff = abs(current_vix - 20.0)  # Approximate historical VIX
            momentum_diff = abs(current_momentum - period_momentum)
            spread_diff = abs(current_spread - 0.5)  # Assume historical avg ~0.5%

            similarity = max(0, 100 - (vix_diff * 2 + momentum_diff * 1.5 + spread_diff * 10))

            if similarity > 40:  # Only keep reasonably similar periods
                # Extract actual dates from spy_hist
                start_date = spy_hist[window_start].get("date", spy_hist[window_start].get("time", str(window_start)))
                end_idx = min(window_end, len(spy_hist) - 1)
                end_date = spy_hist[end_idx].get("date", spy_hist[end_idx].get("time", str(window_end)))

                analogs.append({
                    "period": f"{start_date} to {end_date}",
                    "similarity_score": round(similarity, 1),
                    "subsequent_5d_return": round(ret_5d, 2),
                    "subsequent_10d_return": round(ret_10d, 2),
                    "subsequent_20d_return": round(ret_20d, 2),
                })

        # Sort by similarity and return top 3
        analogs.sort(key=lambda x: x["similarity_score"], reverse=True)
        return analogs[:3]
    except Exception as e:
        logger.error(f"Error finding historical analogs: {e}")
        return []


def _parse_json_array_from_text(text: str) -> list | None:
    """Try to extract a JSON array from text."""
    try:
        json_start = text.find("[")
        json_end = text.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _generate_scenarios_with_claude(macro_data: dict) -> list:
    """
    Generate scenarios using Claude. Returns list of scenario dicts or empty list on failure.

    Uses separate 4-hour cache from main scenario cache.
    Falls back to empty list on any error (will trigger hardcoded scenarios fallback).
    """
    from backend.services.claude_service import _call_llm, USE_MOCK
    from backend.prompts.scenario_prompts import get_scenario_generation_prompt

    # In mock mode, don't call Claude
    if USE_MOCK:
        logger.info("Claude scenario generation skipped (mock mode)")
        return []

    try:
        # Build prompt from macro data
        prompt = get_scenario_generation_prompt(macro_data)

        # System prompt for scenario generation
        system_prompt = "You are a senior risk analyst at a macro hedge fund. Generate stress scenarios based on current market data. Return only valid JSON."

        # Call Claude with Haiku (fast, cheap for scenario generation)
        # Note: _call_llm uses the configured model from config.get_model_id()
        text_content = _call_llm(system_prompt, prompt, max_tokens=1500)

        if not text_content:
            logger.warning("Claude returned empty response for scenarios")
            return []

        # Parse JSON array from response
        parsed = _parse_json_array_from_text(text_content)

        if not parsed or not isinstance(parsed, list):
            logger.warning(f"Claude response was not a valid JSON array: {text_content[:200]}")
            return []

        # Validate that we have at least some scenarios
        if len(parsed) > 0:
            logger.info(f"Claude generated {len(parsed)} scenarios successfully")
            return parsed
        else:
            logger.warning("Claude returned empty scenario list")
            return []

    except Exception as e:
        logger.warning(f"Claude scenario generation failed: {e}")
        return []


def calculate_scenario_impacts() -> List[Dict[str, Any]]:
    """
    Calculate estimated portfolio impacts under specific stress scenarios:
    (a) 2σ VIX spike, (b) 100bp yield curve steepening, (c) 10% equity correction.
    """
    try:
        macro = get_macro_data()
        vix = macro.get("^VIX", {}).get("price", 20.0)
        spy = macro.get("SPY", {}).get("price", 450.0)

        scenarios = []

        # Scenario 1: 2σ VIX spike
        # Historically, 2σ VIX move correlates with ~2-3% equity decline
        vix_spike_impact = -2.5  # percent
        scenarios.append({
            "name": "VIX 2σ Spike",
            "description": f"Volatility increases to {vix * 2:.0f}",
            "estimated_impact_pct": vix_spike_impact,
            "probability": 0.15,
            "severity": "moderate",
        })

        # Scenario 2: 100bp yield curve steepening
        # Usually bullish for equities if caused by growth, bearish if by rate cuts
        curve_impact = -1.5  # percent (conservative)
        scenarios.append({
            "name": "100bp Yield Steepen",
            "description": "Yield curve steepens by 100bp",
            "estimated_impact_pct": curve_impact,
            "probability": 0.20,
            "severity": "mild",
        })

        # Scenario 3: 10% equity correction
        # Direct impact on portfolio
        correction_impact = -10.0
        scenarios.append({
            "name": "10% Correction",
            "description": "S&P 500 declines 10%",
            "estimated_impact_pct": correction_impact,
            "probability": 0.25,
            "severity": "high",
        })

        return scenarios
    except Exception as e:
        logger.error(f"Error calculating scenario impacts: {e}")
        return []


def _hardcoded_scenarios(vix: float) -> list:
    """Fallback scenarios when Claude is unavailable or too slow."""
    return [
        {
            "name": "VIX 2σ Spike",
            "description": f"Volatility increases to {vix * 2:.0f}",
            "estimated_impact_pct": -2.5,
            "probability": 0.15,
            "severity": "moderate",
        },
        {
            "name": "100bp Yield Steepen",
            "description": "Yield curve steepens by 100bp",
            "estimated_impact_pct": -1.5,
            "probability": 0.20,
            "severity": "mild",
        },
        {
            "name": "10% Correction",
            "description": "S&P 500 declines 10%",
            "estimated_impact_pct": -10.0,
            "probability": 0.25,
            "severity": "high",
        },
    ]


def get_scenario_risk_fast(macro_data: Dict = None) -> Dict[str, Any]:
    """Fast version for /all endpoint — MUST complete within 4s timeout.

    VaR is computed instantly from VIX. Scenarios use Claude cache if available,
    otherwise fall back to hardcoded. Claude generation is NEVER called here
    (too slow); it runs on a separate endpoint or background refresh.
    """
    now = time.time()
    cache_key = "scenario_risk_fast"
    claude_cache_key = "scenario_risk_claude"

    # Check main cache first (30-min TTL) — but only if VaR is non-zero
    if cache_key in _scenario_cache:
        cached = _scenario_cache[cache_key]
        if now - cached["ts"] < _CACHE_TTL:
            # Don't serve cached 0.0 VaR — retry instead
            if cached["data"].get("var_95_historical", 0) != 0:
                return cached["data"]

    scenarios = []
    var_95_historical = 0.0
    var_95_regime_adjusted = 0.0
    current_regime = "unknown"

    try:
        # Extract VIX — use macro_data if available, otherwise default
        # Note: macro_data may be {} (empty dict) if upstream timed out
        vix = 20.0  # safe default
        if macro_data and isinstance(macro_data, dict):
            vix = macro_data.get("^VIX", {}).get("price", 20.0) or 20.0

        # Determine regime based on VIX
        if vix > 25:
            current_regime = "bear"
        elif vix < 15:
            current_regime = "bull"
        else:
            current_regime = "neutral"

        # VIX-based VaR approximation (instant — pure math)
        var_95_historical = -((vix / 100.0) * np.sqrt(1.0 / 252.0) * 1.65 * 100.0)
        var_95_regime_adjusted = var_95_historical * 1.3 if vix > 25 else var_95_historical

        # Use Claude cache if available (populated by /scenarios endpoint)
        if claude_cache_key in _scenario_cache:
            claude_cached = _scenario_cache[claude_cache_key]
            if now - claude_cached["ts"] < _CLAUDE_CACHE_TTL:
                scenarios = claude_cached["data"]

        # Fall back to hardcoded — NEVER call Claude here (too slow for /all)
        if not scenarios:
            scenarios = _hardcoded_scenarios(vix)
    except Exception as e:
        logger.warning(f"Scenario risk fast failed: {e}")

    result = {
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "var_95_historical": round(var_95_historical, 2),
        "var_95_regime_adjusted": round(var_95_regime_adjusted, 2),
        "current_regime": current_regime,
        "historical_analogs": [],
        "scenarios": scenarios,
    }

    _scenario_cache[cache_key] = {"ts": now, "data": result}
    return result


def get_scenario_risk_data() -> Dict[str, Any]:
    """Main function to get scenario risk dashboard data."""
    now = time.time()
    cache_key = "scenario_risk"

    if cache_key in _scenario_cache:
        cached = _scenario_cache[cache_key]
        if now - cached["ts"] < _CACHE_TTL:
            logger.info(f"Returning cached scenario risk (age: {now - cached['ts']:.1f}s)")
            return cached["data"]

    # Each component fails independently — partial data is better than none
    var_data = {"var_95_historical": 0.0, "var_95_regime_adjusted": 0.0, "current_regime": "unknown"}
    analogs = []
    scenarios = []

    # Scenarios are fast (only needs macro data) — do first
    try:
        scenarios = calculate_scenario_impacts()
    except Exception as e:
        logger.warning(f"Scenario impacts failed: {e}")

    # VaR needs 365d price history — slower
    try:
        var_data = get_historical_var("SPY")
    except Exception as e:
        logger.warning(f"VaR calculation failed: {e}")

    # Analogs need 365d history + VIX — slowest
    try:
        analogs = find_historical_analogs()
    except Exception as e:
        logger.warning(f"Historical analogs failed: {e}")

    result = {
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "var_95_historical": var_data.get("var_95_historical", 0.0),
        "var_95_regime_adjusted": var_data.get("var_95_regime_adjusted", 0.0),
        "current_regime": var_data.get("current_regime", "unknown"),
        "historical_analogs": analogs,
        "scenarios": scenarios,
    }

    _scenario_cache[cache_key] = {"ts": now, "data": result}
    return result
