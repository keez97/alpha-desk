import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Simple in-memory cache with TTL
_rrg_cache = {}
_CACHE_TTL = 300  # 5 minutes


def calculate_rrg(
    tickers: List[str],
    benchmark: str = "SPY",
    weeks: int = 10
) -> Dict[str, Any]:
    """Calculate Relative Rotation Graph metrics using JdK methodology."""
    try:
        # Check cache first
        cache_key = f"{benchmark}_{weeks}_{','.join(sorted(tickers))}"
        if cache_key in _rrg_cache:
            cached_data, cached_time = _rrg_cache[cache_key]
            if time.time() - cached_time < _CACHE_TTL:
                logger.info(f"Returning cached RRG result (age: {time.time() - cached_time:.1f}s)")
                return cached_data

        # Fetch benchmark data (single call)
        benchmark_history = get_history(benchmark, period="1y")
        if not benchmark_history:
            return {"error": f"Could not fetch {benchmark} data", "sectors": []}

        # Create benchmark DataFrame
        benchmark_dates = [pd.to_datetime(h["date"]) for h in benchmark_history]
        benchmark_prices = [h["close"] for h in benchmark_history]
        benchmark_df = pd.Series(benchmark_prices, index=benchmark_dates)

        # Fetch all ticker data concurrently
        ticker_histories = {}
        results = []

        def fetch_ticker_history(ticker):
            """Fetch history for a single ticker."""
            try:
                history = get_history(ticker, period="1y")
                return ticker, history
            except Exception as e:
                logger.error(f"Error fetching {ticker}: {e}")
                return ticker, None

        # Use ThreadPoolExecutor to fetch all tickers in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_ticker_history, ticker): ticker for ticker in tickers}
            for future in as_completed(futures):
                ticker, history = future.result()
                ticker_histories[ticker] = history

        # Process ticker data
        for ticker in tickers:
            try:
                history = ticker_histories.get(ticker)
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

        result = {
            "benchmark": benchmark,
            "weeks": weeks,
            "sectors": results,
        }

        # Cache the result
        _rrg_cache[cache_key] = (result, time.time())

        return result
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
