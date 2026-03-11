"""
API router for VIX Term Structure Intelligence endpoints.
"""
import asyncio
from fastapi import APIRouter
from datetime import datetime
import logging
from backend.services.vix_term_structure import get_vix_term_structure

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vix-term-structure", tags=["vix-term-structure"])


@router.get("")
async def fetch_vix_term_structure():
    """Get VIX term structure metrics: spot, VIX3M, contango/backwardation, percentile, roll yield."""
    try:
        data = await asyncio.to_thread(get_vix_term_structure)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
    except Exception as e:
        logger.error(f"Error fetching VIX term structure: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "error": str(e),
                "vix_spot": 0,
                "vix3m": 0,
                "ratio": 1.0,
                "state": "unknown",
                "magnitude": 0,
                "percentile": 50,
                "roll_yield": 0,
                "signal": "neutral",
                "history": []
            }
        }
