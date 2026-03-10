import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging
from backend.services.data_provider import get_history

logger = logging.getLogger(__name__)

# Reference ranges for percentile calculation (based on typical market values)
REFERENCE_RANGES = {
    "momentum": {
        "min": -100,
        "max": 100,
        "percentile_thresholds": {"weak": 33, "neutral": 67}
    },
    "volatility": {
        "min": 5,
        "max": 50,
        "percentile_thresholds": {"weak": 33, "neutral": 67}
    },
    "mean_reversion": {
        "min": 0.85,
        "max": 1.15,
        "percentile_thresholds": {"weak": 33, "neutral": 67}
    },
    "volume_profile": {
        "min": 0.5,
        "max": 2.5,
        "percentile_thresholds": {"weak": 33, "neutral": 67}
    }
}


def calculate_stock_factors(ticker: str) -> List[Dict[str, Any]]:
    """Calculate factor exposures for a stock."""
    try:
        # Fetch price history
        history = get_history(ticker, period="1y")
        if not history or len(history) < 30:
            logger.warning(f"Insufficient data for {ticker}")
            return []

        # Convert to DataFrame
        dates = [h["date"] for h in history]
        closes = [h["close"] for h in history]
        volumes = [h["volume"] for h in history]

        df = pd.DataFrame({
            "date": pd.to_datetime(dates),
            "close": closes,
            "volume": volumes
        })

        df = df.sort_values("date")

        # Calculate returns
        df["returns"] = df["close"].pct_change() * 100

        # 1. Momentum: 12M return minus 1M return (12-1 momentum)
        momentum_12m = ((df["close"].iloc[-1] / df["close"].iloc[0]) - 1) * 100
        momentum_1m = ((df["close"].iloc[-1] / df["close"].iloc[-22]) - 1) * 100 if len(df) >= 22 else momentum_12m
        momentum = momentum_12m - momentum_1m

        # 2. Volatility: 30-day rolling standard deviation of returns, annualized
        volatility_30d = df["returns"].tail(30).std()
        volatility = volatility_30d * np.sqrt(252)  # Annualize

        # 3. Mean Reversion: current price vs 200-day SMA ratio
        sma_200 = df["close"].tail(200).mean() if len(df) >= 200 else df["close"].mean()
        current_price = df["close"].iloc[-1]
        mean_reversion = current_price / sma_200

        # 4. Volume Profile: current volume vs 20-day average
        avg_volume_20d = df["volume"].tail(20).mean()
        current_volume = df["volume"].iloc[-1]
        volume_profile = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1.0

        # Calculate percentiles based on reference ranges
        factors = [
            {
                "name": "Momentum (12-1)",
                "value": round(momentum, 2),
                "percentile": _calculate_percentile(momentum, REFERENCE_RANGES["momentum"]),
                "signal": _determine_signal(_calculate_percentile(momentum, REFERENCE_RANGES["momentum"]))
            },
            {
                "name": "Volatility (30D Ann)",
                "value": round(volatility, 2),
                "percentile": _calculate_percentile(volatility, REFERENCE_RANGES["volatility"]),
                "signal": _determine_signal(_calculate_percentile(volatility, REFERENCE_RANGES["volatility"]))
            },
            {
                "name": "Mean Reversion (Price/SMA200)",
                "value": round(mean_reversion, 3),
                "percentile": _calculate_percentile(mean_reversion, REFERENCE_RANGES["mean_reversion"]),
                "signal": _determine_signal(_calculate_percentile(mean_reversion, REFERENCE_RANGES["mean_reversion"]))
            },
            {
                "name": "Volume Profile (20D)",
                "value": round(volume_profile, 2),
                "percentile": _calculate_percentile(volume_profile, REFERENCE_RANGES["volume_profile"]),
                "signal": _determine_signal(_calculate_percentile(volume_profile, REFERENCE_RANGES["volume_profile"]))
            }
        ]

        return factors

    except Exception as e:
        logger.error(f"Error calculating factors for {ticker}: {e}")
        return []


def _calculate_percentile(value: float, range_config: Dict[str, Any]) -> int:
    """Calculate percentile based on reference range (0-100)."""
    min_val = range_config["min"]
    max_val = range_config["max"]

    # Clamp value to range
    clamped = max(min_val, min(max_val, value))

    # Calculate percentile
    if max_val == min_val:
        return 50
    percentile = ((clamped - min_val) / (max_val - min_val)) * 100
    return int(percentile)


def _determine_signal(percentile: int) -> str:
    """Determine signal based on percentile."""
    if percentile >= 67:
        return "strong"
    elif percentile >= 33:
        return "neutral"
    else:
        return "weak"
