from fastapi import APIRouter, Depends
from datetime import datetime
from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS

router = APIRouter(prefix="/api/rrg", tags=["rrg"])


@router.get("/")
def get_rrg(benchmark: str = "SPY", weeks: int = 10):
    """Calculate Relative Rotation Graph for sector ETFs."""
    tickers = list(SECTOR_ETFS.keys())

    rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "benchmark": benchmark,
        "weeks": weeks,
        "data": rrg_data
    }
