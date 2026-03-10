from fastapi import APIRouter, Depends
from datetime import datetime
import logging
from backend.services.data_provider import get_sector_data
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.stock_factors import calculate_stock_factors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["enhanced-sectors"])


@router.get("/enhanced-sectors")
def get_enhanced_sectors(period: str = "1D"):
    """Return sector data enriched with RRG positioning."""
    try:
        # Get sector performance from yfinance
        sector_data = get_sector_data(period=period)

        # Get RRG data from rrg_calculator
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark="SPY", weeks=10)

        # Create lookup for RRG data
        rrg_lookup = {s["ticker"]: s for s in rrg_data.get("sectors", [])}

        # Merge by ticker
        enhanced_sectors = []
        for sector in sector_data:
            ticker = sector.get("ticker")
            rrg_info = rrg_lookup.get(ticker, {})

            enhanced_sectors.append({
                "ticker": ticker,
                "name": sector.get("sector") or sector.get("name") or ticker,
                "price": sector.get("price", 0),
                "change": sector.get("daily_change", 0),
                "pct_change": sector.get("daily_pct_change", 0),
                "rs_ratio": rrg_info.get("rs_ratio", 100),
                "rs_momentum": rrg_info.get("rs_momentum", 0),
                "quadrant": rrg_info.get("quadrant", "Unknown"),
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
def get_stock_factors(ticker: str):
    """Calculate factor exposures for a stock."""
    try:
        factors = calculate_stock_factors(ticker)

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
