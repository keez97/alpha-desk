"""
Cross-Asset Momentum Spillover API endpoints.
"""

import asyncio
from fastapi import APIRouter
from datetime import datetime
from backend.services.cross_asset_momentum import get_momentum_spillover

router = APIRouter(prefix="/api/momentum-spillover", tags=["momentum"])


@router.get("")
async def get_momentum_spillover_endpoint():
    """
    Get cross-asset momentum spillover analysis.

    Returns:
    {
        timestamp: ISO datetime,
        assets: [
            {
                ticker: str,
                name: str,
                asset_class: str,
                momentum_1m: float,
                momentum_3m: float,
                state: "positive"|"negative"|"neutral",
            }
        ],
        signals: [
            {
                description: str,
                type: "bullish"|"bearish"|"warning",
                confidence: float (0-1),
                based_on: [str],
            }
        ],
        matrix: {
            positive_count: int,
            negative_count: int,
            neutral_count: int,
        },
    }
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(get_momentum_spillover),
            timeout=15.0
        )
        return result
    except asyncio.TimeoutError:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": [],
            "signals": [],
            "matrix": {"positive_count": 0, "negative_count": 0, "neutral_count": 0},
            "error": "timeout"
        }
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": [],
            "signals": [],
            "matrix": {"positive_count": 0, "negative_count": 0, "neutral_count": 0},
            "error": str(e)
        }
