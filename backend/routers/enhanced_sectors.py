import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends
from datetime import datetime
import logging
from backend.services.data_provider import get_sector_data
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.stock_factors import calculate_stock_factors
from backend.services import yahoo_direct as yd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["enhanced-sectors"])

# Map UI period to yahoo range string for historical data
PERIOD_RANGE_MAP = {"1D": "5d", "5D": "10d", "1M": "1mo", "3M": "3mo"}
# How many trading days back to compute the period change
PERIOD_DAYS_MAP = {"1D": 1, "5D": 5, "1M": 21, "3M": 63}


def _compute_period_changes(tickers: list, period: str) -> dict:
    """Compute period-specific price changes for each ticker using historical data.

    Returns dict of ticker -> {period_change, period_pct_change, period_start_price}.
    For 1D, uses the daily change from batch_quotes (no extra API call needed).
    """
    if period == "1D":
        return {}  # Will use daily_change from sector_data

    range_str = PERIOD_RANGE_MAP.get(period, "3mo")
    results = {}

    def _fetch_one(ticker: str):
        try:
            history = yd.get_history(ticker, range_str=range_str, interval="1d")
            if not history or len(history) < 2:
                return ticker, None
            start_price = history[0]["close"]
            end_price = history[-1]["close"]
            if start_price and start_price > 0:
                change = end_price - start_price
                pct_change = (change / start_price) * 100
                return ticker, {
                    "period_change": round(change, 2),
                    "period_pct_change": round(pct_change, 2),
                    "period_start_price": round(start_price, 2),
                }
            return ticker, None
        except Exception as e:
            logger.debug(f"Period change calc failed for {ticker}: {e}")
            return ticker, None

    # Fetch in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_fetch_one, t) for t in tickers]
        for f in futures:
            ticker, data = f.result()
            if data:
                results[ticker] = data

    return results


@router.get("/enhanced-sectors")
async def get_enhanced_sectors(period: str = "1D"):
    """Return sector data enriched with RRG positioning and period-specific changes."""
    try:
        # Get sector performance, RRG data, and period changes in parallel
        try:
            sector_data = await asyncio.wait_for(
                asyncio.to_thread(get_sector_data, period=period),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            logger.warning("Sector data fetch timed out")
            sector_data = []

        tickers = list(SECTOR_ETFS.keys())
        # Map period to RRG lookback weeks
        period_to_weeks = {"1D": 10, "5D": 14, "1M": 26, "3M": 52}
        rrg_weeks = period_to_weeks.get(period, 10)

        # Fetch RRG and period changes concurrently
        try:
            rrg_data, period_changes = await asyncio.gather(
                asyncio.wait_for(
                    asyncio.to_thread(calculate_rrg, tickers, "SPY", rrg_weeks),
                    timeout=15.0
                ),
                asyncio.wait_for(
                    asyncio.to_thread(_compute_period_changes, tickers, period),
                    timeout=12.0
                ),
            )
        except asyncio.TimeoutError:
            logger.warning("RRG or period changes timed out")
            rrg_data = rrg_data if 'rrg_data' in dir() else {"sectors": []}
            period_changes = period_changes if 'period_changes' in dir() else {}

        # Create lookup for RRG data
        rrg_sectors = rrg_data.get("sectors", [])
        rrg_lookup = {s["ticker"]: s for s in rrg_sectors}
        rrg_available = len(rrg_sectors) > 0

        if not rrg_available:
            logger.warning("RRG calc returned no sectors — inferring quadrants from performance")

        # Merge by ticker
        enhanced_sectors = []
        for sector in sector_data:
            ticker = sector.get("ticker")
            rrg_info = rrg_lookup.get(ticker, {})
            daily_pct = sector.get("daily_pct_change", 0) or 0

            # Use period-specific change if available, else fall back to daily
            pc = period_changes.get(ticker)
            if pc and period != "1D":
                pct_change = pc["period_pct_change"]
                abs_change = pc["period_change"]
            else:
                pct_change = daily_pct
                abs_change = sector.get("daily_change", 0) or 0

            if rrg_info:
                quadrant = rrg_info.get("quadrant", "Unknown")
                rs_ratio = rrg_info.get("rs_ratio", 100)
                rs_momentum = rrg_info.get("rs_momentum", 0)
                tail_length = rrg_info.get("tail_length", 0)
                quadrant_age = rrg_info.get("quadrant_age", 0)
                rs_trend = rrg_info.get("rs_trend", "flat")
                rotation_direction = rrg_info.get("rotation_direction", "clockwise")
            else:
                # Infer from performance when RRG is unavailable
                if pct_change > 1.0:
                    quadrant = "Strengthening"
                elif pct_change > 0:
                    quadrant = "Recovering"
                elif pct_change > -1.0:
                    quadrant = "Weakening"
                else:
                    quadrant = "Deteriorating"
                rs_ratio = round(100 + (pct_change * 2), 2)
                rs_momentum = round(pct_change * 5, 2)
                tail_length = round(abs(pct_change) * 2, 2)
                quadrant_age = 1
                rs_trend = "up" if pct_change > 0 else "down"
                rotation_direction = "clockwise"

            enhanced_sectors.append({
                "ticker": ticker,
                "name": sector.get("sector") or sector.get("name") or ticker,
                "price": sector.get("price", 0),
                "change": round(abs_change, 2),
                "pct_change": round(pct_change, 2),
                "rs_ratio": rs_ratio,
                "rs_momentum": rs_momentum,
                "quadrant": quadrant,
                "tail_length": tail_length,
                "quadrant_age": quadrant_age,
                "rs_trend": rs_trend,
                "rotation_direction": rotation_direction,
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": period,
            "sectors": enhanced_sectors
        }
    except Exception as e:
        logger.error(f"Error getting enhanced sectors: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "period": period,
            "sectors": [],
            "error": str(e)
        }


@router.get("/stock/{ticker}/factors")
async def get_stock_factors(ticker: str):
    """Calculate factor exposures for a stock."""
    try:
        factors = await asyncio.to_thread(calculate_stock_factors, ticker)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "factors": factors
        }
    except Exception as e:
        logger.error(f"Error calculating factors for {ticker}: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "ticker": ticker,
            "factors": [],
            "error": str(e)
        }
