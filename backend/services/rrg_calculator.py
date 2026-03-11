import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from backend.services.data_provider import get_history
from backend.services import fds_client as fds
from backend.services import yahoo_direct as yd

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
    "XLC": "Communication Services",
}

# Simple in-memory cache with TTL
_rrg_cache = {}
_CACHE_TTL = 300  # 5 minutes


def _get_history_cascade(ticker: str, days: int = 365) -> list:
    """Fetch price history: yahoo_direct (Tier 0) → FDS (Tier 1) → data_provider (Tier 2)."""
    # Tier 0: yahoo_direct
    try:
        records = yd.get_history(ticker, range_str="1y", interval="1d")
        if records and len(records) >= 20:
            return records
    except Exception as e:
        logger.debug(f"yahoo_direct history {ticker}: {e}")

    # Tier 1: FDS
    if fds.is_available():
        try:
            end_date = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
            start_date = (datetime.utcnow().date() - timedelta(days=days)).isoformat()
            records = fds.get_historical_prices(ticker, start_date, end_date)
            if records and len(records) >= 20:
                return records
        except Exception as e:
            logger.debug(f"FDS history {ticker}: {e}")

    # Tier 3: data_provider (yfinance)
    return get_history(ticker, period="1y")


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
        benchmark_history = _get_history_cascade(benchmark)
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
                history = _get_history_cascade(ticker)
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

                # ── Enhanced metrics ──
                # Tail length: Euclidean distance traveled over last 4 trail points
                tail_length = 0.0
                if len(trail) >= 2:
                    for j in range(1, min(5, len(trail))):
                        dx = trail[-j]["rs_ratio"] - trail[-j - 1 if j < len(trail) else 0]["rs_ratio"]
                        dy = trail[-j]["rs_momentum"] - trail[-j - 1 if j < len(trail) else 0]["rs_momentum"]
                        tail_length += (dx**2 + dy**2) ** 0.5

                # Quadrant age: count consecutive trail points in same quadrant
                quadrant_age = 0
                for pt in reversed(trail):
                    pt_q = determine_quadrant(pt["rs_ratio"], pt["rs_momentum"])
                    if pt_q == quadrant:
                        quadrant_age += 1
                    else:
                        break

                # RS trend: slope of RS-Ratio over last 4 weeks
                recent_rs = [pt["rs_ratio"] for pt in trail[-4:]] if len(trail) >= 4 else [pt["rs_ratio"] for pt in trail]
                rs_trend = "up" if len(recent_rs) >= 2 and recent_rs[-1] > recent_rs[0] else "down"

                # Rotation direction: clockwise vs counter-clockwise
                rotation_direction = "clockwise"
                if len(trail) >= 3:
                    p1, p2, p3 = trail[-3], trail[-2], trail[-1]
                    cross = (p2["rs_ratio"] - p1["rs_ratio"]) * (p3["rs_momentum"] - p1["rs_momentum"]) - \
                            (p2["rs_momentum"] - p1["rs_momentum"]) * (p3["rs_ratio"] - p1["rs_ratio"])
                    rotation_direction = "clockwise" if cross < 0 else "counter-clockwise"

                results.append({
                    "ticker": ticker,
                    "sector": sector_name,
                    "rs_ratio": float(current_rs_ratio),
                    "rs_momentum": float(current_rs_momentum),
                    "quadrant": quadrant,
                    "trail": trail,
                    "tail_length": round(tail_length, 2),
                    "quadrant_age": quadrant_age,
                    "rs_trend": rs_trend,
                    "rotation_direction": rotation_direction,
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
