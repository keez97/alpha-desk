"""
Earnings Brief Router for Morning Brief
Provides compact earnings calendar with pre-announcement drift signals.
"""

from fastapi import APIRouter
from datetime import datetime
import logging
from backend.services.earnings_brief import get_earnings_brief

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/earnings-brief", tags=["earnings-brief"])


@router.get("")
def fetch_earnings_brief():
    """Get upcoming earnings (2-week window) with pre-drift signals and clustering."""
    try:
        data = get_earnings_brief()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error fetching earnings brief: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data": {},
            "error": str(e),
        }
