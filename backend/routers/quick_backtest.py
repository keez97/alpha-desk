"""
API endpoints for quick backtest operations.
Allows users to generate pre-configured backtests from RRG positioning.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import date
from pydantic import BaseModel
import logging

from backend.services.rrg_calculator import calculate_rrg, SECTOR_ETFS
from backend.services.quick_backtest_engine import QuickBacktestEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quick-backtest", tags=["quick_backtest"])


class QuickBacktestRequest(BaseModel):
    """Request to create a quick backtest from RRG."""

    ticker: str
    trade_type: str = "single"  # "single" or "pair"
    short_ticker: Optional[str] = None
    benchmark: str = "SPY"
    weeks: int = 10


class TradeIdeaResponse(BaseModel):
    """Response with trade idea and backtest config."""

    ticker: str
    sectorName: str
    quadrant: str
    direction: str  # "long", "short", "avoid"
    thesis: str
    suggestedPairTicker: Optional[str] = None
    confidence: str  # "high", "medium", "low"
    rsRatio: float
    rsMomentum: float
    backtestConfig: dict


class QuickBacktestResponse(BaseModel):
    """Response with pre-configured backtest parameters."""

    name: str
    start_date: str
    end_date: str
    rebalance_frequency: str
    transaction_costs: dict
    universe_selection: str
    factor_allocations: dict
    ticker: str
    short_ticker: Optional[str] = None
    trade_type: str
    direction: str
    quadrant: str
    confidence: str


@router.post("/from-rrg", response_model=QuickBacktestResponse)
def create_quick_backtest_from_rrg(
    request: QuickBacktestRequest,
):
    """
    Generate a pre-configured backtest from RRG positioning.

    Takes a sector ticker and generates backtest parameters based on:
    - Current RRG quadrant (Strengthening, Weakening, Recovering, Deteriorating)
    - RS-Ratio and RS-Momentum values
    - Trade direction inferred from quadrant

    Returns pre-filled configuration without running the backtest.
    User reviews and confirms before creating the actual backtest.

    Args:
        request: Quick backtest request with ticker and trade type

    Returns:
        Pre-filled backtest configuration
    """
    try:
        # Validate ticker
        ticker = request.ticker.upper()
        if ticker not in SECTOR_ETFS:
            raise HTTPException(
                status_code=400, detail=f"Invalid sector ticker: {ticker}"
            )

        # Calculate RRG for all sectors
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark=request.benchmark, weeks=request.weeks)

        if "error" in rrg_data:
            raise HTTPException(status_code=500, detail="Failed to calculate RRG data")

        # Find the requested sector in RRG results
        sector_info = None
        for sector in rrg_data.get("sectors", []):
            if sector["ticker"] == ticker:
                sector_info = sector
                break

        if not sector_info:
            raise HTTPException(
                status_code=404, detail=f"Sector data not found for {ticker}"
            )

        # Generate backtest configuration
        config = QuickBacktestEngine.generate_backtest_config(
            ticker=ticker,
            sector_name=sector_info.get("sector", ticker),
            quadrant=sector_info.get("quadrant", "Unknown"),
            rs_ratio=sector_info.get("rs_ratio", 100),
            rs_momentum=sector_info.get("rs_momentum", 0),
            end_date=date.today(),
            trade_type=request.trade_type,
            short_ticker=request.short_ticker,
        )

        return QuickBacktestResponse(**config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quick backtest: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate backtest configuration"
        )


@router.get("/trade-ideas", response_model=List[TradeIdeaResponse])
def get_rrg_trade_ideas(
    benchmark: str = Query("SPY", description="Benchmark for RRG calculation"),
    weeks: int = Query(10, ge=1, le=260, description="Number of weeks for RRG"),
):
    """
    Generate trade ideas for all sectors based on current RRG positioning.

    Calculates RRG metrics for all sector ETFs and generates:
    - Trade direction (long/short/avoid) based on quadrant
    - Trade thesis explaining the position
    - Suggested pair trade (long/short pair)
    - Pre-configured backtest parameters for each sector

    Trade ideas are sorted by confidence (high > medium > low).

    Args:
        benchmark: Benchmark for RRG calculation (default: SPY)
        weeks: Number of weeks for RRG calculation (default: 10, max: 260)

    Returns:
        List of trade ideas sorted by confidence
    """
    try:
        # Calculate RRG for all sectors
        tickers = list(SECTOR_ETFS.keys())
        rrg_data = calculate_rrg(tickers, benchmark=benchmark, weeks=weeks)

        if "error" in rrg_data:
            raise HTTPException(status_code=500, detail="Failed to calculate RRG data")

        # Get sectors and enrich with sector names
        sectors_data = []
        for sector in rrg_data.get("sectors", []):
            sector_copy = sector.copy()
            sector_copy["name"] = SECTOR_ETFS.get(sector["ticker"], sector["ticker"])
            sectors_data.append(sector_copy)

        # Generate trade ideas for all sectors
        trade_ideas = QuickBacktestEngine.generate_trade_ideas_for_sectors(sectors_data)

        return [TradeIdeaResponse(**idea) for idea in trade_ideas]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating trade ideas: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate trade ideas"
        )
