import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging
from backend.services.data_provider import get_history

logger = logging.getLogger(__name__)

SECTOR_ETFS = {
    "XLK": "Information Technology",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLRE": "Real Estate",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLCQ": "Communication Services",
    "XLC": "Communication Services",
}


def calculate_rrg(
    tickers: List[str],
    benchmark: str = "SPY",
    weeks: int = 10
) -> Dict[str, Any]:
    """Calculate Relative Rotation Graph metrics using JdK methodology."""
    try:
        # Fetch historical data
        benchmark_history = get_history(benchmark, period="1y")
        if not benchmark_history:
            return {"error": f"Could not fetch {benchmark} data", "sectors": []}

        # Create benchmark DataFrame
        benchmark_dates = [pd.to_datetime(h["date"]) for h in benchmark_history]
        benchmark_prices = [h["close"] for h in benchmark_history]
        benchmark_df = pd.Series(benchmark_prices, index=benchmark_dates)

        # Fetch ticker data and compute relative strength
        results = []

        for ticker in tickers:
            try:
                history = get_history(ticker, period="1y")
                if not history:
                    logger.warning(f"No data for {ticker}")
                    continue

                dates = [pd.to_datetime(h["date"]) for h in history]
                prices = [h["close"] for h in history]
                ticker_df = pd.Series(prices, index=dates)

                # Align with benchmark
                aligned = pd.DataFrame({
                    "ticker": ticker_df,
                    "benchmark": benchmark_df
                }).dropna()

                if len(aligned) < weeks:
                    continue

                # Calculate RS-Ratio (relative strength)
                rs_ratio = aligned["ticker"] / aligned["benchmark"]

                # Normalize RS-Ratio to 100 center
                rs_mean = rs_ratio.mean()
                rs_ratio_normalized = (rs_ratio / rs_mean) * 100

                # Calculate RS-Momentum (rate of change of RS-Ratio)
                rs_momentum = rs_ratio_normalized.pct_change(periods=weeks) * 100

                # Get current values
                current_rs_ratio = rs_ratio_normalized.iloc[-1]
                current_rs_momentum = rs_momentum.iloc[-1]

                # Determine quadrant
                quadrant = determine_quadrant(current_rs_ratio, current_rs_momentum)

                # Build trail (last 10 weeks of data)
                trail = []
                for i in range(max(0, len(rs_ratio_normalized) - weeks), len(rs_ratio_normalized)):
                    trail.append({
                        "rs_ratio": float(rs_ratio_normalized.iloc[i]),
                        "rs_momentum": float(rs_momentum.iloc[i]) if i > 0 else 0.0,
                        "date": str(aligned.index[i].date())
                    })

                sector_name = SECTOR_ETFS.get(ticker, ticker)

                results.append({
                    "ticker": ticker,
                    "sector": sector_name,
                    "rs_ratio": float(current_rs_ratio),
                    "rs_momentum": float(current_rs_momentum),
                    "quadrant": quadrant,
                    "trail": trail,
                })
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                continue

        return {
            "benchmark": benchmark,
            "weeks": weeks,
            "sectors": results,
        }
    except Exception as e:
        logger.error(f"Error calculating RRG: {e}")
        return {
            "error": str(e),
            "benchmark": benchmark,
            "sectors": [],
        }


def determine_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    """Determine RRG quadrant based on RS-Ratio and RS-Momentum."""
    above_100 = rs_ratio > 100
    positive_momentum = rs_momentum > 0

    if above_100 and positive_momentum:
        return "Strengthening"
    elif above_100 and not positive_momentum:
        return "Weakening"
    elif not above_100 and positive_momentum:
        return "Recovering"
    else:
        return "Deteriorating"
