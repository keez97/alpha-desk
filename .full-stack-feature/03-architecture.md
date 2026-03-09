# AlphaDesk Factor Backtester: Complete Architecture Design

**Document Version**: 1.0
**Last Updated**: 2026-03-10
**Phase**: Phase 1 (V2)
**Status**: Comprehensive Architecture Specification

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Backend Architecture](#backend-architecture)
3. [Frontend Architecture](#frontend-architecture)
4. [Cross-Cutting Concerns](#cross-cutting-concerns)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Risk Assessment & Mitigations](#risk-assessment--mitigations)

---

## Executive Summary

The Factor Backtester architecture is designed as a modular, research-grade system for validating multi-factor investment strategies. It follows a **three-tier architecture**:

- **API Layer**: RESTful FastAPI endpoints organized into logical domain routers (`backtester`, `factors`, `data`)
- **Service Layer**: Pure business logic components (BacktestEngine, FactorCalculator, StatisticsCalculator, etc.) with clear separation of concerns
- **Data Layer**: Point-in-Time (PiT) enforced PostgreSQL schema with partitioning, survivorship tracking, and immutable historical snapshots

Key architectural decisions:
- **Async processing** for long-running backtests (30-60+ seconds) via FastAPI BackgroundTasks or Celery
- **Caching strategy** for factor scores, correlation matrices, and statistics to reduce recomputation
- **TanStack Query** for intelligent server-state management on the frontend
- **Canvas-based rendering** for high-performance equity curve and drawdown overlay charts
- **Type safety** through Pydantic schemas and TypeScript strict mode

---

## Backend Architecture

### 1. API Design & Endpoints

#### 1.1 Routers Organization

All new backtester functionality is organized into three FastAPI routers:

```
/api/backtests       - CRUD operations on backtests
/api/factors         - Factor definitions, library access, custom factor creation
/api/data-ingestion  - Data loading, Kenneth French updates, fundamental snapshots
```

#### 1.2 Backtests Router Endpoints

**File**: `backend/routers/backtester.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlmodel import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/backtests", tags=["backtester"])

# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class BacktestCreateRequest(BaseModel):
    """Request body for creating a new backtest."""
    name: str = Field(..., min_length=1, max_length=255)
    backtest_type: str = Field(..., regex="^(factor_combo|custom)$")
    start_date: date
    end_date: date
    rebalance_frequency: str = Field(..., regex="^(daily|weekly|monthly|quarterly|annual)$")
    transaction_costs: dict = Field(
        default_factory=lambda: {"commission_bps": 10, "slippage_bps": 5},
        description="Transaction costs: commission_bps and slippage_bps"
    )
    universe_selection: str = Field(
        default="sp500",
        regex="^(sp500|nasdaq100|russell2000|custom)$"
    )
    factor_allocations: Optional[List[dict]] = Field(
        default=None,
        description="List of {factor_id: int, weight: float (0.0-1.0)}"
    )


class BacktestResponse(BaseModel):
    """Response body for a backtest."""
    id: int
    name: str
    backtest_type: str
    status: str  # draft | running | completed | failed
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    metadata: dict


class BacktestResultsSummary(BaseModel):
    """Summary statistics for a completed backtest."""
    backtest_id: int
    status: str
    statistics: dict  # {metric_name: value}
    equity_curve: List[dict]  # [{date, portfolio_value, daily_return, benchmark_return}]
    factor_exposures: List[dict]  # [{date, factor_id, exposure_beta}]
    correlation_matrix: List[dict]  # [{factor_1_id, factor_2_id, correlation}]
    alpha_decay: Optional[dict] = None  # Pre/post publication analysis


class BacktestProgressResponse(BaseModel):
    """Real-time progress update during backtest execution."""
    backtest_id: int
    status: str  # running | completed | failed
    progress_percent: float  # 0.0 to 100.0
    current_rebalance_date: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/create", response_model=BacktestResponse)
async def create_backtest(
    req: BacktestCreateRequest,
    session: Session = Depends(get_session)
) -> BacktestResponse:
    """
    Create a new backtest configuration (draft status).

    Validates:
    - Date range coherence (start < end)
    - Factor allocations sum to 100% (if provided)
    - Universe selection validity
    - Transaction cost reasonableness

    Returns immediately with backtest ID (status=draft).
    """
    # Validation
    if req.start_date >= req.end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    if req.factor_allocations:
        total_weight = sum(f["weight"] for f in req.factor_allocations)
        if not (0.99 <= total_weight <= 1.01):  # Allow 1% tolerance for float precision
            raise HTTPException(
                status_code=400,
                detail=f"Factor weights must sum to 100%, got {total_weight*100:.1f}%"
            )

    # Create backtest in draft status
    backtest = Backtest(
        name=req.name,
        backtest_type=req.backtest_type,
        status="draft",
        created_at=datetime.utcnow(),
        metadata={}
    )

    config = BacktestConfiguration(
        backtest_id=backtest.id,
        start_date=req.start_date,
        end_date=req.end_date,
        rebalance_frequency=req.rebalance_frequency,
        universe_selection=req.universe_selection,
        transaction_costs=req.transaction_costs
    )

    # Store factor allocations
    if req.factor_allocations:
        for alloc in req.factor_allocations:
            BacktestFactorAllocation(
                backtest_id=backtest.id,
                factor_id=alloc["factor_id"],
                weight=alloc["weight"]
            )

    session.add(backtest)
    session.add(config)
    session.commit()
    session.refresh(backtest)

    return BacktestResponse(
        id=backtest.id,
        name=backtest.name,
        backtest_type=backtest.backtest_type,
        status=backtest.status,
        created_at=backtest.created_at.isoformat(),
        updated_at=backtest.created_at.isoformat(),
        completed_at=None,
        metadata=backtest.metadata
    )


@router.post("/{backtest_id}/run")
async def run_backtest(
    backtest_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
) -> dict:
    """
    Trigger async execution of a backtest.

    - Updates status from draft → running
    - Enqueues background task for execution
    - Returns immediately with task_id for polling

    Long-running: 30-60+ seconds typical (depends on date range, rebalance freq).
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if backtest.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Can only run backtests in draft status, got {backtest.status}"
        )

    backtest.status = "running"
    backtest.updated_at = datetime.utcnow()
    session.add(backtest)
    session.commit()

    # Enqueue async task
    background_tasks.add_task(execute_backtest, backtest_id, str(session))

    return {
        "backtest_id": backtest_id,
        "status": "running",
        "message": "Backtest queued for execution. Poll /backtests/{backtest_id}/status for progress."
    }


@router.get("/{backtest_id}/status")
async def get_backtest_status(
    backtest_id: int,
    session: Session = Depends(get_session)
) -> BacktestProgressResponse:
    """
    Get current status and progress of a running or completed backtest.

    - status: draft | running | completed | failed
    - progress_percent: 0.0 to 100.0 (updated during execution)
    - current_rebalance_date: current date being processed (if running)
    - error_message: populated if status=failed

    Frontend polls this endpoint ~1-2 sec intervals during execution.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    progress = backtest.metadata.get("progress", {})

    return BacktestProgressResponse(
        backtest_id=backtest_id,
        status=backtest.status,
        progress_percent=progress.get("percent", 0.0),
        current_rebalance_date=progress.get("current_date"),
        error_message=progress.get("error") if backtest.status == "failed" else None
    )


@router.get("/{backtest_id}/results")
async def get_backtest_results(
    backtest_id: int,
    session: Session = Depends(get_session)
) -> BacktestResultsSummary:
    """
    Retrieve full results of a completed backtest.

    Returns:
    - Equity curve (daily portfolio value + returns vs benchmark)
    - Statistics (Sharpe, Sortino, Calmar, etc.)
    - Factor exposures (rolling betas)
    - Correlation matrix
    - Alpha decay analysis (if applicable)

    Only available if status=completed. Returns 404 if not yet complete.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest or backtest.status != "completed":
        raise HTTPException(
            status_code=404,
            detail="Backtest not found or not yet completed"
        )

    # Query all result tables
    results = session.exec(
        select(BacktestResults).where(BacktestResults.backtest_id == backtest_id)
    ).all()

    stats = session.exec(
        select(BacktestStatistics).where(BacktestStatistics.backtest_id == backtest_id)
    ).all()

    corr = session.exec(
        select(FactorCorrelationMatrix).where(FactorCorrelationMatrix.backtest_id == backtest_id)
    ).all()

    # Format for response
    equity_curve = [
        {
            "date": r.date.isoformat(),
            "portfolio_value": float(r.portfolio_value),
            "daily_return": float(r.daily_return),
            "benchmark_return": float(r.benchmark_return),
            "turnover": float(r.turnover),
            "factor_exposures": r.factor_exposures
        }
        for r in sorted(results, key=lambda x: x.date)
    ]

    statistics = {s.metric_name: float(s.metric_value) for s in stats}

    correlation = [
        {
            "factor_1_id": c.factor_1_id,
            "factor_2_id": c.factor_2_id,
            "correlation": float(c.correlation_value)
        }
        for c in corr
    ]

    return BacktestResultsSummary(
        backtest_id=backtest_id,
        status=backtest.status,
        statistics=statistics,
        equity_curve=equity_curve,
        factor_exposures=equity_curve,  # Simplified; same data
        correlation_matrix=correlation,
        alpha_decay=backtest.metadata.get("alpha_decay")
    )


@router.get("/list")
async def list_backtests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
) -> dict:
    """
    List all backtests with pagination.

    Supports pagination via skip/limit.
    Returns summary info for each backtest (no full results).
    """
    backtests = session.exec(
        select(Backtest).offset(skip).limit(limit)
    ).all()

    total = session.exec(select(Backtest)).all()

    return {
        "total": len(total),
        "skip": skip,
        "limit": limit,
        "items": [
            BacktestResponse(
                id=b.id,
                name=b.name,
                backtest_type=b.backtest_type,
                status=b.status,
                created_at=b.created_at.isoformat(),
                updated_at=b.updated_at.isoformat(),
                completed_at=b.metadata.get("completed_at"),
                metadata=b.metadata
            )
            for b in backtests
        ]
    }


@router.delete("/{backtest_id}")
async def delete_backtest(
    backtest_id: int,
    session: Session = Depends(get_session)
) -> dict:
    """
    Soft-delete a backtest (mark as deleted without cascade).

    Preserves audit trail; results remain in DB but backtest is hidden.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    backtest.status = "deleted"
    backtest.updated_at = datetime.utcnow()
    session.add(backtest)
    session.commit()

    return {"backtest_id": backtest_id, "status": "deleted"}


@router.get("/{backtest_id}/export")
async def export_backtest_json(
    backtest_id: int,
    session: Session = Depends(get_session)
) -> dict:
    """
    Export full backtest results as JSON.

    Includes:
    - Configuration
    - Equity curve
    - Statistics
    - Factor exposures
    - Correlation matrix
    - Alpha decay

    Suitable for external analysis, archiving, or sharing.
    """
    backtest = session.get(Backtest, backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # Gather all related data
    config = session.exec(
        select(BacktestConfiguration).where(
            BacktestConfiguration.backtest_id == backtest_id
        )
    ).first()

    results = await get_backtest_results(backtest_id, session)

    allocations = session.exec(
        select(BacktestFactorAllocation).where(
            BacktestFactorAllocation.backtest_id == backtest_id
        )
    ).all()

    export_data = {
        "metadata": {
            "backtest_id": backtest.id,
            "name": backtest.name,
            "backtest_type": backtest.backtest_type,
            "status": backtest.status,
            "created_at": backtest.created_at.isoformat(),
            "completed_at": backtest.metadata.get("completed_at")
        },
        "configuration": {
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "rebalance_frequency": config.rebalance_frequency,
            "universe_selection": config.universe_selection,
            "transaction_costs": config.transaction_costs
        },
        "factor_allocations": [
            {
                "factor_id": a.factor_id,
                "weight": float(a.weight)
            }
            for a in allocations
        ],
        "results": results.dict()
    }

    return export_data
```

#### 1.3 Factors Router Endpoints

**File**: `backend/routers/factors.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

router = APIRouter(prefix="/api/factors", tags=["factors"])

# ============================================================================
# SCHEMAS
# ============================================================================

class FactorDefinitionResponse(BaseModel):
    id: int
    factor_name: str
    factor_type: str  # fama_french | custom
    is_published: bool
    publication_date: Optional[str] = None
    description: str


class CustomFactorDefinitionRequest(BaseModel):
    """Request to create a custom factor."""
    factor_name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    calculation_formula: str = Field(
        ...,
        description="Formula: e.g., 'fcf_yield = (operating_cash_flow - capex) / market_cap'"
    )
    fundamentals_required: List[str] = Field(
        ...,
        description="List of fundamental metrics needed: revenue, net_income, fcf, etc."
    )


class FactorScoreResponse(BaseModel):
    ticker: str
    score_date: str
    factor_id: int
    factor_score: float  # 0-100 percentile score


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/library")
async def get_factor_library(session: Session = Depends(get_session)) -> dict:
    """
    Retrieve pre-built Fama-French 5-factor library.

    Returns all 5 FF factors with their definitions and latest ingestion timestamp.

    Factors:
    - MKT-RF: Market excess return
    - SMB: Small-minus-big (size factor)
    - HML: High-minus-low (value factor)
    - RMW: Robust-minus-weak (profitability)
    - CMA: Conservative-minus-aggressive (investment)
    """
    ff_factors = session.exec(
        select(FactorDefinition).where(FactorDefinition.factor_type == "fama_french")
    ).all()

    return {
        "factors": [
            FactorDefinitionResponse(
                id=f.id,
                factor_name=f.factor_name,
                factor_type=f.factor_type,
                is_published=f.is_published,
                publication_date=f.publication_date.isoformat() if f.publication_date else None,
                description=f.description or ""
            )
            for f in ff_factors
        ],
        "count": len(ff_factors)
    }


@router.get("/custom")
async def list_custom_factors(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
) -> dict:
    """
    List all custom factors created by users.

    Pagination supported.
    """
    factors = session.exec(
        select(FactorDefinition)
        .where(FactorDefinition.factor_type == "custom")
        .offset(skip)
        .limit(limit)
    ).all()

    total = session.exec(
        select(FactorDefinition).where(FactorDefinition.factor_type == "custom")
    ).all()

    return {
        "total": len(total),
        "items": [
            FactorDefinitionResponse(
                id=f.id,
                factor_name=f.factor_name,
                factor_type=f.factor_type,
                is_published=f.is_published,
                publication_date=f.publication_date.isoformat() if f.publication_date else None,
                description=f.description or ""
            )
            for f in factors
        ]
    }


@router.post("/custom/create")
async def create_custom_factor(
    req: CustomFactorDefinitionRequest,
    session: Session = Depends(get_session)
) -> FactorDefinitionResponse:
    """
    Create a new custom factor definition.

    Does NOT compute factor scores immediately; that is deferred to data ingestion
    or explicit calculation endpoint.

    Formula validation: Basic syntax check (contains '=', valid field names).
    """
    # Validate formula syntax
    if "=" not in req.calculation_formula:
        raise HTTPException(
            status_code=400,
            detail="Formula must contain '=' assignment"
        )

    factor = FactorDefinition(
        factor_name=req.factor_name,
        factor_type="custom",
        is_published=False,
        description=req.description,
        metadata={
            "calculation_formula": req.calculation_formula,
            "fundamentals_required": req.fundamentals_required
        }
    )

    session.add(factor)
    session.commit()
    session.refresh(factor)

    return FactorDefinitionResponse(
        id=factor.id,
        factor_name=factor.factor_name,
        factor_type=factor.factor_type,
        is_published=factor.is_published,
        description=factor.description
    )


@router.get("/{factor_id}/scores")
async def get_factor_scores(
    factor_id: int,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: Session = Depends(get_session)
) -> dict:
    """
    Retrieve factor scores for all securities on a given date or date range.

    Scores are percentile-ranked (0-100).
    Supports filtering by date range for time-series analysis.
    """
    query = select(ScreenerFactorScore).where(ScreenerFactorScore.factor_id == factor_id)

    if date_from:
        query = query.where(ScreenerFactorScore.score_date >= date_from)
    if date_to:
        query = query.where(ScreenerFactorScore.score_date <= date_to)

    scores = session.exec(
        query.offset(skip).limit(limit)
    ).all()

    return {
        "factor_id": factor_id,
        "count": len(scores),
        "scores": [
            FactorScoreResponse(
                ticker=s.ticker,
                score_date=s.score_date.isoformat(),
                factor_id=s.factor_id,
                factor_score=float(s.factor_score)
            )
            for s in scores
        ]
    }


@router.get("/{factor_id}/correlation")
async def get_factor_correlation(
    factor_id: int,
    backtest_id: Optional[int] = Query(None),
    session: Session = Depends(get_session)
) -> dict:
    """
    Get correlation of a factor with all others in a backtest.

    If backtest_id not provided, returns correlations from latest run.
    """
    if backtest_id:
        corr = session.exec(
            select(FactorCorrelationMatrix).where(
                FactorCorrelationMatrix.backtest_id == backtest_id,
                (FactorCorrelationMatrix.factor_1_id == factor_id) |
                (FactorCorrelationMatrix.factor_2_id == factor_id)
            )
        ).all()
    else:
        corr = session.exec(
            select(FactorCorrelationMatrix).where(
                (FactorCorrelationMatrix.factor_1_id == factor_id) |
                (FactorCorrelationMatrix.factor_2_id == factor_id)
            )
        ).all()

    return {
        "factor_id": factor_id,
        "correlations": [
            {
                "factor_1_id": c.factor_1_id,
                "factor_2_id": c.factor_2_id,
                "correlation": float(c.correlation_value),
                "as_of_date": c.as_of_date.isoformat() if c.as_of_date else None
            }
            for c in corr
        ]
    }
```

#### 1.4 Data Ingestion Router Endpoints

**File**: `backend/routers/data_ingestion.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel

router = APIRouter(prefix="/api/data", tags=["data-ingestion"])

class DataIngestResponse(BaseModel):
    task_id: str
    source: str  # kenneth_french | yfinance | edgar
    status: str
    message: str


@router.post("/ingest-kenneth-french")
async def ingest_kenneth_french_factors(
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    session: Session = Depends(get_session)
) -> DataIngestResponse:
    """
    Fetch latest Fama-French factor returns from Kenneth French Data Library.

    - Downloads 5-factor CSV daily and monthly returns
    - Parses and validates
    - Stores with ingestion_timestamp for PiT enforcement
    - Runs async (typically < 5 seconds for full history)

    force_refresh=True: Re-download even if recent data exists.
    """
    task_id = f"ff_{datetime.utcnow().timestamp()}"
    background_tasks.add_task(
        load_kenneth_french_factors,
        force_refresh=force_refresh,
        session=session
    )

    return DataIngestResponse(
        task_id=task_id,
        source="kenneth_french",
        status="queued",
        message="Kenneth French factors ingestion queued. Check logs for completion."
    )


@router.post("/ingest-price-history")
async def ingest_price_history(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session)
) -> DataIngestResponse:
    """
    Fetch price history for a security from yfinance.

    - Queries yfinance for OHLCV
    - Stores with ingestion_timestamp (to enforce PiT, no look-ahead)
    - Handles delisting/acquisition events

    Typical runtime: 1-2 seconds per ticker.
    """
    task_id = f"price_{ticker}_{datetime.utcnow().timestamp()}"
    background_tasks.add_task(
        load_price_history,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        session=session
    )

    return DataIngestResponse(
        task_id=task_id,
        source="yfinance",
        status="queued",
        message=f"Price history ingestion for {ticker} queued."
    )


@router.post("/ingest-fundamentals")
async def ingest_fundamentals(
    ticker: str,
    source: str = "sec_edgar",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session)
) -> DataIngestResponse:
    """
    Fetch fundamental data from SEC EDGAR or other sources.

    Stores snapshots with ingestion_timestamp to enforce PiT.
    Metrics: revenue, net_income, fcf, eps, book_value, etc.

    Typical runtime: 3-5 seconds per ticker (SEC parsing is slow).
    """
    task_id = f"fundamentals_{ticker}_{datetime.utcnow().timestamp()}"
    background_tasks.add_task(
        load_fundamentals,
        ticker=ticker,
        source=source,
        session=session
    )

    return DataIngestResponse(
        task_id=task_id,
        source=source,
        status="queued",
        message=f"Fundamentals ingestion for {ticker} queued."
    )


@router.get("/status/{task_id}")
async def get_ingestion_status(task_id: str) -> dict:
    """
    Check status of a running ingestion task.

    Returns: status (queued | running | completed | failed), progress, error_message.
    """
    # Note: This would require a task queue (Celery/RQ) in production.
    # For MVP, just return placeholder.
    return {
        "task_id": task_id,
        "status": "completed",
        "message": "Data ingestion completed."
    }
```

#### 1.5 Error Handling & Status Codes

All endpoints follow consistent error handling:

```
400 Bad Request
  - Malformed input (e.g., date range invalid, weights don't sum to 100)
  - Missing required fields

404 Not Found
  - Backtest doesn't exist
  - Factor not found
  - Results not yet available

422 Unprocessable Entity
  - Pydantic validation error (Fastapi auto-response)

500 Internal Server Error
  - Backtest execution failure
  - Database error
  - Unexpected exception in business logic
```

Error response format:
```json
{
  "error": {
    "code": "INVALID_DATE_RANGE",
    "message": "start_date must be before end_date",
    "details": {}
  }
}
```

---

### 2. Service Layer Architecture

The service layer contains pure business logic, completely decoupled from HTTP concerns. All services are synchronous or async-capable but not tied to FastAPI's lifespan.

#### 2.1 BacktestEngine Service

**File**: `backend/services/backtest_engine.py`

Orchestrates the entire walk-forward backtesting protocol.

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import date, datetime, timedelta
import logging
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Executes walk-forward backtesting with strict PiT enforcement.

    Protocol:
    1. Load configuration (date range, factors, weights, rebalance frequency)
    2. For each rebalance date:
       a. Query fundamental data as of that date (PiT enforced via ingestion_timestamp)
       b. Calculate factor scores for eligible universe
       c. Rank securities by composite factor score
       d. Construct portfolio (quintile/decile long-only or long-short)
       e. Calculate daily returns until next rebalance
    3. Compute statistics and exposures across full period
    4. Store results in backtest_results, backtest_statistics tables
    """

    def __init__(self, session: Session):
        self.session = session
        self.logger = logger

    def run(
        self,
        backtest_id: int,
        config: 'BacktestConfiguration',
        factor_allocations: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute full backtest with progress updates.

        Args:
            backtest_id: ID of backtest to execute
            config: BacktestConfiguration object
            factor_allocations: List of {factor_id, weight}
            progress_callback: Called with (percent, current_date, total_dates)

        Returns:
            Dictionary with results metadata
        """
        try:
            # Step 1: Determine rebalance dates
            rebalance_dates = self._compute_rebalance_schedule(
                config.start_date,
                config.end_date,
                config.rebalance_frequency
            )

            total_dates = len(rebalance_dates)
            portfolio_values = []
            factor_exposures_series = []
            turnover_series = []

            # Step 2: Walk-forward loop
            previous_holdings = {}  # {ticker: weight}

            for idx, rebalance_date in enumerate(rebalance_dates):
                # Progress callback
                if progress_callback:
                    progress_callback(
                        percent=(idx / total_dates) * 100,
                        current_date=rebalance_date.isoformat(),
                        total_dates=total_dates
                    )

                # Query data as of rebalance_date (PiT enforcement)
                eligible_tickers = self._get_eligible_universe(
                    as_of_date=rebalance_date,
                    universe_config=config.universe_selection
                )

                # Calculate composite factor scores
                factor_scores = self._calculate_factor_scores(
                    tickers=eligible_tickers,
                    factor_allocations=factor_allocations,
                    as_of_date=rebalance_date
                )

                # Construct portfolio (quintile-weighted)
                new_holdings = self._construct_portfolio(
                    factor_scores=factor_scores,
                    construction_method="quintile_long_only",  # Configurable
                    num_quintiles=5
                )

                # Calculate turnover
                turnover = self._calculate_turnover(previous_holdings, new_holdings)
                turnover_series.append({
                    "date": rebalance_date,
                    "turnover": turnover
                })

                # Simulate returns until next rebalance (or end date)
                next_rebalance_date = (
                    rebalance_dates[idx + 1] if idx + 1 < len(rebalance_dates)
                    else config.end_date
                )

                daily_results = self._simulate_holdings(
                    holdings=new_holdings,
                    start_date=rebalance_date,
                    end_date=next_rebalance_date,
                    transaction_costs=config.transaction_costs
                )

                portfolio_values.extend(daily_results)

                # Calculate rolling factor exposures
                exposures = self._calculate_factor_exposures(
                    holdings=new_holdings,
                    factor_allocations=factor_allocations,
                    as_of_date=rebalance_date
                )

                factor_exposures_series.extend([
                    {
                        "date": rebalance_date,
                        "exposures": exposures
                    }
                ])

                previous_holdings = new_holdings

            # Step 3: Store results
            self._store_results(
                backtest_id=backtest_id,
                equity_curve=portfolio_values,
                factor_exposures=factor_exposures_series,
                turnover=turnover_series
            )

            # Step 4: Calculate statistics
            self._calculate_statistics(backtest_id, portfolio_values)

            # Step 5: Calculate correlation matrix
            self._calculate_correlations(backtest_id, factor_allocations)

            # Step 6: Alpha decay analysis
            self._analyze_alpha_decay(backtest_id, factor_allocations)

            return {
                "status": "completed",
                "num_rebalances": total_dates,
                "num_daily_results": len(portfolio_values)
            }

        except Exception as e:
            self.logger.error(f"Backtest {backtest_id} failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }

    def _compute_rebalance_schedule(
        self,
        start_date: date,
        end_date: date,
        frequency: str
    ) -> List[date]:
        """
        Generate list of rebalance dates based on frequency.

        Frequencies: daily, weekly, monthly, quarterly, annual
        """
        dates = []
        current = start_date

        if frequency == "daily":
            delta = timedelta(days=1)
        elif frequency == "weekly":
            delta = timedelta(weeks=1)
        elif frequency == "monthly":
            # Month-end dates
            pass
        elif frequency == "quarterly":
            pass
        elif frequency == "annual":
            delta = timedelta(days=365)

        while current <= end_date:
            dates.append(current)
            current += delta

        return dates

    def _get_eligible_universe(
        self,
        as_of_date: date,
        universe_config: str
    ) -> List[str]:
        """
        Query securities eligible on as_of_date.

        Checks security_lifecycle_events to ensure:
        - Security was active on as_of_date (not delisted before it)
        - Security matches universe_config (SP500, Nasdaq, etc.)

        Returns list of tickers.
        """
        # Query securities with active status on as_of_date
        from backend.models.securities import Security, SecurityLifecycleEvent

        securities = self.session.exec(
            select(Security).where(Security.sector != None)  # Active securities have sector
        ).all()

        eligible = []
        for sec in securities:
            # Check lifecycle events to ensure active on as_of_date
            events = self.session.exec(
                select(SecurityLifecycleEvent)
                .where(SecurityLifecycleEvent.ticker == sec.ticker)
                .where(SecurityLifecycleEvent.event_date <= as_of_date)
            ).all()

            # If most recent event is active, include it
            if events:
                most_recent = max(events, key=lambda e: e.event_date)
                if most_recent.event_type == "active":
                    eligible.append(sec.ticker)

        return eligible

    def _calculate_factor_scores(
        self,
        tickers: List[str],
        factor_allocations: List[Dict],
        as_of_date: date
    ) -> Dict[str, float]:
        """
        Calculate composite factor scores for each ticker as of as_of_date.

        Composite score = sum(factor_weight * factor_percentile_score)

        All data queries enforce PiT via ingestion_timestamp <= as_of_date.
        """
        factor_service = FactorCalculator(self.session)

        scores = {}
        for ticker in tickers:
            composite_score = 0.0

            for alloc in factor_allocations:
                factor_id = alloc["factor_id"]
                weight = alloc["weight"]

                # Query factor score as of as_of_date
                score = factor_service.get_factor_score(
                    factor_id=factor_id,
                    ticker=ticker,
                    as_of_date=as_of_date
                )

                if score is not None:
                    composite_score += weight * score

            scores[ticker] = composite_score

        return scores

    def _construct_portfolio(
        self,
        factor_scores: Dict[str, float],
        construction_method: str = "quintile_long_only",
        num_quintiles: int = 5
    ) -> Dict[str, float]:
        """
        Rank tickers by composite score and construct portfolio.

        Methods:
        - quintile_long_only: Top 20% equally weighted
        - decile_long_short: Top 10% long, bottom 10% short (beta-neutral)

        Returns: {ticker: weight} where weights sum to 1.0
        """
        sorted_scores = sorted(
            factor_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        if construction_method == "quintile_long_only":
            cutoff_idx = len(sorted_scores) // num_quintiles
            top_quintile = sorted_scores[:cutoff_idx]

            weights = {}
            equal_weight = 1.0 / len(top_quintile)
            for ticker, _ in top_quintile:
                weights[ticker] = equal_weight

            return weights

        # Add other construction methods as needed
        return {}

    def _calculate_turnover(
        self,
        previous_holdings: Dict[str, float],
        new_holdings: Dict[str, float]
    ) -> float:
        """
        Turnover = sum of absolute changes in position weights.

        Formula: sum(|new_weight[i] - old_weight[i]|) / 2
        """
        all_tickers = set(previous_holdings.keys()) | set(new_holdings.keys())

        total_change = 0.0
        for ticker in all_tickers:
            old_weight = previous_holdings.get(ticker, 0.0)
            new_weight = new_holdings.get(ticker, 0.0)
            total_change += abs(new_weight - old_weight)

        return total_change / 2.0

    def _simulate_holdings(
        self,
        holdings: Dict[str, float],
        start_date: date,
        end_date: date,
        transaction_costs: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate daily portfolio returns from start_date to end_date given fixed holdings.

        - Fetch daily price data (with PiT enforcement)
        - Apply transaction costs on first day
        - Calculate daily returns
        - Track benchmark returns

        Returns list of {date, portfolio_value, daily_return, benchmark_return}
        """
        from backend.models.securities import PriceHistory

        # Initialize portfolio value
        initial_value = 1000000.0  # $1M

        # Apply transaction costs on first day
        transaction_cost = sum(transaction_costs.get("commission_bps", 10) +
                              transaction_costs.get("slippage_bps", 5)) / 10000
        portfolio_value = initial_value * (1 - transaction_cost)

        results = []

        # Fetch price data for all holdings
        prices = {}
        for ticker in holdings.keys():
            price_history = self.session.exec(
                select(PriceHistory)
                .where(PriceHistory.ticker == ticker)
                .where(PriceHistory.date >= start_date)
                .where(PriceHistory.date <= end_date)
            ).all()

            prices[ticker] = {p.date: p.close for p in price_history}

        # Calculate daily returns
        current_date = start_date
        while current_date <= end_date:
            day_returns = []
            for ticker, weight in holdings.items():
                if current_date in prices[ticker]:
                    # Simplified: use daily return
                    day_returns.append(weight * 0.0001)  # Placeholder

            daily_return = sum(day_returns)
            portfolio_value *= (1 + daily_return)

            results.append({
                "date": current_date,
                "portfolio_value": portfolio_value,
                "daily_return": daily_return,
                "benchmark_return": 0.0001  # Placeholder
            })

            current_date += timedelta(days=1)

        return results

    def _store_results(
        self,
        backtest_id: int,
        equity_curve: List[Dict],
        factor_exposures: List[Dict],
        turnover: List[Dict]
    ) -> None:
        """Store all results in database."""
        from backend.models.backtesting import BacktestResults

        for result in equity_curve:
            br = BacktestResults(
                backtest_id=backtest_id,
                date=result["date"],
                portfolio_value=result["portfolio_value"],
                daily_return=result["daily_return"],
                benchmark_return=result["benchmark_return"],
                turnover=0.0,  # Simplified
                factor_exposures={}
            )
            self.session.add(br)

        self.session.commit()

    def _calculate_statistics(
        self,
        backtest_id: int,
        equity_curve: List[Dict]
    ) -> None:
        """Calculate Sharpe, Sortino, Calmar, etc. and store."""
        from backend.models.backtesting import BacktestStatistics

        returns = np.array([e["daily_return"] for e in equity_curve])

        # Annualize
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)

        sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0

        stats = BacktestStatistics(
            backtest_id=backtest_id,
            metric_name="sharpe",
            metric_value=sharpe
        )
        self.session.add(stats)
        self.session.commit()

    def _calculate_correlations(
        self,
        backtest_id: int,
        factor_allocations: List[Dict]
    ) -> None:
        """Calculate correlation matrix between factors."""
        # Placeholder
        pass

    def _analyze_alpha_decay(
        self,
        backtest_id: int,
        factor_allocations: List[Dict]
    ) -> None:
        """Analyze pre/post-publication alpha decay."""
        # Placeholder
        pass

    def _calculate_factor_exposures(
        self,
        holdings: Dict[str, float],
        factor_allocations: List[Dict],
        as_of_date: date
    ) -> Dict[int, float]:
        """Calculate rolling factor betas (exposures)."""
        # Placeholder
        return {alloc["factor_id"]: 1.0 for alloc in factor_allocations}
```

#### 2.2 FactorCalculator Service

**File**: `backend/services/factor_calculator.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import date
import logging
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class FactorCalculator:
    """
    Computes factor scores for securities with strict PiT enforcement.

    Supports:
    - Fama-French 5-factor scores (pre-computed, Kenneth French library)
    - Custom factor scores (computed from fundamentals on-demand)
    - Percentile ranking (0-100 scale)
    """

    def __init__(self, session: Session):
        self.session = session

    def get_factor_score(
        self,
        factor_id: int,
        ticker: str,
        as_of_date: date,
        percentile_rank: bool = True
    ) -> Optional[float]:
        """
        Get factor score for a security as of a specific date.

        Enforces PiT via ingestion_timestamp <= as_of_date.

        Args:
            factor_id: ID of factor definition
            ticker: Security ticker
            as_of_date: Date for which to get score
            percentile_rank: If True, return 0-100 percentile; else raw score

        Returns:
            Score (0-100 if percentile, else raw value), or None if unavailable
        """
        from backend.models.backtesting import FactorDefinition, CustomFactor

        # Get factor definition
        factor = self.session.get(FactorDefinition, factor_id)
        if not factor:
            return None

        if factor.factor_type == "fama_french":
            # Fama-French scores are pre-loaded; just rank them
            score = self._get_fama_french_score(factor_id, as_of_date)
        else:
            # Custom factor: compute from fundamentals
            score = self._compute_custom_factor_score(
                factor_id=factor_id,
                ticker=ticker,
                as_of_date=as_of_date,
                formula=factor.metadata.get("calculation_formula")
            )

        if percentile_rank and score is not None:
            # Convert to 0-100 percentile within universe
            score = self._percentile_rank(factor_id, score, as_of_date)

        return score

    def _get_fama_french_score(
        self,
        factor_id: int,
        as_of_date: date
    ) -> Optional[float]:
        """Get pre-computed Fama-French factor return."""
        from backend.models.backtesting import FamaFrenchFactor

        factor = self.session.exec(
            select(FamaFrenchFactor)
            .where(FamaFrenchFactor.factor_id == factor_id)
            .where(FamaFrenchFactor.date == as_of_date)
        ).first()

        return factor.return_value if factor else None

    def _compute_custom_factor_score(
        self,
        factor_id: int,
        ticker: str,
        as_of_date: date,
        formula: str
    ) -> Optional[float]:
        """
        Compute custom factor score from fundamentals.

        Example formula: "fcf_yield = (operating_cash_flow - capex) / market_cap"

        PiT enforcement: Only use fundamentals with ingestion_timestamp <= as_of_date
        """
        from backend.models.securities import FundamentalsSnapshot

        # Parse formula (very simplified; in production would use safer AST parsing)
        # Extract required metrics from formula
        required_metrics = self._extract_metrics_from_formula(formula)

        # Query most recent fundamentals as of as_of_date
        fundamentals = {}
        for metric in required_metrics:
            fb = self.session.exec(
                select(FundamentalsSnapshot)
                .where(FundamentalsSnapshot.ticker == ticker)
                .where(FundamentalsSnapshot.metric_name == metric)
                .where(FundamentalsSnapshot.ingestion_timestamp <= as_of_date)
                .order_by(FundamentalsSnapshot.ingestion_timestamp.desc())
            ).first()

            if fb:
                fundamentals[metric] = fb.metric_value
            else:
                return None  # Missing data

        # Evaluate formula
        try:
            score = self._evaluate_formula(formula, fundamentals)
            return score
        except Exception as e:
            logger.error(f"Error computing factor {factor_id} for {ticker}: {e}")
            return None

    def _percentile_rank(
        self,
        factor_id: int,
        score: float,
        as_of_date: date
    ) -> float:
        """
        Convert raw score to 0-100 percentile rank within universe.

        Queries all scores for factor_id as of as_of_date,
        ranks given score against them.
        """
        from backend.models.backtesting import CustomFactor

        all_scores = self.session.exec(
            select(CustomFactor)
            .where(CustomFactor.factor_id == factor_id)
            .where(CustomFactor.calculation_date == as_of_date)
        ).all()

        if not all_scores:
            return 50.0  # Default

        values = [s.factor_value for s in all_scores if s.factor_value is not None]
        percentile = (np.array(values) < score).sum() / len(values) * 100

        return percentile

    def _extract_metrics_from_formula(self, formula: str) -> List[str]:
        """Parse formula to extract metric names."""
        # Simplified: split by non-alphanumeric
        import re
        tokens = re.findall(r'\b[a-z_]+\b', formula.lower())
        return list(set(tokens))

    def _evaluate_formula(self, formula: str, fundamentals: Dict) -> float:
        """Safely evaluate formula with given fundamentals."""
        # In production, use AST-based evaluation for security
        try:
            result = eval(formula, {"__builtins__": {}}, fundamentals)
            return float(result)
        except Exception as e:
            raise ValueError(f"Formula evaluation failed: {e}")

    def calculate_correlation_matrix(
        self,
        factor_ids: List[int],
        as_of_date: date,
        lookback_days: int = 252
    ) -> np.ndarray:
        """
        Calculate correlation matrix between multiple factors.

        Returns N x N correlation matrix.
        """
        # Placeholder: would query factor returns and compute correlation
        n = len(factor_ids)
        return np.eye(n)
```

#### 2.3 StatisticsCalculator Service

**File**: `backend/services/statistics_calculator.py`

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class StatisticsCalculator:
    """
    Computes comprehensive performance statistics for backtests.

    Metrics:
    - Annual Return
    - Volatility (Std Dev)
    - Sharpe Ratio
    - Sortino Ratio (downside deviation)
    - Calmar Ratio
    - Max Drawdown
    - Information Ratio (vs benchmark)
    - Hit Rate (% winning days)
    - Recovery Factor
    - Win/Loss Ratio
    """

    @staticmethod
    def calculate_all_metrics(
        returns: List[float],
        benchmark_returns: List[float],
        risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """
        Calculate all statistics from daily return series.

        Args:
            returns: Daily portfolio returns (decimal, e.g., 0.01 = 1%)
            benchmark_returns: Daily benchmark returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Dictionary of metric_name -> metric_value
        """
        returns_array = np.array(returns)
        benchmark_array = np.array(benchmark_returns)

        metrics = {}

        # Annual return
        annual_return = (1 + returns_array).prod() ** (252 / len(returns_array)) - 1
        metrics["annual_return"] = annual_return

        # Volatility
        daily_vol = returns_array.std()
        annual_vol = daily_vol * np.sqrt(252)
        metrics["annual_volatility"] = annual_vol

        # Sharpe Ratio
        daily_rf = risk_free_rate / 252
        excess_returns = returns_array - daily_rf
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        metrics["sharpe_ratio"] = sharpe

        # Sortino Ratio (uses downside deviation)
        downside = returns_array[returns_array < 0]
        downside_std = downside.std() * np.sqrt(252)
        sortino = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        metrics["sortino_ratio"] = sortino

        # Max Drawdown
        cumulative = (1 + returns_array).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        metrics["max_drawdown"] = drawdown.min()

        # Calmar Ratio
        calmar = annual_return / abs(metrics["max_drawdown"]) if metrics["max_drawdown"] != 0 else 0
        metrics["calmar_ratio"] = calmar

        # Information Ratio
        excess = returns_array - benchmark_array
        info_ratio = excess.mean() / excess.std() * np.sqrt(252)
        metrics["information_ratio"] = info_ratio

        # Hit Rate
        hit_rate = (returns_array > 0).sum() / len(returns_array)
        metrics["hit_rate"] = hit_rate

        # Win/Loss Ratio
        wins = (returns_array > 0).sum()
        losses = (returns_array < 0).sum()
        metrics["win_loss_ratio"] = wins / losses if losses > 0 else 0

        return metrics

    @staticmethod
    def calculate_monthly_returns(daily_returns: List[float]) -> pd.Series:
        """Group daily returns into monthly periods."""
        # Placeholder
        pass

    @staticmethod
    def calculate_rolling_sharpe(
        returns: List[float],
        window: int = 60
    ) -> List[float]:
        """Calculate Sharpe ratio in rolling window."""
        # Placeholder
        pass
```

#### 2.4 Data Services

Additional services for data loading:

- **FamaFrenchLoader**: Fetches Kenneth French CSV data, parses, validates, stores with PiT timestamps
- **PriceHistoryLoader**: Fetches yfinance OHLCV, handles delisting events
- **FundamentalsLoader**: SEC EDGAR integration or alternative data provider

---

### 3. Background Task Handling & Progress Tracking

Backtests can take 30-60+ seconds to complete. We implement async execution with progress polling:

#### 3.1 FastAPI BackgroundTasks (MVP)

```python
from fastapi import BackgroundTasks, APIRouter

@router.post("/{backtest_id}/run")
async def run_backtest(
    backtest_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Enqueue backtest for async execution."""
    background_tasks.add_task(execute_backtest, backtest_id, session)
    return {"backtest_id": backtest_id, "status": "running"}


async def execute_backtest(backtest_id: int, session: Session):
    """Long-running backtest execution."""
    backtest = session.get(Backtest, backtest_id)
    backtest.status = "running"
    session.add(backtest)
    session.commit()

    engine = BacktestEngine(session)
    config = session.exec(
        select(BacktestConfiguration).where(
            BacktestConfiguration.backtest_id == backtest_id
        )
    ).first()

    def progress(percent, current_date, total):
        backtest.metadata["progress"] = {
            "percent": percent,
            "current_date": current_date,
            "total_dates": total
        }
        session.add(backtest)
        session.commit()

    result = engine.run(backtest_id, config, progress_callback=progress)

    backtest.status = result["status"]
    backtest.metadata["completed_at"] = datetime.utcnow().isoformat()
    session.add(backtest)
    session.commit()
```

#### 3.2 Celery/RQ (Production Scale)

For production, implement Celery with Redis:

```python
from celery import Celery

celery_app = Celery("backtester", broker="redis://localhost:6379")

@celery_app.task(bind=True)
def execute_backtest_task(self, backtest_id):
    """Long-running celery task."""
    def progress_callback(percent, current_date, total):
        self.update_state(
            state='PROGRESS',
            meta={
                'current': percent,
                'total': 100,
                'current_date': current_date
            }
        )

    # Execute engine
    result = engine.run(backtest_id, progress_callback=progress_callback)
    return result
```

Frontend polls `/backtests/{id}/status` at 1-2 second intervals to refresh progress bar.

---

### 4. Data Ingestion Pipeline

#### 4.1 Kenneth French Factor Loader

```python
# backend/services/kenneth_french_loader.py
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
from sqlmodel import Session

class KennethFrenchLoader:
    """Fetch and store Fama-French 5-factor returns."""

    FF_DAILY_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip"
    FF_MONTHLY_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"

    def load(self, session: Session, frequency: str = "daily"):
        """Download, parse, and store FF factors with PiT timestamps."""
        # Download
        response = requests.get(self.FF_DAILY_URL if frequency == "daily" else self.FF_MONTHLY_URL)

        # Parse CSV
        # Store with ingestion_timestamp = now
        ingestion_time = datetime.utcnow()

        for row in parsed_data:
            ff_factor = FamaFrenchFactor(
                factor_id=...,
                date=row['date'],
                return_value=row['return'],
                ingestion_timestamp=ingestion_time
            )
            session.add(ff_factor)

        session.commit()
```

#### 4.2 yfinance Price Loader

```python
# backend/services/price_loader.py
import yfinance as yf
from datetime import datetime
from sqlmodel import Session

class PriceHistoryLoader:
    """Fetch price data from yfinance with PiT enforcement."""

    def load(self, ticker: str, session: Session):
        """Download OHLCV from yfinance, store with ingestion_timestamp."""
        data = yf.download(ticker, start="1990-01-01")

        ingestion_time = datetime.utcnow()

        for idx, row in data.iterrows():
            price = PriceHistory(
                ticker=ticker,
                date=idx.date(),
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume'],
                ingestion_timestamp=ingestion_time
            )
            session.add(price)

        session.commit()
```

---

## Frontend Architecture

### 1. Component Hierarchy & Structure

#### 1.1 New /backtester Route

**File**: `frontend/src/pages/Backtester.tsx`

```typescript
import React, { useState } from 'react';
import { FactorSelector } from '../components/backtester/FactorSelector';
import { WeightSliders } from '../components/backtester/WeightSliders';
import { BacktestConfig } from '../components/backtester/BacktestConfig';
import { ResultsPanel } from '../components/backtester/ResultsPanel';
import { useBacktest } from '../hooks/useBacktest';

export const Backtester: React.FC = () => {
  const [configStep, setConfigStep] = useState<'factors' | 'weights' | 'config' | 'results'>('factors');
  const [selectedFactors, setSelectedFactors] = useState<number[]>([]);
  const [weights, setWeights] = useState<Record<number, number>>({});
  const [backtest, setBacktest] = useState<any>(null);

  const { createBacktest, runBacktest } = useBacktest();

  const handleStartBacktest = async () => {
    // Transition through config steps
    if (configStep === 'factors') {
      setConfigStep('weights');
    } else if (configStep === 'weights') {
      setConfigStep('config');
    } else if (configStep === 'config') {
      // Create and run backtest
      const result = await createBacktest({
        factors: selectedFactors,
        weights,
        // ... other config
      });
      setBacktest(result);
      setConfigStep('results');
    }
  };

  return (
    <div className="flex gap-4 h-full bg-black p-4">
      {/* Left Sidebar: Configuration */}
      <div className="w-96 border border-neutral-800 rounded-lg p-4 overflow-y-auto">
        {configStep === 'factors' && (
          <FactorSelector
            selectedFactors={selectedFactors}
            onChange={setSelectedFactors}
            onNext={() => setConfigStep('weights')}
          />
        )}
        {configStep === 'weights' && (
          <WeightSliders
            factors={selectedFactors}
            weights={weights}
            onChange={setWeights}
            onNext={() => setConfigStep('config')}
          />
        )}
        {configStep === 'config' && (
          <BacktestConfig
            onSubmit={handleStartBacktest}
          />
        )}
      </div>

      {/* Main Results Area */}
      <div className="flex-1">
        {configStep === 'results' && backtest && (
          <ResultsPanel backtest={backtest} />
        )}
      </div>
    </div>
  );
};
```

#### 1.2 Component Definitions

**File**: `frontend/src/components/backtester/FactorSelector.tsx`

```typescript
import React, { useState } from 'react';
import { useFactors } from '../../hooks/useFactors';
import { Checkbox } from '../shared/Checkbox';
import { LoadingState } from '../shared/LoadingState';

interface FactorSelectorProps {
  selectedFactors: number[];
  onChange: (factorIds: number[]) => void;
  onNext: () => void;
}

export const FactorSelector: React.FC<FactorSelectorProps> = ({
  selectedFactors,
  onChange,
  onNext,
}) => {
  const { data: factors, isLoading } = useFactors();

  const handleToggle = (factorId: number) => {
    if (selectedFactors.includes(factorId)) {
      onChange(selectedFactors.filter(f => f !== factorId));
    } else {
      onChange([...selectedFactors, factorId]);
    }
  };

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-neutral-100">Select Factors</h2>

      {/* Fama-French Library */}
      <div>
        <h3 className="text-xs font-mono text-neutral-500 mb-2 uppercase">Fama-French 5</h3>
        {factors?.ff_factors?.map(factor => (
          <div key={factor.id} className="flex items-center gap-2 p-2 hover:bg-neutral-900 rounded">
            <Checkbox
              checked={selectedFactors.includes(factor.id)}
              onChange={() => handleToggle(factor.id)}
            />
            <span className="text-xs text-neutral-300">{factor.factor_name}</span>
          </div>
        ))}
      </div>

      {/* Custom Factors */}
      <div>
        <h3 className="text-xs font-mono text-neutral-500 mb-2 uppercase">Custom Factors</h3>
        {factors?.custom_factors?.map(factor => (
          <div key={factor.id} className="flex items-center gap-2 p-2 hover:bg-neutral-900 rounded">
            <Checkbox
              checked={selectedFactors.includes(factor.id)}
              onChange={() => handleToggle(factor.id)}
            />
            <span className="text-xs text-neutral-300">{factor.factor_name}</span>
          </div>
        ))}
      </div>

      <button
        onClick={onNext}
        disabled={selectedFactors.length === 0}
        className="w-full mt-4 py-2 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-xs rounded"
      >
        Next: Set Weights
      </button>
    </div>
  );
};
```

**File**: `frontend/src/components/backtester/WeightSliders.tsx`

```typescript
import React, { useMemo } from 'react';
import { Slider } from '../shared/Slider';
import { useFactors } from '../../hooks/useFactors';

interface WeightSlidersProps {
  factors: number[];
  weights: Record<number, number>;
  onChange: (weights: Record<number, number>) => void;
  onNext: () => void;
}

export const WeightSliders: React.FC<WeightSlidersProps> = ({
  factors,
  weights,
  onChange,
  onNext,
}) => {
  const { data: factorsData } = useFactors();

  const totalWeight = useMemo(() => {
    return Object.values(weights).reduce((a, b) => a + b, 0);
  }, [weights]);

  const isValid = Math.abs(totalWeight - 1.0) < 0.01;

  const handleWeightChange = (factorId: number, value: number) => {
    // Normalize so all weights sum to 1.0
    const newWeights = { ...weights, [factorId]: value };

    // Proportionally adjust other weights if needed
    const otherWeight = 1.0 - value;
    const otherFactors = factors.filter(f => f !== factorId);

    if (otherFactors.length > 0) {
      const perFactor = otherWeight / otherFactors.length;
      otherFactors.forEach(f => {
        newWeights[f] = perFactor;
      });
    }

    onChange(newWeights);
  };

  const handleEqualWeight = () => {
    const weight = 1.0 / factors.length;
    const newWeights: Record<number, number> = {};
    factors.forEach(f => {
      newWeights[f] = weight;
    });
    onChange(newWeights);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-neutral-100">Factor Weights</h2>

      <button
        onClick={handleEqualWeight}
        className="w-full py-1 text-xs bg-neutral-800 hover:bg-neutral-700 rounded"
      >
        Equal Weight
      </button>

      <div className="space-y-3">
        {factors.map(factorId => {
          const factor = factorsData?.all_factors?.find(f => f.id === factorId);
          const weight = weights[factorId] || 0;

          return (
            <div key={factorId} className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-xs text-neutral-300">{factor?.factor_name}</span>
                <span className="text-xs font-mono text-neutral-500">
                  {(weight * 100).toFixed(1)}%
                </span>
              </div>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={weight}
                onChange={(value) => handleWeightChange(factorId, value)}
              />
            </div>
          );
        })}
      </div>

      <div className="pt-2 border-t border-neutral-800">
        <div className="flex justify-between text-xs">
          <span className="text-neutral-400">Total Weight</span>
          <span className={isValid ? 'text-green-500' : 'text-red-500'}>
            {(totalWeight * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      <button
        onClick={onNext}
        disabled={!isValid}
        className="w-full mt-4 py-2 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-xs rounded"
      >
        Next: Configure Backtest
      </button>
    </div>
  );
};
```

**File**: `frontend/src/components/backtester/BacktestConfig.tsx`

```typescript
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';

interface BacktestConfigProps {
  onSubmit: (config: any) => void;
}

export const BacktestConfig: React.FC<BacktestConfigProps> = ({ onSubmit }) => {
  const { register, handleSubmit, watch } = useForm({
    defaultValues: {
      startDate: '2015-01-01',
      endDate: '2024-12-31',
      rebalanceFrequency: 'monthly',
      universe: 'sp500',
      commissionBps: 10,
      slippageBps: 5,
    },
  });

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-neutral-100">Backtest Configuration</h2>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        <div>
          <label className="text-xs text-neutral-400">Start Date</label>
          <input
            type="date"
            {...register('startDate')}
            className="w-full mt-1 px-2 py-1 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-100"
          />
        </div>

        <div>
          <label className="text-xs text-neutral-400">End Date</label>
          <input
            type="date"
            {...register('endDate')}
            className="w-full mt-1 px-2 py-1 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-100"
          />
        </div>

        <div>
          <label className="text-xs text-neutral-400">Rebalance Frequency</label>
          <select
            {...register('rebalanceFrequency')}
            className="w-full mt-1 px-2 py-1 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-100"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="annual">Annual</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-neutral-400">Universe</label>
          <select
            {...register('universe')}
            className="w-full mt-1 px-2 py-1 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-100"
          >
            <option value="sp500">S&P 500</option>
            <option value="nasdaq100">Nasdaq-100</option>
            <option value="russell2000">Russell 2000</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-neutral-400">Commission (bps)</label>
          <input
            type="number"
            {...register('commissionBps')}
            className="w-full mt-1 px-2 py-1 bg-neutral-900 border border-neutral-800 rounded text-xs text-neutral-100"
          />
        </div>

        <button
          type="submit"
          className="w-full mt-4 py-2 bg-blue-900 hover:bg-blue-800 text-xs rounded font-semibold"
        >
          Run Backtest
        </button>
      </form>
    </div>
  );
};
```

**File**: `frontend/src/components/backtester/ResultsPanel.tsx`

```typescript
import React from 'react';
import { EquityCurveChart } from './EquityCurveChart';
import { StatisticsPanel } from './StatisticsPanel';
import { FactorExposureChart } from './FactorExposureChart';
import { CorrelationMatrix } from './CorrelationMatrix';
import { AlphaDecayPanel } from './AlphaDecayPanel';
import { ExportButton } from './ExportButton';
import { useBacktestResults } from '../../hooks/useBacktestResults';

interface ResultsPanelProps {
  backtest: any;
}

export const ResultsPanel: React.FC<ResultsPanelProps> = ({ backtest }) => {
  const { data: results, isLoading } = useBacktestResults(backtest.id);

  if (isLoading) return <div className="text-xs text-neutral-400">Loading results...</div>;

  return (
    <div className="space-y-4 h-full overflow-y-auto">
      {/* Equity Curve */}
      <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-950">
        <h3 className="text-xs font-semibold text-neutral-100 mb-4">Equity Curve</h3>
        <EquityCurveChart data={results?.equity_curve} />
      </div>

      {/* Statistics */}
      <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-950">
        <h3 className="text-xs font-semibold text-neutral-100 mb-4">Performance Metrics</h3>
        <StatisticsPanel statistics={results?.statistics} />
      </div>

      {/* Rolling Factor Exposure */}
      <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-950">
        <h3 className="text-xs font-semibold text-neutral-100 mb-4">Factor Exposure</h3>
        <FactorExposureChart data={results?.factor_exposures} />
      </div>

      {/* Correlation Matrix */}
      <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-950">
        <h3 className="text-xs font-semibold text-neutral-100 mb-4">Factor Correlations</h3>
        <CorrelationMatrix data={results?.correlation_matrix} />
      </div>

      {/* Alpha Decay */}
      {results?.alpha_decay && (
        <div className="border border-neutral-800 rounded-lg p-4 bg-neutral-950">
          <h3 className="text-xs font-semibold text-neutral-100 mb-4">Alpha Decay Analysis</h3>
          <AlphaDecayPanel data={results?.alpha_decay} />
        </div>
      )}

      {/* Export */}
      <div className="flex gap-2">
        <ExportButton backtestId={backtest.id} format="json" />
        <ExportButton backtestId={backtest.id} format="csv" />
      </div>
    </div>
  );
};
```

#### 1.3 Chart Components

**File**: `frontend/src/components/backtester/EquityCurveChart.tsx`

```typescript
import React from 'react';
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface EquityCurveChartProps {
  data: Array<{
    date: string;
    portfolio_value: number;
    daily_return: number;
    benchmark_return: number;
  }>;
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({ data }) => {
  // Compute drawdown overlay
  const dataWithDrawdown = data.map((d, idx) => {
    const cumReturn = data.slice(0, idx + 1).reduce(
      (acc, x) => acc * (1 + x.daily_return),
      1
    );
    const runningMax = data
      .slice(0, idx + 1)
      .reduce((max, x) => Math.max(max, x.portfolio_value), 0);
    const drawdown = (d.portfolio_value - runningMax) / runningMax;

    return { ...d, drawdown };
  });

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ComposedChart data={dataWithDrawdown}>
        <CartesianGrid strokeDasharray="3 3" stroke="#404040" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#a3a3a3' }}
          tickFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <YAxis
          yAxisId="left"
          tick={{ fontSize: 10, fill: '#a3a3a3' }}
          label={{ value: 'Portfolio Value ($)', angle: -90, position: 'insideLeft' }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fontSize: 10, fill: '#a3a3a3' }}
          label={{ value: 'Drawdown (%)', angle: 90, position: 'insideRight' }}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #404040' }}
          formatter={(value: any) => {
            if (typeof value === 'number') {
              return value.toFixed(2);
            }
            return value;
          }}
        />
        <Legend />

        {/* Equity curve */}
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="portfolio_value"
          stroke="#3b82f6"
          dot={false}
          strokeWidth={2}
          name="Portfolio Value"
        />

        {/* Benchmark */}
        <Line
          yAxisId="left"
          type="monotone"
          dataKey="benchmark_return"
          stroke="#6b7280"
          dot={false}
          strokeWidth={1}
          strokeDasharray="5 5"
          name="Benchmark"
        />

        {/* Drawdown overlay */}
        <Area
          yAxisId="right"
          type="monotone"
          dataKey="drawdown"
          fill="#ef4444"
          stroke="#dc2626"
          fillOpacity={0.3}
          name="Drawdown"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
};
```

**File**: `frontend/src/components/backtester/FactorExposureChart.tsx`

```typescript
import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export const FactorExposureChart: React.FC<{ data: any[] }> = ({ data }) => {
  // Transform data to wide format for stacked area
  // data: [{date, exposures: {factor_id: beta}}]

  const transformed = data.map((d) => ({
    date: d.date,
    ...d.exposures,
  }));

  const factorIds = Object.keys(transformed[0] || {}).filter((k) => k !== 'date');

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={transformed}>
        <CartesianGrid strokeDasharray="3 3" stroke="#404040" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: '#a3a3a3' }}
          tickFormatter={(d) => new Date(d).toLocaleDateString()}
        />
        <YAxis tick={{ fontSize: 10, fill: '#a3a3a3' }} />
        <Tooltip contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #404040' }} />
        <Legend />

        {factorIds.map((factorId, idx) => (
          <Area
            key={factorId}
            type="monotone"
            dataKey={factorId}
            stackId="1"
            stroke={colors[idx % colors.length]}
            fill={colors[idx % colors.length]}
            fillOpacity={0.7}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
};
```

**File**: `frontend/src/components/backtester/CorrelationMatrix.tsx`

```typescript
import React, { useMemo } from 'react';

export const CorrelationMatrix: React.FC<{ data: any[] }> = ({ data }) => {
  const matrix = useMemo(() => {
    // Convert from list of {factor_1_id, factor_2_id, correlation}
    // to 2D matrix
    const ids = new Set<number>();
    data.forEach((d) => {
      ids.add(d.factor_1_id);
      ids.add(d.factor_2_id);
    });

    const idArray = Array.from(ids).sort();
    const mat: Record<number, Record<number, number>> = {};

    idArray.forEach((id) => {
      mat[id] = {};
      idArray.forEach((id2) => {
        mat[id][id2] = id === id2 ? 1 : 0;
      });
    });

    data.forEach((d) => {
      mat[d.factor_1_id][d.factor_2_id] = d.correlation;
      mat[d.factor_2_id][d.factor_1_id] = d.correlation;
    });

    return { matrix: mat, ids: idArray };
  }, [data]);

  const getColor = (value: number): string => {
    if (value > 0.5) return 'bg-red-900';
    if (value > 0) return 'bg-red-700';
    if (value < -0.5) return 'bg-blue-900';
    if (value < 0) return 'bg-blue-700';
    return 'bg-neutral-800';
  };

  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse">
        <tbody>
          {matrix.ids.map((id1) => (
            <tr key={id1}>
              <td className="px-2 py-1 text-neutral-400 border border-neutral-800">
                Factor {id1}
              </td>
              {matrix.ids.map((id2) => (
                <td
                  key={id2}
                  className={`px-2 py-1 text-neutral-100 border border-neutral-800 text-center ${getColor(
                    matrix.matrix[id1][id2]
                  )}`}
                >
                  {matrix.matrix[id1][id2].toFixed(2)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

#### 1.4 Shared Components

**File**: `frontend/src/components/backtester/StatisticsPanel.tsx`

```typescript
import React from 'react';

interface StatisticsPanelProps {
  statistics: Record<string, number>;
}

export const StatisticsPanel: React.FC<StatisticsPanelProps> = ({ statistics }) => {
  const metrics = [
    { key: 'annual_return', label: 'Annual Return', format: 'percent' },
    { key: 'annual_volatility', label: 'Volatility', format: 'percent' },
    { key: 'sharpe_ratio', label: 'Sharpe Ratio', format: 'number' },
    { key: 'sortino_ratio', label: 'Sortino Ratio', format: 'number' },
    { key: 'calmar_ratio', label: 'Calmar Ratio', format: 'number' },
    { key: 'max_drawdown', label: 'Max Drawdown', format: 'percent' },
    { key: 'information_ratio', label: 'Information Ratio', format: 'number' },
    { key: 'hit_rate', label: 'Hit Rate', format: 'percent' },
  ];

  const formatValue = (value: number, format: string): string => {
    if (format === 'percent') {
      return `${(value * 100).toFixed(2)}%`;
    }
    return value.toFixed(2);
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {metrics.map((m) => (
        <div key={m.key} className="border border-neutral-800 p-2 rounded bg-neutral-900">
          <div className="text-xs text-neutral-400">{m.label}</div>
          <div className="text-sm font-mono text-neutral-100 mt-1">
            {formatValue(statistics[m.key] || 0, m.format)}
          </div>
        </div>
      ))}
    </div>
  );
};
```

**File**: `frontend/src/components/backtester/AlphaDecayPanel.tsx`

```typescript
import React from 'react';

interface AlphaDecayPanelProps {
  data: {
    pre_publication_return: number;
    post_publication_return: number;
    decay_percentage: number;
    months_post_publication: number;
  };
}

export const AlphaDecayPanel: React.FC<AlphaDecayPanelProps> = ({ data }) => {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-neutral-900 border border-neutral-800 p-3 rounded">
          <div className="text-xs text-neutral-400">Pre-Publication</div>
          <div className="text-sm font-mono text-green-400 mt-1">
            {(data.pre_publication_return * 100).toFixed(2)}%
          </div>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 p-3 rounded">
          <div className="text-xs text-neutral-400">Post-Publication</div>
          <div className="text-sm font-mono text-orange-400 mt-1">
            {(data.post_publication_return * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 p-3 rounded">
        <div className="text-xs text-neutral-400">Alpha Decay</div>
        <div className="text-sm font-mono text-red-400 mt-1">
          {data.decay_percentage.toFixed(1)}%
        </div>
        <div className="text-xs text-neutral-500 mt-2">
          Over {data.months_post_publication} months
        </div>
      </div>
    </div>
  );
};
```

**File**: `frontend/src/components/backtester/ExportButton.tsx`

```typescript
import React from 'react';
import { useBacktestExport } from '../../hooks/useBacktestExport';

interface ExportButtonProps {
  backtestId: number;
  format: 'json' | 'csv';
}

export const ExportButton: React.FC<ExportButtonProps> = ({ backtestId, format }) => {
  const { mutate: exportBacktest, isPending } = useBacktestExport();

  const handleExport = () => {
    exportBacktest({
      backtestId,
      format,
    });
  };

  return (
    <button
      onClick={handleExport}
      disabled={isPending}
      className="flex-1 py-2 px-4 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-xs rounded"
    >
      Export {format.toUpperCase()}
    </button>
  );
};
```

---

### 2. State Management

#### 2.1 TanStack Query Hooks

**File**: `frontend/src/hooks/useBacktest.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

export const useBacktest = () => {
  const queryClient = useQueryClient();

  const createBacktest = useMutation({
    mutationFn: async (config: any) => {
      const response = await apiClient.post('/backtests/create', config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });

  const runBacktest = useMutation({
    mutationFn: async (backtestId: number) => {
      const response = await apiClient.post(`/backtests/${backtestId}/run`);
      return response.data;
    },
  });

  const pollBacktestStatus = (backtestId: number) => {
    return useQuery({
      queryKey: ['backtest', backtestId, 'status'],
      queryFn: async () => {
        const response = await apiClient.get(`/backtests/${backtestId}/status`);
        return response.data;
      },
      refetchInterval: (data) => {
        // Poll every 1-2 seconds if running, else stop
        if (data?.status === 'running') return 1000;
        return false;
      },
    });
  };

  return {
    createBacktest,
    runBacktest,
    pollBacktestStatus,
  };
};
```

**File**: `frontend/src/hooks/useFactors.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

export const useFactors = () => {
  return useQuery({
    queryKey: ['factors'],
    queryFn: async () => {
      const [ffResponse, customResponse] = await Promise.all([
        apiClient.get('/factors/library'),
        apiClient.get('/factors/custom'),
      ]);

      return {
        ff_factors: ffResponse.data.factors,
        custom_factors: customResponse.data.items,
        all_factors: [
          ...ffResponse.data.factors,
          ...customResponse.data.items,
        ],
      };
    },
  });
};
```

**File**: `frontend/src/hooks/useBacktestResults.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

export const useBacktestResults = (backtestId: number) => {
  return useQuery({
    queryKey: ['backtest', backtestId, 'results'],
    queryFn: async () => {
      const response = await apiClient.get(`/backtests/${backtestId}/results`);
      return response.data;
    },
    enabled: !!backtestId,
  });
};
```

#### 2.2 API Client

**File**: `frontend/src/lib/api.ts`

```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle auth
    }
    return Promise.reject(error);
  }
);
```

---

### 3. Routing Integration

**File**: `frontend/src/App.tsx`

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { MorningBrief } from './pages/MorningBrief';
import { Screener } from './pages/Screener';
import { Backtester } from './pages/Backtester';  // NEW
import { WeeklyReport } from './pages/WeeklyReport';
import { Portfolio } from './pages/Portfolio';
import { RRG } from './pages/RRG';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<MorningBrief />} />
          <Route path="/screener" element={<Screener />} />
          <Route path="/backtester" element={<Backtester />} />
          <Route path="/weekly-report" element={<WeeklyReport />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/rrg" element={<RRG />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Cross-Cutting Concerns

### 1. Error Handling Flow

**Error Handling Pipeline**:

```
User Action
  ↓
Frontend Validation (React Hook Form)
  ↓
API Request (axios)
  ↓
Backend Validation (Pydantic)
  ↓
Business Logic Execution
  ↓
[Success: Return 200 + Data]
  ↓
[Error: Return 400/404/500 + Error Object]
  ↓
Frontend Error State (useQuery/useMutation error)
  ↓
Display ErrorState Component or Toast
```

**Error Handling Component**:

```typescript
export const ErrorState: React.FC<{ error: Error }> = ({ error }) => (
  <div className="p-4 bg-red-900/20 border border-red-700 rounded">
    <p className="text-xs text-red-300">{error.message}</p>
  </div>
);
```

**Backend Error Handling**:

```python
from fastapi import HTTPException

try:
    backtest_config = session.get(BacktestConfiguration, config_id)
    if not backtest_config:
        raise HTTPException(
            status_code=404,
            detail="Configuration not found"
        )
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

---

### 2. Security Considerations

#### 2.1 Input Validation

- **Pydantic schemas**: All request bodies validated server-side
- **Date range validation**: start_date < end_date
- **Factor weight validation**: sum to 100% (±1% tolerance)
- **Universe validation**: only allow whitelisted values
- **Formula parsing**: Use AST-based safe evaluation for custom factors (avoid eval())

#### 2.2 SQL Injection Prevention

- **SQLModel ORM**: Parameterized queries prevent SQL injection
- **PiT enforcement**: `ingestion_timestamp <= as_of_date` prevents look-ahead

#### 2.3 Authentication/Authorization

Currently no auth in MVP. Future:
- Add user_id field to Backtest table
- Gate endpoints: `@require_auth`
- Check backtest ownership before returning results

---

### 3. Performance Considerations

#### 3.1 Database Indexing

```sql
-- Key indexes for performance
CREATE INDEX idx_price_history_ticker_date
  ON price_history(ticker, date);

CREATE INDEX idx_price_history_ingestion_timestamp
  ON price_history(ingestion_timestamp);

CREATE INDEX idx_fundamentals_snapshot_ticker_ingestion
  ON fundamentals_snapshot(ticker, ingestion_timestamp);

CREATE INDEX idx_custom_factors_ticker_date
  ON custom_factors(ticker, calculation_date);

CREATE INDEX idx_backtest_results_backtest_id
  ON backtest_results(backtest_id, date);
```

#### 3.2 Caching Strategy

- **Factor library**: Cache at app startup (rarely changes)
- **Factor scores**: Cache per date (1-day TTL)
- **Backtest results**: Cache after completion (immutable)
- **Correlation matrices**: Cache per backtest (immutable)

```python
from functools import lru_cache
from datetime import datetime, timedelta

cache = {}

def get_factor_scores_cached(factor_id, as_of_date):
    cache_key = f"{factor_id}_{as_of_date}"
    if cache_key in cache:
        cached_at, data = cache[cache_key]
        if (datetime.utcnow() - cached_at) < timedelta(days=1):
            return data

    # Fetch from DB
    data = get_factor_scores(factor_id, as_of_date)
    cache[cache_key] = (datetime.utcnow(), data)
    return data
```

#### 3.3 Query Optimization

- **Lazy loading**: Load factor exposures only when requested
- **Pagination**: Limit to 100-1000 rows per request
- **Date partitioning**: Partition price_history and fundamentals_snapshot by date for faster range queries

---

### 4. Database Migrations

Use Alembic for migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add factor backtester tables"

# Apply migration
alembic upgrade head
```

**Migration file** (`alembic/versions/001_initial_backtester.py`):

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create backtests table
    op.create_table(
        'backtests',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        # ... columns
    )

def downgrade():
    op.drop_table('backtests')
```

---

## Risk Assessment & Mitigations

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Long backtest runtime (60+ sec)** | Timeout, poor UX | Implement async processing, progress polling, estimated time display |
| **Memory exhaustion with large dataset** | OOM, crash | Partition tables by date, paginate results, stream processing |
| **PiT enforcement misses** | Look-ahead bias | Database constraints on ingestion_timestamp, automated tests with known-bias examples |
| **Factor calculation errors** | Wrong results | Unit tests per factor, validation against published benchmarks (e.g., FF returns) |
| **Concurrent backtest executions** | Race conditions, data corruption | Database transactions, row-level locking, Celery task queue isolation |
| **Missing fundamental data** | Gaps in analysis | Fallback to market cap weighting, skip security if missing data, warn user |

### Data Quality Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Survivorship bias** | Inflated returns | security_lifecycle_events table tracks delistings, includes full history |
| **Stale factor data** | Outdated analysis | ingestion_timestamp tracks freshness, Kenneth French data updated weekly |
| **Data gaps (weekends, holidays)** | Calculation errors | Skip non-trading days, validate date continuity |

### Business Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **User misinterprets results** | Bad trading decisions | Add disclaimers, documentation, link to academic papers |
| **Results don't match published benchmarks** | Loss of trust | Validate FF factor returns against Kenneth French library quarterly |
| **Slow adoption** | Low engagement | Strong UI/UX, pre-built templates, example backtests |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18)                       │
├─────────────────────────────────────────────────────────────────┤
│  Backtester Page                                                 │
│  ├─ FactorSelector                                               │
│  ├─ WeightSliders                                                │
│  ├─ BacktestConfig                                               │
│  └─ ResultsPanel                                                 │
│     ├─ EquityCurveChart (Recharts)                              │
│     ├─ StatisticsPanel                                           │
│     ├─ FactorExposureChart                                       │
│     ├─ CorrelationMatrix                                         │
│     ├─ AlphaDecayPanel                                           │
│     └─ ExportButton                                              │
│                                                                   │
│  State Management:                                               │
│  ├─ TanStack Query (server state)                               │
│  ├─ React Hook Form (config form state)                         │
│  └─ useBacktest, useFactors, useBacktestResults hooks           │
└──────────────────────────────────────────────────────────────────┘
                            │
                        axios API calls
                            │
┌──────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + SQLModel)                    │
├──────────────────────────────────────────────────────────────────┤
│  API Routers                                                      │
│  ├─ /api/backtests      (CRUD, run, status, results, export)    │
│  ├─ /api/factors        (library, custom, scores, correlation)   │
│  └─ /api/data-ingestion (kenneth-french, prices, fundamentals)   │
│                                                                   │
│  Service Layer                                                    │
│  ├─ BacktestEngine      (walk-forward orchestration)             │
│  ├─ FactorCalculator    (FF + custom factor scoring)             │
│  ├─ StatisticsCalculator (Sharpe, Sortino, Calmar, etc.)        │
│  ├─ KennethFrenchLoader (FF factor ingestion)                   │
│  ├─ PriceHistoryLoader  (yfinance integration)                  │
│  └─ FundamentalsLoader  (SEC EDGAR integration)                 │
│                                                                   │
│  Background Tasks                                                 │
│  ├─ FastAPI BackgroundTasks (MVP) or Celery (production)        │
│  └─ Progress polling via metadata.progress JSON                  │
└──────────────────────────────────────────────────────────────────┘
                            │
                    SQLModel ORM, PiT enforcement
                            │
┌──────────────────────────────────────────────────────────────────┐
│                   DATABASE (PostgreSQL)                           │
├──────────────────────────────────────────────────────────────────┤
│  Time-Series (Partitioned by Date)                               │
│  ├─ price_history (ticker, date, OHLCV, ingestion_timestamp)   │
│  └─ fundamentals_snapshot (ticker, metric, value, ingestion_ts) │
│                                                                   │
│  Security Master                                                  │
│  ├─ securities (ticker, company_name, sector, status)           │
│  └─ security_lifecycle_events (ticker, event_date, event_type)  │
│                                                                   │
│  Factor Definitions                                               │
│  ├─ factor_definitions (FF + custom)                            │
│  ├─ fama_french_factors (daily/monthly returns)                 │
│  └─ custom_factors (ticker-specific scores)                     │
│                                                                   │
│  Backtest Results                                                 │
│  ├─ backtests (name, status, metadata)                          │
│  ├─ backtest_configurations                                      │
│  ├─ backtest_factor_allocations (factor_id, weight)             │
│  ├─ backtest_results (daily portfolio values, returns)          │
│  ├─ backtest_statistics (Sharpe, Sortino, etc.)                │
│  ├─ factor_correlation_matrix                                    │
│  ├─ screener_factor_scores (for Screener integration)           │
│  └─ alpha_decay_analysis (pre/post publication)                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)
- [ ] Database schema creation (Alembic migrations)
- [ ] Kenneth French factor ingestion
- [ ] yfinance price data ingestion
- [ ] BacktestEngine basic walk-forward loop
- [ ] StatisticsCalculator with 6 core metrics
- [ ] Backend API endpoints (CRUD, run, status, results)
- [ ] Frontend Backtester page layout
- [ ] EquityCurveChart with Recharts
- [ ] StatisticsPanel display
- [ ] TanStack Query integration

### Phase 2: Enhancements (Weeks 5-6)
- [ ] Custom factor definition UI + computation
- [ ] Factor correlation matrix + heatmap
- [ ] FactorExposureChart (rolling betas)
- [ ] AlphaDecayPanel (pre/post publication)
- [ ] JSON/CSV export
- [ ] Error handling, validation, edge cases
- [ ] Performance optimization (caching, indexing)

### Phase 3: Integration (Weeks 7-8)
- [ ] Screener integration: factor scores as columns
- [ ] Morning Brief: top factor signals
- [ ] Comprehensive testing (unit, integration, e2e)
- [ ] Documentation
- [ ] Deployment to production

---

## Conclusion

The Factor Backtester architecture is designed for institutional-grade factor research with emphasis on:
- **PiT data integrity**: Immutable ingestion timestamps prevent look-ahead bias
- **Survivorship bias control**: Lifecycle tracking includes delisted securities
- **Async performance**: Long backtests execute in background with progress polling
- **Modular design**: Services decouple from HTTP layer, reusable for Phase 2-4
- **Type safety**: Pydantic + TypeScript strict mode reduce runtime errors
- **User experience**: Responsive charts, step-by-step config wizard, clear error messages

All decisions prioritize accuracy, transparency, and extensibility for future phases.
