"""
Overnight Returns & Pre-Market Analysis Router
Provides endpoint for fetching overnight gap data.
"""

from fastapi import APIRouter
from datetime import datetime
import logging
from backend.services.overnight_returns import get_overnight_returns

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/overnight-returns", tags=["overnight-returns"])


@router.get("")
def fetch_overnight_returns():
    """Get overnight returns for major indices and sector ETFs with statistical flagging."""
    try:
        data = get_overnight_returns()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error fetching overnight returns: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},
            "error": str(e),
        }
