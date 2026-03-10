"""
API endpoints for position sizing recommendations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import logging

from backend.services.position_sizing_engine import (
    calculate_position_sizing,
    batch_position_sizing,
)

logger = logging.getLogger(__name__)


# Request/Response Models
class FactorBreakdown(BaseModel):
    """Factor contribution to composite score."""
    name: str
    value: float
    percentile: float
    weight: float
    contribution: float


class PositionSizingResponse(BaseModel):
    """Position sizing recommendation response."""
    ticker: str
    compositeScore: float
    sizeCategory: str
    sizePct: float
    positionValue: float
    kellyFraction: float
    stopLoss: float
    factorBreakdown: List[FactorBreakdown]
    riskNotes: List[str]


class BatchPositionSizingRequest(BaseModel):
    """Request for batch position sizing."""
    tickers: List[str]
    portfolio_value: float = 100000.0


class BatchPositionSizingResponse(BaseModel):
    """Response for batch position sizing."""
    results: List[PositionSizingResponse]
    count: int
    totalAllocation: float
    utilizationPct: float
    portfolioValue: float


# Create router
router = APIRouter(prefix="/api/position-sizing", tags=["position-sizing"])


@router.get("/{ticker}", response_model=PositionSizingResponse)
def get_position_sizing(
    ticker: str,
    portfolio_value: float = Query(100000.0, gt=0, description="Portfolio value in dollars")
):
    """
    Get position sizing recommendation for a ticker.

    The recommendation is based on multi-factor exposures:
    - Momentum (30% weight)
    - Volatility (20% weight, inverted)
    - Mean Reversion (25% weight)
    - Volume Profile (25% weight)

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        portfolio_value: Total portfolio value in dollars (default: $100,000)

    Returns:
        Position sizing recommendation with composite score, size category, and risk notes

    Raises:
        HTTPException: If unable to calculate position sizing (insufficient data)
    """
    try:
        sizing = calculate_position_sizing(ticker, portfolio_value)

        if not sizing:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to calculate position sizing for {ticker}. Insufficient data."
            )

        return PositionSizingResponse(**sizing)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating position sizing for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while calculating position sizing."
        )


@router.post("/batch", response_model=BatchPositionSizingResponse)
def get_batch_position_sizing(request: BatchPositionSizingRequest):
    """
    Get position sizing recommendations for multiple tickers.

    Useful for calculating allocations across a portfolio of candidates.

    Args:
        request: Batch request with ticker list and portfolio value

    Returns:
        Batch results with individual sizing recommendations and total allocation

    Raises:
        HTTPException: If no valid tickers can be processed
    """
    try:
        if not request.tickers:
            raise HTTPException(
                status_code=400,
                detail="At least one ticker is required"
            )

        if len(request.tickers) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 tickers allowed per batch request"
            )

        result = batch_position_sizing(request.tickers, request.portfolio_value)

        if result["count"] == 0:
            raise HTTPException(
                status_code=404,
                detail="No valid position sizing recommendations could be generated"
            )

        return BatchPositionSizingResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch position sizing: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing batch request."
        )
