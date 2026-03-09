"""
API endpoints for factor management.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlmodel import Session, select
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
import logging

from backend.database import get_session
from backend.models.factors import FactorDefinition, CustomFactorScore
from backend.repositories.factor_repo import FactorRepository
from backend.services.factor_calculator import FactorCalculator
from backend.services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)


# Request/Response Models
class FactorDefinitionResponse(BaseModel):
    """Response with factor definition."""
    id: int
    factor_name: str
    factor_type: str
    description: Optional[str] = None
    frequency: str
    is_published: bool
    publication_date: Optional[date] = None
    calculation_formula: Optional[str] = None
    created_at: datetime


class CreateFactorRequest(BaseModel):
    """Request to create a custom factor."""
    factor_name: str
    description: Optional[str] = None
    calculation_formula: str
    frequency: str = "daily"


class FactorScoresResponse(BaseModel):
    """Response with factor scores for a date."""
    factor_id: int
    as_of_date: date
    scores: List[dict]  # [{ticker: str, score: float, percentile: float}, ...]
    count: int


class FactorListResponse(BaseModel):
    """Response with list of factors."""
    total: int
    limit: int
    offset: int
    factors: List[FactorDefinitionResponse]


# Create router
router = APIRouter(prefix="/api/factors", tags=["factors"])


@router.get("", response_model=FactorListResponse)
def list_factors(
    factor_type: Optional[str] = None,
    is_published: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """
    List all available factors (FF5 + custom).

    Args:
        factor_type: Optional filter by type ("fama_french", "custom")
        is_published: Optional filter by publication status
        limit: Number of results to return
        offset: Number of results to skip
        session: Database session

    Returns:
        Paginated list of factors
    """
    try:
        repo = FactorRepository(session)
        factors = repo.list_factors(
            factor_type=factor_type,
            is_published=is_published,
            limit=limit,
            offset=offset
        )

        # Get total count
        query = select(FactorDefinition)
        if factor_type:
            query = query.where(FactorDefinition.factor_type == factor_type)
        if is_published is not None:
            query = query.where(FactorDefinition.is_published == is_published)

        total = len(session.exec(query).all())

        return FactorListResponse(
            total=total,
            limit=limit,
            offset=offset,
            factors=[
                FactorDefinitionResponse(
                    id=f.id,
                    factor_name=f.factor_name,
                    factor_type=f.factor_type,
                    description=f.description,
                    frequency=f.frequency,
                    is_published=f.is_published,
                    publication_date=f.publication_date,
                    calculation_formula=f.calculation_formula,
                    created_at=f.created_at,
                )
                for f in factors
            ],
        )

    except Exception as e:
        logger.error(f"Error listing factors: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{factor_id}", response_model=FactorDefinitionResponse)
def get_factor(
    factor_id: int = Path(..., gt=0),
    session: Session = Depends(get_session)
):
    """
    Get factor details.

    Args:
        factor_id: ID of factor
        session: Database session

    Returns:
        Factor definition details
    """
    try:
        repo = FactorRepository(session)
        factor = repo.get_factor(factor_id)

        if not factor:
            raise HTTPException(status_code=404, detail="Factor not found")

        return FactorDefinitionResponse(
            id=factor.id,
            factor_name=factor.factor_name,
            factor_type=factor.factor_type,
            description=factor.description,
            frequency=factor.frequency,
            is_published=factor.is_published,
            publication_date=factor.publication_date,
            calculation_formula=factor.calculation_formula,
            created_at=factor.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting factor: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("", response_model=FactorDefinitionResponse)
def create_factor(
    request: CreateFactorRequest,
    session: Session = Depends(get_session)
):
    """
    Create custom factor definition.

    Args:
        request: Factor creation request
        session: Database session

    Returns:
        Created factor details
    """
    try:
        repo = FactorRepository(session)

        # Check if factor already exists
        existing = repo.get_factor_by_name(request.factor_name)
        if existing:
            raise HTTPException(status_code=400, detail="Factor with this name already exists")

        # Create factor
        factor = repo.create_factor(
            factor_name=request.factor_name,
            factor_type="custom",
            description=request.description,
            frequency=request.frequency,
            is_published=False,
            calculation_formula=request.calculation_formula,
        )

        return FactorDefinitionResponse(
            id=factor.id,
            factor_name=factor.factor_name,
            factor_type=factor.factor_type,
            description=factor.description,
            frequency=factor.frequency,
            is_published=factor.is_published,
            publication_date=factor.publication_date,
            calculation_formula=factor.calculation_formula,
            created_at=factor.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating factor: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{factor_id}/scores", response_model=FactorScoresResponse)
def get_factor_scores(
    factor_id: int = Path(..., gt=0),
    as_of_date: date = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session)
):
    """
    Get factor scores for universe (paginated).

    Args:
        factor_id: ID of factor
        as_of_date: Optional specific date (defaults to latest)
        limit: Number of results to return
        offset: Number of results to skip
        session: Database session

    Returns:
        Factor scores for the date
    """
    try:
        repo = FactorRepository(session)

        # Check if factor exists
        factor = repo.get_factor(factor_id)
        if not factor:
            raise HTTPException(status_code=404, detail="Factor not found")

        # If no date specified, use today
        if not as_of_date:
            as_of_date = date.today()

        # Get scores for the date
        scores = repo.get_factor_scores_for_date(factor_id, as_of_date)

        # Apply pagination
        paginated_scores = scores[offset:offset + limit]

        # Format response
        scores_list = [
            {
                "ticker": score.ticker,
                "score": float(score.factor_value),
                "percentile": float(score.percentile_rank) if score.percentile_rank else None,
            }
            for score in paginated_scores
        ]

        return FactorScoresResponse(
            factor_id=factor_id,
            as_of_date=as_of_date,
            scores=scores_list,
            count=len(scores),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting factor scores: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.get("/{factor_id}/correlation")
def get_factor_correlation(
    factor_id: int = Path(..., gt=0),
    as_of_date: date = None,
    session: Session = Depends(get_session)
):
    """
    Get factor correlation matrix.

    Args:
        factor_id: ID of factor
        as_of_date: Optional specific date
        session: Database session

    Returns:
        Correlation data
    """
    try:
        repo = FactorRepository(session)

        # Check if factor exists
        factor = repo.get_factor(factor_id)
        if not factor:
            raise HTTPException(status_code=404, detail="Factor not found")

        # Get all factors for correlation matrix
        all_factors = repo.list_factors(limit=1000)

        # This is a simplified response
        # In production, would compute actual correlations
        return {
            "factor_id": factor_id,
            "as_of_date": as_of_date or date.today(),
            "correlations": [],
            "message": "Correlation matrix computation not yet implemented"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting factor correlation: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


@router.post("/fama-french/load")
async def load_fama_french(
    session: Session = Depends(get_session)
):
    """
    Trigger Kenneth French data load.

    Args:
        session: Database session

    Returns:
        Status response
    """
    try:
        service = DataIngestionService(session)
        count = await service.ingest_fama_french_factors()

        return {
            "status": "success",
            "records_ingested": count,
            "message": f"Loaded {count} Fama-French factor records"
        }

    except Exception as e:
        logger.error(f"Error loading Fama-French factors: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")
