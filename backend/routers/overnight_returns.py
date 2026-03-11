"""
Overnight Returns & Pre-Market Analysis Router
Provides endpoint for fetching overnight gap data.
"""

from fastapi import APIRouter
from datetime import datetime
import asyncio
import logging
from backend.services.overnight_returns import get_overnight_returns

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overnight-returns", tags=["overnight-returns"])


@router.get("")
async def fetch_overnight_returns():
    """Get overnight returns for major indices and sector ETFs with statistical flagging."""
    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(get_overnight_returns),
            timeout=25.0,
        )
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
    except asyncio.TimeoutError:
        logger.warning("Overnight returns timed out after 25s")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},
            "error": "timeout",
        }
    except Exception as e:
        logger.error(f"Error fetching overnight returns: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},
            "error": str(e),
        }
