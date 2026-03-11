import asyncio
from fastapi import APIRouter, Query
from datetime import datetime
import logging
from backend.services.intraday_momentum_engine import IntradayMomentumEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intraday-momentum", tags=["intraday-momentum"])


@router.get("/scan")
async def scan_intraday_momentum(
    interval: str = Query("5m", description="5m or 15m"),
    benchmark: str = Query("SPY", description="RRG benchmark"),
    weeks: int = Query(10, description="RRG calculation weeks"),
):
    """
    Run intraday momentum scan for sectors in leading RRG quadrants.

    Returns signals with breakout detection for 5m or 15m intervals.
    """
    try:
        if interval not in ("5m", "15m"):
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "signals": [],
                "error": "interval must be '5m' or '15m'",
            }

        result = await asyncio.to_thread(
            IntradayMomentumEngine.scan_intraday_momentum,
            interval=interval, benchmark=benchmark, weeks=weeks
        )

        return result
    except Exception as e:
        logger.error(f"Error in intraday momentum scan: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [],
            "error": str(e),
        }


@router.get("/{ticker}")
async def get_ticker_detail(
    ticker: str,
    interval: str = Query("5m", description="5m or 15m"),
):
    """
    Get detailed intraday analysis for a specific sector ETF.

    Returns metrics and last 10 candles for the specified interval.
    """
    try:
        if interval not in ("5m", "15m"):
            return {
                "ticker": ticker,
                "interval": interval,
                "error": "interval must be '5m' or '15m'",
            }

        result = await asyncio.to_thread(IntradayMomentumEngine.get_ticker_detail, ticker, interval)

        return result
    except Exception as e:
        logger.error(f"Error getting detail for {ticker}: {e}")
        return {
            "ticker": ticker,
            "interval": interval,
            "error": str(e),
        }
