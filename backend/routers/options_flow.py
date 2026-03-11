"""
Options Flow & Gamma Exposure API endpoints.
"""

from fastapi import APIRouter, Query
from datetime import datetime
from backend.services.options_flow import get_options_flow

router = APIRouter(prefix="/api/options-flow", tags=["options"])


@router.get("")
def get_options_flow_endpoint(ticker: str = Query("SPY", description="Stock ticker (default: SPY)")):
    """
    Get options flow analysis for a given ticker.

    Query Parameters:
    - ticker: Stock ticker symbol (default: SPY)

    Returns:
    {
        timestamp: ISO datetime,
        ticker: str,
        spot_price: float,
        iv_skew: float (-1 to 1),
        put_call_ratio: float,
        volume_imbalance: float,
        gex_signal: "positive"|"negative"|"neutral",
        gex_value: float,
        total_call_volume: int,
        total_put_volume: int,
        total_call_oi: int,
        total_put_oi: int,
        signal: "bullish"|"bearish"|"neutral",
        details: [str],
        expiry: str,
    }
    """
    result = get_options_flow(ticker)
    return result
