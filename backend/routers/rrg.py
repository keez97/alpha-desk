from fastapi import APIRouter, Depends
from datetime import datetime
import logging
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rrg", tags=["rrg"])


@router.get("/")
def get_rrg(benchmark: str = "SPY", weeks: int = 10):
    """Calculate Relative Rotation Graph for sector ETFs."""
    try:
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "benchmark": benchmark,
            "weeks": weeks,
            "data": rrg_data
        }
    except Exception as e:
        logger.error(f"RRG calculation error: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "benchmark": benchmark,
            "weeks": weeks,
            "data": {"benchmark": benchmark, "weeks": weeks, "sectors": []}
        }
