"""
Overnight Returns & Pre-Market Analysis Service.

Calculates overnight gaps for major indices and sector ETFs.
Flags statistical outliers (>2 std dev) and provides direction summary.

Data source cascade:
  1. yahoo_direct (v8 API — independent rate limiting)
  2. yfinance (library — may be rate-limited)
  3. stooq (EOD CSV — less accurate but reliable)
  4. synthetic_estimator (VIX-based statistical model)
  5. static mock (last resort — should almost never hit)
"""

import logging
import time
from typing import Dict, List, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
from backend.services import yfinance_service
from backend.services.yfinance_service import _yf_session
from backend.services import yahoo_direct
from backend.services import stooq_service
from backend.services import synthetic_estimator

logger = logging.getLogger(__name__)

# Cache for overnight returns data (30 min TTL)
_cache_overnight = None
_cache_overnight_expires = 0

# Major indices and sector ETFs to track
MAJOR_INDICES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq-100",
    "IWM": "Russell 2000",
    "DIA": "Dow 30",
}

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLY": "Consumer Disc",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLRE": "Real Estate",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLC": "Comm Services",
}

ALL_TICKERS = {**MAJOR_INDICES, **SECTOR_ETFS}

# Beta multipliers for VIX-based std estimation
_BETA_MAP = {
    "SPY": 1.0, "QQQ": 1.25, "IWM": 1.3, "DIA": 0.85,
    "XLK": 1.2, "XLV": 0.7, "XLF": 1.1, "XLY": 1.15,
    "XLP": 0.55, "XLE": 1.4, "XLRE": 0.9, "XLI": 0.95,
    "XLU": 0.5, "XLC": 1.1,
}


def _calculate_overnight_return_cascade(ticker: str) -> Dict[str, Any] | None:
    """
    Calculate overnight return using the data source cascade.

    Tier 1: yahoo_direct (v8 API)
    Tier 2: yfinance (library)
    Tier 3: stooq (EOD CSV)

    Returns dict with overnight return metrics, or None if all tiers fail.
    """
    # --- Tier 1: yahoo_direct ---
    yd_result = yahoo_direct.get_overnight_return(ticker)
    if yd_result is not None:
        # Get historical for std dev calculation
        hist = yahoo_direct.get_history(ticker, range_str="3mo")
        stats = _compute_stats_from_history(hist, yd_result["overnight_pct"])
        return {
            "ticker": ticker,
            "overnight_return_pct": round(yd_result["overnight_pct"], 3),
            "avg_overnight": stats["avg"],
            "std_overnight": stats["std"],
            "z_score": stats["z_score"],
            "is_outlier": abs(stats["z_score"]) > 2.0,
            "direction": "up" if yd_result["overnight_pct"] > 0 else "down",
            "last_price": round(yd_result.get("yesterday_close", 0), 2),
            "data_source": "yahoo_direct",
        }

    # --- Tier 2: yfinance ---
    if time.time() >= yfinance_service._rate_limited_until:
        try:
            data = yf.Ticker(ticker, session=_yf_session)
            hist = data.history(period="3mo")

            if not hist.empty and len(hist) >= 2:
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                today_open = today["Open"]
                yesterday_close = yesterday["Close"]

                if yesterday_close != 0:
                    overnight_return = (today_open - yesterday_close) / yesterday_close * 100

                    # Historical overnight returns for std dev
                    overnight_returns_history = []
                    for i in range(1, min(61, len(hist))):
                        o = hist.iloc[-i - 1]["Close"]
                        n = hist.iloc[-i]["Open"]
                        if o != 0:
                            gap = (n - o) / o * 100
                            overnight_returns_history.append(gap)

                    if overnight_returns_history:
                        avg = sum(overnight_returns_history) / len(overnight_returns_history)
                        variance = sum((x - avg) ** 2 for x in overnight_returns_history) / len(overnight_returns_history)
                        std = variance ** 0.5
                    else:
                        avg, std = 0, 0

                    z_score = (overnight_return - avg) / std if std > 0 else 0

                    return {
                        "ticker": ticker,
                        "overnight_return_pct": round(overnight_return, 3),
                        "avg_overnight": round(avg, 3),
                        "std_overnight": round(std, 3),
                        "z_score": round(z_score, 2),
                        "is_outlier": abs(z_score) > 2.0,
                        "direction": "up" if overnight_return > 0 else "down",
                        "last_price": round(float(yesterday_close), 2),
                        "data_source": "yfinance",
                    }
        except Exception as e:
            logger.debug(f"yfinance overnight {ticker}: {e}")

    # --- Tier 3: stooq (EOD only) ---
    try:
        stooq_result = stooq_service.get_overnight_return(ticker)
    except Exception as e:
        logger.debug(f"stooq overnight {ticker}: {e}")
        stooq_result = None
    if stooq_result is not None:
        stooq_hist = stooq_service.get_history(ticker, lookback_days=90)
        overnight_pct = stooq_result["overnight_pct"]

        # Compute stats from stooq history
        if len(stooq_hist) >= 3:
            gaps = []
            for i in range(1, len(stooq_hist)):
                prev_close = stooq_hist[i - 1]["close"]
                cur_open = stooq_hist[i]["open"]
                if prev_close != 0:
                    gaps.append((cur_open - prev_close) / prev_close * 100)

            if gaps:
                avg = sum(gaps) / len(gaps)
                variance = sum((x - avg) ** 2 for x in gaps) / len(gaps)
                std = variance ** 0.5
                z_score = (overnight_pct - avg) / std if std > 0 else 0
            else:
                avg, std, z_score = 0, 0, 0
        else:
            avg, std, z_score = 0, 0, 0

        last_p = stooq_result.get("yesterday_close", stooq_hist[-1]["close"] if stooq_hist else 0)
        return {
            "ticker": ticker,
            "overnight_return_pct": round(overnight_pct, 3),
            "avg_overnight": round(avg, 3),
            "std_overnight": round(std, 3),
            "z_score": round(z_score, 2),
            "is_outlier": abs(z_score) > 2.0,
            "direction": "up" if overnight_pct > 0 else "down",
            "last_price": round(float(last_p), 2),
            "data_source": "stooq",
        }

    return None


