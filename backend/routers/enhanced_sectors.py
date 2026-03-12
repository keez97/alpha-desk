import asyncio
from fastapi import APIRouter, Depends
from datetime import datetime
import logging
from backend.services.data_provider import get_sector_data
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.stock_factors import calculate_stock_factors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["enhanced-sectors"])


@router.get("/enhanced-sectors")
async def get_enhanced_sectors(period: str = "1D"):
    """Return sector data enriched with RRG positioning."""
    try:
        # Get sector performance and RRG data with timeouts
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
        try:
            rrg_data = await asyncio.wait_for(
                asyncio.to_thread(calculate_rrg, tickers, "SPY", rrg_weeks),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.warning("RRG calculation timed out")
            rrg_data = {"sectors": []}

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
            pct_change = sector.get("daily_pct_change", 0) or 0

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
                "change": sector.get("daily_change", 0),
                "pct_change": pct_change,
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
