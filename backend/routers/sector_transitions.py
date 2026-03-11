"""Router for sector transition alerts and factor decomposition."""
import asyncio
from fastapi import APIRouter
from datetime import datetime
import logging
from backend.services.sector_transitions import get_sector_transitions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sector-transitions"])


@router.get("/sector-transitions")
async def get_sector_transitions_endpoint():
    """
    Get sector transition data including:
    - Quadrant transitions (e.g., Improving → Leading)
    - Factor decomposition (beta, size, value, momentum)
    - Business cycle overlay (favorable/unfavorable sectors)
    """
    try:
        data = await asyncio.to_thread(get_sector_transitions)
        return {
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "transitions": data.get("transitions", []),
            "factor_decomposition": data.get("factor_decomposition", []),
            "cycle_overlay": data.get("cycle_overlay", {}),
        }
    except Exception as e:
        logger.error(f"Error in get_sector_transitions_endpoint: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "transitions": [],
            "factor_decomposition": [],
            "cycle_overlay": {},
            "error": str(e),
        }