def _compute_stats_from_history(hist: List[Dict], current_overnight: float) -> Dict[str, float]:
    """Compute avg, std, z_score from yahoo_direct history."""
    if len(hist) < 3:
        return {"avg": 0, "std": 0, "z_score": 0}

    gaps = []
    for i in range(1, len(hist)):
        prev_close = hist[i - 1]["close"]
        cur_open = hist[i]["open"]
        if prev_close != 0:
            gaps.append((cur_open - prev_close) / prev_close * 100)

    if not gaps:
        return {"avg": 0, "std": 0, "z_score": 0}

    avg = sum(gaps) / len(gaps)
    variance = sum((x - avg) ** 2 for x in gaps) / len(gaps)
    std = variance ** 0.5
    z_score = (current_overnight - avg) / std if std > 0 else 0

    return {"avg": round(avg, 3), "std": round(std, 3), "z_score": round(z_score, 2)}


def get_overnight_returns() -> Dict[str, Any]:
    """
    Get overnight returns for all major indices and sector ETFs.
    Uses 4-tier cascade: yahoo_direct → yfinance → stooq → synthetic estimation.
    """
    global _cache_overnight, _cache_overnight_expires

    # Check cache
    if _cache_overnight and time.time() < _cache_overnight_expires:
        logger.info("Returning cached overnight returns")
        return _cache_overnight

    # Fetch live data with cascade — parallel execution (was sequential, 14 tickers × 4 tiers = 546s worst case)
    indices_data = []
    gaps_up = 0
    gaps_down = 0
    notable_gaps = []
    data_sources = set()

    def _fetch_one(ticker_name: Tuple[str, str]) -> Tuple[str, str, Any]:
        ticker, name = ticker_name
        try:
            return (ticker, name, _calculate_overnight_return_cascade(ticker))
        except Exception as e:
            logger.warning(f"Error fetching overnight return for {ticker}: {e}")
            return (ticker, name, None)

    # Process 4 tickers concurrently (balance speed vs rate-limiting)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in ALL_TICKERS.items()}
        for future in as_completed(futures, timeout=20):
            try:
                ticker, name, result = future.result(timeout=10)
            except Exception as e:
                logger.warning(f"Overnight return future failed: {e}")
                continue
            if result:
                result["name"] = name
                indices_data.append(result)
                data_sources.add(result.get("data_source", "unknown"))

                if result["direction"] == "up":
                    gaps_up += 1
                else:
                    gaps_down += 1

                if result["is_outlier"]:
                    notable_gaps.append({
                        "ticker": ticker,
                        "overnight_return_pct": result["overnight_return_pct"],
                        "z_score": result["z_score"],
                        "direction": result["direction"],
                    })

    # If we got live data for most tickers, use it
    if len(indices_data) >= 8:
        notable_gaps.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "indices": indices_data,
            "summary": {
                "total_tracked": len(indices_data),
                "gaps_up": gaps_up,
                "gaps_down": gaps_down,
                "net_direction": "up" if gaps_up > gaps_down else ("down" if gaps_down > gaps_up else "neutral"),
                "notable_gaps": notable_gaps[:5],
            },
            "data_sources": list(data_sources),
        }

        _cache_overnight = response
        _cache_overnight_expires = time.time() + 30 * 60
        return response

    # --- Tier 4: Synthetic estimation ---
    logger.info("All live sources failed; using VIX-based synthetic estimation for overnight returns")
    estimated = synthetic_estimator.estimate_overnight_returns(ALL_TICKERS)
    _cache_overnight = estimated
    _cache_overnight_expires = time.time() + 15 * 60  # Shorter TTL for estimates
    return estimated
