"""
API endpoints for backtesting operations.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlmodel import Session, select
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, validator

from backend.database import get_session
from backend.models.backtests import Backtest, BacktestConfiguration, BacktestFactorAllocation
from backend.repositories.backtest_repo import BacktestRepository
from backend.services.backtest_engine import BacktestEngine
import logging

logger = logging.getLogger(__name__)


# Request/Response Models
class CreateBacktestRequest(BaseModel):
    """Request to create a new backtest."""
    name: str
    backtest_type: str = "factor_combination"
    start_date: date
    end_date: date
    rebalance_frequency: str = "monthly"
    universe_selection: str = "sp500"
    commission_bps: float = 5.0
    slippage_bps: float = 2.0
    benchmark_ticker: str = "SPY"
    rolling_window_months: int = 60
    factor_allocations: List[dict]  # [{factor_id: int, weight: float}, ...]

    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Backtest name cannot be empty')
        return v

    @validator('end_date')
    def end_date_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

    @validator('factor_allocations')
    def validate_allocations(cls, v):
        if not v:
            raise ValueError('At least one factor allocation is required')

        total_weight = 0.0
        for alloc in v:
            if 'factor_id' not in alloc or 'weight' not in alloc:
                raise ValueError('Each allocation must have factor_id and weight')
            weight = float(alloc['weight'])
            if weight < 0 or weight > 1:
                raise ValueError('Each weight must be between 0 and 1')
            total_weight += weight

        # Check that weights sum to approximately 1.0 (with small tolerance)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f'Factor weights must sum to 1.0 (got {total_weight:.4f})')

        return v


class BacktestResponse(BaseModel):
    """Response with backtest details."""
    id: int
    name: str
    backtest_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BacktestStatusResponse(BaseModel):
    """Response with backtest status."""
    id: int
    name: str
    status: str
    progress_percent: float
    current_rebalance_date: Optional[date] = None
    error_message: Optional[str] = None


class BacktestResultsResponse(BaseModel):
    """Response with full backtest results."""
    id: int
    name: str
    status: str
    statistics: dict
    results_count: int
    start_date: date
    end_date: date


class BacktestListResponse(BaseModel):
    """Response with list of backtests."""
    total: int
    limit: int
    offset: int
    backtests: List[BacktestResponse]


# Create router
router = APIRouter(prefix="/api/backtests", tags=["backtesting"])


@router.post("", response_model=BacktestResponse)
def create_backtest(
    request: CreateBacktestRequest,
    session: Session = Depends(get_session)
):
    """
    Create a new backtest (returns immediately with ID, status=DRAFT).

    Args:
        request: Backtest creation request
        session: Database session

    Returns:
        Created backtest details
    """
    try:
        repo = BacktestRepository(session)

        # Create backtest
        backtest = repo.create_backtest(
            name=request.name,
            backtest_type=request.backtest_type
        )

        # Create configuration
        repo.create_configuration(
            backtest_id=backtest.id,
            start_date=request.start_date,
            end_date=request.end_date,
            rebalance_frequency=request.rebalance_frequency,
            universe_selection=request.universe_selection,
            commission_bps=Decimal(str(request.commission_bps)),
            slippage_bps=Decimal(str(request.slippage_bps)),
            benchmark_ticker=request.benchmark_ticker,
            rolling_window_months=request.rolling_window_months,
        )

        # Add factor allocations
        for allocation in request.factor_allocations:
            repo.add_factor_allocation(
                backtest_id=backtest.id,
                factor_id=allocation["factor_id"],
                weight=Decimal(str(allocation["weight"])),
            )

        return BacktestResponse(
            id=backtest.id,
            name=backtest.name,
            backtest_type=backtest.backtest_type,
            status=backtest.status,
            created_at=backtest.created_at,
            updated_at=backtest.updated_at,
            completed_at=backtest.completed_at,
            error_message=backtest.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backtest: {e}")
        raise HTTPException(status_code=400, detail="Failed to create backtest. Please verify your input.")


@router.post("/{backtest_id}/run")
def run_backtest(
    backtest_id: int = Path(..., gt=0, description="Backtest ID must be greater than 0"),
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session)
):
    """
    Start backtest execution (background task, returns status=RUNNING).

    Args:
        backtest_id: ID of backtest to run
        background_tasks: FastAPI background tasks manager
        session: Database session

    Returns:
        Status response
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        # Add background task to run backtest
        engine = BacktestEngine()
        background_tasks.add_task(engine.run_backtest, backtest_id, session)

        return {
            "status": "running",
            "backtest_id": backtest_id,
            "message": "Backtest started in background"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{backtest_id}", response_model=BacktestResponse)
def get_backtest(
    backtest_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Get backtest details + status.

    Args:
        backtest_id: ID of backtest
        session: Database session

    Returns:
        Backtest details
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        return BacktestResponse(
            id=backtest.id,
            name=backtest.name,
            backtest_type=backtest.backtest_type,
            status=backtest.status,
            created_at=backtest.created_at,
            updated_at=backtest.updated_at,
            completed_at=backtest.completed_at,
            error_message=backtest.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{backtest_id}/status", response_model=BacktestStatusResponse)
def get_backtest_status(
    backtest_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Poll for progress (progress_percent, current_rebalance_date).

    Args:
        backtest_id: ID of backtest
        session: Database session

    Returns:
        Status with progress information
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        # Calculate progress based on results
        results = repo.get_results(backtest_id)
        config = repo.get_configuration(backtest_id)

        progress_percent = 0.0
        if config:
            total_days = (config.end_date - config.start_date).days
            progress_percent = min(100.0, (len(results) / max(1, total_days)) * 100)

        current_date = None
        if results:
            current_date = results[-1].date

        return BacktestStatusResponse(
            id=backtest.id,
            name=backtest.name,
            status=backtest.status,
            progress_percent=progress_percent,
            current_rebalance_date=current_date,
            error_message=backtest.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest status: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{backtest_id}/results", response_model=BacktestResultsResponse)
def get_backtest_results(
    backtest_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Get full results (equity curve, statistics, exposures).

    Args:
        backtest_id: ID of backtest
        session: Database session

    Returns:
        Full results with statistics
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        config = repo.get_configuration(backtest_id)
        results = repo.get_results(backtest_id)
        statistics = repo.get_statistics(backtest_id)

        # Convert statistics to dictionary
        stats_dict = {}
        for stat in statistics:
            stats_dict[stat.metric_name] = float(stat.metric_value)

        return BacktestResultsResponse(
            id=backtest.id,
            name=backtest.name,
            status=backtest.status,
            statistics=stats_dict,
            results_count=len(results),
            start_date=config.start_date if config else None,
            end_date=config.end_date if config else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{backtest_id}/export")
def export_backtest(
    backtest_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Export results as JSON.

    Args:
        backtest_id: ID of backtest
        session: Database session

    Returns:
        JSON export of results
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        config = repo.get_configuration(backtest_id)
        results = repo.get_results(backtest_id)
        statistics = repo.get_statistics(backtest_id)
        allocations = repo.get_factor_allocations(backtest_id)

        # Build export JSON
        export_data = {
            "backtest": {
                "id": backtest.id,
                "name": backtest.name,
                "status": backtest.status,
                "created_at": backtest.created_at.isoformat(),
                "completed_at": backtest.completed_at.isoformat() if backtest.completed_at else None,
            },
            "configuration": {
                "start_date": config.start_date.isoformat() if config else None,
                "end_date": config.end_date.isoformat() if config else None,
                "rebalance_frequency": config.rebalance_frequency if config else None,
                "benchmark_ticker": config.benchmark_ticker if config else None,
                "commission_bps": float(config.commission_bps) if config else None,
                "slippage_bps": float(config.slippage_bps) if config else None,
            },
            "statistics": {
                stat.metric_name: float(stat.metric_value)
                for stat in statistics
            },
            "results": [
                {
                    "date": result.date.isoformat(),
                    "portfolio_value": float(result.portfolio_value),
                    "daily_return": float(result.daily_return),
                    "benchmark_return": float(result.benchmark_return) if result.benchmark_return else None,
                    "turnover": float(result.turnover) if result.turnover else None,
                    "holdings_count": result.holdings_count,
                }
                for result in results
            ],
            "factor_allocations": [
                {
                    "factor_id": alloc.factor_id,
                    "weight": float(alloc.weight),
                }
                for alloc in allocations
            ],
        }

        return export_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting backtest: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("", response_model=BacktestListResponse)
def list_backtests(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500, description="Must be between 1 and 500"),
    offset: int = Query(0, ge=0, description="Must be >= 0"),
    session: Session = Depends(get_session)
):
    """
    List all backtests (paginated).

    Args:
        status: Optional filter by status
        limit: Number of results to return
        offset: Number of results to skip
        session: Database session

    Returns:
        Paginated list of backtests
    """
    try:
        repo = BacktestRepository(session)
        backtests = repo.list_backtests(
            status=status,
            limit=limit,
            offset=offset
        )

        # Get total count
        query = select(Backtest)
        if status:
            query = query.where(Backtest.status == status)

        total = len(session.exec(query).all())

        return BacktestListResponse(
            total=total,
            limit=limit,
            offset=offset,
            backtests=[
                BacktestResponse(
                    id=b.id,
                    name=b.name,
                    backtest_type=b.backtest_type,
                    status=b.status,
                    created_at=b.created_at,
                    updated_at=b.updated_at,
                    completed_at=b.completed_at,
                    error_message=b.error_message,
                )
                for b in backtests
            ],
        )

    except Exception as e:
        logger.error(f"Error listing backtests: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.delete("/{backtest_id}")
def delete_backtest(
    backtest_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Delete a backtest.

    Args:
        backtest_id: ID of backtest
        session: Database session

    Returns:
        Confirmation response
    """
    try:
        repo = BacktestRepository(session)
        backtest = repo.get_backtest(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        # Delete related records first
        # In a real implementation, use cascade delete or foreign key constraints
        session.delete(backtest)
        session.commit()

        return {
            "message": "Backtest deleted successfully",
            "backtest_id": backtest_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backtest: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
