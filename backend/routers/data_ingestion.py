"""
API endpoints for data ingestion and loading.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlmodel import Session, select
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, validator
import re
import logging

from backend.database import get_session
from backend.models.securities import Security
from backend.services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)


# Request/Response Models
class IngestPricesRequest(BaseModel):
    """Request to ingest price data."""
    tickers: List[str]
    period: str = "5y"

    @validator('tickers')
    def validate_tickers(cls, v):
        if not v:
            raise ValueError('At least one ticker is required')
        ticker_pattern = re.compile(r'^[A-Z0-9.-]{1,10}$')
        for ticker in v:
            if not ticker_pattern.match(ticker):
                raise ValueError(f'Invalid ticker format: {ticker}. Tickers must be 1-10 uppercase alphanumeric characters, dots, or hyphens.')
        return v


class IngestFundamentalsRequest(BaseModel):
    """Request to ingest fundamental data."""
    tickers: List[str]

    @validator('tickers')
    def validate_tickers(cls, v):
        if not v:
            raise ValueError('At least one ticker is required')
        ticker_pattern = re.compile(r'^[A-Z0-9.-]{1,10}$')
        for ticker in v:
            if not ticker_pattern.match(ticker):
                raise ValueError(f'Invalid ticker format: {ticker}. Tickers must be 1-10 uppercase alphanumeric characters, dots, or hyphens.')
        return v


class IngestStatusResponse(BaseModel):
    """Response with ingestion status."""
    status: str
    tickers_processed: int
    records_ingested: int
    timestamp: datetime


class UniverseResponse(BaseModel):
    """Response with securities in universe."""
    total: int
    limit: int
    offset: int
    securities: List[dict]


# Create router
router = APIRouter(prefix="/api/data", tags=["data_ingestion"])


@router.post("/ingest/prices")
async def ingest_prices(
    request: IngestPricesRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Ingest price history for tickers.

    Args:
        request: List of tickers to ingest
        background_tasks: FastAPI background tasks manager
        session: Database session

    Returns:
        Status response
    """
    try:
        if not request.tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")

        # Add background task
        async def ingest_task():
            service = DataIngestionService(session)
            total_records = 0

            for ticker in request.tickers:
                records = await service.ingest_price_history(ticker, request.period)
                total_records += records

            return total_records

        background_tasks.add_task(ingest_task)

        return {
            "status": "ingestion_started",
            "tickers": request.tickers,
            "period": request.period,
            "message": f"Started price ingestion for {len(request.tickers)} tickers"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting prices: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/ingest/fundamentals")
async def ingest_fundamentals(
    request: IngestFundamentalsRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Ingest fundamentals for tickers.

    Args:
        request: List of tickers to ingest
        background_tasks: FastAPI background tasks manager
        session: Database session

    Returns:
        Status response
    """
    try:
        if not request.tickers:
            raise HTTPException(status_code=400, detail="No tickers provided")

        # Add background task
        async def ingest_task():
            service = DataIngestionService(session)
            total_records = 0

            for ticker in request.tickers:
                records = await service.ingest_fundamentals(ticker)
                total_records += records

            return total_records

        background_tasks.add_task(ingest_task)

        return {
            "status": "ingestion_started",
            "tickers": request.tickers,
            "message": f"Started fundamental ingestion for {len(request.tickers)} tickers"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting fundamentals: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/ingest/fama-french")
async def ingest_fama_french(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Load Fama-French factor data.

    Args:
        background_tasks: FastAPI background tasks manager
        session: Database session

    Returns:
        Status response
    """
    try:
        # Add background task
        async def ingest_task():
            service = DataIngestionService(session)
            records = await service.ingest_fama_french_factors()
            return records

        background_tasks.add_task(ingest_task)

        return {
            "status": "ingestion_started",
            "message": "Started Fama-French factor data ingestion"
        }

    except Exception as e:
        logger.error(f"Error ingesting Fama-French factors: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/universe", response_model=UniverseResponse)
def get_universe(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """
    Get list of securities in universe.

    Args:
        limit: Number of results to return
        offset: Number of results to skip
        session: Database session

    Returns:
        List of securities
    """
    try:
        # Get all securities
        query = select(Security).order_by(Security.ticker.asc())
        all_securities = session.exec(query).all()

        # Apply pagination
        total = len(all_securities)
        paginated = all_securities[offset:offset + limit]

        securities_list = [
            {
                "ticker": sec.ticker,
                "name": sec.name,
                "sector": sec.sector,
                "industry": sec.industry,
                "country": sec.country,
                "status": sec.status,
            }
            for sec in paginated
        ]

        return UniverseResponse(
            total=total,
            limit=limit,
            offset=offset,
            securities=securities_list,
        )

    except Exception as e:
        logger.error(f"Error getting universe: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/universe/search")
def search_universe(
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """
    Search for securities in universe.

    Args:
        ticker: Optional ticker filter (partial match)
        sector: Optional sector filter
        limit: Number of results to return
        session: Database session

    Returns:
        Filtered list of securities
    """
    try:
        query = select(Security)

        if ticker:
            query = query.where(Security.ticker.like(f"%{ticker}%"))

        if sector:
            query = query.where(Security.sector == sector)

        query = query.limit(limit).order_by(Security.ticker.asc())
        securities = session.exec(query).all()

        securities_list = [
            {
                "ticker": sec.ticker,
                "name": sec.name,
                "sector": sec.sector,
                "industry": sec.industry,
                "country": sec.country,
                "status": sec.status,
            }
            for sec in securities
        ]

        return {
            "total": len(securities_list),
            "securities": securities_list,
        }

    except Exception as e:
        logger.error(f"Error searching universe: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/ingest/security")
async def ingest_security(
    ticker: str,
    session: Session = Depends(get_session)
):
    """
    Ensure a security exists in the database.

    Args:
        ticker: Security ticker
        session: Database session

    Returns:
        Security details
    """
    try:
        service = DataIngestionService(session)
        security = await service.ensure_security_exists(ticker)

        return {
            "ticker": security.ticker,
            "name": security.name,
            "sector": security.sector,
            "industry": security.industry,
            "country": security.country,
            "status": security.status,
            "message": "Security loaded successfully"
        }

    except Exception as e:
        logger.error(f"Error ingesting security: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
